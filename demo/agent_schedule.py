"""
agent_schedule.py
1. Uses GPT to suggest ideal posting dates for the given month/platform.
2. Asks user to confirm or regenerate (up to 3 attempts).
3. Pushes confirmed dates to Google Calendar via the API.
"""

import json, re, asyncio, textwrap, datetime
from pathlib import Path
from openai import AsyncOpenAI


class ScheduleAgent:
    def __init__(self, openai_key: str, credentials_json: str, calendar_id: str):
        self.client         = AsyncOpenAI(api_key=openai_key)
        self.credentials_json = credentials_json
        self.calendar_id    = calendar_id

    # ── Main ─────────────────────────────────────────────────────────────────

    async def run(self, receipt: dict, posts: list[dict], output_dir: Path):
        month    = receipt.get("when", "next month")
        n_posts  = len(posts)
        platform = receipt.get("platforms", "Instagram")
        product  = receipt.get("product", "product")

        suggested_dates = None
        for attempt in range(1, 4):   # max 3 tries
            suggested_dates = await self._suggest_dates(month, n_posts, platform)
            print(f"\n📅 Suggested posting dates ({attempt}/3):")
            for i, d in enumerate(suggested_dates, 1):
                print(f"  Post {i}: {d['date']}  — {d['reason']}")

            ok = input("\nAre these dates good? (Y/n): ").strip().lower()
            if ok in ("", "y", "yes"):
                break
            if attempt == 3:
                print("  ⏭️  Max attempts reached — skipping scheduling.")
                return

        if not suggested_dates:
            return

        # Confirm one last time before pushing
        print("\n🗓️  Pushing to Google Calendar…")
        service = self._get_calendar_service()
        if not service:
            print("  ⚠️  Could not connect to Google Calendar (credentials issue). Skipping.")
            return

        for i, (post, date_info) in enumerate(zip(posts, suggested_dates), 1):
            event = self._build_event(
                title=f"[{platform}] Post {i} — {product}",
                date_str=date_info["date"],
                description=post.get("caption", "")[:500],
            )
            try:
                created = service.events().insert(
                    calendarId=self.calendar_id, body=event
                ).execute()
                print(f"  ✅ Scheduled Post {i}: {created.get('htmlLink')}")
            except Exception as e:
                print(f"  ❌ Failed to schedule Post {i}: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _suggest_dates(self, month: str, n_posts: int, platform: str) -> list[dict]:
        year = datetime.date.today().year
        prompt = textwrap.dedent(f"""
            You are a social media strategist. Suggest {n_posts} ideal posting dates
            for {platform} in {month} {year}.
            Consider: best days of week, avoid weekends if B2B, spread them out.

            Respond ONLY with a JSON array of {n_posts} objects:
            [{{"date": "YYYY-MM-DD", "reason": "brief reason"}}]
            No markdown fences.
        """)
        resp = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        try:
            return json.loads(raw)
        except Exception:
            # Fallback: evenly spaced dates across the month
            return _evenly_spaced(month, year, n_posts)

    def _build_event(self, title: str, date_str: str, description: str) -> dict:
        return {
            "summary":     title,
            "description": description,
            "start":       {"date": date_str},
            "end":         {"date": date_str},
        }

    def _get_calendar_service(self):
        """Return an authorized Google Calendar service, or None on failure."""
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


def _evenly_spaced(month: str, year: int, n: int) -> list[dict]:
    """Fallback: distribute n dates across the month."""
    import calendar as cal
    month_map = {m.lower(): i for i, m in enumerate(
        ["", "January","February","March","April","May","June",
         "July","August","September","October","November","December"]
    ) if m}
    m = month_map.get(month.lower().strip(), datetime.date.today().month)
    _, days_in_month = cal.monthrange(year, m)
    step = days_in_month // (n + 1)
    return [
        {"date": f"{year}-{m:02d}-{(i+1)*step:02d}", "reason": "evenly spaced"}
        for i in range(n)
    ]
