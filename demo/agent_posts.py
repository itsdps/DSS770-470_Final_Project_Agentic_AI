"""
agent_posts.py
Creates social media posts for each platform in receipt["platforms"].
Each post = {caption, image_prompt, platform, score}.
Uses a separate (cheaper) model to A/B score posts and keep the best one.
Supports: Instagram, Twitter/X, Blog
"""

import json, re, asyncio, textwrap
from openai import AsyncOpenAI


class PostAgent:
    def __init__(self, openai_key: str, review_key: str,
                 main_model: str = "gpt-4o",
                 review_model: str = "gpt-3.5-turbo",
                 ab_threshold: float = 7.5,
                 ab_max_tries: int = 3):
        self.main_client   = AsyncOpenAI(api_key=openai_key)
        self.review_client = AsyncOpenAI(api_key=review_key)
        self.main_model    = main_model
        self.review_model  = review_model
        self.threshold     = ab_threshold
        # Defined here so the module-level functions exist by the time this runs
        self.PLATFORMS = {
            "instagram": _instagram_instructions,
            "twitter":   _twitter_instructions,
            "x":         _twitter_instructions,
            "blog":      _blog_instructions,
        }
        self.max_tries     = ab_max_tries

    # ── Public ────────────────────────────────────────────────────────────────

    async def generate(self, receipt: dict, company_report: dict,
                       product_report: dict, style_guide: dict) -> list[dict]:
        """
        Returns a list of post dicts, one per post number requested.
        Platforms can be a comma-separated string or list.
        """
        platforms = _parse_platforms(receipt.get("platforms", "instagram"))
        n_posts   = int(receipt.get("num_posts", 1))
        extra     = receipt.get("additional_info", "")
        month     = receipt.get("when", "")

        context = _build_context(company_report, product_report, style_guide, extra, month)

        # Generate all posts in parallel (one task per post × platform)
        tasks = []
        for platform in platforms:
            for post_num in range(1, n_posts + 1):
                tasks.append(self._generate_one(platform, post_num, n_posts, context))

        results = await asyncio.gather(*tasks)
        return list(results)

    # ── Private ───────────────────────────────────────────────────────────────

    async def _generate_one(self, platform: str, post_num: int,
                            total: int, context: str) -> dict:
        instructions = self._platform_instructions(platform)
        print(f"  ✍️  [{platform.upper()}] Generating post {post_num}/{total}…")

        best_post  = None
        best_score = 0.0

        for attempt in range(1, self.max_tries + 1):
            candidate = await self._draft_post(platform, post_num, total,
                                               context, instructions)
            score = await self._review_post(candidate, platform, context)
            print(f"      Attempt {attempt}: score {score:.1f}/10")

            if score > best_score:
                best_score = score
                best_post  = candidate
                best_post["score"] = score

            if score >= self.threshold:
                break

        print(f"  ✅  [{platform.upper()}] Post {post_num} — final score {best_score:.1f}")
        return best_post

    async def _draft_post(self, platform: str, post_num: int, total: int,
                          context: str, instructions: str) -> dict:
        prompt = textwrap.dedent(f"""
            You are a social media content creator.
            Create post #{post_num} of {total} for {platform.upper()}.

            {instructions}

            Context (do NOT copy verbatim — draw inspiration):
            {context}

            Respond ONLY with a JSON object:
            {{
              "caption": "...",
              "image_prompt": "Detailed DALL-E image generation prompt (Instagram only, else empty string)",
              "platform": "{platform}"
            }}
            No markdown fences.
        """)
        raw = await self._chat(self.main_client, self.main_model, prompt, temp=0.8)
        data = _safe_json(raw)
        data.setdefault("platform", platform)
        data.setdefault("image_prompt", "")
        return data

    async def _review_post(self, post: dict, platform: str, context: str) -> float:
        prompt = textwrap.dedent(f"""
            You are a strict social media content reviewer.
            Rate this {platform.upper()} post from 0–10 based on:
            - Engagement potential
            - Brand consistency with the context
            - Creativity
            - Call-to-action quality
            - Platform best practices

            Post caption:
            {post.get('caption', '')}

            Context summary:
            {context[:800]}

            Respond ONLY with a JSON object: {{"score": <float 0-10>, "reason": "..."}}
            No markdown fences.
        """)
        raw = await self._chat(self.review_client, self.review_model, prompt, temp=0.2)
        data = _safe_json(raw)
        try:
            return float(data.get("score", 5.0))
        except (TypeError, ValueError):
            return 5.0

    async def _chat(self, client, model: str, prompt: str, temp: float = 0.7) -> str:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        return resp.choices[0].message.content.strip()

    def _platform_instructions(self, platform: str) -> str:
        fn = self.PLATFORMS.get(platform.lower(), _instagram_instructions)
        return fn()


# ── Platform instruction factories ────────────────────────────────────────────

def _instagram_instructions() -> str:
    return textwrap.dedent("""
        Instagram post requirements:
        - Caption: 150–300 words, engaging, story-driven
        - Use 5–10 relevant hashtags at the end
        - Include a clear call-to-action
        - Include 2–4 relevant emojis naturally placed
        - Image prompt: describe a vivid, on-brand visual for DALL-E
    """)

def _twitter_instructions() -> str:
    return textwrap.dedent("""
        Twitter/X post requirements:
        - Caption: max 280 characters (hard limit)
        - Punchy, direct, conversational
        - 1–3 hashtags max
        - Optional: add a poll question as a comment block
        - image_prompt: leave empty string
    """)

def _blog_instructions() -> str:
    return textwrap.dedent("""
        Blog post requirements:
        - Caption field = full blog post: headline + 3–5 paragraphs
        - Include subheadings using **bold**
        - SEO-friendly, informative, engaging tone
        - End with a strong CTA paragraph
        - image_prompt: leave empty string
    """)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_context(company: dict, product: dict, style: dict,
                   extra: str, month: str) -> str:
    return json.dumps({
        "company":       company.get("company_name"),
        "industry":      company.get("industry"),
        "brand_voice":   company.get("brand_voice"),
        "product":       product.get("product_name"),
        "description":   product.get("product_description"),
        "target_market": product.get("target_market"),
        "theme":         product.get("theme"),
        "vibe":          style.get("vibe"),
        "tone":          style.get("tone"),
        "do_list":       style.get("do_list"),
        "dont_list":     style.get("dont_list"),
        "month":         month,
        "extra_request": extra,
    }, indent=2)

def _parse_platforms(platforms) -> list[str]:
    if isinstance(platforms, list):
        return [p.lower().strip() for p in platforms]
    return [p.lower().strip() for p in str(platforms).split(",")]

def _safe_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"caption": text, "image_prompt": "", "platform": "unknown"}
