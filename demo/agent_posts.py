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
from agent_utils import IMAGE_PLATFORM_DEFAULTS


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
    supported = {"instagram", "twitter", "x", "blog"}
    if isinstance(platforms, list):
        parsed = [p.lower().strip() for p in platforms]
    else:
        parsed = [p.lower().strip() for p in str(platforms).split(",")]

    for p in parsed:
        if p and p not in supported:
            print(f"  ⚠️  Platform '{p}' is not supported yet. "
                  f"Supported: Instagram, Twitter/X, Blog. Skipping.")
    return parsed


# ── Shared image handling helper ──────────────────────────────────────────────
# Module-level counter so parallel agents cycle through images without repeating.
# Initialized randomly so each run starts at a different image.
# Thread-safe — multiple platform agents run simultaneously via ThreadPoolExecutor.
# ═══════════════════════════════════════════════════════════════════════════════
# HOW THIS FILE WORKS
# This file defines the three platform agents (Instagram, Twitter, Blog) and
# the shared logic that connects caption generation to image generation.
#
# The flow for each post:
#   1. _run_caption_audit_loop() — generates a caption via A/B scoring,
#      then checks it for lies/harmful content before accepting it
#   2. _handle_image() — generates or enhances an image using that caption,
#      then runs the image auditor with up to 4 escalating correction attempts
#   3. The platform agent (Instagram/Twitter/Blog) calls both in sequence
#      and returns the finished post dict
#
# Parallel execution: all agents in a batch run simultaneously via
# agent_parallel.py (ThreadPoolExecutor) — same pattern as 07_workflow_multitasking
# ═══════════════════════════════════════════════════════════════════════════════
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


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE AUDIT LOOP (_handle_image)
# This is the guardrail section — after a caption is approved, this function
# generates the image and runs it through the auditor up to 4 times:
#   Attempt 1: Generate + audit with basic correction if fails
#   Attempt 2: Generate + audit with emotional urgency correction ("OR I WILL BE FIRED")
#   Attempt 3: Nuclear — strips all text from the prompt, tries one last time
#   Attempt 4: Final audit. If still fails, no image is used.
# "No image is better than a bad image" — deliberate design decision.
# ─────────────────────────────────────────────────────────────────────────────
def _handle_image(agent: BaseAgent, post: dict, image_mode: str,
                  selected_images: list, style_vibe: str,
                  context: str = "",
                  logo_description: str = "",
                  additional_notes: str = "",
                  enhance_as_inspiration: bool = False,
                  brand_context: str = "") -> tuple:
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
    agent._brand_context     = brand_context

    # ── No image ─────────────────────────────────────────────────────────────
    if image_mode == "No":
        return None, {"passed": True, "reason": ""}

    # ── Provided Images — use_enhance already decided before parallel execution ──
    # enhance_as_inspiration was asked once in Step 7.6 before threads started.
    # chosen and use_enhance initialized here so they're always defined.
    chosen      = None
    use_enhance = not enhance_as_inspiration

    if image_mode == "Provided Images":
        if not selected_images:
            print("  ℹ️  No images selected, falling back to AI Generated…")
            image_mode = "AI Generated"
        else:
            chosen = _pick_image(selected_images)
            print(f"\n  📸 Using image: {chosen.name}")

    # ── Audit loop — mirrors orchestrator_loop.py revision pattern ──────────
    # All prior rejections are stacked — each becomes a short punchy correction
    # line at the top of the prompt so the model cannot miss any of them.
    all_rejections = []   # grows with each failed attempt

    for audit_attempt in range(MAX_AUDIT_RETRIES + 1):

        # Generate image — pass previous_rejection explicitly
        if image_mode == "Provided Images" and chosen:
            if use_enhance:
                image_bytes = agent._enhance_image(
                    source_image_path=chosen,
                    caption=caption,
                    image_context=image_context,
                    style_vibe=style_vibe,
                    previous_rejections=all_rejections,
                    brand_context=brand_context,
                )
            else:
                image_bytes = agent._generate_image(
                    caption, image_context, style_vibe,
                    reference_images=selected_images,
                    previous_rejection=all_rejections,
                    brand_context=brand_context,
                )
        else:
            image_bytes = agent._generate_image(
                caption, image_context, style_vibe,
                reference_images=selected_images or None,
                previous_rejection=all_rejections,
                brand_context=brand_context,
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
            return image_bytes, {"passed": True, "reason": "", "correction_history": all_rejections}
        else:
            reason = audit["reason"]
            fix    = audit.get("fix", "").upper()[:60] if audit.get("fix") else ""
            # Show human-readable reason to user — if GPT collapsed reason/fix,
            # fall back to a generic description based on the fix content
            display_reason = reason if reason and reason.upper() != fix else \
                             f"Image did not pass audit ({fix.lower() if fix else 'see fix'})"
            print(f"  ⚠️  Audit failed: {display_reason}")

            if audit_attempt == 0:
                # Attempt 1 → fail → concise fix
                print("  🔄 Regenerating with correction…")
                if fix:
                    all_rejections.append(fix)
                    print(f"     → Sending: {fix}")

            elif audit_attempt == 1:
                # Attempt 2 → fail → emotional urgency
                print("  🔄 Regenerating with stronger correction…")
                reason_lower = reason.lower()
                if any(w in reason_lower for w in ("clip", "cut", "edge", "top", "bottom", "border")):
                    msg = "DON'T LET TEXT BE CUT OFF OR I WILL BE FIRED — KEEP ALL TEXT FAR FROM EVERY EDGE"
                elif any(w in reason_lower for w in ("spell", "misspell", "typo")):
                    msg = "DO NOT MISSPELL WORDS OR I WILL BE FIRED — CHECK EVERY LETTER"
                elif any(w in reason_lower for w in ("logo", "brand")):
                    msg = "DO NOT INVENT LOGOS OR I WILL BE FIRED — MATCH BRAND EXACTLY"
                else:
                    msg = f"THIS IS CRITICAL — FIX THIS NOW OR I WILL BE FIRED: {fix}"
                all_rejections.append(msg)
                print(f"     → Sending: {msg}")

            elif audit_attempt == 2:
                # Attempt 3 → nuclear → generate with NO TEXT, then attempt 4 audits it
                print("  💥 Nuclear — generating with no text for final audit…")
                reason_lower = reason.lower()
                if any(w in reason_lower for w in ("clip", "cut", "edge", "top", "bottom", "spell", "text")):
                    msg = "NO TEXT IN THE IMAGE AT ALL. ZERO WORDS. ZERO LETTERS. PURELY VISUAL"
                else:
                    msg = "REMOVE ALL TEXT FROM THE IMAGE. VISUAL ELEMENTS ONLY. NO EXCEPTIONS"
                all_rejections.append(msg)
                print(f"     → Sending: {msg}")
                # Don't return — loop continues to attempt 3 which generates and audits

            else:
                # Attempt 4 → auditor ran on nuclear image → if here it failed
                print(f"  ❌ Failed all audit attempts [nuclear applied].")
                print(f"     {reason}")
                return None, {"passed": False, "reason": reason, "went_nuclear": True,
                              "correction_history": all_rejections, "last_image_bytes": image_bytes}

    # All 4 attempts exhausted — no image is better than a bad image
    print("  ❌ Failed all audit attempts — saving caption only.")
    return None, {"passed": False, "reason": "Failed all audit attempts.", "went_nuclear": True,
                  "correction_history": all_rejections, "last_image_bytes": image_bytes if 'image_bytes' in dir() else None}


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM AGENT CLASSES
# Each class is a specialized agent for one social media platform.
# They all inherit from BaseAgent and only define:
#   - Their name and image default
#   - Their caption instructions (length, hashtags, tone, CTA style)
# The heavy lifting (A/B scoring, image gen, auditing) is all in BaseAgent.
# Mirrors the Twitter/LinkedIn/Blog agent pattern from 07_workflow_multitasking.
# ═══════════════════════════════════════════════════════════════════════════════
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

        # ── Step 2: Resolve image_mode for Instagram ─────────────────────────
        image_mode = product_brief.get("image_mode", "")
        if image_mode not in ("Provided Images", "AI Generated", "No"):
            image_mode = IMAGE_PLATFORM_DEFAULTS.get("instagram", "Provided Images")

        # ── Step 3: Generate image using final caption as context ─────────────
        # Caption comes first so the image matches what the post is saying
        image_bytes, audit_result = _handle_image(
            agent=self,
            post=post,
            image_mode=image_mode,
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
            context=product_brief.get("context", ""),
            logo_description=product_brief.get("logo_description", ""),
            additional_notes=product_brief.get("additional_info", ""),
            enhance_as_inspiration=product_brief.get("enhance_as_inspiration", False),
            brand_context=product_brief.get("brand_context", ""),
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

        # ── Step 2: Resolve image_mode for Twitter ────────────────────────
        image_mode = product_brief.get("image_mode", "")
        explicit_image = any(
            w in product_brief.get("additional_info", "").lower()
            for w in ("image", "photo", "picture", "ai generated", "dall")
        )
        if not explicit_image:
            image_mode = IMAGE_PLATFORM_DEFAULTS.get("twitter", "No")

        # ── Step 3: Image if requested ────────────────────────────────────
        image_bytes, audit_result = _handle_image(
            agent=self,
            post=post,
            image_mode=image_mode,
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
            context=product_brief.get("context", ""),
            logo_description=product_brief.get("logo_description", ""),
            additional_notes=product_brief.get("additional_info", ""),
            enhance_as_inspiration=product_brief.get("enhance_as_inspiration", False),
            brand_context=product_brief.get("brand_context", ""),
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

        # ── Step 2: Resolve image_mode for Blog ──────────────────────────
        image_mode = product_brief.get("image_mode", "")
        explicit_image = any(
            w in product_brief.get("additional_info", "").lower()
            for w in ("image", "photo", "picture", "ai generated", "dall")
        )
        if not explicit_image:
            image_mode = IMAGE_PLATFORM_DEFAULTS.get("blog", "No")

        # ── Step 3: Image if requested ────────────────────────────────────
        image_bytes, audit_result = _handle_image(
            agent=self,
            post=post,
            image_mode=image_mode,
            selected_images=product_brief.get("selected_images", []),
            style_vibe=product_brief.get("style_vibe", ""),
            context=product_brief.get("context", ""),
            logo_description=product_brief.get("logo_description", ""),
            additional_notes=product_brief.get("additional_info", ""),
            enhance_as_inspiration=product_brief.get("enhance_as_inspiration", False),
            brand_context=product_brief.get("brand_context", ""),
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
