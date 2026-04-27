"""
agent_posts.py

Three specialized platform agents — each mirrors the TwitterAgent pattern
from class (domo_agents/twitter_agent.py) but adapted for this project.

Each class:
  • Inherits BaseAgent (shared OpenAI client, A/B loop)
  • Has one execute(product_brief, model_name) method
  • Returns a dict: {caption, image_prompt, platform, score}

Parallelism is handled externally by ParallelWorkflow (agent_parallel.py),
exactly like the class notebook — no async/await needed here.
"""

import textwrap
from agent_base import BaseAgent, _safe_json


# ── Helper: build context string from reports ─────────────────────────────────

def build_context(company: dict, product: dict, style: dict,
                  extra: str = "", month: str = "") -> str:
    """
    Converts company/product/style reports into a single context string
    that gets passed to each platform agent's execute() call.
    Called once in the notebook before running the parallel workflow.
    """
    import json
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


# ── Platform agent classes ─────────────────────────────────────────────────────

class InstagramAgent(BaseAgent):
    """
    Specialized agent for Instagram content.
    Generates story-driven captions with hashtags and a DALL-E image prompt.
    Mirrors the TwitterAgent class structure from the class notebook.
    """

    def __init__(self, openai_key: str, review_key: str = None, **kwargs):
        super().__init__(name="Instagram Specialist",
                         openai_key=openai_key, review_key=review_key, **kwargs)

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Generate one Instagram post using the A/B scoring loop.

        Args:
            product_brief (dict): Must contain keys:
                context (str), post_num (int), total_posts (int)
            model_name (str): Ignored here — model is set on the agent itself.

        Returns:
            dict: {caption, image_prompt, platform, score}
        """
        print(f"[{self.name}] Starting Instagram post #{product_brief['post_num']}...")

        instructions = textwrap.dedent("""
            Instagram post requirements:
            - Caption: 150-300 words, engaging, story-driven
            - 5-10 relevant hashtags at the end
            - Clear call-to-action
            - 2-4 relevant emojis placed naturally
            - image_prompt: describe a vivid, on-brand visual for DALL-E
        """)

        result = self._ab_loop(
            platform="instagram",
            post_num=product_brief["post_num"],
            total=product_brief["total_posts"],
            context=product_brief["context"],
            instructions=instructions,
        )

        print(f"[{self.name}] Finished Instagram post #{product_brief['post_num']}.")
        return result


class TwitterAgent(BaseAgent):
    """
    Specialized agent for Twitter/X content.
    Generates punchy, under-280-character tweets with hashtags.
    Directly mirrors the TwitterAgent class from the class notebook.
    """

    def __init__(self, openai_key: str, review_key: str = None, **kwargs):
        super().__init__(name="Twitter Specialist",
                         openai_key=openai_key, review_key=review_key, **kwargs)

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Generate one Twitter post using the A/B scoring loop.

        Args:
            product_brief (dict): Must contain keys:
                context (str), post_num (int), total_posts (int)
            model_name (str): Ignored here — model is set on the agent itself.

        Returns:
            dict: {caption, image_prompt, platform, score}
        """
        print(f"[{self.name}] Starting tweet #{product_brief['post_num']}...")

        instructions = textwrap.dedent("""
            Twitter/X post requirements:
            - Caption: max 280 characters (hard limit)
            - Punchy, direct, conversational tone
            - 1-3 hashtags max
            - image_prompt: leave as empty string
        """)

        result = self._ab_loop(
            platform="twitter",
            post_num=product_brief["post_num"],
            total=product_brief["total_posts"],
            context=product_brief["context"],
            instructions=instructions,
        )

        print(f"[{self.name}] Finished tweet #{product_brief['post_num']}.")
        return result


class BlogAgent(BaseAgent):
    """
    Specialized agent for long-form blog content.
    Generates a full headline + multi-paragraph article.
    Mirrors the BlogPostAgent class structure from the class notebook.
    """

    def __init__(self, openai_key: str, review_key: str = None, **kwargs):
        super().__init__(name="Blog Post Writer",
                         openai_key=openai_key, review_key=review_key, **kwargs)

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Generate one blog post using the A/B scoring loop.

        Args:
            product_brief (dict): Must contain keys:
                context (str), post_num (int), total_posts (int)
            model_name (str): Ignored here — model is set on the agent itself.

        Returns:
            dict: {caption, image_prompt, platform, score}
        """
        print(f"[{self.name}] Starting blog post #{product_brief['post_num']}...")

        instructions = textwrap.dedent("""
            Blog post requirements:
            - Caption field = full blog post: headline + 3-5 paragraphs
            - Use **bold** for subheadings
            - SEO-friendly, informative, engaging tone
            - End with a strong call-to-action paragraph
            - image_prompt: leave as empty string
        """)

        result = self._ab_loop(
            platform="blog",
            post_num=product_brief["post_num"],
            total=product_brief["total_posts"],
            context=product_brief["context"],
            instructions=instructions,
        )

        print(f"[{self.name}] Finished blog post #{product_brief['post_num']}.")
        return result


# ── Platform to Agent class mapping ────────────────────────────────────────────

PLATFORM_AGENTS = {
    "instagram": InstagramAgent,
    "twitter":   TwitterAgent,
    "x":         TwitterAgent,
    "blog":      BlogAgent,
}
