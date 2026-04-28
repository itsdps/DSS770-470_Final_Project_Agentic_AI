"""
agent_posts.py

Three specialized platform agents — each mirrors the TwitterAgent pattern
from class (domo_agents/twitter_agent.py) but adapted for this project.

Each class:
  • Inherits BaseAgent (shared OpenAI client, A/B loop, image methods)
  • Has one execute(product_brief, model_name) method
  • Returns a dict: {caption, image_context, image_bytes, platform, score}

Image generation happens AFTER the caption A/B loop in each execute() method.
Caption always comes first so it can be passed as context to the image methods,
keeping the caption and image cohesive as a single post.

Parallelism is handled externally by ParallelWorkflow (agent_parallel.py),
exactly like the class notebook — no async/await needed here.
"""

import json
import textwrap
from pathlib import Path

from agent_base import BaseAgent, _safe_json


# ── Helper: build context string from reports ─────────────────────────────────

def build_context(company: dict, product: dict, style: dict,
                  extra: str = "", month: str = "") -> str:
    """
    Converts company/product/style reports into a single context string
    passed to each platform agent's execute() call.
    Called once in the notebook before running the parallel workflow.
    """
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


def parse_platforms(platforms) -> list[str]:
    """Turn 'Instagram, Twitter' or ['Instagram','Twitter'] into ['instagram','twitter']."""
    if isinstance(platforms, list):
        return [p.lower().strip() for p in platforms]
    return [p.lower().strip() for p in str(platforms).split(",")]


# ── Shared image handling helper ──────────────────────────────────────────────

def _handle_image(agent: BaseAgent, post: dict, image_mode: str,
                  selected_images: list, style_vibe: str) -> bytes | None:
    """
    Called at the end of each execute() method after the caption is final.
    Routes to the right image method based on image_mode.

    Args:
        agent:           The platform agent (has access to _generate_image etc.)
        post:            The post dict from _ab_loop() — contains caption + image_context
        image_mode:      "Provided Images", "AI Generated", or "No"
        selected_images: List of Path objects chosen by the user in the notebook
        style_vibe:      Brand vibe string from the style guide

    Returns:
        Raw PNG bytes or None.
    """
    caption       = post.get("caption", "")
    image_context = post.get("image_context", "")

    if image_mode == "No":
        return None

    if image_mode == "Provided Images":
        if not selected_images:
            # No images available — fall back to AI Generated automatically
            print(f"  ℹ️  No images selected, falling back to AI Generated…")
            return agent._generate_image(caption, image_context, style_vibe)

        # Ask user: enhance real photo or use as inspiration?
        print(f"\n  📸 Selected images: {[p.name for p in selected_images]}")
        print("  How would you like to use these images?")
        print("  1. Enhance real photo with AI effects (keeps the real photo)")
        print("  2. Use as inspiration for a new AI image")
        choice = input("  Enter 1 or 2 (default 1): ").strip()

        if choice == "2":
            return agent._generate_image(
                caption, image_context, style_vibe,
                reference_images=selected_images
            )
        else:
            # Default to enhance — use the first selected image
            return agent._enhance_image(
                source_image_path=selected_images[0],
                caption=caption,
                image_context=image_context,
                style_vibe=style_vibe,
            )

    if image_mode == "AI Generated":
        return agent._generate_image(
            caption, image_context, style_vibe,
            reference_images=selected_images or None
        )

    return None


# ── Platform agent classes ────────────────────────────────────────────────────

class InstagramAgent(BaseAgent):
    """
    Specialized agent for Instagram content.
    Generates story-driven captions with hashtags.
    Default image mode: Provided Images.
    Mirrors the TwitterAgent class structure from the class notebook.
    """

    def __init__(self, openai_key: str, review_key: str = None, **kwargs):
        super().__init__(name="Instagram Specialist",
                         openai_key=openai_key, review_key=review_key, **kwargs)

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Generate one Instagram post — caption first, then image.

        product_brief keys:
            context (str)         — company/product/style context
            post_num (int)        — which post number this is
            total_posts (int)     — total posts being generated
            image_mode (str)      — "Provided Images" | "AI Generated" | "No"
            selected_images (list)— list of Path objects chosen by user
            style_vibe (str)      — brand vibe from style guide

        Returns:
            dict: {caption, image_context, image_bytes, platform, score}
        """
        print(f"[{self.name}] Starting Instagram post #{product_brief['post_num']}...")

        instructions = textwrap.dedent("""
            Instagram post requirements:
            - Caption: 150-300 words, engaging, story-driven
            - 5-10 relevant hashtags at the end
            - Clear call-to-action
            - 2-4 relevant emojis placed naturally
        """)

        # ── Step 1: Generate caption via A/B loop ─────────────────────────────
        post = self._ab_loop(
            platform="instagram",
            post_num=product_brief["post_num"],
            total=product_brief["total_posts"],
            context=product_brief["context"],
            instructions=instructions,
        )

        # ── Step 2: Generate image using final caption as context ─────────────
        # Caption comes first so the image matches what the post is saying
        post["image_bytes"] = _handle_image(
            agent=self,
            post=post,
            image_mode=product_brief.get("image_mode", "Provided Images"),
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
        )

        print(f"[{self.name}] Finished Instagram post #{product_brief['post_num']}.")
        return post


class TwitterAgent(BaseAgent):
    """
    Specialized agent for Twitter/X content.
    Generates punchy, under-280-character tweets with hashtags.
    Default image mode: No. Supports images if explicitly requested.
    Directly mirrors the TwitterAgent class from the class notebook.
    """

    def __init__(self, openai_key: str, review_key: str = None, **kwargs):
        super().__init__(name="Twitter Specialist",
                         openai_key=openai_key, review_key=review_key, **kwargs)

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Generate one Twitter post — caption first, then image if requested.

        product_brief keys: same as InstagramAgent.execute()

        Returns:
            dict: {caption, image_context, image_bytes, platform, score}
        """
        print(f"[{self.name}] Starting tweet #{product_brief['post_num']}...")

        instructions = textwrap.dedent("""
            Twitter/X post requirements:
            - Caption: max 280 characters (hard limit — count carefully)
            - Punchy, direct, conversational tone
            - 1-3 hashtags max
        """)

        # ── Step 1: Caption ───────────────────────────────────────────────────
        post = self._ab_loop(
            platform="twitter",
            post_num=product_brief["post_num"],
            total=product_brief["total_posts"],
            context=product_brief["context"],
            instructions=instructions,
        )

        # ── Step 2: Image (No by default, but respects explicit request) ──────
        post["image_bytes"] = _handle_image(
            agent=self,
            post=post,
            image_mode=product_brief.get("image_mode", "No"),
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
        )

        print(f"[{self.name}] Finished tweet #{product_brief['post_num']}.")
        return post


class BlogAgent(BaseAgent):
    """
    Specialized agent for long-form blog content.
    Generates a full headline + multi-paragraph article.
    Default image mode: No. Supports images if explicitly requested.
    Mirrors the BlogPostAgent class structure from the class notebook.
    """

    def __init__(self, openai_key: str, review_key: str = None, **kwargs):
        super().__init__(name="Blog Post Writer",
                         openai_key=openai_key, review_key=review_key, **kwargs)

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Generate one blog post — caption first, then image if requested.

        product_brief keys: same as InstagramAgent.execute()

        Returns:
            dict: {caption, image_context, image_bytes, platform, score}
        """
        print(f"[{self.name}] Starting blog post #{product_brief['post_num']}...")

        instructions = textwrap.dedent("""
            Blog post requirements:
            - Caption field = full blog post: headline + 3-5 paragraphs
            - Use **bold** for subheadings
            - SEO-friendly, informative, engaging tone
            - End with a strong call-to-action paragraph
        """)

        # ── Step 1: Caption ───────────────────────────────────────────────────
        post = self._ab_loop(
            platform="blog",
            post_num=product_brief["post_num"],
            total=product_brief["total_posts"],
            context=product_brief["context"],
            instructions=instructions,
        )

        # ── Step 2: Image (No by default, but respects explicit request) ──────
        post["image_bytes"] = _handle_image(
            agent=self,
            post=post,
            image_mode=product_brief.get("image_mode", "No"),
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
        )

        print(f"[{self.name}] Finished blog post #{product_brief['post_num']}.")
        return post


# ── Platform to Agent class mapping ──────────────────────────────────────────

PLATFORM_AGENTS = {
    "instagram": InstagramAgent,
    "twitter":   TwitterAgent,
    "x":         TwitterAgent,
    "blog":      BlogAgent,
}
