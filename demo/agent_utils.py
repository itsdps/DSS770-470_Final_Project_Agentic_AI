"""
agent_utils.py
Shared utilities: request parsing, receipt editor, user prompts.
"""

import re


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
    Example: "Create 3 Instagram posts for Rita's Kiwi Melon in June + Schedule."
    """
    receipt = {
        "company":          "",
        "product":          "",
        "platforms":        "Instagram",
        "num_posts":        "1",
        "when":             "",
        "schedule":         "No",
        "additional_info":  "",
    }

    # Number of posts
    m = re.search(r"\b(\d+)\s+post", text, re.I)
    if m:
        receipt["num_posts"] = m.group(1)

    # Platform(s)
    platforms_found = re.findall(
        r"\b(Instagram|Twitter|X(?=\s)|Facebook|LinkedIn|TikTok|Blog)\b", text, re.I
    )
    if platforms_found:
        receipt["platforms"] = ", ".join(dict.fromkeys(p.capitalize() for p in platforms_found))

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
    m = re.search(r"\bfor\s+(.+?)(?:\s+in\b|\s*\+|\s*\.|\s*$)", text, re.I)
    if m:
        entity = m.group(1).strip()
        # Try to split into company + product heuristically:
        # "Rita's Kiwi Melon" → company "Rita's", product "Kiwi Melon"
        parts = entity.split()
        if len(parts) >= 3:
            receipt["company"]  = " ".join(parts[:2])   # first 2 words
            receipt["product"]  = " ".join(parts[2:])   # rest
        elif len(parts) == 2:
            receipt["company"]  = parts[0]
            receipt["product"]  = parts[1]
        else:
            receipt["company"]  = entity

    # Additional info — grab sentences after the main request
    m = re.search(r"\.\s+(.+)$", text.strip())
    if m:
        receipt["additional_info"] = m.group(1).strip()
    elif re.search(r"interactive|funny|seasonal|urgent", text, re.I):
        extras = re.findall(r"(?:make it|please)\s+(.+?)(?:\.|$)", text, re.I)
        receipt["additional_info"] = "; ".join(extras)

    return receipt


# ── Interactive receipt editor ────────────────────────────────────────────────

def interactive_receipt_editor(receipt: dict) -> dict:
    """
    Show receipt and let user modify fields until they confirm.
    Commands: modify <field> to <value>  |  Enter / 'all good'
    """
    print_receipt(receipt)
    print("\n  ✏️  To change a field type:  modify <field> to <value>")
    print("  Press Enter or type 'all good' to confirm.\n")

    while True:
        cmd = input("  > ").strip()
        if not cmd or cmd.lower() in ("all good", "looks good", "ok", "done", "yes"):
            break

        m = re.match(r"modify\s+(.+?)\s+to\s+(.+)", cmd, re.I)
        if m:
            field, value = m.group(1).strip().lower(), m.group(2).strip()
            # Find closest key
            key_map = {k.lower().replace(" ", "_"): k for k in receipt}
            key_map.update({k.lower(): k for k in receipt})
            matched_key = key_map.get(field.replace(" ", "_")) or key_map.get(field)
            if matched_key:
                receipt[matched_key] = value
                print_receipt(receipt)
            else:
                print(f"  ❌ Unknown field '{field}'. Valid fields: {', '.join(receipt.keys())}")
        else:
            print("  Usage: modify <field> to <value>  |  Enter to confirm")

    return receipt
