"""
agent_schedule.py

Handles post scheduling with natural language date input.

Flow:
  1. Ask user when they want to schedule (natural language or Enter to auto-pick)
  2. Parse their input into {date, count} pairs via DATE_PARSE_PROMPT
  3. Fill any missing dates automatically with GPT suggestions
  4. Show final schedule (user-provided + auto-generated clearly labeled)
  5. User confirms before pushing to Google Calendar

Prompt Engineering artifact: DATE_PARSE_PROMPT
  Interprets natural language like "2 on June 5th and 1 two days later"
  into structured date assignments. Good before/after story — vague prompt
  misreads intent, specific prompt with examples handles edge cases correctly.
"""

import json
import re
import textwrap
import datetime
from pathlib import Path
from openai import OpenAI

# ── Editable prompts ──────────────────────────────────────────────────────────

DATE_PARSE_PROMPT = """
You are a scheduling assistant parsing a natural language date request
for scheduling {n_posts} social media post(s) in {month} {year}.

Today's date: {today}

User input: "{user_input}"

Rules:
- If the user gives a single date with no count (e.g. "June 5th"), assign ALL posts to that date.
- If the user gives a count + date (e.g. "1 June 5th" or "2 on June 10th"), assign that many posts.
- If the user gives multiple date instructions, parse each one.
- Dates must be in {year} unless the user specifies otherwise.
- Total assigned posts across all dates should not exceed {n_posts}.

Return ONLY a JSON array of objects, no markdown fences:
[{{"date": "YYYY-MM-DD", "count": <number of posts on this date>, "user_provided": true}}]

If you cannot parse any dates from the input, return an empty array: []
""".strip()

AUTO_DATE_PROMPT = """
You are a social media strategist. Suggest {n_needed} ideal posting date(s)
for {platform} in {month} {year}, avoiding dates already used: {used_dates}.

Spread them out. Consider best days of the week for engagement.

Return ONLY a JSON array, no markdown fences:
[{{"date": "YYYY-MM-DD", "reason": "brief reason"}}]
""".strip()


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULE AGENT
# Handles the post scheduling step after posts are generated.
# Accepts natural language date input ("2 on June 5th and 1 two days later")
# and turns it into specific calendar dates using DATE_PARSE_PROMPT.
#
# If the user gives fewer dates than posts, GPT fills the gaps automatically
# and labels them [auto] so the user knows which ones were chosen for them.
# After confirmation, pushes events to Google Calendar via the API.
#
# DATE_PARSE_PROMPT is the main prompt engineering artifact here —
# same extraction pattern as parse_request() in agent_utils.py.
# ═══════════════════════════════════════════════════════════════════════════════
class ScheduleAgent:
    def __init__(self, openai_key: str, credentials_json: str, calendar_id: str):
        self.client           = OpenAI(api_key=openai_key)
        self.credentials_json = credentials_json
        self.calendar_id      = calendar_id

    # ── Main ─────────────────────────────────────────────────────────────────

    def run(self, receipt: dict, posts: list[dict], output_dir: Path):
        n_posts  = len(posts)
        month    = receipt.get("when", "next month")
        platform = receipt.get("platforms", "Instagram")
        product  = receipt.get("product", "product")
        year     = datetime.date.today().year

        print(f"\n📅 Scheduling {n_posts} post(s) for [{product}]")
        print(f"   Platform: {platform} | Month: {month}")

        # ── Step 1: Get date input from user ──────────────────────────────────
        print("\n  When would you like to schedule these posts?")
        print("  Examples:")
        print("    June 5th              → all posts on June 5th")
        print("    1 June 5th            → 1 post on June 5th (rest auto-picked)")
        print("    2 on June 5 and 1 two days later → 2 on June 5th, 1 on June 7th")
        print("    Enter / 'pick dates'  → GPT picks all dates automatically")
        print()

        user_input = input("  Your scheduling preference: ").strip()

        # ── Step 2: Parse user input ──────────────────────────────────────────
        assigned = []   # list of {date, count, user_provided}

        skip_phrases = ("", "pick", "pick dates", "i don't know",
                        "don't know", "choose", "auto", "you pick")
        if user_input.lower() not in skip_phrases:
            assigned = self._parse_dates(user_input, n_posts, month, year)

        # ── Step 3: Fill missing slots automatically ──────────────────────────
        assigned_count = sum(a["count"] for a in assigned)
        n_missing      = n_posts - assigned_count
        used_dates     = [a["date"] for a in assigned]

        if n_missing > 0:
            auto_dates = self._suggest_dates(
                n_missing, month, year, platform, used_dates
            )
            for d in auto_dates:
                assigned.append({
                    "date":           d["date"],
                    "count":          1,
                    "user_provided":  False,
                    "auto_reason":    d.get("reason", "auto-selected"),
                })
            if n_missing == n_posts:
                print(f"\n  🤖 GPT selected all {n_posts} date(s) automatically:")
            else:
                print(f"\n  🤖 GPT filled {n_missing} remaining date(s) automatically:")
            for a in assigned:
                if not a["user_provided"]:
                    print(f"     {a['date']} — {a.get('auto_reason','')}")

        # ── Step 4: Expand into per-post date list ────────────────────────────
        schedule = []
        for entry in assigned:
            for _ in range(entry["count"]):
                schedule.append({
                    "date":          entry["date"],
                    "user_provided": entry["user_provided"],
                })
        schedule = schedule[:n_posts]   # safety cap

        # ── Step 5: Show final schedule and confirm ───────────────────────────
        print(f"\n📋 Final schedule:")
        for i, (post, slot) in enumerate(zip(posts, schedule), 1):
            label    = "" if slot["user_provided"] else " [auto]"
            platform_tag = post.get("platform", platform).upper()
            print(f"   Post {i} [{platform_tag}]: {slot['date']}{label}")

        confirm = input("\n  Confirm and push to Google Calendar? (Y/n): ").strip().lower()
        if confirm not in ("", "y", "yes"):
            print("  ⏭️  Scheduling cancelled.")
            return

        # ── Step 6: Push to Google Calendar ──────────────────────────────────
        print("\n🗓️  Pushing to Google Calendar…")
        service = self._get_calendar_service()
        if not service:
            print("  ⚠️  Could not connect to Google Calendar. Skipping.")
            return

        for i, (post, slot) in enumerate(zip(posts, schedule), 1):
            event = {
                "summary":     f"[{post.get('platform', platform).upper()}] Post {i} — {product}",
                "description": post.get("caption", "")[:500],
                "start":       {"date": slot["date"]},
                "end":         {"date": slot["date"]},
            }
            try:
                created = service.events().insert(
                    calendarId=self.calendar_id, body=event
                ).execute()
                print(f"  ✅ Post {i} scheduled: {slot['date']} — {created.get('htmlLink')}")
            except Exception as e:
                print(f"  ❌ Failed to schedule Post {i}: {e}")

    # ── Date parsing ──────────────────────────────────────────────────────────

    def _parse_dates(self, user_input: str, n_posts: int,
                     month: str, year: int) -> list[dict]:
        """
        Parses natural language date input into structured {date, count} pairs.
        Uses DATE_PARSE_PROMPT — the main prompt engineering artifact here.
        Same extraction pattern as receipt parsing in agent_utils.py.
        """
        prompt = DATE_PARSE_PROMPT.format(
            n_posts    = n_posts,
            month      = month,
            year       = year,
            today      = datetime.date.today().isoformat(),
            user_input = user_input,
        )
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw    = resp.choices[0].message.content.strip()
            raw    = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)
            # Validate and cap counts
            result = []
            remaining = n_posts
            for entry in parsed:
                if remaining <= 0:
                    break
                count = min(int(entry.get("count", 1)), remaining)
                result.append({
                    "date":          entry["date"],
                    "count":         count,
                    "user_provided": True,
                })
                remaining -= count
            return result
        except Exception as e:
            print(f"  ⚠️  Could not parse dates ({e}) — will auto-select all.")
            return []

    def _suggest_dates(self, n_needed: int, month: str, year: int,
                       platform: str, used_dates: list[str]) -> list[dict]:
        """GPT suggests n_needed dates avoiding already-used ones."""
        prompt = AUTO_DATE_PROMPT.format(
            n_needed   = n_needed,
            platform   = platform,
            month      = month,
            year       = year,
            used_dates = ", ".join(used_dates) if used_dates else "none",
        )
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            return json.loads(raw)
        except Exception:
            return _evenly_spaced(month, year, n_needed, used_dates)

    # ── Calendar ──────────────────────────────────────────────────────────────

    def _get_calendar_service(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_json,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            return build("calendar", "v3", credentials=creds)
        except ImportError:
            print("  ⚠️  google-api-python-client not installed.")
            print("       Run: pip install google-api-python-client google-auth")
            return None
        except Exception as e:
            print(f"  ⚠️  Calendar auth error: {e}")
            return None


# ── Fallback date spreader ────────────────────────────────────────────────────

def _evenly_spaced(month: str, year: int, n: int,
                   used_dates: list[str] = None) -> list[dict]:
    """Fallback if GPT date suggestion fails — evenly spaces dates."""
    import calendar as cal
    month_map = {m.lower(): i for i, m in enumerate(
        ["","January","February","March","April","May","June",
         "July","August","September","October","November","December"]
    ) if m}
    m = month_map.get(month.lower().strip(), datetime.date.today().month)
    _, days_in_month = cal.monthrange(year, m)
    step  = days_in_month // (n + 1)
    taken = set(used_dates or [])
    dates = []
    day   = step
    while len(dates) < n and day <= days_in_month:
        date_str = f"{year}-{m:02d}-{day:02d}"
        if date_str not in taken:
            dates.append({"date": date_str, "reason": "evenly spaced"})
        day += step or 1
    return dates
