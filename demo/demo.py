"""
demo.py

Interactive terminal UI for the Social Media Post AI Agent.
Run with: python demo.py

Design mirrors orchestrator.py from class:
  - rich console for styled output (panels, spinners, colors)
  - console.input() for all user interaction
  - numbered stages with colored headers
  - error handling with clear messages

Editable prompts at the top of this file (prompt engineering artifacts):
  SYSTEM_PROMPT   — agent personality and goal for post creation chat
  PARSE_PROMPT    — extracts structured receipt from conversation
  INTENT_PROMPT   — classifies user message as create_posts / manage / quit
                    Same pattern as sentiment_analysis from class
                    (prompts_text_usecases.py) — returns a label from
                    natural language, here with entity extraction too
  SUMMARY_PROMPT  — generates 1-2 sentence plain English summary of a file
  EDIT_PROMPT     — applies a plain English change request to a JSON file
"""

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table

load_dotenv()

console = Console()

# ── Editable prompts ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a friendly social media campaign assistant. Your goal is to collect
enough information to create social media posts for a company's product or event.

You need to gather:
  - Company name
  - Product or event name
  - Platform(s): Instagram, Twitter, Blog (default: Instagram)
  - Number of posts (default: 1)
  - Month to post (optional)
  - Whether to schedule on Google Calendar (yes/no)
  - Image preference: Provided Images, AI Generated, or No
  - Any additional creative direction

Be conversational and friendly. If the user gives you most of the info in one
message, confirm what you understood and only ask about what's truly missing.
Don't ask for things one at a time if the user already gave them to you.

When you have enough to proceed, end your message with exactly:
  READY: <one-line summary of the request>

Examples of READY:
  READY: 3 Instagram posts for Rita's Kiwi Melon in June, with scheduling
  READY: 2 Twitter posts for Nike Air Max in July, no image
  READY: 1 Blog post with image for the Philly Food Festival in August
""".strip()

PARSE_PROMPT = """
Extract a structured receipt from this conversation summary.
Return ONLY a JSON object with these exact keys:
  company, product, platforms, num_posts, when, schedule, images, additional_info

Rules:
- platforms: comma-separated string e.g. "Instagram" or "Instagram, Twitter"
- num_posts: string number e.g. "3"
- schedule: "Yes" or "No"
- images: "Provided Images", "AI Generated", or "No"
  * Default Instagram -> "Provided Images"
  * Default Twitter/Blog -> "No"
  * "with image" on any platform -> "Provided Images"
  * "AI generated image" explicitly -> "AI Generated"
  * "without image" -> "No"
- additional_info: any creative direction or special requests
- If a field is unknown use empty string ""

Conversation summary:
{summary}

Respond ONLY with valid JSON. No markdown fences.
""".strip()

# ── Intent classifier prompt ──────────────────────────────────────────────────
# Same classification pattern as sentiment_analysis in class
# (prompts_text_usecases.py) — reads natural language and returns a label.
# Extended here to also extract entities (company, product, file_type)
# so we know exactly what file the user wants to manage.
#
# Prompt Engineering note: this is a good before/after for the report.
# Before: simple label only (like positive/negative/neutral in class)
# After:  structured JSON with label + entity extraction

INTENT_PROMPT = """
You are an intent classifier for a social media agent.
Read the user's message and return a JSON object with these keys:

  intent:    one of "create_posts", "manage", "quit"
  company:   company name if mentioned, else ""
  product:   product name if mentioned, else ""
  file_type: one of "company_report", "product_report", "style_guide", "log", ""

Intent rules:
- "create_posts": user wants to make social media posts
- "manage": user wants to view, update, or edit a company report,
            product report, style guide, or log file
- "quit": user wants to exit, leave, stop, or is done

Examples:
  "Make 3 Instagram posts for Rita's Kiwi Melon"
  -> {{"intent": "create_posts", "company": "Rita's", "product": "Kiwi Melon", "file_type": ""}}

  "I want to update Rita's Cherry Italian Ice product report"
  -> {{"intent": "manage", "company": "Rita's", "product": "Cherry Italian Ice", "file_type": "product_report"}}

  "Show me the style guide for Kiwi Melon"
  -> {{"intent": "manage", "company": "", "product": "Kiwi Melon", "file_type": "style_guide"}}

  "View the logs"
  -> {{"intent": "manage", "company": "", "product": "", "file_type": "log"}}

  "I'm done" / "exit" / "quit" / "leave"
  -> {{"intent": "quit", "company": "", "product": "", "file_type": ""}}

User message: {message}

Respond ONLY with valid JSON. No markdown fences.
""".strip()

SUMMARY_PROMPT = """
Write 1-2 plain English sentences summarizing this JSON data file.
Be specific — mention key facts, not just field names.
Do not use technical terms like "JSON" or "object".

File type: {file_type}
Content:
{content}

Summary (1-2 sentences only):
""".strip()

EDIT_PROMPT = """
You are editing a JSON data file based on a plain English change request.
Apply ONLY the requested change. Do not modify anything else.
Return the complete updated JSON.

File type: {file_type}
Current content:
{content}

Change requested by user: {change_request}

Return ONLY the updated JSON. No markdown fences. No explanation.
""".strip()


# ── Agent class ───────────────────────────────────────────────────────────────

class SocialMediaAgent:
    """
    Conversational frontend agent.

    Mirrors four class patterns:
      - simpleChatBot_chatgpt.py: message history, system prompt at init
      - openai_client.py generate_text_stream(): stream=True, token-by-token
        printing so responses flow out naturally
      - agency_core.py / 02_react_agent.ipynb: live ReAct trace printed live
      - orchestrator.py: numbered stages, rich panels, console.input()

    New: INTENT_PROMPT classifies each message before routing —
    same pattern as sentiment_analysis from prompts_text_usecases.py in class.
    """

    # Guardrail: only these file types can be edited
    EDITABLE_FILES = {"company_report", "product_report", "style_guide"}
    VIEWABLE_FILES = {"company_report", "product_report", "style_guide", "log"}

    def __init__(self, openai_key: str, storage, researcher,
                 schedule_agent_class, logger_class):
        self.client          = OpenAI(api_key=openai_key)
        self.storage         = storage
        self.researcher      = researcher
        self.ScheduleAgent   = schedule_agent_class
        self.Logger          = logger_class
        self.history         = []   # conversation history, like SimpleChatBot

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self, openai_key: str, gcal_credentials: str, gcal_id: str):
        """
        Main entry point. Shows banner then loops:
          1. Ask user what they want
          2. Classify intent (create_posts / manage / quit)
          3. Route to the right flow
          4. Loop back after each action
        """
        banner = (
            "[bold cyan]Social Media Post AI Agent[/bold cyan]\n"
            "[dim]Pattern: ReAct Research \u2192 Parallel Post Generation[/dim]\n"
            "[dim]Type 'exit' or 'quit' at any time to leave.[/dim]"
        )
        console.print(Panel.fit(banner, border_style="cyan"))
        console.print(
            "\n[dim]You can create posts, view or update your reports and style guides,"
            " or view logs. Just tell me what you need.[/dim]\n"
        )

        while True:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
            if not user_input:
                continue

            # ── Classify intent — same pattern as sentiment_analysis in class ──
            intent_data = self._classify_intent(user_input)
            intent      = intent_data.get("intent", "create_posts")

            if intent == "quit":
                console.print("\n[bold yellow]Goodbye! \ud83d\udc4b[/bold yellow]")
                break

            elif intent == "manage":
                self._manage_flow(
                    company=intent_data.get("company", ""),
                    product=intent_data.get("product", ""),
                    file_type=intent_data.get("file_type", ""),
                    openai_key=openai_key,
                )

            else:
                # Default: create_posts flow
                self.history = []   # fresh history for each new post request
                self._create_posts_flow(
                    initial_message=user_input,
                    openai_key=openai_key,
                    gcal_credentials=gcal_credentials,
                    gcal_id=gcal_id,
                )

            # After any action, ask what's next
            console.print()
            console.print(Rule(style="dim"))
            console.print("[dim]What would you like to do next? (create posts, view/update a file, or 'done' to exit)[/dim]")

    # ── Intent classifier ─────────────────────────────────────────────────────

    def _classify_intent(self, message: str) -> dict:
        """
        Classify user message into create_posts / manage / quit.

        Uses INTENT_PROMPT — same classification pattern as sentiment_analysis
        from class (prompts_text_usecases.py). Extended to also extract
        company, product, and file_type so we know exactly what to act on.
        """
        prompt = INTENT_PROMPT.format(message=message)
        resp   = self.client.chat.completions.create(
            model="gpt-4o-mini",   # classification doesn't need gpt-4o
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"intent": "create_posts", "company": "", "product": "", "file_type": ""}

    # ── Manage flow ───────────────────────────────────────────────────────────

    def _manage_flow(self, company: str, product: str,
                     file_type: str, openai_key: str):
        """
        Side flow for viewing and updating core files.
        Guardrail: only company_report, product_report, style_guide can be edited.
        Logs are view-only.
        """
        self._stage_header("M", "File Manager", "yellow")

        # ── Resolve missing company/product if not in the message ─────────────
        if not company:
            company = console.input("[bold yellow]Which company? [/bold yellow]").strip()
        if not product and file_type in ("product_report", "style_guide"):
            product = console.input("[bold yellow]Which product? [/bold yellow]").strip()
        if not file_type:
            file_type = console.input(
                "[bold yellow]What would you like to see? "
                "(company_report / product_report / style_guide / log): [/bold yellow]"
            ).strip().lower().replace(" ", "_")

        # ── Load the file ─────────────────────────────────────────────────────
        data, path = self._load_file(company, product, file_type)

        if data is None:
            self._warn(f"No {file_type.replace('_',' ')} found for [{company}]"
                       + (f" / [{product}]" if product else "") + ".")
            return

        # ── Show summary + formatted JSON ─────────────────────────────────────
        self._display_file(data, file_type, company, product)

        # ── Logs are view-only — guardrail ────────────────────────────────────
        if file_type == "log":
            self._info("Logs are view-only and cannot be edited.")
            return

        # ── Ask what they want to do ──────────────────────────────────────────
        console.print("\n[dim]What would you like to do?[/dim]")
        console.print("  [bold]1[/bold] Auto-update (re-research and rewrite the whole file)")
        console.print("  [bold]2[/bold] Make a specific change (describe it in plain English)")
        console.print("  [bold]3[/bold] View only — no changes")
        console.print("  [bold]4[/bold] Exit / go back\n")

        choice = console.input("[bold yellow]Choice (1/2/3/4): [/bold yellow]").strip()

        if choice == "1":
            self._auto_update(company, product, file_type, openai_key)

        elif choice == "2":
            self._specific_change_loop(data, path, file_type, company, product)

        elif choice == "3":
            self._info("No changes made.")

        else:
            self._info("Going back.")

    def _load_file(self, company: str, product: str,
                   file_type: str) -> tuple[dict | list | None, Path | None]:
        """Load the right file based on file_type. Returns (data, path)."""
        try:
            if file_type == "company_report":
                path = self.storage.company_report_path(company)
                return self.storage.load_company_report(company), path

            elif file_type == "product_report":
                path = self.storage.product_report_path(company, product)
                return self.storage.load_product_report(company, product), path

            elif file_type == "style_guide":
                path = self.storage.style_guide_path(company, product)
                return self.storage.load_style_guide(company, product), path

            elif file_type == "log":
                log_dir = self.storage.log_files_dir(company)
                if not log_dir.exists():
                    return None, None
                logs = sorted(log_dir.glob("*.txt"), reverse=True)
                if not logs:
                    return None, None
                # Show list and let user pick
                console.print(f"\n[dim]Log files for [{company}]:[/dim]")
                for i, l in enumerate(logs, 1):
                    console.print(f"  {i}. {l.name}")
                pick = console.input("\n[bold yellow]Which log? (number, or Enter for latest): [/bold yellow]").strip()
                chosen = logs[int(pick) - 1] if pick.isdigit() else logs[0]
                return chosen.read_text(encoding="utf-8"), chosen

        except Exception:
            return None, None
        return None, None

    def _display_file(self, data, file_type: str, company: str, product: str):
        """Show 1-2 sentence summary + formatted JSON."""

        # Generate plain English summary
        content_str = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
        summary_prompt = SUMMARY_PROMPT.format(
            file_type=file_type.replace("_", " "),
            content=content_str[:2000],
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3,
        )
        summary = resp.choices[0].message.content.strip()

        # Display summary + JSON in a panel
        label = f"{file_type.replace('_', ' ').title()}"
        if product:
            label += f" — {product}"
        label += f" ({company})"

        console.print(Panel(f"[bold]{summary}[/bold]", title=label, border_style="yellow"))

        # Show formatted JSON with syntax highlighting
        if isinstance(data, dict):
            syntax = Syntax(json.dumps(data, indent=2), "json", theme="monokai", word_wrap=True)
            console.print(syntax)
        else:
            console.print(str(data))

    def _auto_update(self, company: str, product: str,
                     file_type: str, openai_key: str):
        """Re-run the full research loop for the specific file type."""
        self._stage_header("M1", "Auto-Update", "blue")

        # Guardrail — only the 3 editable file types
        if file_type not in self.EDITABLE_FILES:
            self._warn(f"'{file_type}' cannot be auto-updated.")
            return

        console.print(f"[dim]Re-researching and rewriting the {file_type.replace('_',' ')}…[/dim]")

        if file_type == "company_report":
            console.print("[dim]Running full research loop for company…[/dim]")
            company_report, _ = self.researcher.resolve(
                company_name=company,
                product_name=product or "N/A",
            )
            self._display_file(company_report, file_type, company, product)

        elif file_type == "product_report":
            company_report = self.storage.load_company_report(company)
            _, product_report = self.researcher.resolve(
                company_name=company,
                product_name=product,
            )
            self._display_file(product_report, file_type, company, product)

        elif file_type == "style_guide":
            company_report = self.storage.load_company_report(company)
            product_report = self.storage.load_product_report(company, product)
            style_guide    = self.researcher.resolve_style_guide(
                company_report=company_report,
                product_report=product_report,
            )
            self._display_file(style_guide, file_type, company, product)

        self._success(f"{file_type.replace('_',' ').title()} updated.")

    def _specific_change_loop(self, data: dict, path: Path,
                               file_type: str, company: str, product: str):
        """
        Let the user describe a change in plain English.
        GPT applies it to the JSON. Loop until confirmed or Enter to exit.
        """
        self._stage_header("M2", "Specific Change", "magenta")
        self._info("Describe what you want to change. Press Enter with nothing to go back.")

        working_data = dict(data)   # work on a copy

        while True:
            change = console.input("\n[bold magenta]Change>[/bold magenta] ").strip()
            if not change:
                self._info("No changes saved.")
                break

            # Apply change via GPT
            edit_prompt = EDIT_PROMPT.format(
                file_type=file_type.replace("_", " "),
                content=json.dumps(working_data, indent=2),
                change_request=change,
            )
            with console.status("[bold magenta]Applying change…"):
                resp = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": edit_prompt}],
                    temperature=0,
                )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

            try:
                updated = json.loads(raw)
            except json.JSONDecodeError:
                self._warn("Something went wrong applying that change. Try rephrasing.")
                continue

            # Show updated file
            self._display_file(updated, file_type, company, product)

            # Ask if happy
            confirm = console.input(
                "\n[bold yellow]Happy with this? (Y to save | tell me what else to change | Enter to cancel): [/bold yellow]"
            ).strip()

            if confirm.lower() in ("y", "yes"):
                # Save to disk
                self.storage.save_json(path, updated)
                self._success(f"Saved to {path.name}")
                break
            elif not confirm:
                self._info("Change discarded.")
                break
            else:
                # User described another change — loop with updated data
                working_data = updated

    # ── Create posts flow ─────────────────────────────────────────────────────

    def _create_posts_flow(self, initial_message: str, openai_key: str,
                            gcal_credentials: str, gcal_id: str):
        """Full post creation pipeline — same as before, now a named method."""

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 1: CONVERSATION
        # ══════════════════════════════════════════════════════════════════════
        self._stage_header(1, "Request Collection", "cyan")
        console.print("[dim]Tell me what you need — be as specific or casual as you like.[/dim]\n")

        # Feed the initial message in as the first turn
        print()
        reply = self._chat(initial_message)
        print()

        receipt = {}
        while True:
            if "READY:" in reply:
                summary_line = reply.split("READY:")[-1].strip()
                self._info(f"Understood: {summary_line}")

                full_history = "\n".join(
                    f"{m['role'].upper()}: {m['content']}"
                    for m in self.history
                )
                receipt = self._parse_receipt(full_history)
                self._show_receipt_table(receipt)

                confirm = console.input(
                    "\n[bold yellow]Does this look right? (Y to continue | tell me what to change): [/bold yellow]"
                ).strip()

                if confirm.lower() in ("y", "yes", ""):
                    break
                elif confirm.lower() in ("exit", "quit"):
                    return
                else:
                    print()
                    reply = self._chat(confirm)
                    print()
            else:
                user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
                if user_input.lower() in ("exit", "quit"):
                    return
                if not user_input:
                    continue
                print()
                reply = self._chat(user_input)
                print()

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 2: RESEARCH
        # ══════════════════════════════════════════════════════════════════════
        self._stage_header(2, "Research", "blue")

        provided_url  = None
        uploaded_file = None
        has_company   = self.storage.company_exists(receipt.get("company", ""))
        has_product   = self.storage.product_exists(receipt.get("company", ""), receipt.get("product", ""))

        if not has_company or not has_product:
            extra = console.input(
                "[dim]Optional — paste a URL or filename for reference (Enter to skip): [/dim]"
            ).strip()
            if extra.startswith("http"):
                provided_url = extra
            elif extra:
                uploaded_file = extra

        console.print("[dim]Watching the agent think in real time…[/dim]")
        company_report, product_report, resolved_company, resolved_product = self.researcher.resolve(
            company_name=receipt.get("company", ""),
            product_name=receipt.get("product", ""),
            provided_url=provided_url,
            uploaded_file=uploaded_file,
        )
        # Update receipt with canonical names so downstream steps use the right name
        receipt["company"] = resolved_company
        receipt["product"] = resolved_product

        self._panel(
            f"Company: {company_report.get('company_name')}\n"
            f"Industry: {company_report.get('industry')}\n"
            f"Product: {product_report.get('product_name')}\n"
            f"Description: {str(product_report.get('product_description',''))[:120]}",
            title="Research Complete", color="blue",
        )

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 3: STYLE GUIDE
        # ══════════════════════════════════════════════════════════════════════
        self._stage_header(3, "Style Guide", "magenta")
        style_guide = self.researcher.resolve_style_guide(
            company_report=company_report,
            product_report=product_report,
        )
        self._panel(
            f"Vibe: {style_guide.get('vibe')}\n"
            f"Tone: {style_guide.get('tone')}\n"
            f"Emoji usage: {style_guide.get('emoji_usage')}",
            title="Style Guide Ready", color="magenta",
        )

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 4: IMAGE SELECTION
        # ══════════════════════════════════════════════════════════════════════
        self._stage_header(4, "Image Selection", "yellow")
        image_mode       = receipt.get("images", "No")
        selected_images  = []
        reference_images = []
        style_vibe       = style_guide.get("vibe", "")

        if image_mode == "No":
            self._info("Image mode is No — skipping.")
        else:
            selected_images = self._image_selection_loop(
                company=receipt.get("company", ""),
                product=receipt.get("product", ""),
                image_mode=image_mode,
                receipt=receipt,
            )
            image_mode = receipt.get("images", image_mode)

        # Style references — offered regardless of image mode
        reference_images = self._reference_selection_loop(
            company=receipt.get("company", ""),
            product=receipt.get("product", ""),
        )

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 5: POST GENERATION
        # ══════════════════════════════════════════════════════════════════════
        self._stage_header(5, "Post Generation (Parallel)", "green")

        from agent_posts    import PLATFORM_AGENTS, build_context, parse_platforms
        from agent_parallel import run_all_posts

        context   = build_context(
            company=company_report, product=product_report,
            style=style_guide, extra=receipt.get("additional_info", ""),
            month=receipt.get("when", ""),
        )
        platforms = parse_platforms(receipt.get("platforms", "instagram"))
        n_posts   = int(receipt.get("num_posts", 1))

        agents_per_post = [
            [PLATFORM_AGENTS[p](openai_key=openai_key)
             for p in platforms if p in PLATFORM_AGENTS]
            for _ in range(n_posts)
        ]

        console.print(f"[dim]Platforms: {', '.join(p.capitalize() for p in platforms)} | "
                      f"Posts: {n_posts} | Images: {image_mode}[/dim]\n")

        base_brief = {
            "context": context, "total_posts": n_posts,
            "image_mode": image_mode, "selected_images": selected_images,
            "reference_images": reference_images,
            "style_vibe": style_vibe,
        }

        start = time.time()
        with console.status("[bold green]Generating posts in parallel…"):
            posts = run_all_posts(agents_per_post, base_brief)
        elapsed = time.time() - start

        console.print(f"\n[bold green]✨ All posts generated in {elapsed:.1f}s[/bold green]")
        console.print(Rule(style="green"))

        for i, post in enumerate(posts, 1):
            has_img = post.get("image_bytes") is not None
            self._panel(
                post.get("caption", ""),
                title=f"Post {i} [{post.get('platform','?').upper()}] — Score: {post.get('score','N/A')}{' 🖼️' if has_img else ''}",
                color="green",
            )

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 6: SAVE
        # ══════════════════════════════════════════════════════════════════════
        self._stage_header(6, "Saving Posts & Images", "cyan")
        output_dir = self.storage.save_posts(
            company=receipt["company"], product=receipt["product"],
            posts=posts, receipt=receipt,
        )
        for i, post in enumerate(posts, 1):
            if post.get("image_bytes"):
                self.storage.save_image(output_dir / f"Post {i}", post["image_bytes"])
        self._success(f"Saved to: {output_dir}")

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 7: SCHEDULE
        # ══════════════════════════════════════════════════════════════════════
        if receipt.get("schedule") == "Yes":
            self._stage_header(7, "Scheduling", "yellow")
            try:
                scheduler = self.ScheduleAgent(
                    openai_key=openai_key,
                    credentials_json=gcal_credentials,
                    calendar_id=gcal_id,
                )
                scheduler.run(receipt=receipt, posts=posts, output_dir=output_dir)
            except Exception as e:
                self._warn(f"Scheduling failed: {e}")
        else:
            self._info("Scheduling skipped.")

        # ══════════════════════════════════════════════════════════════════════
        # STAGE 8: LOG
        # ══════════════════════════════════════════════════════════════════════
        logger   = self.Logger(self.storage)
        log_path = logger.write(
            receipt=receipt, company_report=company_report,
            product_report=product_report, style_guide=style_guide,
            posts=posts, output_dir=output_dir,
        )

        console.print(Rule(style="cyan"))
        console.print(Panel.fit(
            f"[bold green]✅ Campaign complete![/bold green]\n\n"
            f"Posts saved : {output_dir}\n"
            f"Log file    : {log_path}\n"
            f"Total posts : {len(posts)}\n"
            f"Images      : {'Yes' if any(p.get('image_bytes') for p in posts) else 'No'}",
            title="Summary", border_style="green",
        ))

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _chat(self, user_message: str, stream: bool = True) -> str:
        self.history.append({"role": "user", "content": user_message})
        if stream:
            reply = self._stream_print(
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *self.history],
                prefix="[bold magenta]Agent:[/bold magenta] ",
            )
        else:
            resp  = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *self.history],
                temperature=0.6,
            )
            reply = resp.choices[0].message.content.strip()
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _stream_print(self, messages: list, prefix: str = "") -> str:
        """
        Stream GPT response token by token.
        Mirrors generate_text_stream() + demo_streaming() from class openai_client.py.
        """
        stream     = self.client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.6, stream=True,
        )
        full_reply = []
        console.print(prefix, end="")
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token is not None:
                print(token, end="", flush=True)
                full_reply.append(token)
        print()
        return "".join(full_reply).strip()

    def _parse_receipt(self, summary: str) -> dict:
        prompt = PARSE_PROMPT.format(summary=summary)
        resp   = self.client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _stage_header(self, number, title: str, color: str):
        console.print(f"\n[bold {color}]STAGE {number}: {title}[/bold {color}]")

    def _panel(self, content: str, title: str, color: str):
        console.print(Panel(content, title=title, border_style=color))

    def _success(self, msg: str):
        console.print(f"[bold green]✅ {msg}[/bold green]")

    def _warn(self, msg: str):
        console.print(f"[bold yellow]⚠️  {msg}[/bold yellow]")

    def _info(self, msg: str):
        console.print(f"[dim]{msg}[/dim]")

    def _show_receipt_table(self, receipt: dict):
        table = Table(title="📋 Receipt", border_style="cyan", show_header=False)
        table.add_column("Field", style="bold cyan", width=22)
        table.add_column("Value")
        for k, v in receipt.items():
            table.add_row(k, str(v) if v else "[dim]—[/dim]")
        console.print(table)

    def _image_selection_loop(self, company: str, product: str,
                               image_mode: str, receipt: dict) -> list:
        img_dir  = self.storage.images_dir(company, product)
        img_dir.mkdir(parents=True, exist_ok=True)
        existing = self.storage.list_images(company, product)

        console.print(f"[dim]Image library: {img_dir}[/dim]")
        if existing:
            table = Table(title=f"Images for {product}", style="yellow")
            table.add_column("#", style="dim", width=4)
            table.add_column("Filename")
            for i, p in enumerate(existing, 1):
                table.add_row(str(i), p.name)
            console.print(table)
        else:
            console.print("[dim]  No images in library yet.[/dim]")

        console.print("\n[dim]Commands: add <filepath> | select <number> | remove <number> | Enter to continue[/dim]")
        selected = []
        while True:
            cmd    = console.input("[bold yellow]Images>[/bold yellow] ").strip()
            if not cmd:
                break
            parts  = cmd.split(None, 1)
            action = parts[0].lower()
            arg    = parts[1].strip() if len(parts) > 1 else ""
            if action == "add" and arg:
                added = self.storage.add_image_to_library(company, product, arg)
                if added:
                    existing = self.storage.list_images(company, product)
            elif action == "select" and arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(existing):
                    chosen = existing[idx]
                    if chosen not in selected:
                        selected.append(chosen)
                        self._success(f"Selected: {chosen.name}")
                    else:
                        self._info(f"Already selected: {chosen.name}")
                else:
                    self._warn(f"Invalid number. Choose 1–{len(existing)}.")
            elif action == "remove" and arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(existing):
                    target = existing[idx]
                    target.unlink()
                    existing = self.storage.list_images(company, product)
                    selected = [p for p in selected if p != target]
                    self._info(f"Removed: {target.name}")
                else:
                    self._warn("Invalid number.")
            else:
                self._info("Commands: add <filepath> | select <number> | remove <number> | Enter to continue")

        if image_mode == "Provided Images" and not selected:
            if not existing:
                self._warn("No images found — falling back to AI Generated.")
                receipt["images"] = "AI Generated"
            else:
                self._info("No images selected — agents will prompt per-post.")
        return selected


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    GCAL_ID    = os.getenv("GCAL_ID", "primary")
    GCAL_CREDS = os.getenv("GCAL_CREDENTIALS", "credentials.json")

    if not OPENAI_KEY:
        console.print("[bold red]OPENAI_API_KEY not found. Did you fill in your .env file?[/bold red]")
        raise SystemExit(1)

    from agent_storage  import Storage
    from agent_research import ResearchAgent
    from agent_schedule import ScheduleAgent
    from agent_logger   import Logger

    storage    = Storage(Path(".") / "AI Storage")
    researcher = ResearchAgent(storage=storage, openai_key=OPENAI_KEY)

    agent = SocialMediaAgent(
        openai_key=OPENAI_KEY, storage=storage, researcher=researcher,
        schedule_agent_class=ScheduleAgent, logger_class=Logger,
    )

    try:
        agent.run(openai_key=OPENAI_KEY, gcal_credentials=GCAL_CREDS, gcal_id=GCAL_ID)
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Interrupted. Goodbye![/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        raise
