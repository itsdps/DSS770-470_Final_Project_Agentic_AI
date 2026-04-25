"""
agent_research.py
ReAct-style agent that:
  • Looks up company / product in local storage
  • Web-searches missing info via Serper
  • Calls OpenAI to write Company Report, Product Report, Style Guide
  • Handles user confirmation at each step
"""

import json, re, textwrap
import httpx
from openai import AsyncOpenAI
from agent_storage import Storage
from agent_utils import confirm, print_section


class ResearchAgent:
    def __init__(self, storage: Storage, openai_key: str, serper_key: str):
        self.storage   = storage
        self.client    = AsyncOpenAI(api_key=openai_key)
        self.serper_key = serper_key

    # ── Main entry point ──────────────────────────────────────────────────────

    async def resolve(self, company_name: str, product_name: str):
        """Return (company_report, product_report), creating them if needed."""
        has_company = self.storage.company_exists(company_name)
        has_product = self.storage.product_exists(company_name, product_name)

        # ── Announce state ────────────────────────────────────────────────────
        if has_company and has_product:
            msg = (f"Just to verify — I found an existing company [{company_name}] "
                   f"and product [{product_name}]. I'll use the existing reports.")
        elif has_company and not has_product:
            msg = (f"Just to verify — I found company [{company_name}] but "
                   f"[{product_name}] is a new product. I'll create a product report.")
        else:
            msg = (f"Just to verify — [{company_name}] is a new company and "
                   f"[{product_name}] is a new product. I'll create both reports.")

        print(f"\n🔍 {msg}")
        ok = confirm("Is this correct? (Y/n)")
        if not ok:
            company_name = input("Enter the correct company name: ").strip() or company_name
            product_name = input("Enter the correct product name: ").strip() or product_name
            # Re-check after correction
            has_company = self.storage.company_exists(company_name)
            has_product = self.storage.product_exists(company_name, product_name)

        # ── Build company report ──────────────────────────────────────────────
        if has_company:
            company_report = self.storage.load_company_report(company_name)
            print(f"  ✅ Loaded existing company report for [{company_name}]")
        else:
            company_report = await self._create_company_report(company_name)

        # ── Build product report ──────────────────────────────────────────────
        if has_product:
            product_report = self.storage.load_product_report(company_name, product_name)
            print(f"  ✅ Loaded existing product report for [{product_name}]")
        else:
            product_report = await self._create_product_report(
                company_name, product_name, company_report
            )

        return company_report, product_report

    # ── Style Guide ───────────────────────────────────────────────────────────

    async def resolve_style_guide(self, company_report: dict, product_report: dict) -> dict:
        company = company_report.get("company_name", "Unknown")
        product = product_report.get("product_name", "Unknown")

        existing_guides = self.storage.list_style_guides(company)
        has_guide = self.storage.style_guide_exists(company, product)

        if has_guide:
            print(f"\n🎨 Found existing style guide for [{product}].")
            style_guide = self.storage.load_style_guide(company, product)
            style_guide = await self._offer_reference_update(style_guide, label="existing")
        elif existing_guides:
            print(f"\n🎨 No style guide for [{product}] yet.")
            print(f"  Existing style guides: {', '.join(existing_guides)}")
            use_base = confirm(f"Would you like to use one as a base? (Y/n)")
            base_guide = None
            if use_base:
                print("  Enter the name (or part of it) of the guide to use as base:")
                choice = input("  > ").strip()
                match = next((g for g in existing_guides if choice.lower() in g.lower()), None)
                if match:
                    base_guide = self.storage.load_style_guide(company, match)
                    print(f"  ✅ Using [{match}] as base.")
                    base_guide = await self._offer_reference_update(base_guide, label="base")
                else:
                    print("  No matching guide found, creating fresh.")
            style_guide = await self._create_style_guide(company_report, product_report, base_guide)
        else:
            print(f"\n🎨 No style guides exist yet for [{company}]. Creating fresh.")
            refs = self._ask_for_references()
            style_guide = await self._create_style_guide(
                company_report, product_report, base_guide=None, extra_refs=refs
            )

        self.storage.save_style_guide(company, product, style_guide)
        return style_guide

    # ── Private: create reports ───────────────────────────────────────────────

    async def _create_company_report(self, company_name: str) -> dict:
        print(f"\n🌐 Searching the web for [{company_name}]…")
        search_results = await self._web_search(f"{company_name} company overview products")

        if not search_results:
            print("  ⚠️  Web search returned nothing. Please provide a URL for reference.")
            url = input("  URL (or press Enter to skip): ").strip()
            search_results = await self._fetch_url(url) if url else ""

        print(f"  🤖 Generating company report…")
        prompt = textwrap.dedent(f"""
            You are a market research analyst. Using the information below, write a thorough
            company report for "{company_name}" as a JSON object with these keys:
              company_name, also_known_as (list), industry, headquarters, founded,
              main_products (list), competitors (list), target_market,
              brand_voice, notable_facts (list)

            Web search results:
            {search_results[:4000]}

            Respond ONLY with valid JSON, no markdown fences.
        """)
        report = await self._gpt(prompt)
        report = _safe_json(report)
        report["company_name"] = company_name
        self.storage.save_company_report(company_name, report)
        return report

    async def _create_product_report(self, company_name: str, product_name: str,
                                     company_report: dict) -> dict:
        print(f"\n🌐 Searching the web for [{company_name} {product_name}]…")
        search_results = await self._web_search(f"{company_name} {product_name} product details")

        if not search_results:
            print("  ⚠️  Nothing found. Please provide a URL or press Enter to skip.")
            url = input("  URL: ").strip()
            search_results = await self._fetch_url(url) if url else ""

        print(f"  🤖 Generating product report…")
        prompt = textwrap.dedent(f"""
            You are a product marketing analyst. Using the company context and web results below,
            write a product report for "{product_name}" by "{company_name}" as a JSON object
            with these keys:
              product_name, product_description, price_range, target_market,
              key_features (list), theme, season_availability, flavors_or_variants (list if applicable)

            Company context:
            {json.dumps(company_report, indent=2)[:1500]}

            Web search results:
            {search_results[:3000]}

            Respond ONLY with valid JSON, no markdown fences.
        """)
        report = await self._gpt(prompt)
        report = _safe_json(report)
        report["product_name"] = product_name
        self.storage.save_product_report(company_name, product_name, report)
        return report

    async def _create_style_guide(self, company_report: dict, product_report: dict,
                                  base_guide: dict | None, extra_refs: list | None = None) -> dict:
        print(f"  🤖 Generating style guide…")
        refs_text = json.dumps(extra_refs or [], indent=2)
        base_text = json.dumps(base_guide or {}, indent=2)

        prompt = textwrap.dedent(f"""
            You are a creative brand strategist. Using the company and product info below,
            create a social media style guide as a JSON object with these keys:
              vibe (2–4 words), tone, color_palette (list of 3–5 hex codes),
              typography_feel, emoji_usage, caption_structure,
              visual_themes (list), do_list (list), dont_list (list),
              references (list of {{url, description}})

            Do NOT include specific company or product facts — only style/vibe.
            Base guide to build from (if any): {base_text[:1000]}
            Reference posts provided: {refs_text}

            Company: {json.dumps(company_report, indent=2)[:1200]}
            Product: {json.dumps(product_report, indent=2)[:1200]}

            Respond ONLY with valid JSON, no markdown fences.
        """)
        guide = await self._gpt(prompt)
        return _safe_json(guide)

    # ── Private: reference management ────────────────────────────────────────

    async def _offer_reference_update(self, style_guide: dict, label: str) -> dict:
        refs = style_guide.get("references", [])
        print(f"\n  Current references in {label} style guide:")
        if refs:
            for i, r in enumerate(refs, 1):
                print(f"    {i}. {r.get('url')} — {r.get('description','')}")
        else:
            print("    (none)")

        print("  You can: add <URL>, remove <number>, or press Enter when done.")
        while True:
            cmd = input("  > ").strip()
            if not cmd:
                break
            if cmd.lower().startswith("add "):
                url = cmd[4:].strip()
                desc = input(f"    Short description for {url}: ").strip()
                refs.append({"url": url, "description": desc})
                print(f"    ✅ Added.")
            elif cmd.lower().startswith("remove "):
                idx = int(cmd.split()[1]) - 1
                if 0 <= idx < len(refs):
                    removed = refs.pop(idx)
                    print(f"    🗑️  Removed: {removed['url']}")
                else:
                    print("    ❌ Invalid number.")
            else:
                print("    Commands: add <URL> | remove <number> | Enter to finish")

        style_guide["references"] = refs
        return style_guide

    def _ask_for_references(self) -> list:
        print("  Would you like to add reference post URLs? (Enter URLs one at a time, blank to stop)")
        refs = []
        while True:
            url = input("  URL (or Enter to skip): ").strip()
            if not url:
                break
            desc = input(f"  Description for {url}: ").strip()
            refs.append({"url": url, "description": desc})
        return refs

    # ── Private: web / LLM helpers ────────────────────────────────────────────

    async def _web_search(self, query: str) -> str:
        """Search via Serper.dev and return a plain-text summary of results."""
        if not self.serper_key or self.serper_key == "...":
            return ""  # No key → skip gracefully
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 5},
                )
                data = resp.json()
            snippets = [
                f"[{r.get('title','')}] {r.get('snippet','')}"
                for r in data.get("organic", [])
            ]
            return "\n".join(snippets)
        except Exception as e:
            print(f"  ⚠️  Web search error: {e}")
            return ""

    async def _fetch_url(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                resp = await c.get(url, follow_redirects=True)
                return resp.text[:5000]
        except Exception as e:
            print(f"  ⚠️  Could not fetch {url}: {e}")
            return ""

    async def _gpt(self, prompt: str, model: str = "gpt-4o") -> str:
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(text: str) -> dict:
    """Parse JSON even if the model wraps it in markdown fences."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: return raw as a dict with single key
        return {"raw": text}
