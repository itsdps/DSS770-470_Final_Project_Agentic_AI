"""
agent_research.py

ReAct + Function Calling research agent.

How it works (matches class patterns):
  - REACT_PROMPT: a plain string like prompt_react_agent.py from class.
    It tells GPT how to think (Thought / Action / Pause / Observation).
  - Four tool schemas (like 01_function_calling.ipynb from class):
      web_search    — searches the web via DuckDuckGo (ddgs, free, no API key)
      fetch_url     — fetches a specific URL the user provides
      read_document — reads an uploaded file (PDF, txt, etc.)
      ask           — pauses and asks the user a clarifying question
  - GPT decides which tool to call. Your code executes it locally
    and sends the result back as a "tool" role message (Observation).
  - The loop runs up to MAX_STEPS times, then GPT writes the final report.

What stays the same from before:
  - resolve() entry point and company/product branching logic
  - resolve_style_guide() and all reference management
  - Storage calls, _safe_json, confirm() helpers
"""

import json
import os
import re
import textwrap
from pathlib import Path

import httpx                        # still used for fetch_url only
from ddgs import DDGS               # free web search — same lib as class requirements.txt
from dotenv import load_dotenv      # same pattern as class openai_client.py
from openai import OpenAI           # sync client — matches class pattern
from agent_storage import Storage
from agent_utils import confirm

load_dotenv()   # reads OPENAI_API_KEY etc. from .env automatically

# MAX_STEPS: how many tool calls the research agent can make before being forced to answer.
# Lowered from 6 to 3 — in practice 2-3 searches is enough for most companies.
# Lower = faster research phase. Raise it if you find the agent needs more steps
# for obscure companies or events with little online presence.
MAX_STEPS = 3


# ── ReAct system prompt ───────────────────────────────────────────────────────
# Extracted as a plain string so you can edit and iterate on it easily.
# This is your Prompt Engineering artifact for the report — show before/after here.
# Matches the structure of prompt_react_agent.py from class.

REACT_PROMPT = """
You are a market research agent. You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output a final JSON report.

Use Thought to describe your reasoning about what information you need.
Use Action to call one of your available tools — then stop and wait.
Observation will be the result of that tool call.

IMPORTANT:
- You MUST perform at least one tool call before producing a final answer.
- Always base your final report on Observations, not on assumptions.
- If the first search returns thin results (very little specific information),
  do a SECOND search with a different, more specific query before answering.
- For product research: search for the product name + company name together,
  then search for the product name + 'price' or 'flavors' or 'description' separately.
- Do NOT stop after one search if the results are vague or generic.
- If a search returns nothing and no document is provided, use the ask tool.
- If the user provides a URL, use fetch_url rather than web_search.
- If a document was uploaded, use read_document before searching the web.

Your available actions are:

1. web_search: <query>
   Search the web for publicly available information about a company or product.
   Example: web_search: Rita's Water Ice brand overview history products

2. fetch_url: <url>
   Fetch the content of a specific URL provided by the user.
   Example: fetch_url: https://www.ritaswaterice.com/about

3. read_document: <filename>
   Read an uploaded document (PDF, txt, docx) for product or event info.
   Example: read_document: kiwi_melon_launch_brief.pdf

4. ask: <question>
   Ask the user a clarifying question when you need more information.
   Example: ask: Could you provide a website or document for this product?

Example session:
Thought: I need to find information about Rita's Water Ice to write a company report.
Action: web_search: Rita's Water Ice company overview history
PAUSE

Observation: [Rita's Italian Ice] Founded in 1984 by Bob Tumolo in Philadelphia...

Thought: I have enough information to write the company report.
Answer: { ... json report ... }
""".strip()


# ── Report-writing prompts ────────────────────────────────────────────────────
# Separated from the ReAct loop so they are easy to find and improve.
# These are also good candidates for your Prompt Engineering iteration log.

COMPANY_REPORT_PROMPT = """
STOP the ReAct loop. Do NOT output Thought, Action, or PAUSE.
Your research is complete. Now write the final report.

You are a market research analyst. Using everything you found in this conversation,
write a company report for "{company_name}" as a JSON object with these keys:
  company_name, also_known_as (list), industry, headquarters, founded,
  main_products (list), competitors (list), target_market,
  brand_voice, notable_facts (list),
  logo_description (string describing the logo: colors, shape, text style, e.g.
    "White script 'Rita\'s' lettering on a green rectangular background with red accent cup icon"
    — use null if logo cannot be determined from search results)

Rules:
- Respond ONLY with valid JSON. No markdown fences, no explanation, no Thought/Action lines.
- Use the search results from this conversation as your primary source.
- You may use well-known general knowledge to fill gaps for widely known companies.
- For logo_description: describe what you actually found. Do NOT invent a logo if unsure — use null.
- If a field is genuinely unknown and cannot be reasonably inferred, use null.
"""

PRODUCT_REPORT_PROMPT = """
STOP the ReAct loop. Do NOT output Thought, Action, or PAUSE.
Your research is complete. Now write the final report.

You are a product marketing analyst. Using everything you found in this conversation,
write a product report for "{product_name}" as a JSON object with these keys:
  product_name, product_description, price_range, target_market,
  key_features (list), theme, season_availability,
  flavors_or_variants (list if applicable)

Company context:
{company_context}

Rules:
- Respond ONLY with valid JSON. No markdown fences, no explanation, no Thought/Action lines.
- Use the search results from this conversation as your primary source.
- You may use well-known general knowledge to fill gaps for widely known products.
- If a field is genuinely unknown, use null.
"""


# ── Style guide touch-up prompt ──────────────────────────────────────────────
# Used when references changed and user wants a light update rather than
# full regenerate. Blends new reference insights into the existing style guide.
# Future improvement: replace the numbered menu that triggers this with a
# free-form input classified by GPT (same sentiment_analysis pattern from class).

STYLE_TOUCHUP_PROMPT = """
You are a creative brand strategist updating an existing social media style guide.
Make LIGHT adjustments only — preserve the core vibe and tone, just blend in
insights from the new reference screenshots described below.

Existing style guide:
{existing_guide}

New style insights from updated references:
{vision_notes}

Return the updated style guide as a JSON object with the same keys.
Respond ONLY with valid JSON. No markdown fences.
""".strip()


# ── Official name lookup prompt ───────────────────────────────────────────────
# Used to resolve short/informal names like "Rita's" to official names like
# "Rita's Water Ice" before any folder creation or searching happens.
# Keeping the official name as the canonical identifier prevents duplicate
# folders and improves search quality (official name → better results).

OFFICIAL_NAME_PROMPT = """
Based on the search results below, what is the full official name of the company
the user is referring to when they say "{input_name}"?

Search results:
{search_results}

Rules:
- Return ONLY the official company name as a plain string, nothing else.
- If you cannot determine the official name from the results, return "{input_name}" unchanged.
- Do not include quotes, punctuation, or explanation.
""".strip()


class ResearchAgent:
    def __init__(self, storage: Storage, openai_key: str):
        self.storage = storage
        self.client  = OpenAI(api_key=openai_key)   # sync, like class pattern

        # Tool schemas — same structure as 01_function_calling.ipynb from class
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for publicly available info about a company or product.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_url",
                    "description": "Fetch the full content of a specific URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to fetch"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_document",
                    "description": "Read an uploaded document file (PDF, txt) for product or event info.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Name of the uploaded file"}
                        },
                        "required": ["filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ask",
                    "description": "Ask the user a clarifying question when more info is needed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "The question to ask the user"}
                        },
                        "required": ["question"]
                    }
                }
            },
        ]

    # ── Main entry point ──────────────────────────────────────────────────────

    def _resolve_official_name(self, input_name: str,
                                product_name: str = "") -> str:
        """
        Resolves a short or informal company name to its official name.

        Flow:
          1. Check for exact match in existing company folders — use it if found
          2. Check for fuzzy matches in existing folders — ask user if it's the same
          3. If no match, search the web for the official name
          4. Ask user to confirm the found name before using it
          5. Return the confirmed official name (used for all folder creation + searching)

        This prevents duplicate folders (Rita's vs Rita's Water Ice) and
        improves search quality since official names return better results.
        """
        # ── Step 1: Exact match ───────────────────────────────────────────────
        if self.storage.company_exists(input_name):
            return input_name

        # ── Step 2: Fuzzy match against existing companies ────────────────────
        # Uses difflib.SequenceMatcher instead of simple substring containment.
        # Substring check misses partial overlaps like "Rita's Italian Ice" vs
        # "Rita's Water Ice". SequenceMatcher gives a 0-1 similarity ratio —
        # 0.6 threshold catches close variants without being too aggressive.
        # Documented prompt engineering improvement — see Slide 4.
        from difflib import SequenceMatcher
        existing = self.storage.list_companies()
        if existing:
            input_lower = input_name.lower()
            fuzzy_matches = [
                c for c in existing
                if (
                    # Similarity score — catches variants of similar length
                    SequenceMatcher(None, input_lower, c.lower()).ratio() > 0.6
                    or
                    # Substring containment — catches short names like "Rita's"
                    # being contained in "Rita's Water Ice" or vice versa
                    input_lower in c.lower() or c.lower() in input_lower
                )
            ]
            if fuzzy_matches:
                for match in fuzzy_matches:
                    print(f"\n\U0001f50d I found an existing company that looks similar: [{match}]")
                    answer = confirm(
                        f'Is "{input_name}" the same company as [{match}]? (Y/n)'
                    )
                    if answer:
                        print(f"  \u2705 Using existing company [{match}]")
                        return match

        # ── Step 3: Search web for official name ──────────────────────────────
        # Use product name as context if available to anchor the search
        hint = f" {product_name}" if product_name else ""
        print(f"\n\U0001f50d Looking up official name for [{input_name}]\u2026")
        search_results = self._tool_web_search(
            f"{input_name}{hint} official company name"
        )

        if not search_results or search_results.startswith("Web search error"):
            # Nothing found — use input as-is
            return input_name

        # Ask GPT to extract the official name from search results
        prompt = OFFICIAL_NAME_PROMPT.format(
            input_name=input_name,
            search_results=search_results[:2000],
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        official_name = resp.choices[0].message.content.strip().strip('"').strip("'")

        # ── Step 4: Confirm with user ─────────────────────────────────────────
        if official_name.lower() != input_name.lower():
            print(f"\n\U0001f50d I found the official company name: [{official_name}]")
            answer = confirm("Is that the company you meant? (Y/n)")
            if not answer:
                # User says no — ask them to type the correct name
                official_name = input("  Please enter the correct company name: ").strip()
                if not official_name:
                    official_name = input_name
        else:
            print(f"\n\U0001f50d Using company name: [{official_name}]")

        # ── Step 5: Check for duplicate with the resolved name ────────────────
        if self.storage.company_exists(official_name):
            print(f"  ✅ Found existing company report for [{official_name}]")

        return official_name

    def _resolve_official_product_name(self, company_name: str,
                                        input_name: str) -> str:
        """
        Resolves a short or informal product name to its official name.
        Mirrors _resolve_official_name() but checks existing product reports
        for this company rather than company folders.

        Examples:
          "Melon" -> fuzzy matches "Kiwi Melon" (score ~0.67) -> asks user
          "Cherry" -> fuzzy matches "Cherry Italian Ice" -> asks user
        """
        from difflib import SequenceMatcher

        # ── Step 1: Exact match ───────────────────────────────────────────────
        if self.storage.product_exists(company_name, input_name):
            return input_name

        # ── Step 2: Fuzzy match against existing products for this company ────
        products_dir = self.storage.products_dir(company_name)
        if products_dir.exists():
            existing_products = [
                f.stem.replace(" Product Report", "")
                for f in products_dir.glob("*.json")
            ]
            input_lower = input_name.lower()
            fuzzy_matches = [
                p for p in existing_products
                if (
                    SequenceMatcher(None, input_lower, p.lower()).ratio() > 0.6
                    or
                    input_lower in p.lower() or p.lower() in input_lower
                )
            ]
            if fuzzy_matches:
                for match in fuzzy_matches:
                    print(f"\n\U0001f50d I found an existing product that looks similar: [{match}]")
                    answer = confirm(
                        f'Is "{input_name}" the same product as [{match}]? (Y/n)'
                    )
                    if answer:
                        print(f"  ✅ Using existing product [{match}]")
                        return match

        # ── Step 3: No match — use input as-is (new product) ─────────────────
        return input_name

    def resolve(self, company_name: str, product_name: str,
                provided_url: str = None, uploaded_file: str = None,
                company_url: str = None, company_file: str = None,
                product_url: str = None, product_file: str = None,
                skip_name_resolution: bool = False):
        """
        Return (company_report, product_report, company_name, product_name).

        Returns the canonical company_name and product_name alongside the reports
        so the caller (notebook / demo.py) can update the receipt with the
        official names rather than keeping the user's original input.

        Args:
            company_name:  Company name from the user's request (may be informal)
            product_name:  Product or event name from the user's request
            provided_url:  Optional URL the user gave for the company or product
            uploaded_file: Optional path to an uploaded document
        """
        # ── Resolve official names (skip if already done by caller) ───────────
        if not skip_name_resolution:
            company_name = self._resolve_official_name(company_name, product_name)
            product_name = self._resolve_official_product_name(company_name, product_name)

        has_company = self.storage.company_exists(company_name)
        has_product = self.storage.product_exists(company_name, product_name)

        # Announce what we found
        if has_company and has_product:
            msg = (f"Just to verify — I found an existing company [{company_name}] "
                   f"and product [{product_name}]. I'll use the existing reports.")
        elif has_company and not has_product:
            msg = (f"Just to verify — I found company [{company_name}] but "
                   f"[{product_name}] is a new product. I'll research and create a report.")
        else:
            msg = (f"Just to verify — [{company_name}] is a new company and "
                   f"[{product_name}] is a new product. I'll research both.")

        print(f"\n🔍 {msg}")
        ok = confirm("Is this correct? (Y/n)")
        if not ok:
            company_name = input("Enter the correct company name: ").strip() or company_name
            product_name = input("Enter the correct product name: ").strip() or product_name
            has_company  = self.storage.company_exists(company_name)
            has_product  = self.storage.product_exists(company_name, product_name)

        # ── Company report ────────────────────────────────────────────────────
        if has_company:
            company_report = self.storage.load_company_report(company_name)
            print(f"  ✅ Loaded existing company report for [{company_name}]")
        else:
            # Use company-specific ref if given, fall back to generic
            company_report = self._create_company_report(
                company_name,
                provided_url=company_url or provided_url,
                uploaded_file=company_file or uploaded_file,
            )

        # ── Product report ────────────────────────────────────────────────────
        if has_product:
            product_report = self.storage.load_product_report(company_name, product_name)
            print(f"  ✅ Loaded existing product report for [{product_name}]")
        else:
            # Use product-specific ref if given, fall back to generic
            product_report = self._create_product_report(
                company_name, product_name, company_report,
                provided_url=product_url or provided_url,
                uploaded_file=product_file or uploaded_file,
            )

        return company_report, product_report, company_name, product_name

    # ── Style Guide ───────────────────────────────────────────────────────────

    def resolve_style_guide(self, company_report: dict, product_report: dict,
                            reference_images: list | None = None,
                            update_mode: str = "leave") -> dict:
        """
        Generates or loads the style guide.
        update_mode controls what happens when references changed and a guide exists:
          "leave"      — load and return existing guide unchanged (default)
          "touchup"    — light blend of new references into existing guide
          "regenerate" — full rewrite using all current references
        Called AFTER references are collected so GPT sees them during generation.
        """
        company = company_report.get("company_name", "Unknown")
        product = product_report.get("product_name", "Unknown")

        existing_guides = self.storage.list_style_guides(company)
        has_guide       = self.storage.style_guide_exists(company, product)

        if has_guide:
            existing = self.storage.load_style_guide(company, product)

            if update_mode == "leave":
                print(f"\n🎨 Loaded existing style guide for [{product}].")
                return existing

            elif update_mode == "touchup" and reference_images:
                print(f"\n🎨 Touching up style guide for [{product}] with new references…")
                try:
                    vision_notes = self._describe_references_for_style(reference_images)
                    prompt = STYLE_TOUCHUP_PROMPT.format(
                        existing_guide=json.dumps(existing, indent=2)[:2000],
                        vision_notes=vision_notes,
                    )
                    updated = _safe_json(self._gpt(prompt))
                    self.storage.save_style_guide(company, product, updated)
                    print(f"  ✅ Style guide touched up.")
                    return updated
                except Exception as e:
                    print(f"  ⚠️  Touch up failed ({e}) — using existing guide.")
                    return existing

            elif update_mode == "regenerate":
                print(f"\n🎨 Regenerating style guide for [{product}]…")
                style_guide = self._create_style_guide(
                    company_report, product_report,
                    base_guide=existing,
                    reference_images=reference_images,
                )
                self.storage.save_style_guide(company, product, style_guide)
                return style_guide

            else:
                return existing

        elif existing_guides:
            print(f"\n🎨 No style guide for [{product}] yet.")
            print(f"  Existing style guides: {', '.join(existing_guides)}")
            base_guide = None
            if confirm("Would you like to use one as a base? (Y/n)"):
                choice = input("  Enter name (or part of it): ").strip()
                match  = next((g for g in existing_guides if choice.lower() in g.lower()), None)
                if match:
                    base_guide = self.storage.load_style_guide(company, match)
                    print(f"  ✅ Using [{match}] as base.")

                    # Ask if they want to copy the reference screenshots too.
                    # Default yes — most of the time you want the same brand
                    # references to carry over to the new product's style.
                    base_refs = self.storage.list_references(company, match)
                    if base_refs:
                        print(f"  Found {len(base_refs)} reference screenshot(s) in [{match}]:")
                        for r in base_refs:
                            print(f"    • {r.name}")
                        copy_refs = confirm(
                            "  Copy these references to the new style guide? (Y/n)"
                        )
                        if copy_refs:
                            import shutil
                            dest_dir = self.storage.references_dir(company, product)
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            for ref in base_refs:
                                dest = dest_dir / ref.name
                                if not dest.exists():
                                    shutil.copy2(ref, dest)
                            print(f"  ✅ Copied {len(base_refs)} reference(s) to [{product}].")
                        else:
                            print("  Skipping references — starting fresh for this product.")
                    else:
                        print(f"  No references found in [{match}] to copy.")
                else:
                    print("  No matching guide found, creating fresh.")
            style_guide = self._create_style_guide(company_report, product_report, base_guide,
                                                    reference_images=reference_images)

        else:
            print(f"\n🎨 No style guides exist yet for [{company}]. Creating fresh.")
            refs        = self._ask_for_references()
            style_guide = self._create_style_guide(
                company_report, product_report, base_guide=None, extra_refs=refs,
                reference_images=reference_images
            )

        self.storage.save_style_guide(company, product, style_guide)
        return style_guide

    # ── ReAct research loop ───────────────────────────────────────────────────

    def _run_react_loop(self, user_query: str,
                        provided_url: str = None,
                        uploaded_file: str = None) -> str:
        """
        Core ReAct + function calling loop.
        Mirrors the pattern from 01_function_calling.ipynb in class:
          1. Send messages + tools to GPT
          2. If GPT requests a tool, execute it locally and send result back
          3. Repeat until GPT produces a plain text Answer (no tool call)

        Returns the final Answer string (raw JSON report text from GPT).

        Args:
            user_query:    What we want GPT to research and write
            provided_url:  URL to hint GPT toward fetch_url first
            uploaded_file: Filename to hint GPT toward read_document first
        """
        # Build the opening user message, adding hints if user gave us extra info
        hints = []
        if provided_url:
            hints.append(f"The user has provided this URL for reference: {provided_url}")
        if uploaded_file:
            hints.append(f"The user has uploaded a document: {uploaded_file}")
        hint_block = ("\n\n" + "\n".join(hints)) if hints else ""

        messages = [
            {"role": "system", "content": REACT_PROMPT},
            {"role": "user",   "content": user_query + hint_block},
        ]

        observations = []   # collected for report writing later

        for step in range(MAX_STEPS):
            response = self.client.chat.completions.create(
                # gpt-4o-mini chosen here deliberately over gpt-4o:
                # The research loop is doing factual retrieval and tool routing —
                # not creative writing. gpt-4o-mini handles this just as well
                # at a fraction of the cost and roughly 2x faster per call.
                # gpt-4o is reserved for report writing (_gpt()) where
                # structured JSON quality and reasoning depth matter more.
                model="gpt-4o-mini",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            # ── GPT wants to call a tool (Action step) ────────────────────────
            if msg.tool_calls:
                messages.append({
                    "role":       "assistant",
                    "content":    msg.content or "",
                    "tool_calls": msg.tool_calls,
                })

                # Execute each requested tool locally — same pattern as class notebook
                for call in msg.tool_calls:
                    fn_name = call.function.name
                    args    = json.loads(call.function.arguments or "{}")

                    print(f"  💭 Thought logged")
                    print(f"  🔧 Action: {fn_name}({args})")

                    # ── Dispatch to the right local function ──────────────────
                    if fn_name == "web_search":
                        result = self._tool_web_search(args["query"])
                    elif fn_name == "fetch_url":
                        result = self._tool_fetch_url(args["url"])
                    elif fn_name == "read_document":
                        result = self._tool_read_document(args["filename"])
                    elif fn_name == "ask":
                        result = self._tool_ask(args["question"])
                    else:
                        result = f"Unknown tool: {fn_name}"

                    observations.append(f"[{fn_name}] {result[:2000]}")
                    print(f"  👁️  Observation: {result[:120]}...")

                    # Send the result back as the Observation
                    # Same "tool" role message structure as class notebook
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": call.id,
                        "content":      result,
                    })

            # ── GPT produced a final Answer (no tool call) ────────────────────
            else:
                print(f"  ✅ Research complete ({step + 1} steps)")
                return messages, observations

        # Fallback if we hit MAX_STEPS without a clean answer
        print(f"  ⚠️  Max steps ({MAX_STEPS}) reached — using collected observations.")
        return messages, observations

    # ── Private: create reports using the ReAct loop ─────────────────────────

    def _create_company_report(self, company_name: str,
                                provided_url: str = None,
                                uploaded_file: str = None) -> dict:
        print(f"\n🔬 Researching company [{company_name}]…")

        user_query = (
            f"Research the company '{company_name}' and find specific information for: "
            f"(1) industry/sector, (2) headquarters city and state, (3) founding year, "
            f"(4) main products or services, (5) key competitors, (6) target market, "
            f"(7) brand voice and tone, "
            f"(8) logo description — colors, shape, text style, any iconic elements. "
            f"Search for '{company_name}' directly and also search '{company_name} logo' "
            f"to find logo details."
        )

        messages, _ = self._run_react_loop(user_query, provided_url, uploaded_file)

        # Write the report as a follow-up in the SAME conversation so GPT
        # has full access to all search results it just retrieved.
        # No tools passed here so GPT cannot call any — plain text JSON response only.
        print(f"  🤖 Writing company report…")
        report_instruction = COMPANY_REPORT_PROMPT.format(company_name=company_name)
        messages.append({"role": "user", "content": report_instruction})

        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
        )
        raw    = resp.choices[0].message.content.strip()
        report = _safe_json(raw)
        report["company_name"] = company_name
        self.storage.save_company_report(company_name, report)
        return report

    def _create_product_report(self, company_name: str, product_name: str,
                                company_report: dict,
                                provided_url: str = None,
                                uploaded_file: str = None) -> dict:
        print(f"\n🔬 Researching product/event [{product_name}]…")

        user_query = (
            f"Research the product or event '{product_name}' by '{company_name}' "
            f"and gather enough information to write a product report covering: "
            f"description, price range, target market, key features, theme, "
            f"seasonal availability, and any variants or flavors."
        )

        messages, _ = self._run_react_loop(user_query, provided_url, uploaded_file)

        # Write the report as a follow-up in the SAME conversation so GPT
        # has full access to all the search results it just retrieved.
        # No tools passed here so GPT cannot call any — plain text JSON response only.
        print(f"  🤖 Writing product report…")
        report_instruction = PRODUCT_REPORT_PROMPT.format(
            product_name=product_name,
            company_context=json.dumps(company_report, indent=2)[:1500],
        )
        messages.append({"role": "user", "content": report_instruction})

        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
        )
        raw    = resp.choices[0].message.content.strip()
        report = _safe_json(raw)
        report["product_name"] = product_name

        # ── Null field check — if more than 1 field is null, ask user for help ──
        # Rather than auto-searching again, we ask the user for a URL or document
        # so they stay in control and can provide the most accurate source.
        expected_fields = ["product_description", "price_range", "target_market",
                           "key_features", "theme", "season_availability",
                           "flavors_or_variants"]
        null_count = sum(1 for f in expected_fields if not report.get(f))
        if null_count > 1:
            print(f"\n  ⚠️  Product report has {null_count} empty fields after research.")
            print(f"  Missing: {[f for f in expected_fields if not report.get(f)]}")
            followup = input(
                f"  Do you have a URL or file with more info about [{product_name}]? "
                f"(paste it, or Enter to continue with what we have): "
            ).strip().strip('"').strip("'")
            if followup:
                # Run one more pass with the user-provided source
                extra_url  = followup if followup.startswith("http") else None
                extra_file = followup if not followup.startswith("http") else None
                print(f"  🔍 Researching with additional source…")
                followup_result = (
                    self._tool_fetch_url(extra_url) if extra_url
                    else self._tool_read_document(extra_file)
                )
                if followup_result:
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content":
                        f"Additional information from user-provided source:\n"
                        f"{followup_result[:2000]}\n\n"
                        f"Rewrite the product report using all information gathered. "
                        f"Return ONLY valid JSON."
                    })
                    resp2 = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        temperature=0.2,
                    )
                    raw2    = resp2.choices[0].message.content.strip()
                    report2 = _safe_json(raw2)
                    if report2 and (report2.get("product_description") or report2.get("product_name")):
                        report  = report2
                        print(f"  ✅ Report updated with additional source.")

        report["product_name"] = product_name
        self.storage.save_product_report(company_name, product_name, report)
        return report

    def _create_style_guide(self, company_report: dict, product_report: dict,
                             base_guide: dict | None,
                             extra_refs: list | None = None,
                             reference_images: list | None = None) -> dict:
        """
        Generates a style guide. If reference_images are provided, uses GPT Vision
        to describe their style first, then folds that description into the prompt.
        This means the style guide is directly informed by real example posts.
        """
        print(f"  🤖 Generating style guide…")

        # Get Vision description of reference screenshots if provided
        vision_style = ""
        if reference_images:
            print(f"  👁️  Analyzing {len(reference_images)} style reference(s) via Vision…")
            try:
                vision_style = self._describe_references_for_style(reference_images)
            except Exception as e:
                print(f"  ⚠️  Vision analysis failed: {e}")

        vision_block = f"\nStyle insights from reference screenshots:\n{vision_style}" if vision_style else ""

        prompt = textwrap.dedent(f"""
            You are a creative brand strategist. Using the company and product info below,
            create a social media style guide as a JSON object with these keys:
              vibe (2-4 words), tone, color_palette (list of 3-5 hex codes),
              typography_feel, emoji_usage, caption_structure,
              visual_themes (list), do_list (list), dont_list (list),
              references (list of {{url, description}})

            Do NOT include specific company or product facts — only style and vibe.
            Base guide to build from (if any): {json.dumps(base_guide or {}, indent=2)[:1000]}
            {vision_block}

            Company: {json.dumps(company_report, indent=2)[:1200]}
            Product: {json.dumps(product_report, indent=2)[:1200]}

            Respond ONLY with valid JSON. No markdown fences.
        """)
        return _safe_json(self._gpt(prompt))

    def _describe_references_for_style(self, reference_images: list) -> str:
        """
        Passes reference screenshots to GPT Vision and gets a style description.
        Used during style guide creation so the guide reflects real example posts.
        Mirrors _describe_images_for_reference() in agent_base.py but focused
        on extracting style/tone/humor patterns rather than visual aesthetics.
        """
        content = [
            {
                "type": "text",
                "text": (
                    "Look at these social media post screenshots and describe their style "
                    "in 4-5 sentences. Focus on: tone (funny/serious/inspirational), "
                    "caption structure, use of emojis, hashtag style, call-to-action approach, "
                    "and overall energy. This will be used to create a brand style guide."
                )
            }
        ]
        for path in reference_images[:3]:
            try:
                with open(path, "rb") as f:
                    import base64
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                mime = "image/png" if str(path).endswith(".png") else "image/jpeg"
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encoded}"}
                })
            except Exception as e:
                print(f"  ⚠️  Could not load {path}: {e}")

        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()

    # ── Tool implementations (called locally when GPT requests them) ──────────
    # Same pattern as the local get_current_weather() function in class notebook

    def _tool_web_search(self, query: str) -> str:
        """
        Search the web via DuckDuckGo (ddgs).
        Free, no API key needed — same library as class requirements.txt.
        Returns plain text snippets as the Observation.
        """
        try:
            with DDGS() as ddgs:
                results  = ddgs.text(query, max_results=5)
                snippets = [
                    f"[{r.get('title', '')}] {r.get('body', '')}"
                    for r in results
                ]
            return "\n".join(snippets) or "No results found."
        except Exception as e:
            return f"Web search error: {e}"

    def _tool_fetch_url(self, url: str) -> str:
        """Fetch a specific URL and return its text content as the Observation."""
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=20)
            return resp.text[:5000]
        except Exception as e:
            return f"Could not fetch {url}: {e}"

    def _tool_read_document(self, filename: str) -> str:
        """
        Read an uploaded document file and return its text as the Observation.
        Supports .txt and .pdf (requires pypdf for PDF).
        The file is expected to be in the same folder as this script,
        or in a standard uploads location.
        """
        # Look in the current folder and one level up
        search_paths = [
            Path(filename),
            Path(".") / filename,
            Path("uploads") / filename,
        ]
        found = next((p for p in search_paths if p.exists()), None)

        if not found:
            return (f"Document '{filename}' not found. "
                    f"Please make sure the file is in the project folder.")

        suffix = found.suffix.lower()
        try:
            if suffix == ".txt":
                return found.read_text(encoding="utf-8")[:5000]
            elif suffix == ".pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(found))
                    text   = "\n".join(page.extract_text() or "" for page in reader.pages)
                    return text[:5000]
                except ImportError:
                    return "PDF reading requires pypdf. Run: pip install pypdf"
            else:
                # Fallback: try reading as plain text
                return found.read_text(encoding="utf-8", errors="ignore")[:5000]
        except Exception as e:
            return f"Error reading {filename}: {e}"

    def _tool_ask(self, question: str) -> str:
        """
        Pause the loop and ask the user a clarifying question.
        The user's answer becomes the Observation sent back to GPT.
        """
        print(f"\n  ❓ Agent needs more info:")
        answer = input(f"  {question}\n  Your answer: ").strip()
        return answer if answer else "No answer provided."

    # ── Reference management (unchanged from original) ────────────────────────

    def _offer_reference_update(self, style_guide: dict, label: str) -> dict:
        """
        Show existing style reference screenshots and let user add/remove them.
        References are stored as screenshots in Images/{Product}/references/
        rather than URLs — use the image selection step in the notebook or demo.py
        to manage them. This method just shows what exists and returns unchanged.
        """
        # References are now managed via the references/ folder in Step 7.5
        # Just show what's there and return — no URL prompts
        print(f"\n  Style references are managed in the Images/{{product}}/references/ folder.")
        print(f"  Add screenshots there during the image selection step (Step 7.5).")
        return style_guide

    def _ask_for_references(self) -> list:
        """
        References are now screenshot files in Images/{Product}/references/
        rather than URLs. Users add them via the image selection step.
        This method is kept for compatibility but does nothing.
        """
        print("  Style references are managed as screenshots in the image selection step.")
        return []

    # ── Shared GPT call ───────────────────────────────────────────────────────

    def _gpt(self, prompt: str, model: str = "gpt-4o") -> str:
        """
        Simple single-turn GPT call for report writing.
        Matches generate_text() pattern from class's openai_client.py.
        """
        resp = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()


# ── Module-level helper ───────────────────────────────────────────────────────

def _safe_json(text: str) -> dict:
    """Parse JSON even if GPT wraps it in markdown fences."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
