"""
agent_logger.py
Writes a structured log file to the company's Log Files folder.
Filename: {date} – {company} – {product} – Receipt.txt
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

        log_dir  = self.storage.log_files_dir(company)
        log_dir.mkdir(parents=True, exist_ok=True)

        base_name = f"{today} – {company} – {product} – Receipt"
        log_path  = log_dir / f"{base_name}.txt"

        # Handle duplicate log names
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
            "── RECEIPT ──────────────────────────────────────────────",
        ]
        for k, v in receipt.items():
            lines.append(f"  {k:<20}: {v}")

        lines += [
            "",
            "── COMPANY REPORT (summary) ─────────────────────────────",
            f"  Name:         {company_report.get('company_name')}",
            f"  Industry:     {company_report.get('industry')}",
            f"  Headquarters: {company_report.get('headquarters')}",
            "",
            "── PRODUCT REPORT (summary) ─────────────────────────────",
            f"  Product:      {product_report.get('product_name')}",
            f"  Description:  {product_report.get('product_description','')[:120]}",
            "",
            "── STYLE GUIDE (summary) ────────────────────────────────",
            f"  Vibe:         {style_guide.get('vibe')}",
            f"  Tone:         {style_guide.get('tone')}",
            "",
            "── POSTS GENERATED ──────────────────────────────────────",
        ]

        for i, post in enumerate(posts, 1):
            lines.append(f"\n  Post {i} [{post.get('platform','').upper()}]"
                         f" — Score: {post.get('score', 'N/A')}")
            caption = post.get("caption", "")
            for ln in caption.splitlines():
                lines.append(f"    {ln}")

        lines += [
            "",
            "── OUTPUT ───────────────────────────────────────────────",
            f"  Saved to: {output_dir}",
            "=" * 60,
        ]

        log_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  📝 Log written: {log_path}")
        return log_path
