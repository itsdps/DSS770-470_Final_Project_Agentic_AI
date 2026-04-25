"""
agent_storage.py
Handles all local folder creation, reading, and writing.

Folder structure (mirroring your spec):
AI Storage/
  {Company}/
    {Company} Company Report.json
    Products/
      {Product} Product Report.json
    Style Guides/
      {Product} Style Guide.json
    Created Posts/
      {date} - Request {Product}/
        Post 1/  (caption.txt + prompt.txt)
        Post 2/
        Receipt of Creation.txt
    Log Files/
      {date} - {company} - {product} - Receipt.txt
"""

import json, datetime
from pathlib import Path


class Storage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ── Path helpers ──────────────────────────────────────────────────────────

    def company_dir(self, company: str) -> Path:
        return self.root / self._slug(company)

    def company_report_path(self, company: str) -> Path:
        return self.company_dir(company) / f"{company} Company Report.json"

    def products_dir(self, company: str) -> Path:
        return self.company_dir(company) / "Products"

    def product_report_path(self, company: str, product: str) -> Path:
        return self.products_dir(company) / f"{product} Product Report.json"

    def style_guides_dir(self, company: str) -> Path:
        return self.company_dir(company) / "Style Guides"

    def style_guide_path(self, company: str, product: str) -> Path:
        return self.style_guides_dir(company) / f"{product} Style Guide.json"

    def created_posts_dir(self, company: str) -> Path:
        return self.company_dir(company) / "Created Posts"

    def log_files_dir(self, company: str) -> Path:
        return self.company_dir(company) / "Log Files"

    # ── Existence checks ──────────────────────────────────────────────────────

    def company_exists(self, company: str) -> bool:
        return self.company_report_path(company).exists()

    def product_exists(self, company: str, product: str) -> bool:
        return self.product_report_path(company, product).exists()

    def style_guide_exists(self, company: str, product: str) -> bool:
        return self.style_guide_path(company, product).exists()

    def list_style_guides(self, company: str) -> list[str]:
        d = self.style_guides_dir(company)
        if not d.exists():
            return []
        return [f.stem for f in d.glob("*.json")]

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_json(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_company_report(self, company: str) -> dict:
        return self.load_json(self.company_report_path(company))

    def load_product_report(self, company: str, product: str) -> dict:
        return self.load_json(self.product_report_path(company, product))

    def load_style_guide(self, company: str, product: str) -> dict:
        return self.load_json(self.style_guide_path(company, product))

    # ── Write ─────────────────────────────────────────────────────────────────

    def save_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_company_report(self, company: str, data: dict):
        self.save_json(self.company_report_path(company), data)
        print(f"  💾 Company report saved: {self.company_report_path(company)}")

    def save_product_report(self, company: str, product: str, data: dict):
        self.save_json(self.product_report_path(company, product), data)
        print(f"  💾 Product report saved: {self.product_report_path(company, product)}")

    def save_style_guide(self, company: str, product: str, data: dict):
        self.save_json(self.style_guide_path(company, product), data)
        print(f"  💾 Style guide saved: {self.style_guide_path(company, product)}")

    def save_posts(self, company: str, product: str, posts: list, receipt: dict) -> Path:
        today = datetime.date.today().strftime("%Y-%m-%d")
        folder_name = f"{today} – Request {product}"
        out_dir = self.created_posts_dir(company) / folder_name

        # Handle duplicate dates
        base = out_dir
        suffix = 2
        while out_dir.exists():
            out_dir = base.parent / (base.name + f" ({suffix})")
            suffix += 1

        out_dir.mkdir(parents=True, exist_ok=True)

        for i, post in enumerate(posts, 1):
            post_dir = out_dir / f"Post {i}"
            post_dir.mkdir(exist_ok=True)
            (post_dir / "caption.txt").write_text(post.get("caption", ""), encoding="utf-8")
            if post.get("image_prompt"):
                (post_dir / "image_prompt.txt").write_text(post["image_prompt"], encoding="utf-8")

        # Receipt of creation
        receipt_text = _format_receipt(receipt)
        (out_dir / "Receipt of Creation.txt").write_text(receipt_text, encoding="utf-8")

        print(f"  💾 Posts saved: {out_dir}")
        return out_dir

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _slug(name: str) -> str:
        """Keep company/product name as-is for folder (spaces allowed on most OS)."""
        return name.strip()


def _format_receipt(receipt: dict) -> str:
    lines = ["=" * 40, "RECEIPT OF CREATION", "=" * 40]
    for k, v in receipt.items():
        lines.append(f"{k:<22}: {v}")
    lines += ["=" * 40, f"Generated: {datetime.datetime.now().isoformat()}"]
    return "\n".join(lines)
