"""
agent_storage.py
Handles all local folder creation, reading, and writing.

Folder structure:
AI Storage/
  {Company}/
    {Company} Company Report.json
    Products/
      {Product} Product Report.json
    Style Guides/
      {Product} Style Guide.json
    Images/
      {Product}/        ← per product image library (.png and .jpg only)
        photo1.png
        photo2.jpg
    Created Posts/
      {date} - Request {Product}/
        Post 1/
          caption.txt
          post_image.png   ← real generated or enhanced image (if images enabled)
        Post 2/
        Receipt of Creation.txt
    Log Files/
      {date} - {company} - {product} - Receipt.txt
"""

import json
import shutil
import datetime
from pathlib import Path

# Guardrail: only these extensions are accepted into the Images folder
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


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

    def images_dir(self, company: str, product: str) -> Path:
        """
        Per-product image library folder — actual product photos used in posts.
        Shared across all platforms. Grows over time as the user adds photos.
        """
        return self.company_dir(company) / "Images" / self._slug(product)

    def references_dir(self, company: str, product: str) -> Path:
        """
        Per-product style reference folder — screenshots of posts to imitate.
        Lives inside the Images folder as a subfolder called 'references'.
        These are passed to GPT Vision during caption drafting so the agent
        can see example posts and match their style, humor, and energy.
        Separate from product photos which go in the root images_dir.
        """
        return self.images_dir(company, product) / "references"

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

    def list_companies(self) -> list[str]:
        """
        Returns the names of all company folders that have a company report.
        Used by the research agent to detect duplicates before creating a new folder.
        """
        if not self.root.exists():
            return []
        return [
            d.name for d in self.root.iterdir()
            if d.is_dir() and (d / f"{d.name} Company Report.json").exists()
        ]

    def list_style_guides(self, company: str) -> list[str]:
        d = self.style_guides_dir(company)
        if not d.exists():
            return []
        return [f.stem for f in d.glob("*.json")]

    # ── Image helpers ─────────────────────────────────────────────────────────

    def list_images(self, company: str, product: str) -> list[Path]:
        """
        Returns valid product photo files from the root Images folder.
        Only .png and .jpg/.jpeg — excludes the references/ subfolder.
        These are the actual photos used in post generation (enhance or inspire).
        """
        d = self.images_dir(company, product)
        if not d.exists():
            return []
        return [
            f for f in sorted(d.iterdir())
            if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
        ]

    def list_references(self, company: str, product: str) -> list[Path]:
        """
        Returns style reference screenshots from the references/ subfolder.
        These are screenshots of posts the user wants the agent to imitate —
        passed to GPT Vision during caption drafting using the class pattern
        from 01_langchain_basics.ipynb (HumanMessage with image_url blocks).
        """
        d = self.references_dir(company, product)
        if not d.exists():
            return []
        return [
            f for f in sorted(d.iterdir())
            if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
        ]

    def add_reference_to_library(self, company: str, product: str,
                                  source_path: str) -> Path | None:
        """
        Validates and copies a screenshot into the references/ subfolder.
        Same guardrail as add_image_to_library — .png and .jpg/.jpeg only.
        """
        valid, reason = self.validate_image(source_path)
        if not valid:
            print(f"  ❌ {reason}")
            return None

        dest_dir = self.references_dir(company, product)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(source_path).name

        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            i = 2
            while dest.exists():
                dest = dest_dir / f"{stem}_{i}{suffix}"
                i += 1

        import shutil
        shutil.copy2(source_path, dest)
        print(f"  ✅ Reference added: {dest.name}")
        return dest

    def validate_image(self, file_path: str) -> tuple[bool, str]:
        """
        Guardrail: checks that a file exists and has an allowed extension.
        Returns (True, "") if valid, or (False, reason) if not.
        Called before copying any image into the Images folder.
        """
        p = Path(file_path)
        if not p.exists():
            return False, f"File not found: {file_path}"
        if p.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            return False, (
                f"'{p.suffix}' files are not accepted. "
                f"Please use .png or .jpg/.jpeg only."
            )
        return True, ""

    def add_image_to_library(self, company: str, product: str,
                             source_path: str) -> Path | None:
        """
        Validates and copies an image into the product's Images folder.
        Returns the new Path if successful, None if the file was rejected.
        The original file is never moved — a copy is made into the library.
        """
        valid, reason = self.validate_image(source_path)
        if not valid:
            print(f"  ❌ {reason}")
            return None

        dest_dir = self.images_dir(company, product)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(source_path).name

        # If a file with the same name already exists, add a suffix
        if dest.exists():
            stem   = dest.stem
            suffix = dest.suffix
            i      = 2
            while dest.exists():
                dest = dest_dir / f"{stem}_{i}{suffix}"
                i   += 1

        shutil.copy2(source_path, dest)
        print(f"  ✅ Image added to library: {dest.name}")
        return dest

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

    def save_image(self, post_dir: Path, image_bytes: bytes,
                   filename: str = "post_image.png"):
        """
        Saves a generated or enhanced image into a specific post folder.
        Called by agent_base.py after DALL-E or the image edit endpoint returns bytes.
        The post folder is created by save_posts() first, then this fills it in.
        """
        post_dir.mkdir(parents=True, exist_ok=True)
        dest = post_dir / filename
        dest.write_bytes(image_bytes)
        print(f"  🖼️  Image saved: {dest}")
        return dest

    def save_posts(self, company: str, product: str,
                   posts: list, receipt: dict) -> Path:
        """
        Creates the output folder structure for a batch of posts.
        Each post gets its own subfolder (Post 1, Post 2...) with caption.txt.
        Images are saved separately via save_image() after generation.
        """
        today       = datetime.date.today().strftime("%Y-%m-%d")
        folder_name = f"{today} \u2013 Request {product}"
        out_dir     = self.created_posts_dir(company) / folder_name

        # Handle duplicate dates
        base   = out_dir
        suffix = 2
        while out_dir.exists():
            out_dir = base.parent / (base.name + f" ({suffix})")
            suffix += 1

        out_dir.mkdir(parents=True, exist_ok=True)

        for i, post in enumerate(posts, 1):
            post_dir = out_dir / f"Post {i}"
            post_dir.mkdir(exist_ok=True)
            # Only save caption — no more image_prompt.txt
            # Real images are saved by save_image() in agent_base.py
            (post_dir / "caption.txt").write_text(
                post.get("caption", ""), encoding="utf-8"
            )

        # Receipt of creation
        (out_dir / "Receipt of Creation.txt").write_text(
            _format_receipt(receipt), encoding="utf-8"
        )

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
