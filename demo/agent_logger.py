"""
agent_logger.py
Writes two log files to the company's Log Files folder:
  1. {date} – {company} – {product} – Receipt.txt  (main run log)
  2. {date} – {company} – {product} – Audit.txt    (caption + image audit results)
"""

import json, datetime
from pathlib import Path
from agent_storage import Storage


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGER
# Writes one combined log file per run, saved to the company's Log Files folder:
#
#   {date} – {company} – {product} – Receipt.txt
#
# The file has two sections:
#   1. RECEIPT — what was requested, reports used, captions with A/B scores
#   2. CONTENT AUDIT — guardrail results for every post:
#        caption audit (lies/harmful language pass/fail)
#        image audit (pass/fail, reason, correction prompts sent per attempt)
#        overall result
#
# Everything in one place — no need to open two files after a run.
# ═══════════════════════════════════════════════════════════════════════════════
class Logger:
    def __init__(self, storage: Storage):
        self.storage = storage

    def write(self, receipt: dict, company_report: dict, product_report: dict,
              style_guide: dict, posts: list, output_dir: Path) -> Path:
        company = receipt.get("company", "Unknown")
        product = receipt.get("product", "Unknown")
        today   = datetime.date.today().strftime("%Y-%m-%d")

        log_dir = self.storage.log_files_dir(company)
        log_dir.mkdir(parents=True, exist_ok=True)

        # ── Main receipt log ──────────────────────────────────────────────────
        base_name = f"{today} \u2013 {company} \u2013 {product} \u2013 Receipt"
        log_path  = log_dir / f"{base_name}.txt"
        suffix = 2
        while log_path.exists():
            log_path = log_dir / f"{base_name}{suffix}.txt"
            suffix += 1

        lines = [
            "=" * 60,
            "SOCIAL MEDIA POST CREATION LOG",
            "=" * 60,
            f"Date:          {datetime.datetime.now().isoformat()}",
            "",
            "\u2500\u2500 RECEIPT \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        ]
        for k, v in receipt.items():
            if k.startswith("_"):
                continue
            lines.append(f"  {k:<20}: {v}")

        lines += [
            "",
            "\u2500\u2500 COMPANY REPORT (summary) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"  Name:         {company_report.get('company_name')}",
            f"  Industry:     {company_report.get('industry')}",
            f"  Headquarters: {company_report.get('headquarters')}",
            "",
            "\u2500\u2500 PRODUCT REPORT (summary) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"  Product:      {product_report.get('product_name')}",
            f"  Description:  {product_report.get('product_description','')[:120]}",
            "",
            "\u2500\u2500 STYLE GUIDE (summary) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"  Vibe:         {style_guide.get('vibe')}",
            f"  Tone:         {style_guide.get('tone')}",
            "",
            "\u2500\u2500 POSTS GENERATED \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        ]

        for i, post in enumerate(posts, 1):
            lines.append(
                f"\n  Post {i} [{post.get('platform','').upper()}]"
                f" \u2014 Score: {post.get('score', 'N/A')}"
            )
            for ln in post.get("caption", "").splitlines():
                lines.append(f"    {ln}")

        lines += [
            "",
            "── OUTPUT ────────────────────────────────────────────────────────────────",
            f"  Saved to: {output_dir}",
            "",
        ]

        # ── Inline audit section ──────────────────────────────────────────────
        lines += self._build_audit_lines(company, product, posts)

        lines += ["=" * 60]

        log_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  📝 Log written: {log_path}")
        return log_path

    def _build_audit_lines(self, company: str, product: str, posts: list) -> list:
        """Builds the audit section — inlined into the main log."""
        lines = [
            "── CONTENT AUDIT ─────────────────────────────────────────────────────────",
            "",
            "  Two guardrail layers run on every post:",
            "    1. Caption Auditor — checks for lies and harmful language",
            "    2. Image Auditor   — checks logo, facts, and text legibility",
            "",
        ]

        all_passed = True

        for i, post in enumerate(posts, 1):
            platform  = post.get("platform", "?").upper()
            score     = post.get("score", "N/A")
            score_str = f"{score:.1f}/10" if isinstance(score, float) else str(score)

            lines += [
                f"  ── Post {i} [{platform}]  A/B Score: {score_str} ──────────────────────────",
                "",
                "    Caption (first 200 chars):",
                f"    {post.get('caption','')[:200]}...",
                "",
            ]

            # Caption audit
            cap_audit  = post.get("caption_audit_result", {})
            cap_passed = cap_audit.get("passed", True)
            cap_reason = cap_audit.get("reason", "")
            if cap_passed:
                lines.append("    CAPTION AUDIT:  ✅ PASSED")
            else:
                lines.append("    CAPTION AUDIT:  ❌ FAILED")
                lines.append(f"      Reason: {cap_reason}")
                all_passed = False

            # Image audit
            img_audit = post.get("audit_result", {})
            has_image = post.get("image_bytes") is not None
            if not has_image:
                went_nuclear = img_audit.get("went_nuclear", False)
                lines.append("    IMAGE AUDIT:    — No image generated"
                             + (" [nuclear corrections applied]" if went_nuclear else ""))
                img_reason = img_audit.get("reason", "")
                if img_reason:
                    lines.append(f"      Reason: {img_reason}")
            else:
                img_passed   = img_audit.get("passed", True)
                img_reason   = img_audit.get("reason", "")
                went_nuclear = img_audit.get("went_nuclear", False)
                override     = img_audit.get("failed_audit_override", False)
                if override:
                    lines.append("    IMAGE AUDIT:    ⚠️  SAVED (Failed Audit — user override)")
                    all_passed = False
                elif img_passed:
                    lines.append("    IMAGE AUDIT:    ✅ PASSED"
                                 + (" [nuclear corrections applied]" if went_nuclear else ""))
                else:
                    lines.append("    IMAGE AUDIT:    ❌ FAILED (post saved without image)")
                    lines.append(f"      Reason: {img_reason}")
                    all_passed = False

            # Correction history
            corrections = img_audit.get("correction_history", [])
            if corrections:
                lines.append("    CORRECTION PROMPTS SENT:")
                for j, c in enumerate(corrections, 1):
                    lines.append(f"      Attempt {j}: {c}")

            lines.append("")

        lines += [
            f"  OVERALL AUDIT: {'ALL PASSED ✅' if all_passed else 'ISSUES DETECTED ⚠️'}",
            "",
        ]
        return lines
