"""
demo.py — Social Media Post AI Agent
Run with: python demo.py

This is the notebook made interactive. Same steps, same order, same logic
as AI_Agent.ipynb, just wrapped in a terminal UI with rich formatting.

Steps mirror the notebook exactly:
  Step 3:   Parse User Request
  Step 4:   Company & Product Lookup
  Step 5:   Review Reports (Optional)
  Step 6:   Confirm Receipt
  Step 7:   Style References
  Step 7.5: Generate Style Guide
  Step 7.6: Image Selection
  Step 8:   Generate Posts (Parallel Workflow)
  Step 9:   Save Posts & Images
  Step 10:  Schedule Posts (Optional)
  Step 11:  Write Log

Editable prompts:
  INTENT_PROMPT  — classifies message as create_posts / manage / quit
  SUMMARY_PROMPT — plain English summary of a file (for file manager)
  EDIT_PROMPT    — applies plain English change to a JSON file
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

# Same classification pattern as sentiment_analysis from class
# (prompts_text_usecases.py) — natural language in, structured label out.
# Extended with entity extraction so we know what file to manage.
INTENT_PROMPT = """
Classify the user's message and return a JSON object:
  intent:    "create_posts" | "manage" | "quit"
  company:   company name if mentioned, else ""
  product:   product name if mentioned, else ""
  file_type: "company_report" | "product_report" | "style_guide" | "log" | ""

- create_posts: user wants to make social media posts
- manage: user wants to view or edit a report, style guide, or log
- quit: user wants to exit

User message: {message}
Return ONLY valid JSON. No markdown fences.
""".strip()

SUMMARY_PROMPT = """
Write 1-2 plain English sentences summarizing this file.
Mention specific facts, not just field names.
File type: {file_type}
Content: {content}
""".strip()

EDIT_PROMPT = """
Edit this JSON based on the user's request. Apply ONLY the requested change.
Return the complete updated JSON with no markdown fences.
File type: {file_type}
Current content: {content}
Change: {change_request}
""".strip()


# ── Agent ─────────────────────────────────────────────────────────────────────

class SocialMediaAgent:

    EDITABLE_FILES = {"company_report", "product_report", "style_guide"}

    def __init__(self, openai_key, storage, researcher,
                 schedule_agent_class, logger_class):
        self.client        = OpenAI(api_key=openai_key)
        self.storage       = storage
        self.researcher    = researcher
        self.ScheduleAgent = schedule_agent_class
        self.Logger        = logger_class

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self, openai_key, gcal_credentials, gcal_id):
        # Banner
        console.print(Panel.fit(
            "[bold cyan]Social Media Post AI Agent[/bold cyan]\n"
            "[dim]Enter your request, 'manage' to view/edit files, or 'quit' to exit.[/dim]",
            border_style="cyan"
        ))

        # Steps 0, 1, 2 — shown once under the banner
        console.print(f"\n[cyan]── Step 0: Loading Packages ──[/cyan]  Imports OK")
        console.print(f"[cyan]── Step 1: API Keys ──[/cyan]           Keys loaded from .env")
        console.print(f"[cyan]── Step 2: Storage Paths ──[/cyan]      {self.storage.root.resolve()}")

        while True:
            console.print()
            user_input = console.input("[cyan]Request:[/cyan] ").strip()
            if not user_input:
                continue

            intent_data = self._classify_intent(user_input)
            intent      = intent_data.get("intent", "create_posts")

            if intent == "quit":
                console.print("Goodbye.")
                break
            elif intent == "manage":
                self._manage_flow(
                    company=intent_data.get("company", ""),
                    product=intent_data.get("product", ""),
                    file_type=intent_data.get("file_type", ""),
                    openai_key=openai_key,
                )
            else:
                self._run_notebook_flow(
                    request=user_input,
                    openai_key=openai_key,
                    gcal_credentials=gcal_credentials,
                    gcal_id=gcal_id,
                )

            console.print(Rule(style="dim"))

    # ── Notebook flow — mirrors AI_Agent.ipynb step by step ──────────────────

    def _run_notebook_flow(self, request, openai_key, gcal_credentials, gcal_id):
        from agent_utils import parse_request, print_receipt, interactive_receipt_editor, IMAGE_PLATFORM_DEFAULTS
        from agent_posts import PLATFORM_AGENTS, build_context, parse_platforms
        from agent_parallel import run_all_posts

        # ══════════════════════════════════════════════════════════════════════
        # STEP 3: PARSE USER REQUEST
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 3: Parse User Request ──[/bold]")

        receipt = parse_request(request)

        table = Table(title="Receipt", border_style="cyan", show_header=False)
        table.add_column("Field", style="bold", width=22)
        table.add_column("Value")
        for k, v in receipt.items():
            if k.startswith("_"):
                continue  # hide internal fields
            table.add_row(k, str(v) if v else "—")
        console.print(table)

        # ══════════════════════════════════════════════════════════════════════
        # STEP 4: COMPANY & PRODUCT LOOKUP
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 4: Company & Product Lookup ──[/bold]")

        # First resolve names via fuzzy match — this asks the user to confirm
        # before we know if they're new or existing
        from agent_research import ResearchAgent
        company_name = self.researcher._resolve_official_name(
            receipt.get("company", ""), receipt.get("product", "")
        )
        product_name = self.researcher._resolve_official_product_name(
            company_name, receipt.get("product", "")
        )

        has_company = self.storage.company_exists(company_name)
        has_product = self.storage.product_exists(company_name, product_name)

        # Announce status — mirrors notebook output
        if has_company and has_product:
            console.print(f"\n  Found existing company [{company_name}] and "
                          f"product [{product_name}] — using existing reports.")
        elif has_company and not has_product:
            console.print(f"\n  Found existing company [{company_name}].")
            console.print(f"  [{product_name}] is a new product — will research.")
        else:
            console.print(f"\n  [{company_name}] is a new company.")
            console.print(f"  [{product_name}] is a new product — will research both.")

        # Ask for optional references — only for new companies/products, separately
        company_url = company_file = product_url = product_file = None

        if not has_company:
            console.print(f"\n  Optional reference for [{company_name}]:")
            extra = console.input(
                "  Paste a URL or filename (Enter to skip): "
            ).strip().strip('"').strip("'")
            if extra.startswith("http"):
                company_url = extra
            elif extra:
                company_file = extra

        if not has_product:
            console.print(f"\n  Optional reference for [{product_name}]:")
            extra = console.input(
                "  Paste a URL or filename (Enter to skip): "
            ).strip().strip('"').strip("'")
            if extra.startswith("http"):
                product_url = extra
            elif extra:
                product_file = extra

        company_report, product_report, resolved_company, resolved_product = \
            self.researcher.resolve(
                company_name=company_name,
                product_name=product_name,
                company_url=company_url,
                company_file=company_file,
                product_url=product_url,
                product_file=product_file,
                skip_name_resolution=True,  # already resolved above
            )

        receipt["company"] = resolved_company
        receipt["product"] = resolved_product

        # Stream the summary — mirrors generate_text_stream() from class
        console.print()
        self._stream_print(
            f"Company: {company_report.get('company_name')} | "
            f"Industry: {company_report.get('industry')} | "
            f"Product: {product_report.get('product_name')} | "
            f"{str(product_report.get('product_description',''))[:100]}"
        )

        # ══════════════════════════════════════════════════════════════════════
        # STEP 5: REVIEW REPORTS (OPTIONAL)
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 5: Review Reports (Optional) ──[/bold]")

        want_review = console.input(
            "Would you like to review the Company or Product report? (y/N): "
        ).strip().lower()

        if want_review == "y":
            choice = console.input("Type 'company', 'product', or 'both': ").strip().lower()
            if choice in ("company", "both"):
                console.print(Syntax(json.dumps(company_report, indent=2),
                                     "json", theme="monokai", word_wrap=True))
            if choice in ("product", "both"):
                console.print(Syntax(json.dumps(product_report, indent=2),
                                     "json", theme="monokai", word_wrap=True))
            console.input("Press Enter to continue...")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 6: CONFIRM RECEIPT
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 6: Confirm Receipt ──[/bold]")
        receipt = interactive_receipt_editor(receipt)

        # ══════════════════════════════════════════════════════════════════════
        # STEP 7: STYLE REFERENCES
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 7: Style References ──[/bold]")
        console.print(f"  Folder: {self.storage.references_dir(receipt['company'], receipt['product'])}")

        # Snapshot BEFORE the loop so we can detect any changes after
        refs_before_loop = set(
            r.name for r in self.storage.list_references(receipt["company"], receipt["product"])
        )

        reference_images = self._reference_selection_loop(
            receipt["company"], receipt["product"]
        )

        # Detect reference changes using before/after snapshot
        refs_after   = set(r.name for r in self.storage.list_references(receipt["company"], receipt["product"]))
        has_guide    = self.storage.style_guide_exists(receipt["company"], receipt["product"])
        refs_changed = refs_after != refs_before_loop

        update_mode = "leave"
        if refs_changed and has_guide:
            console.print("\n  References changed and a style guide already exists.")
            console.print("  1. Leave as-is")
            console.print("  2. Touch up (lightly blend new references into existing style)")
            console.print("  3. Regenerate (full rewrite using all current references)")
            choice = console.input("  Choice (1/2/3, default 1): ").strip()
            if choice == "2":
                update_mode = "touchup"
            elif choice == "3":
                update_mode = "regenerate"

        # ══════════════════════════════════════════════════════════════════════
        # STEP 7.5: GENERATE STYLE GUIDE
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 7.5: Generate Style Guide ──[/bold]")

        style_guide = self.researcher.resolve_style_guide(
            company_report=company_report,
            product_report=product_report,
            reference_images=reference_images,
            update_mode=update_mode,
        )
        style_vibe = style_guide.get("vibe", "")
        console.print(f"  Vibe: {style_vibe}")
        console.print(f"  Tone: {style_guide.get('tone')}")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 7.6: IMAGE SELECTION
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 7.6: Image Selection ──[/bold]")

        image_mode             = receipt.get("images", "No")
        selected_images        = []
        enhance_as_inspiration = False

        if image_mode == "No":
            console.print("  Image mode: No — skipping.")
        else:
            selected_images = self._image_selection_loop(
                receipt["company"], receipt["product"], image_mode, receipt
            )
            image_mode = receipt.get("images", image_mode)

            # Debug — remove after fixing
            console.print(f"  [debug] image_mode={image_mode!r} selected_images={len(selected_images)}")

            # Ask enhance vs inspire ONCE here — before parallel execution.
            # If asked inside threads, multiple agents conflict on input().
            enhance_as_inspiration = False
            if image_mode == "Provided Images" and selected_images:
                console.print("\n  How would you like to use these images?")
                console.print("  1. Enhance real photo with AI effects")
                console.print("  2. Use as inspiration for a new AI image")
                choice = console.input("  Enter 1 or 2 (default 1): ").strip()
                enhance_as_inspiration = (choice == "2")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 8: GENERATE POSTS (PARALLEL WORKFLOW)
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 8: Generate Posts (Parallel Workflow) ──[/bold]")

        context  = build_context(
            company=company_report, product=product_report,
            style=style_guide, extra=receipt.get("additional_info", ""),
            month=receipt.get("when", ""),
        )
        platforms = parse_platforms(receipt.get("platforms", "instagram"))
        n_posts   = int(receipt.get("num_posts", 1))

        # Build post_platform_list from per-platform counts stored in receipt
        # e.g. "1 Instagram and 2 Twitter" → [instagram, twitter, twitter]
        # Falls back to even cycling if no per-platform counts available
        import re as _re
        raw_request     = receipt.get("_raw_request", "")
        platform_counts = _re.findall(r"\b(\d+)\s+(instagram|twitter|blog|x)\b",
                                      raw_request, _re.I)
        if platform_counts:
            post_platform_list = []
            for count, platform in platform_counts:
                post_platform_list.extend([platform.lower()] * int(count))
        else:
            valid_platforms    = [p for p in platforms if p in PLATFORM_AGENTS]
            post_platform_list = [valid_platforms[i % len(valid_platforms)]
                                  for i in range(n_posts)]

        # Group into parallel rounds — all unique platforms per round run together
        # e.g. [instagram, twitter, twitter] → Round1:[insta,twitter], Round2:[twitter]
        agents_per_post = []
        i = 0
        while i < len(post_platform_list):
            # Take one of each platform that appears next
            seen = set()
            round_platforms = []
            j = i
            while j < len(post_platform_list):
                p = post_platform_list[j]
                if p not in seen and p in PLATFORM_AGENTS:
                    seen.add(p)
                    round_platforms.append(p)
                    j += 1
                else:
                    break
            if not round_platforms:
                i += 1
                continue
            agents_per_post.append([PLATFORM_AGENTS[p](openai_key=openai_key)
                                     for p in round_platforms])
            i += len(round_platforms)

        console.print(f"  Platforms: {', '.join(p.capitalize() for p in post_platform_list)}")
        console.print(f"  Posts: {len(post_platform_list)} | Images: {image_mode}")

        base_brief = {
            "context":                context,
            "total_posts":            n_posts,
            "image_mode":             image_mode,
            "selected_images":        selected_images,
            "reference_images":       reference_images,
            "style_vibe":             style_vibe,
            "logo_description":       company_report.get("logo_description", "") or "",
            "additional_info":        receipt.get("additional_info", ""),
            "enhance_as_inspiration": enhance_as_inspiration,
            "brand_context": " | ".join(filter(None, [
                f"Notes: {receipt.get('additional_info','')}" if receipt.get("additional_info") else "",
                f"Vibe: {style_guide.get('vibe','')}" if style_guide.get("vibe") else "",
                f"Tone: {style_guide.get('tone','')}" if style_guide.get("tone") else "",
                f"Product: {product_report.get('product_name','')} — {str(product_report.get('product_description',''))[:80]}" if product_report.get("product_name") else "",
                f"Company: {company_report.get('company_name','')}" if company_report.get("company_name") else "",
            ])),
        }

        start = time.time()
        posts = run_all_posts(agents_per_post, base_brief)
        elapsed = time.time() - start

        # ── Image recovery — safe here since we're outside threads ───────────
        from agent_posts import _handle_image
        for i, post in enumerate(posts, 1):
            audit = post.get("audit_result", {})
            if post.get("image_bytes") is None and not audit.get("passed", True):
                plat = post.get("platform", "?").upper()
                console.print(f"\n  Post {i} [{plat}] — image failed: {audit.get('reason','')}")
                console.print("  1. Try a different image")
                console.print("  2. Use final failed image anyway (marked as Failed Audit)")
                console.print("  3. Skip — caption only (default)")
                choice = console.input("  Choice (1/2/3): ").strip()

                if choice == "1":
                    retry_mode = image_mode if image_mode != "No" else "AI Generated"
                    img_bytes, img_audit = _handle_image(
                        agent=agents_per_post[i-1][0],
                        post=post,
                        image_mode=retry_mode,
                        selected_images=selected_images if retry_mode == "Provided Images" else [],
                        style_vibe=style_vibe,
                        context=base_brief["context"],
                        logo_description=base_brief.get("logo_description", ""),
                        additional_notes=base_brief.get("additional_info", ""),
                        enhance_as_inspiration=enhance_as_inspiration if retry_mode == "Provided Images" else False,
                        brand_context=base_brief.get("brand_context", ""),
                    )
                    post["image_bytes"]  = img_bytes
                    post["audit_result"] = img_audit

                elif choice == "2":
                    # Use the last failed image — store it but mark it clearly
                    last_image = audit.get("last_image_bytes")
                    if last_image:
                        post["image_bytes"]        = last_image
                        post["audit_result"]       = {**audit, "passed": False, "failed_audit_override": True}
                        console.print("  ⚠️  Image saved and marked as (Failed Audit).")
                    else:
                        console.print("  ⚠️  No image available to save — skipping.")

        console.print(f"\n  All agents finished in {elapsed:.2f} seconds")
        console.print("=" * 70)

        # A/B score summary
        console.print("\nA/B SCORE SUMMARY")
        console.print("-" * 40)
        for i, post in enumerate(posts, 1):
            platform  = post.get("platform", "?").upper()
            score     = post.get("score", "N/A")
            score_str = f"{score:.1f}/10" if isinstance(score, float) else str(score)
            has_image = post.get("image_bytes") is not None
            audit     = post.get("audit_result", {})
            cap_audit = post.get("caption_audit_result", {})

            if not has_image:
                nuclear_note = " [nuclear corrections applied]" if audit.get("went_nuclear") else ""
                audit_str = f"(no image{nuclear_note})"
            elif audit.get("failed_audit_override"):
                audit_str = "⚠️  Image saved (Failed Audit)"
            elif audit.get("passed", True):
                went_nuclear = audit.get("went_nuclear", False)
                audit_str = "Image passed audit" + (" [nuclear]" if went_nuclear else "")
            else:
                audit_str = f"Image audit failed: {audit.get('reason','')[:60]}"

            cap_str = "Caption passed" if cap_audit.get("passed", True) \
                      else f"Caption failed: {cap_audit.get('reason','')}"

            console.print(f"  Post {i} [{platform}]  Score: {score_str}  {cap_str}  {audit_str}")
        console.print("-" * 40)

        # Post content
        console.print("\nGENERATED SOCIAL MEDIA CONTENT")
        console.print("=" * 70)
        for i, post in enumerate(posts, 1):
            has_img   = post.get("image_bytes") is not None
            score     = post.get("score", "N/A")
            score_str = f"{score:.1f}/10" if isinstance(score, float) else str(score)
            label     = f"Post {i} [{post.get('platform','?').upper()}] — Score: {score_str}"
            if has_img:
                label += " 🖼️"
            console.print(f"┌─ {label} " + "─" * max(0, 67 - len(label)))
            console.print("│")
            for line in post.get("caption", "").split("\n"):
                console.print(f"│ {line}")
            console.print("└" + "─" * 69)
            console.print()

        console.print("=" * 70)
        console.print(f"✅ Generation complete! Total time: {elapsed:.2f}s")
        console.print("=" * 70)

        # ══════════════════════════════════════════════════════════════════════
        # STEP 9: SAVE POSTS & IMAGES
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 9: Save Posts & Images ──[/bold]")

        output_dir = self.storage.save_posts(
            company=receipt["company"], product=receipt["product"],
            posts=posts, receipt=receipt,
        )
        for i, post in enumerate(posts, 1):
            if post.get("image_bytes"):
                audit = post.get("audit_result", {})
                filename = "post_image (Failed Audit).png" if audit.get("failed_audit_override") else "post_image.png"
                self.storage.save_image(
                    output_dir / f"Post {i}", post["image_bytes"], filename=filename
                )
        console.print(f"\n  All posts saved to: {output_dir}")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 10: SCHEDULE POSTS (OPTIONAL)
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 10: Schedule Posts (Optional) ──[/bold]")

        if receipt.get("schedule") == "Yes":
            try:
                scheduler = self.ScheduleAgent(
                    openai_key=openai_key,
                    credentials_json=gcal_credentials,
                    calendar_id=gcal_id,
                )
                scheduler.run(receipt=receipt, posts=posts, output_dir=output_dir)
            except Exception as e:
                console.print(f"  Scheduling failed: {e}")
        else:
            console.print("  Scheduling skipped.")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 11: WRITE LOG
        # ══════════════════════════════════════════════════════════════════════
        console.print("\n[bold]── Step 11: Write Log ──[/bold]")

        logger   = self.Logger(self.storage)
        log_path = logger.write(
            receipt=receipt, company_report=company_report,
            product_report=product_report, style_guide=style_guide,
            posts=posts, output_dir=output_dir,
        )
        console.print(f"\n🎉 All done! Log: {log_path}")

    # ── File manager ──────────────────────────────────────────────────────────

    def _manage_flow(self, company, product, file_type, openai_key):
        console.print("\n[bold]── File Manager ──[/bold]")

        if not company:
            company = console.input("Which company? ").strip()
        if not product and file_type in ("product_report", "style_guide"):
            product = console.input("Which product? ").strip()
        if not file_type:
            file_type = console.input(
                "What would you like to see? (company_report / product_report / style_guide / log): "
            ).strip().lower().replace(" ", "_")

        # Fuzzy match company
        if company:
            from difflib import SequenceMatcher
            existing = self.storage.list_companies()
            matches  = [
                c for c in existing
                if SequenceMatcher(None, company.lower(), c.lower()).ratio() > 0.6
                or company.lower() in c.lower() or c.lower() in company.lower()
            ]
            if matches and matches[0].lower() != company.lower():
                ans = console.input(f"Found [{matches[0]}] — is that the one? (Y/n): ").strip().lower()
                if ans in ("", "y", "yes"):
                    company = matches[0]

        # Fuzzy match product
        if product and company:
            from difflib import SequenceMatcher
            products_dir = self.storage.products_dir(company)
            if products_dir.exists():
                existing_products = [
                    f.stem.replace(" Product Report", "")
                    for f in products_dir.glob("*.json")
                ]
                matches = [
                    p for p in existing_products
                    if SequenceMatcher(None, product.lower(), p.lower()).ratio() > 0.6
                    or product.lower() in p.lower() or p.lower() in product.lower()
                ]
                if matches and matches[0].lower() != product.lower():
                    ans = console.input(f"Found [{matches[0]}] — is that the one? (Y/n): ").strip().lower()
                    if ans in ("", "y", "yes"):
                        product = matches[0]

        data, path = self._load_file(company, product, file_type)
        if data is None:
            console.print(f"  No {file_type} found for [{company}]"
                          + (f" / [{product}]" if product else "") + ".")
            return

        self._display_file(data, file_type, company, product)

        if file_type == "log":
            console.print("  Logs are view-only and cannot be edited.")
            return

        console.print("\n  1. Auto-update (re-research and rewrite the whole file)")
        console.print("  2. Make a specific change (describe it in plain English)")
        console.print("  3. View only — no changes")
        console.print("  4. Exit / go back")
        choice = console.input("Choice (1/2/3/4): ").strip()

        if choice == "1":
            self._auto_update(company, product, file_type, openai_key)
        elif choice == "2":
            self._specific_change_loop(data, path, file_type, company, product)

    def _load_file(self, company, product, file_type):
        try:
            if file_type == "company_report":
                return (self.storage.load_company_report(company),
                        self.storage.company_report_path(company))
            elif file_type == "product_report":
                return (self.storage.load_product_report(company, product),
                        self.storage.product_report_path(company, product))
            elif file_type == "style_guide":
                return (self.storage.load_style_guide(company, product),
                        self.storage.style_guide_path(company, product))
            elif file_type == "log":
                log_dir = self.storage.log_files_dir(company)
                if not log_dir.exists():
                    return None, None
                logs = sorted(log_dir.glob("*.txt"), reverse=True)
                if not logs:
                    return None, None
                console.print(f"\n  Log files for [{company}]:")
                for i, l in enumerate(logs, 1):
                    console.print(f"    {i}. {l.name}")
                pick = console.input("  Which log? (number, Enter for latest): ").strip()
                chosen = logs[int(pick) - 1] if pick.isdigit() else logs[0]
                return chosen.read_text(encoding="utf-8"), chosen
        except Exception:
            return None, None
        return None, None

    def _display_file(self, data, file_type, company, product):
        content_str = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": SUMMARY_PROMPT.format(
                file_type=file_type.replace("_", " "),
                content=content_str[:2000],
            )}],
            temperature=0.3,
        )
        label = f"{file_type.replace('_',' ').title()} — {company}"
        if product:
            label += f" / {product}"
        console.print(Panel(resp.choices[0].message.content.strip(),
                            title=label, border_style="yellow"))
        if isinstance(data, dict):
            console.print(Syntax(json.dumps(data, indent=2), "json",
                                 theme="monokai", word_wrap=True))
        else:
            console.print(str(data))

    def _auto_update(self, company, product, file_type, openai_key):
        if file_type not in self.EDITABLE_FILES:
            console.print(f"  '{file_type}' cannot be auto-updated.")
            return
        console.print(f"  Re-researching {file_type.replace('_',' ')}…")
        if file_type == "company_report":
            self.researcher.resolve(company_name=company, product_name=product or "N/A")
        elif file_type == "product_report":
            self.researcher.resolve(company_name=company, product_name=product)
        elif file_type == "style_guide":
            cr = self.storage.load_company_report(company)
            pr = self.storage.load_product_report(company, product)
            self.researcher.resolve_style_guide(
                company_report=cr, product_report=pr, update_mode="regenerate"
            )
        console.print("  Done.")

    def _specific_change_loop(self, data, path, file_type, company, product):
        console.print("  Describe what you want to change. Press Enter with nothing to go back.")
        working = dict(data)
        while True:
            change = console.input("\n  Change> ").strip()
            if not change:
                console.print("  No changes saved.")
                break
            with console.status("  Applying change…"):
                resp = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": EDIT_PROMPT.format(
                        file_type=file_type, content=json.dumps(working, indent=2),
                        change_request=change,
                    )}],
                    temperature=0,
                )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            try:
                updated = json.loads(raw)
            except json.JSONDecodeError:
                console.print("  Could not apply that change. Try rephrasing.")
                continue
            self._display_file(updated, file_type, company, product)
            confirm = console.input(
                "\n  Happy with this? (Y to save | describe another change | Enter to cancel): "
            ).strip()
            if confirm.lower() in ("y", "yes"):
                self.storage.save_json(path, updated)
                console.print("  Saved.")
                break
            elif not confirm:
                console.print("  Change discarded.")
                break
            else:
                working = updated

    # ── Intent classifier ─────────────────────────────────────────────────────

    def _stream_print(self, text: str, delay: float = 0.012):
        """
        Prints text character by character — mirrors generate_text_stream()
        and demo_streaming() from class openai_client.py. Uses a small delay
        per character so output flows naturally rather than appearing all at once.
        For pre-known strings (not live API streaming) this simulates the effect.
        """
        import time as _time
        for char in text:
            print(char, end="", flush=True)
            _time.sleep(delay)
        print()

    def _classify_intent(self, message):
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": INTENT_PROMPT.format(message=message)}],
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"intent": "create_posts", "company": "", "product": "", "file_type": ""}

    # ── Image & reference selection loops ─────────────────────────────────────

    def _image_selection_loop(self, company, product, image_mode, receipt):
        img_dir  = self.storage.images_dir(company, product)
        img_dir.mkdir(parents=True, exist_ok=True)
        existing = self.storage.list_images(company, product)

        console.print(f"\n  Image library for [{product}]: {img_dir}")
        if existing:
            console.print(f"  Found {len(existing)} product photo(s):")
            for i, p in enumerate(existing, 1):
                console.print(f"    {i}. {p.name}")
        else:
            console.print("  No product photos in library yet.")

        console.print()
        console.print("  Commands:")
        console.print("    all              — select all photos")
        console.print("    select <number>  — select a specific photo")
        console.print("    add <filepath>   — add a photo to the library")
        console.print("    remove <number>  — remove a photo")
        console.print("    Enter            — done")
        console.print()

        selected = []
        while True:
            cmd = console.input("  > ").strip().strip('"').strip("'")
            if not cmd:
                break
            parts  = cmd.split(None, 1)
            action = parts[0].lower()
            arg    = parts[1].strip() if len(parts) > 1 else ""

            is_path = ("\\" in cmd or "/" in cmd or
                       cmd.lower().endswith((".png", ".jpg", ".jpeg")))
            if is_path and action not in ("add", "select", "remove", "all"):
                action, arg = "add", cmd

            if action in ("all", "select all") or (action == "select" and arg.lower() == "all"):
                for img in existing:
                    if img not in selected:
                        selected.append(img)
                console.print(f"  ✅ Selected all {len(existing)} image(s).")
                break
            elif action == "add" and arg:
                added = self.storage.add_image_to_library(company, product, arg)
                if added:
                    existing = self.storage.list_images(company, product)
                    if added not in selected:
                        selected.append(added)
                        console.print(f"  ✅ Added and selected: {added.name}")
            elif action == "select" and arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(existing):
                    chosen = existing[idx]
                    if chosen not in selected:
                        selected.append(chosen)
                        console.print(f"  ✅ Selected: {chosen.name}")
                    else:
                        console.print(f"  Already selected: {chosen.name}")
                else:
                    console.print(f"  Invalid number. Choose 1–{len(existing)}.")
            elif action == "remove" and arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(existing):
                    target = existing[idx]
                    target.unlink()
                    existing = self.storage.list_images(company, product)
                    selected = [p for p in selected if p != target]
                    console.print(f"  🗑️  Removed: {target.name}")
                else:
                    console.print(f"  Invalid number.")
            else:
                console.print("  all | select <number> | add <filepath> | remove <number> | Enter")

        if image_mode == "Provided Images" and not selected:
            if not existing:
                console.print("\n  No images found — falling back to AI Generated.")
                image_mode = "AI Generated"
                receipt["images"] = "AI Generated"
            else:
                console.print("\n  No images selected — agents will prompt per-post.")

        console.print(f"\n  ✅ Image mode: {image_mode}")
        console.print(f"     Selected: {[p.name for p in selected] or 'none'}")
        return selected

    def _reference_selection_loop(self, company, product):
        ref_dir  = self.storage.references_dir(company, product)
        ref_dir.mkdir(parents=True, exist_ok=True)
        existing = self.storage.list_references(company, product)

        console.print(f"\n  Style references for [{product}]: {ref_dir}")
        if existing:
            console.print(f"  Found {len(existing)} reference(s):")
            for i, r in enumerate(existing, 1):
                console.print(f"    {i}. {r.name}")
        else:
            console.print("  No style references yet.")

        console.print()
        console.print("  Commands: addref <filepath> | rmref <number> | Enter to continue")
        console.print()

        while True:
            cmd    = console.input("  ref> ").strip().strip('"').strip("'")
            if not cmd:
                break
            parts  = cmd.split(None, 1)
            action = parts[0].lower()
            arg    = parts[1].strip() if len(parts) > 1 else ""

            is_path = ("\\" in cmd or "/" in cmd or
                       cmd.lower().endswith((".png", ".jpg", ".jpeg")))
            if is_path and action not in ("addref", "rmref"):
                action, arg = "addref", cmd

            if action == "addref" and arg:
                added = self.storage.add_reference_to_library(company, product, arg)
                if added:
                    existing = self.storage.list_references(company, product)
            elif action == "rmref" and arg.isdigit():
                idx = int(arg) - 1
                if 0 <= idx < len(existing):
                    existing[idx].unlink()
                    existing = self.storage.list_references(company, product)
                    console.print("  🗑️  Removed.")
                else:
                    console.print("  Invalid number.")
            else:
                console.print("  addref <filepath> | rmref <number> | Enter")

        refs = self.storage.list_references(company, product)
        console.print(f"\n  {len(refs)} style reference(s) loaded.")
        return refs


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    GCAL_ID    = os.getenv("GCAL_ID", "primary")
    GCAL_CREDS = os.getenv("GCAL_CREDENTIALS", "credentials.json")

    if not OPENAI_KEY:
        console.print("OPENAI_API_KEY not found. Check your .env file.")
        raise SystemExit(1)

    from agent_storage  import Storage
    from agent_research import ResearchAgent
    from agent_schedule import ScheduleAgent
    from agent_logger   import Logger

    storage    = Storage(Path(__file__).parent / "AI Storage")
    researcher = ResearchAgent(storage=storage, openai_key=OPENAI_KEY)

    agent = SocialMediaAgent(
        openai_key=OPENAI_KEY, storage=storage, researcher=researcher,
        schedule_agent_class=ScheduleAgent, logger_class=Logger,
    )

    try:
        agent.run(openai_key=OPENAI_KEY,
                  gcal_credentials=GCAL_CREDS, gcal_id=GCAL_ID)
    except KeyboardInterrupt:
        console.print("\nInterrupted.")
    except Exception as e:
        console.print(f"\nError: {e}")
        raise
