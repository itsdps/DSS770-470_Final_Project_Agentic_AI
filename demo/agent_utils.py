"""
agent_utils.py
Shared utilities: request parsing, receipt editor, user prompts.
"""

import re


# ── Image mode defaults per platform ─────────────────────────────────────────
# Clear dict you can edit if you want to change defaults.
# "Provided Images" = use stored photos first (falls back to AI Generated if none)
# "AI Generated"    = always use DALL-E
# "No"              = no image generated

IMAGE_PLATFORM_DEFAULTS = {
    "instagram": "Provided Images",
    "twitter":   "No",
    "x":         "No",
    "blog":      "No",
    "facebook":  "Provided Images",
    "linkedin":  "No",
    "tiktok":    "Provided Images",
}


# ── User interaction ──────────────────────────────────────────────────────────

def confirm(prompt: str, default_yes: bool = True) -> bool:
    """Ask a yes/no question. Returns True for yes."""
    answer = input(f"\n{prompt} ").strip().lower()
    if not answer:
        return default_yes
    return answer in ("y", "yes")


def multiline_input(prompt: str) -> str:
    """Read multiple lines until blank line."""
    print(prompt)
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def print_section(title: str):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


def print_receipt(receipt: dict):
    print("\n" + "=" * 45)
    print("  📋  RECEIPT")
    print("=" * 45)
    for k, v in receipt.items():
        print(f"  {k:<22}: {v}")
    print("=" * 45)


# ── Request parser ────────────────────────────────────────────────────────────

def parse_request(text: str) -> dict:
    """
    Parse a natural language request into a receipt dict.

    Examples:
      "Create 3 Instagram posts for Rita's Kiwi Melon in June + Schedule."
        → images: "Provided Images"  (Instagram default)

      "Create 2 Instagram posts without image for Rita's Kiwi Melon"
        → images: "No"  (explicit override)

      "Create 1 Blog post with image for Nike Air Max"
        → images: "Provided Images"  (explicit override on blog)

      "Create 3 Instagram posts AI generated images for Rita's Kiwi Melon"
        → images: "AI Generated"  (explicit override)
    """
    receipt = {
        "company":         "",
        "product":         "",
        "platforms":       "Instagram",
        "num_posts":       "1",
        "when":            "",
        "schedule":        "No",
        "images":          "",   # filled in below after platform is known
        "additional_info": "",
    }

    # Number of posts — finds ALL "N platform posts" patterns and sums them
    # e.g. "1 Instagram post and 2 Twitter posts" → num_posts = 3
    all_counts = re.findall(r"\b(\d+)\s+(?:\w+\s+)?posts?", text, re.I)
    if all_counts:
        receipt["num_posts"] = str(sum(int(n) for n in all_counts))

    # Platform(s)
    platforms_found = re.findall(
        r"\b(Instagram|Twitter|X(?=\s)|Facebook|LinkedIn|TikTok|Blog)\b", text, re.I
    )
    if platforms_found:
        receipt["platforms"] = ", ".join(
            dict.fromkeys(p.capitalize() for p in platforms_found)
        )

    # Month / time
    months = (r"January|February|March|April|May|June|July|"
              r"August|September|October|November|December")
    m = re.search(months, text, re.I)
    if m:
        receipt["when"] = m.group(0).capitalize()

    # Schedule flag
    if re.search(r"\+\s*schedule|schedule\s*\+|schedule them|auto.?schedule", text, re.I):
        receipt["schedule"] = "Yes"

    # Company & product — look for "for <Company> <Product>"
    # Company boundary: word ending in apostrophe+s (e.g. "Rita's") or first word
    m = re.search(r"\bfor\s+(.+?)(?:\s+in\b|\s*\+|\s*\.|\s*$)", text, re.I)
    if m:
        entity = m.group(1).strip()
        parts  = entity.split()
        # Find company boundary — word ending in "'s" is likely the company name
        apostrophe_idx = next(
            (i for i, p in enumerate(parts) if p.endswith("'s") or p.endswith("\u2019s")),
            None
        )
        if apostrophe_idx is not None and apostrophe_idx + 1 < len(parts):
            # e.g. "Rita's Kiwi Melon" → company="Rita's", product="Kiwi Melon"
            receipt["company"] = parts[apostrophe_idx]
            receipt["product"] = " ".join(parts[apostrophe_idx + 1:])
        elif len(parts) >= 3:
            receipt["company"] = " ".join(parts[:2])
            receipt["product"] = " ".join(parts[2:])
        elif len(parts) == 2:
            receipt["company"] = parts[0]
            receipt["product"] = parts[1]
        else:
            receipt["company"] = entity

    # Image mode — parse AFTER platform is known
    receipt["images"] = _parse_image_mode(text, receipt["platforms"])

    # Additional info
    m = re.search(r"\.\s+(.+)$", text.strip())
    if m:
        receipt["additional_info"] = m.group(1).strip()
    elif re.search(r"interactive|funny|seasonal|urgent", text, re.I):
        extras = re.findall(r"(?:make it|please)\s+(.+?)(?:\.|$)", text, re.I)
        receipt["additional_info"] = "; ".join(extras)

    return receipt


def _parse_image_mode(text: str, platforms_str: str) -> str:
    """
    Determine the image mode from the request text.

    Priority order:
      1. Explicit "without image" / "no image"     → "No"
      2. Explicit "AI generated image(s)"           → "AI Generated"
      3. Explicit "with image" (any platform)       → "Provided Images"
      4. Platform default from IMAGE_PLATFORM_DEFAULTS
         (uses the first platform if multiple)

    This function is separated out so it's easy to find and improve
    for the prompt engineering section of the report.
    """
    text_lower = text.lower()

    # Explicit NO
    if re.search(r"without\s+image|no\s+image|without\s+photo", text_lower):
        return "No"

    # Explicit AI Generated
    if re.search(r"ai.?generat\w+\s+image|generat\w+\s+image|dall.?e", text_lower):
        return "AI Generated"

    # Explicit "with image" — defaults to Provided Images
    if re.search(r"with\s+image|with\s+photo|include\s+image", text_lower):
        return "Provided Images"

    # Fall back to platform default
    # Use the first platform listed if multiple
    first_platform = platforms_str.split(",")[0].strip().lower()
    return IMAGE_PLATFORM_DEFAULTS.get(first_platform, "No")


# ── Interactive receipt editor ────────────────────────────────────────────────

def interactive_receipt_editor(receipt: dict) -> dict:
    """
    Show receipt and let user modify fields until they confirm.
    Commands: modify <field> to <value>  |  Enter / 'all good'

    Valid values for the images field:
      "Provided Images", "AI Generated", "No"
    """
    print_receipt(receipt)
    print("\n  ✏️  To change a field type:  modify <field> to <value>")
    print("  For the images field, valid values are:")
    print("    Provided Images  |  AI Generated  |  No")
    print("  Press Enter or type 'all good' to confirm.\n")

    while True:
        cmd = input("  > ").strip()
        if not cmd or cmd.lower() in ("all good", "looks good", "ok", "done", "yes"):
            break

        m = re.match(r"modify\s+(.+?)\s+to\s+(.+)", cmd, re.I)
        if m:
            field, value = m.group(1).strip().lower(), m.group(2).strip()

            # Find closest matching key
            key_map = {k.lower().replace(" ", "_"): k for k in receipt}
            key_map.update({k.lower(): k for k in receipt})
            matched_key = key_map.get(field.replace(" ", "_")) or key_map.get(field)

            if matched_key:
                # Guardrail on the images field
                if matched_key == "images":
                    normalized = _normalize_image_value(value)
                    if not normalized:
                        print(f"  ❌ '{value}' is not valid for images.")
                        print("     Use: Provided Images | AI Generated | No")
                        continue
                    value = normalized

                receipt[matched_key] = value
                print_receipt(receipt)
            else:
                print(
                    f"  ❌ Unknown field '{field}'. "
                    f"Valid fields: {', '.join(receipt.keys())}"
                )
        else:
            print("  Usage: modify <field> to <value>  |  Enter to confirm")

    return receipt


def _normalize_image_value(value: str) -> str | None:
    """
    Accept flexible user input for the images field and normalize it.
    Returns the canonical value or None if unrecognized.

    Examples:
      "provided"     → "Provided Images"
      "ai"           → "AI Generated"
      "no" / "none"  → "No"
    """
    v = value.lower().strip()
    if v in ("provided images", "provided", "yes", "photos"):
        return "Provided Images"
    if v in ("ai generated", "ai", "dall-e", "generate", "generated"):
        return "AI Generated"
    if v in ("no", "none", "skip"):
        return "No"
    return None
