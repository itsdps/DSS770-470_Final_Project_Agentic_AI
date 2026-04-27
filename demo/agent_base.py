"""
agent_base.py

Base class for all platform agents — mirrors the BaseAgent pattern from class.
Each platform agent (Instagram, Twitter, Blog) inherits from this and only
needs to implement its own execute() method.
"""

from openai import OpenAI   # sync client — threads handle parallelism, not async


class BaseAgent:
    """
    Provides a shared OpenAI client and agent name to all platform agents.
    Mirrors the BaseAgent from class (domo_agents/base_agent.py).
    """

    def __init__(self, name: str, openai_key: str,
                 review_key: str = None,
                 main_model: str = "gpt-4o",
                 review_model: str = "gpt-3.5-turbo",
                 ab_threshold: float = 7.5,
                 ab_max_tries: int = 3):
        self.name          = name
        self.openai_client = OpenAI(api_key=openai_key)          # main drafting client
        self.review_client = OpenAI(api_key=review_key or openai_key)  # A/B reviewer
        self.main_model    = main_model
        self.review_model  = review_model
        self.threshold     = ab_threshold
        self.max_tries     = ab_max_tries

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Override in each platform subclass.
        Must return a dict: {caption, image_prompt, platform, score}
        """
        raise NotImplementedError(f"{self.name} must implement execute()")

    # ── Shared helpers available to all subclasses ────────────────────────────

    def _chat(self, prompt: str, model: str = None, temp: float = 0.7) -> str:
        """Synchronous OpenAI call — safe to call from threads."""
        resp = self.openai_client.chat.completions.create(
            model=model or self.main_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        return resp.choices[0].message.content.strip()

    def _review_chat(self, prompt: str, temp: float = 0.2) -> str:
        """Separate call using the cheaper review model for A/B scoring."""
        resp = self.review_client.chat.completions.create(
            model=self.review_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        return resp.choices[0].message.content.strip()

    def _ab_loop(self, platform: str, post_num: int, total: int,
                 context: str, instructions: str) -> dict:
        """
        A/B scoring loop shared by all platform agents:
          1. Draft a post candidate
          2. Score it with the reviewer model
          3. Keep the best score; stop early if threshold is reached
          4. Repeat up to max_tries times
        """
        import re, json

        best_post  = None
        best_score = 0.0

        for attempt in range(1, self.max_tries + 1):
            # ── Draft ──────────────────────────────────────────────────────
            draft_prompt = (
                f"You are a social media content creator.\n"
                f"Create post #{post_num} of {total} for {platform.upper()}.\n\n"
                f"{instructions}\n\n"
                f"Context (draw inspiration, do NOT copy verbatim):\n{context}\n\n"
                f"Respond ONLY with a JSON object — no markdown fences:\n"
                f'{{"caption": "...", '
                f'"image_prompt": "DALL-E prompt (Instagram only, else empty string)", '
                f'"platform": "{platform}"}}'
            )
            raw = self._chat(draft_prompt, temp=0.8)
            candidate = _safe_json(raw)
            candidate.setdefault("platform", platform)
            candidate.setdefault("image_prompt", "")

            # ── Review / score ─────────────────────────────────────────────
            review_prompt = (
                f"You are a strict social media content reviewer.\n"
                f"Rate this {platform.upper()} post from 0–10 on:\n"
                f"- Engagement potential\n"
                f"- Brand consistency\n"
                f"- Creativity\n"
                f"- Call-to-action quality\n"
                f"- Platform best practices\n\n"
                f"Post caption:\n{candidate.get('caption', '')}\n\n"
                f"Context summary:\n{context[:800]}\n\n"
                f'Respond ONLY with JSON — no markdown fences:\n'
                f'{{"score": <float 0-10>, "reason": "..."}}'
            )
            review_raw = self._review_chat(review_prompt)
            review_data = _safe_json(review_raw)
            try:
                score = float(review_data.get("score", 5.0))
            except (TypeError, ValueError):
                score = 5.0

            print(f"      [{self.name}] Post {post_num} — attempt {attempt}: score {score:.1f}/10")

            if score > best_score:
                best_score = score
                best_post  = candidate
                best_post["score"] = score

            if score >= self.threshold:
                break

        print(f"  ✅  [{self.name}] Post {post_num} done — final score {best_score:.1f}")
        return best_post


# ── Module-level helper (used by BaseAgent and subclasses) ────────────────────

def _safe_json(text: str) -> dict:
    import re, json
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"caption": text, "image_prompt": "", "platform": "unknown"}
