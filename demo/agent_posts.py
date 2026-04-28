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
# Module-level counter so parallel agents cycle through images without repeating.
# Initialized randomly so each run starts at a different image.
# Thread-safe — multiple platform agents run simultaneously via ThreadPoolExecutor.
import random as _random
_image_counter      = _random.randint(0, 999)
_image_counter_lock = __import__("threading").Lock()

def _pick_image(selected_images: list):
    """
    Cycles through selected images in order so multiple posts each get
    a different photo rather than always using the first one.
    Thread-safe so parallel agents don't all pick the same image.
    """
    global _image_counter
    with _image_counter_lock:
        idx = _image_counter % len(selected_images)
        _image_counter += 1
    return selected_images[idx]



def _run_caption_audit_loop(agent: BaseAgent, platform: str,
                            post_num: int, total: int, context: str,
                            instructions: str,
                            reference_images: list | None = None) -> dict:
    """
    Runs _ab_loop() then audits the caption for lies and harmful language.
    If audit fails, retries the full _ab_loop() up to MAX_AUDIT_RETRIES times.
    Mirrors the orchestrator_loop.py revision pattern from class.

    Returns the best post dict with caption_audit_result stored on it.
    """
    from agent_base import MAX_AUDIT_RETRIES

    caption_rejection = ""

    for attempt in range(MAX_AUDIT_RETRIES + 1):
        # Generate caption via A/B loop, passing any previous rejection as context
        extra_instructions = (
            f"{instructions}\n\nCORRECTION REQUIRED from previous attempt:\n"
            f"{caption_rejection}\nDo NOT repeat this issue."
        ) if caption_rejection else instructions

        post = agent._ab_loop(
            platform=platform,
            post_num=post_num,
            total=total,
            context=context,
            instructions=extra_instructions,
            reference_images=reference_images,
        )

        # Audit caption
        print(f"  📋 Auditing caption (attempt {attempt + 1}/{MAX_AUDIT_RETRIES + 1})…")
        audit = agent._audit_caption(
            caption=post.get("caption", ""),
            platform=platform,
            context=context[:400],
        )

        post["caption_audit_result"] = audit

        if audit["passed"]:
            print("  ✅ Caption passed audit.")
            return post
        else:
            print(f"  ⚠️  Caption audit failed: {audit['reason']}")
            if attempt < MAX_AUDIT_RETRIES:
                print("  🔄 Regenerating caption…")
                caption_rejection = audit["reason"]
            else:
                print(f"  ❌ Caption failed audit after {MAX_AUDIT_RETRIES + 1} attempts.")
                # Return the post anyway but with failed audit noted
                return post

    return post


def _handle_image(agent: BaseAgent, post: dict, image_mode: str,
                  selected_images: list, style_vibe: str,
                  context: str = "",
                  logo_description: str = "",
                  additional_notes: str = "") -> tuple:
    """
    Routes to the right image method, then runs the audit loop.
    Always returns a tuple: (image_bytes | None, audit_result dict).
    Audit loop retries up to MAX_AUDIT_RETRIES times on failure.
    """
    from agent_base import MAX_AUDIT_RETRIES

    caption       = post.get("caption", "")
    image_context = post.get("image_context", "")
    use_enhance   = True
    chosen        = None

    # Store on agent so _build_image_prompt can access logo/notes
    agent._logo_description  = logo_description
    agent._additional_notes  = additional_notes

    # ── No image ─────────────────────────────────────────────────────────────
    if image_mode == "No":
        return None, {"passed": True, "reason": ""}

    # ── Provided Images — ask once before the audit loop ─────────────────────
    if image_mode == "Provided Images":
        if not selected_images:
            print("  ℹ️  No images selected, falling back to AI Generated…")
            image_mode = "AI Generated"
        else:
            chosen = _pick_image(selected_images)
            print(f"\n  📸 Using image: {chosen.name}")
            print("  1. Enhance real photo  2. Use as inspiration")
            choice      = input("  Enter 1 or 2 (default 1): ").strip()
            use_enhance = (choice != "2")

    # ── Audit loop — mirrors orchestrator_loop.py revision pattern ──────────
    # previous_rejection is passed directly into _enhance_image/_generate_image
    # so the correction appears at the TOP of the instruction, not buried in context.
    previous_rejection = ""

    for audit_attempt in range(MAX_AUDIT_RETRIES + 1):

        # Generate image — pass previous_rejection explicitly
        if image_mode == "Provided Images" and chosen:
            if use_enhance:
                image_bytes = agent._enhance_image(
                    source_image_path=chosen,
                    caption=caption,
                    image_context=image_context,
                    style_vibe=style_vibe,
                    previous_rejection=previous_rejection,
                )
            else:
                image_bytes = agent._generate_image(
                    caption, image_context, style_vibe,
                    reference_images=selected_images,
                    previous_rejection=previous_rejection,
                )
        else:
            image_bytes = agent._generate_image(
                caption, image_context, style_vibe,
                reference_images=selected_images or None,
                previous_rejection=previous_rejection,
            )

        if not image_bytes:
            return None, {"passed": False, "reason": "Image generation returned nothing"}

        # Audit
        print(f"  🔍 Auditing image (attempt {audit_attempt + 1}/{MAX_AUDIT_RETRIES + 1})…")
        audit = agent._audit_image(
            image_bytes, context,
            logo_description=logo_description,
            additional_notes=additional_notes,
        )

        if audit["passed"]:
            print("  ✅ Image passed audit.")
            return image_bytes, {"passed": True, "reason": ""}
        else:
            print(f"  ⚠️  Audit failed: {audit['reason']}")
            if audit_attempt < MAX_AUDIT_RETRIES:
                print("  🔄 Regenerating with correction…")
                # Store rejection to inject at top of next instruction
                previous_rejection = audit["reason"]
            else:
                print(f"  ❌ Failed audit after {MAX_AUDIT_RETRIES + 1} attempts.")
                print(f"     Last reason: {audit['reason']}")

                # ── User recovery options ─────────────────────────────────────
                # Show different options depending on current image mode.
                print("\n  What would you like to do?")
                if image_mode == "Provided Images" and selected_images:
                    print("  1. Try a different image from the library")
                    print("  2. Switch to AI Generated instead")
                    print("  3. Cancel — keep caption only, no image")
                    recovery = input("  Choice (1/2/3, default 3): ").strip()
                else:
                    # Already AI Generated — can only retry or cancel
                    print("  1. Try generating again (new attempt)")
                    print("  2. Cancel — keep caption only, no image")
                    raw = input("  Choice (1/2, default 2): ").strip()
                    recovery = raw if raw in ("1",) else "3"

                if recovery == "1" and selected_images and image_mode == "Provided Images":
                    # Pick a different image and restart the audit loop
                    new_chosen = _pick_image(selected_images)
                    print(f"  🔄 Trying with: {new_chosen.name}")
                    chosen             = new_chosen
                    previous_rejection = ""
                    # Reset and run loop again with fresh image
                    for retry_attempt in range(MAX_AUDIT_RETRIES + 1):
                        image_bytes = agent._enhance_image(
                            source_image_path=chosen,
                            caption=caption,
                            image_context=image_context,
                            style_vibe=style_vibe,
                            previous_rejection=previous_rejection,
                        ) if use_enhance else agent._generate_image(
                            caption, image_context, style_vibe,
                            reference_images=selected_images,
                            previous_rejection=previous_rejection,
                        )
                        if not image_bytes:
                            break
                        retry_audit = agent._audit_image(
                            image_bytes, context,
                            logo_description=logo_description,
                            additional_notes=additional_notes,
                        )
                        print(f"  🔍 Retry audit {retry_attempt + 1}/{MAX_AUDIT_RETRIES + 1}…")
                        if retry_audit["passed"]:
                            print("  ✅ Image passed audit on retry.")
                            return image_bytes, {"passed": True, "reason": ""}
                        else:
                            previous_rejection = retry_audit["reason"]
                            print(f"  ⚠️  Still failing: {retry_audit['reason']}")
                    print("  ❌ Retry also failed — saving caption only.")
                    return None, {"passed": False, "reason": audit["reason"]}

                elif recovery == "2" and image_mode == "Provided Images":
                    # Switch to AI Generated
                    print("  🎨 Switching to AI Generated…")
                    image_bytes = agent._generate_image(
                        caption, image_context, style_vibe,
                        previous_rejection=audit["reason"],
                    )
                    if image_bytes:
                        ai_audit = agent._audit_image(
                            image_bytes, context,
                            logo_description=logo_description,
                            additional_notes=additional_notes,
                        )
                        if ai_audit["passed"]:
                            print("  ✅ AI Generated image passed audit.")
                            return image_bytes, {"passed": True, "reason": ""}
                        else:
                            print(f"  ❌ AI Generated also failed: {ai_audit['reason']}")
                    return None, {"passed": False, "reason": audit["reason"]}

                elif recovery == "1" and image_mode == "AI Generated":
                    # Retry AI generation with stronger correction
                    print("  🎨 Retrying AI generation…")
                    image_bytes = agent._generate_image(
                        caption, image_context, style_vibe,
                        previous_rejection=audit["reason"],
                    )
                    if image_bytes:
                        retry_audit = agent._audit_image(
                            image_bytes, context,
                            logo_description=logo_description,
                            additional_notes=additional_notes,
                        )
                        if retry_audit["passed"]:
                            print("  ✅ Retry passed audit.")
                            return image_bytes, {"passed": True, "reason": ""}
                        else:
                            print(f"  ❌ Retry also failed: {retry_audit['reason']}")
                    return None, {"passed": False, "reason": audit["reason"]}

                else:
                    # Cancel — caption only
                    print("  ⏭️  Saving caption only.")
                    return None, {"passed": False, "reason": audit["reason"]}

    return None, {"passed": True, "reason": ""}


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
        image_bytes, audit_result = _handle_image(
            agent=self,
            post=post,
            image_mode=product_brief.get("image_mode", "Provided Images"),
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
            context=product_brief.get("context", ""),
            logo_description=product_brief.get("logo_description", ""),
            additional_notes=product_brief.get("additional_info", ""),
        )
        post["image_bytes"]   = image_bytes
        post["audit_result"]  = audit_result

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
        image_bytes, audit_result = _handle_image(
            agent=self,
            post=post,
            image_mode=product_brief.get("image_mode", "No"),
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
            context=product_brief.get("context", ""),
            logo_description=product_brief.get("logo_description", ""),
            additional_notes=product_brief.get("additional_info", ""),
        )
        post["image_bytes"]   = image_bytes
        post["audit_result"]  = audit_result

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
        image_bytes, audit_result = _handle_image(
            agent=self,
            post=post,
            image_mode=product_brief.get("image_mode", "No"),
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
            context=product_brief.get("context", ""),
            logo_description=product_brief.get("logo_description", ""),
            additional_notes=product_brief.get("additional_info", ""),
        )
        post["image_bytes"]   = image_bytes
        post["audit_result"]  = audit_result

        print(f"[{self.name}] Finished blog post #{product_brief['post_num']}.")
        return post


# ── Platform to Agent class mapping ──────────────────────────────────────────

PLATFORM_AGENTS = {
    "instagram": InstagramAgent,
    "twitter":   TwitterAgent,
    "x":         TwitterAgent,
    "blog":      BlogAgent,
}
