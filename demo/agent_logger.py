"""
agent_logger.py
Writes two log files to the company's Log Files folder:
  1. {date} – {company} – {product} – Receipt.txt  (main run log)
  2. {date} – {company} – {product} – Audit.txt    (caption + image audit results)
"""

import json, datetime
from pathlib import Path
from agent_storage import Storage


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
            "\u2500\u2500 OUTPUT \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"  Saved to: {output_dir}",
            "=" * 60,
        ]

        log_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  \U0001f4dd Log written: {log_path}")

        # ── Audit log ─────────────────────────────────────────────────────────
        audit_path = self._write_audit_log(
            log_dir, today, company, product, posts, suffix
        )
        return log_path

    def _write_audit_log(self, log_dir: Path, today: str,
                         company: str, product: str,
                         posts: list, suffix: int) -> Path:
        """
        Writes a dedicated audit log covering caption and image audit results
        for every post. Useful for the ethics/guardrails section of the report.
        """
        base_name  = f"{today} \u2013 {company} \u2013 {product} \u2013 Audit"
        audit_path = log_dir / f"{base_name}.txt"
        s = suffix
        while audit_path.exists():
            audit_path = log_dir / f"{base_name}{s}.txt"
            s += 1

        lines = [
            "=" * 60,
            "CONTENT AUDIT LOG",
            "=" * 60,
            f"Date:    {datetime.datetime.now().isoformat()}",
            f"Company: {company}",
            f"Product: {product}",
            "",
            "This log records the output of two guardrail layers:",
            "  1. Caption Auditor  \u2014 checks for lies and harmful language",
            "  2. Image Auditor    \u2014 checks logo, facts, and text legibility",
            "=" * 60,
        ]

        all_passed = True

        for i, post in enumerate(posts, 1):
            platform = post.get("platform", "?").upper()
            score    = post.get("score", "N/A")
            score_str = f"{score:.1f}/10" if isinstance(score, float) else str(score)

            lines += [
                "",
                f"\u2500\u2500 POST {i} [{platform}]  A/B Score: {score_str} \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
                "",
                "  Caption (first 200 chars):",
                f"  {post.get('caption','')[:200]}...",
                "",
            ]

            # Caption audit result
            cap_audit = post.get("caption_audit_result", {})
            cap_passed = cap_audit.get("passed", True)
            cap_reason = cap_audit.get("reason", "")
            if cap_passed:
                lines.append("  CAPTION AUDIT:  \u2705 PASSED")
            else:
                lines.append(f"  CAPTION AUDIT:  \u274c FAILED")
                lines.append(f"    Reason: {cap_reason}")
                all_passed = False

            # Image audit result
            img_audit = post.get("audit_result", {})
            has_image = post.get("image_bytes") is not None
            if not has_image:
                lines.append("  IMAGE AUDIT:    \u2014 No image generated")
            else:
                img_passed = img_audit.get("passed", True)
                img_reason = img_audit.get("reason", "")
                if img_passed:
                    lines.append("  IMAGE AUDIT:    \u2705 PASSED")
                else:
                    lines.append(f"  IMAGE AUDIT:    \u274c FAILED (post saved without image)")
                    lines.append(f"    Reason: {img_reason}")
                    all_passed = False

        lines += [
            "",
            "=" * 60,
            f"OVERALL AUDIT RESULT: {'ALL PASSED \u2705' if all_passed else 'ISSUES DETECTED \u26a0\ufe0f'}",
            "=" * 60,
        ]

        audit_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  \U0001f4cb Audit log written: {audit_path}")
        return audit_path
