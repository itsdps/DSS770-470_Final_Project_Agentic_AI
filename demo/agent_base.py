"""
agent_base.py

Base class for all platform agents — mirrors the BaseAgent pattern from class.
Each platform agent (Instagram, Twitter, Blog) inherits from this and only
needs to implement its own execute() method.

Image generation is handled here as shared methods so all platform agents
can use them without duplicating code:
  _generate_image() — calls DALL-E (with optional reference images via GPT Vision)
  _enhance_image()  — calls images/edits endpoint to enhance a real photo
  _build_image_prompt() — builds the instruction passed to DALL-E or the edit
                          endpoint, always includes the caption for cohesion.
                          This is the main prompt engineering artifact for images.
"""

import base64
import json
import re
from pathlib import Path

from openai import OpenAI   # sync client — threads handle parallelism, not async


# ── Image audit prompt ───────────────────────────────────────────────────────
# Prompt Engineering artifact — this is the guardrail for generated images.
# GPT Vision checks the image against these criteria and returns a pass/fail.
# Good before/after for report: vague criteria ("looks good?") vs specific
# criteria below. The specificity of the rules directly affects what gets caught.
# Mentioned in Slide 6 (Ethics & Guardrails).

IMAGE_AUDIT_PROMPT = """
You are a strict brand compliance auditor reviewing a social media image.
Examine the image carefully against ALL three criteria below.

---
CRITERIA 1 — LOGO & BRANDING
{logo_section}

If a logo or brand name is visible in the image:
- It must clearly match the description above (if provided).
- Text in the logo must not be distorted, misspelled, or invented.
- If the logo looks clearly WRONG (different colors, wrong name, made-up design),
  FAIL the image. If you are simply unsure, PASS — do not fail on uncertainty alone.

---
CRITERIA 2 — FACTUAL ACCURACY
The image must not display outright false or impossible claims. FAIL if you see:
- Promises of free money or unrealistic cash rewards (e.g. "Win $1000!")
- "100% off" or similar impossible discounts
- Medical or health claims not supported by the product context
- Pricing that clearly contradicts the product context below
Creative phrasing and marketing enthusiasm are fine — only fail on clear lies.

Product context: {context}

---
CRITERIA 3 — TEXT LEGIBILITY (MOST IMPORTANT — ZERO TOLERANCE)
Look at every piece of text in the image, especially near the TOP and BOTTOM edges.
FAIL immediately if ANY of these are true:
- ANY letter of ANY word touches or goes beyond the image edge — even 1 pixel
- The top of any letter is clipped, even slightly (e.g. "Taste of" losing the tops of letters)
- Any word is partially outside the frame
- Text at the very top or bottom of the image where ascenders or descenders are cut
DO NOT pass an image just because the word is still readable — if any part of any
letter is cut off, it FAILS. There are NO exceptions for text at edges.
Decorative non-text elements at edges are fine. Text is never fine if clipped.

---
IMPORTANT: If you FAIL the image, your reason must be a SHORT, PUNCHY, UPPERCASE
correction command — like a direct order to the image generator.
MAX 10 WORDS. No long explanations. No describing what went wrong.
Just tell it what to fix.

Examples:
  TEXT CUTOFF AT TOP — KEEP ALL TEXT FAR FROM EDGES
  CHECK SPELLING — DO NOT MISSPELL PRODUCT NAME
  LOGO WRONG — USE CORRECT BRAND COLORS AND NAME
  NO TEXT NEAR ANY BORDER — CENTER ALL TEXT

Respond ONLY with a JSON object — no markdown fences:
{{"passed": true or false, "reason": "SHORT UPPERCASE COMMAND if failed, else empty string"}}
""".strip()

MAX_AUDIT_RETRIES = 3   # 4 total attempts: normal → emotional → nuclear → final audit

# ── Caption audit prompt ──────────────────────────────────────────────────────
# Narrow guardrail — only checks for outright lies and hateful/harmful language.
# Quality, creativity, and brand voice are handled by the A/B scorer.
# This is a veto-only check: passes unless something is genuinely harmful.
# Slide 6 guardrail — second layer alongside the image auditor.

CAPTION_AUDIT_PROMPT = """
You are a content safety auditor reviewing a social media caption.
Your job is narrow — you are NOT judging quality or creativity.
Only FAIL the caption if it contains:

1. OUTRIGHT LIES: False factual claims that could mislead customers.
   Examples: fake prices, impossible guarantees, fabricated statistics,
   claims the product can do something it clearly cannot.
   Creative marketing language and enthusiasm are FINE — only fail on clear lies.

2. HATEFUL OR HARMFUL LANGUAGE: Anything offensive, discriminatory, or
   inappropriate for a public social media post. This includes slurs,
   hate speech, content targeting any group, or anything that could
   harm or offend a reasonable reader.

Platform: {platform}
Product context: {context}

Caption to review:
{caption}

Respond ONLY with a JSON object — no markdown fences:
{{"passed": true or false, "reason": "specific reason if failed, else empty string"}}
""".strip()


class BaseAgent:
    """
    Provides a shared OpenAI client and agent name to all platform agents.
    Mirrors the BaseAgent from class (domo_agents/base_agent.py).
    """

    def __init__(self, name: str, openai_key: str,
                 review_key: str = None,
                 main_model: str = "gpt-4o",
                 review_model: str = "gpt-3.5-turbo",
                 ab_threshold: float = 9.0,
                 ab_max_tries: int = 3):
        self.name          = name
        self.openai_client = OpenAI(api_key=openai_key)
        self.review_client = OpenAI(api_key=review_key or openai_key)
        self.main_model    = main_model
        self.review_model  = review_model
        self.threshold     = ab_threshold
        self.max_tries     = ab_max_tries

    def execute(self, product_brief: dict, model_name: str = None) -> dict:
        """
        Override in each platform subclass.
        Returns a dict with at minimum:
          caption (str), platform (str), score (float),
          image_bytes (bytes | None) — real PNG data if image was generated
        """
        raise NotImplementedError(f"{self.name} must implement execute()")

    # ── Shared text helpers ───────────────────────────────────────────────────

    def _chat(self, prompt: str, model: str = None, temp: float = 0.7) -> str:
        """Synchronous OpenAI call — safe to call from threads."""
        resp = self.openai_client.chat.completions.create(
            model=model or self.main_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        return resp.choices[0].message.content.strip()

    def _chat_content(self, content: list, model: str = None, temp: float = 0.7) -> str:
        """
        Multimodal OpenAI call — accepts a content list with text and image blocks.
        Mirrors the HumanMessage pattern from class 01_langchain_basics.ipynb
        Example 7 (Vision API):
          content=[
            {"type": "text", "text": "..."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
          ]
        Falls back to text-only if no image blocks are present.
        """
        resp = self.openai_client.chat.completions.create(
            model=model or self.main_model,
            messages=[{"role": "user", "content": content}],
            temperature=temp,
        )
        return resp.choices[0].message.content.strip()

    def _review_chat(self, prompt: str, temp: float = 0.2) -> str:
        """Cheaper review model call for A/B scoring."""
        resp = self.review_client.chat.completions.create(
            model=self.review_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        return resp.choices[0].message.content.strip()

    def _ab_loop(self, platform: str, post_num: int, total: int,
                 context: str, instructions: str,
                 reference_images: list | None = None) -> dict:
        """
        A/B scoring loop shared by all platform agents:
          1. Draft a caption candidate
          2. Score it with the reviewer model
          3. Keep the best; stop early if threshold is reached
          4. Repeat up to max_tries times

        Returns the best post dict including an image_context string
        (mood, colors, subject) that gets passed to image generation later.
        Image generation happens AFTER this loop so caption always comes first.
        """
        best_post  = None
        best_score = 0.0

        for attempt in range(1, self.max_tries + 1):

            # ── Draft caption ─────────────────────────────────────────────────
            # image_context is a brief visual description used later to guide
            # DALL-E or the image edit endpoint — NOT a full prompt yet.
            # The full image prompt is built in _build_image_prompt() which
            # also receives the caption, keeping both cohesive.
            draft_prompt = (
                f"You are a social media content creator.\n"
                f"Create post #{post_num} of {total} for {platform.upper()}.\n\n"
                f"{instructions}\n\n"
                f"Context (draw inspiration, do NOT copy verbatim):\n{context}\n\n"
                f"Respond ONLY with a JSON object — no markdown fences:\n"
                f'{{"caption": "...", '
                f'"image_context": "2-3 sentence visual description: mood, colors, '
                f'subject matter that would make a great matching image", '
                f'"platform": "{platform}"}}'
            )
            raw       = self._chat(draft_prompt, temp=0.8)
            candidate = _safe_json(raw)
            candidate.setdefault("platform", platform)
            candidate.setdefault("image_context", "")
            candidate.setdefault("image_bytes", None)

            # ── Score caption ─────────────────────────────────────────────────
            # Prompt Engineering note: V1 too lenient (all 9.5), V2 too harsh (all 6.5-7.5).
            # V3 rebalanced: well-written on-brand posts should score 7.5-8.0,
            # exceptional posts 9.0+, truly weak posts below 7.0.
            review_prompt = (
                f"You are a social media content reviewer. Be fair but discerning.\n"
                f"Rate this {platform.upper()} post from 0-10 using these benchmarks:\n\n"
                f"  9-10: Exceptional. Highly specific, memorable, stops someone mid-scroll.\n"
                f"        Perfect CTA, strong brand voice, feels completely original.\n"
                f"  7.5-8.5: Good. Well-written, on-brand, engaging. Minor weaknesses\n"
                f"        like a slightly generic phrase or a hashtag that feels routine.\n"
                f"        This is where most solid, professional posts should land.\n"
                f"  6-7:  Adequate. Does the job but lacks personality or specificity.\n"
                f"        Generic enough that it could be for a different brand.\n"
                f"  4-5:  Weak. Cliché, off-brand, or missing a real CTA.\n"
                f"  0-3:  Poor. Misleading, inappropriate, or completely off-brief.\n\n"
                f"Only penalize if clearly problematic:\n"
                f"  - Outright generic filler ('Amazing product! Try it today!')\n"
                f"  - CTA that is completely absent or confusing\n"
                f"  - Caption that could apply to any brand with zero customization\n\n"
                f"Rate criteria:\n"
                f"- Engagement potential\n"
                f"- Brand consistency\n"
                f"- Creativity and specificity\n"
                f"- Call-to-action quality\n"
                f"- Platform best practices\n\n"
                f"Post caption:\n{candidate.get('caption', '')}\n\n"
                f"Context summary:\n{context[:800]}\n\n"
                f"Respond ONLY with JSON — no markdown fences:\n"
                f'{{"score": <float 0-10>, "reason": "specific reason for this score"}}'
            )
            review_data = _safe_json(self._review_chat(review_prompt))
            try:
                score = float(review_data.get("score", 5.0))
            except (TypeError, ValueError):
                score = 5.0

            print(f"      [{self.name}] Post {post_num} — attempt {attempt}: score {score:.1f}/10")

            if score > best_score:
                best_score        = score
                best_post         = candidate
                best_post["score"] = score

            if score >= self.threshold:
                break

        print(f"  ✅  [{self.name}] Post {post_num} done — final score {best_score:.1f}")
        return best_post

    # ── Image generation methods ──────────────────────────────────────────────

    def _build_image_prompt(self, caption: str, image_context: str,
                             style_vibe: str = "",
                             logo_description: str = "",
                             additional_notes: str = "",
                             brand_context: str = "") -> str:
        """
        Builds the instruction sent to DALL-E or the image edit endpoint.

        KEY DESIGN DECISION: caption is always included so the image and
        caption feel like one cohesive post, not two independent pieces.
        logo_description ensures DALL-E uses the real logo rather than
        inventing one — this was the main cause of logo errors.

        Args:
            caption:           Final caption text from _ab_loop()
            image_context:     Visual description generated alongside caption
            style_vibe:        Optional brand vibe from style guide
            logo_description:  Company logo description from company report
            additional_notes:  Additional post notes from receipt
        """
        prompt = (
            f"Create a vibrant, eye-catching social media image.\n\n"
            f"The accompanying post caption reads:\n\"{caption}\"\n\n"
            f"Visual direction:\n{image_context}\n"
        )
        if style_vibe:
            prompt += f"\nBrand vibe: {style_vibe}\n"

        # Logo guidance — tells DALL-E exactly what the logo looks like
        # so it doesn't invent one. additional_notes takes priority over
        # company report logo_description (same priority as auditor).
        notes_mention_logo = any(
            word in additional_notes.lower()
            for word in ("logo", "cup", "branding", "brand", "color", "colour", "sign")
        ) if additional_notes else False

        # Brand context — additional notes first (most specific), then brand_context
        if additional_notes:
            prompt += f"\n\nPost notes: {additional_notes[:150]}\n"
        if brand_context:
            prompt += f"\nBrand context: {brand_context[:200]}\n"
        if additional_notes and notes_mention_logo:
            prompt += f"\nLogo notes: {additional_notes[:100]}\n"
        elif logo_description:
            prompt += (
                f"\n\nLOGO ACCURACY IS CRITICAL: If the brand logo appears in the image, "
                f"it MUST match this exact description: {logo_description}. "
                f"Do not invent a different logo or use generic branding.\n"
            )

        prompt += (
            f"\nTEXT PLACEMENT IS CRITICAL: Any text in the image must be FULLY "
            f"inside the frame with NO clipping of any letters. Keep ALL text "
            f"at least 100px away from every edge (top, bottom, left, right). "
            f"Never place text so close to an edge that ascenders or descenders "
            f"could be cut off.\n"
            f"Photorealistic style."
        )
        return prompt

    def _generate_image(self, caption: str, image_context: str,
                         style_vibe: str = "",
                         reference_images: list[Path] | None = None,
                         previous_rejection: str | list = "",
                         brand_context: str = "") -> bytes | None:
        """
        Generates a new image using DALL-E 3.

        If reference_images are provided, first asks GPT Vision to describe
        their style/mood, then incorporates that into the DALL-E prompt.
        This is the "AI Generated with inspiration" path.

        Args:
            caption:          Final caption — passed to _build_image_prompt()
            image_context:    Visual description from _ab_loop()
            style_vibe:       Optional brand vibe from style guide
            reference_images: Optional list of Paths to local images for inspiration

        Returns:
            Raw PNG bytes, or None if generation failed.
        """
        # If reference images given, ask GPT Vision to describe their style
        vision_notes = ""
        if reference_images:
            vision_notes = self._describe_images_for_reference(reference_images)

        # Build the full prompt, optionally incorporating vision notes
        full_context = image_context
        if vision_notes:
            full_context = f"{image_context}\n\nStyle inspiration from reference images:\n{vision_notes}"

        # Stacked correction block — strings already processed in agent_posts.py
        if previous_rejection:
            rejections = previous_rejection if isinstance(previous_rejection, list) \
                         else [previous_rejection]
            lines = [f"FIX: {r[:80]}" for r in rejections[-4:] if r]
            correction = "\n".join(lines) + "\n\n"
            full_context = correction + full_context
        image_prompt = self._build_image_prompt(
            caption, full_context, style_vibe,
            logo_description=self.__dict__.get("_logo_description", ""),
            additional_notes=self.__dict__.get("_additional_notes", ""),
            brand_context=brand_context,
        )

        print(f"  🎨 Generating image with DALL-E 3…")
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                quality="standard",
                response_format="b64_json",   # get raw bytes back, not a URL
                n=1,
            )
            image_b64 = response.data[0].b64_json
            return base64.b64decode(image_b64)
        except Exception as e:
            print(f"  ⚠️  DALL-E generation failed: {e}")
            return None

    def _enhance_image(self, source_image_path: Path,
                        caption: str, image_context: str,
                        style_vibe: str = "",
                        previous_rejections: list | None = None,
                        brand_context: str = "") -> bytes | None:
        """
        Enhances a real photo. previous_rejections is a list of all prior
        audit failure reasons — each becomes its own short punchy correction
        line at the top of the prompt (emotion prompting pattern from class).
        Stacking keeps each rule visible rather than burying them in one sentence.
        """
        # Build stacked correction block — each failure = one short urgent line.
        # Kept very short so nothing gets truncated by the ~1000 char limit.
        if previous_rejections:
            lines = []
            for r in previous_rejections[-4:]:  # up to 4 stacked fixes
                if r:
                    lines.append(f"FIX: {r[:80]}")
            correction_block = "\n".join(lines) + "\n\n"
        else:
            correction_block = ""

        short_caption = caption[:80] + "…" if len(caption) > 80 else caption
        short_context = image_context[:100] + "…" if len(image_context) > 100 else image_context

        # Build brand block — priority: additional_notes > style > product/company
        brand_block = f"\n{brand_context[:200]}" if brand_context else ""

        edit_instruction = (
            f"{correction_block}"
            f"Enhance this photo. Caption: \"{short_caption}\"\n"
            f"Direction: {short_context}\n"
            f"{brand_block}\n"
            f"TEXT RULE: ALL TEXT 150px FROM TOP. 120px FROM ALL EDGES. "
            f"NO LETTER TOUCHES ANY EDGE. NO EXCEPTIONS. "
            f"KEEP REAL PHOTO INTACT."
        )
        if style_vibe:
            edit_instruction += f" Vibe: {style_vibe[:40]}"

        print(f"  🎨 Enhancing photo: {source_image_path.name}…")
        try:
            # The image edit endpoint needs a PNG with RGBA (supports transparency)
            # We open the file as bytes — OpenAI handles the rest
            with open(source_image_path, "rb") as img_file:
                response = self.openai_client.images.edit(
                    model="gpt-image-1",   # required — OpenAI image edit model
                    image=img_file,
                    prompt=edit_instruction,
                    size="1024x1024",
                    n=1,
                )
            # gpt-image-1 may return b64_json or url depending on settings
            image_b64 = response.data[0].b64_json
            if image_b64:
                return base64.b64decode(image_b64)
            url = getattr(response.data[0], "url", None)
            if url:
                import httpx
                return httpx.get(url).content
            return None
        except Exception as e:
            print(f"  ⚠️  Image enhancement failed: {e}")
            print(f"       Falling back to DALL-E generation…")
            # Graceful fallback — if enhancement fails, generate fresh
            return self._generate_image(
                caption, image_context, style_vibe,
                reference_images=[source_image_path]
            )

    def _audit_caption(self, caption: str, platform: str,
                       context: str = "") -> dict:
        """
        Caption safety auditor — narrow guardrail checking only:
          1. Outright lies / false claims
          2. Hateful or harmful language

        Returns {"passed": bool, "reason": str}
        Does NOT check quality, creativity, or brand voice — A/B scorer handles those.
        """
        prompt = CAPTION_AUDIT_PROMPT.format(
            platform=platform.upper(),
            context=context[:400],
            caption=caption,
        )
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",   # simple classification — doesn't need gpt-4o
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            raw = __import__("re").sub(
                r"^```(?:json)?|```$", "", raw, flags=__import__("re").MULTILINE
            ).strip()
            result = __import__("json").loads(raw)
            return {
                "passed": bool(result.get("passed", True)),
                "reason": result.get("reason", "")
            }
        except Exception as e:
            print(f"  ⚠️  Caption audit error: {e} — defaulting to passed.")
            return {"passed": True, "reason": ""}

    def _describe_images_for_reference(self, image_paths: list[Path]) -> str:
        """
        Passes reference images to GPT Vision and asks it to describe
        the visual style, mood, and color palette.

        The description is then folded into the DALL-E prompt so the
        generated image is inspired by the reference photos without
        directly copying them.

        Args:
            image_paths: List of local image file Paths

        Returns:
            A plain text style description string.
        """
        # Build a message with all images encoded as base64
        content = [
            {
                "type": "text",
                "text": (
                    "Look at these reference images and describe their visual style "
                    "in 3-4 sentences. Focus on: color palette, mood, lighting, "
                    "composition style, and overall energy. This description will "
                    "be used to inspire a new social media image in a similar style."
                )
            }
        ]

        for path in image_paths[:3]:   # cap at 3 to keep token usage reasonable
            try:
                encoded = _encode_image(path)
                mime    = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encoded}"}
                })
            except Exception as e:
                print(f"  ⚠️  Could not encode {path.name}: {e}")

        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o",   # needs Vision capability
                messages=[{"role": "user", "content": content}],
                max_tokens=300,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  ⚠️  GPT Vision description failed: {e}")
            return ""


    def _audit_image(self, image_bytes: bytes, context: str,
                     logo_description: str = "",
                     additional_notes: str = "") -> dict:
        """
        GPT Vision compliance auditor for generated/enhanced images.
        Checks: logo correctness, factual accuracy, text legibility.

        Logo check priority:
          1. additional_notes (from receipt) — if it mentions logo, use that
          2. logo_description (from company report) — fallback
          3. No logo check if both are empty

        The IMAGE_AUDIT_PROMPT at the top of this file is the prompt
        engineering artifact — specificity of criteria directly affects
        what gets caught. Good before/after story for the report.

        Returns:
            {"passed": bool, "reason": str}
        """
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        mime = "image/png" if image_bytes[:4] == b"\x89PNG" else "image/jpeg"

        # Build logo section — additional_notes takes priority
        notes_mention_logo = any(
            word in additional_notes.lower()
            for word in ("logo", "cup", "branding", "brand", "color", "colour", "sign")
        )
        if additional_notes and notes_mention_logo:
            logo_section = f"Additional notes from the post request: {additional_notes}"
        elif logo_description:
            logo_section = f"Company logo description: {logo_description}"
        else:
            logo_section = "No logo description available — skip logo check."

        audit_prompt = IMAGE_AUDIT_PROMPT.format(
            context=context[:500],
            logo_section=logo_section,
        )

        content = [
            {"type": "text", "text": audit_prompt},
            {"type": "image_url",
             "image_url": {"url": f"data:{mime};base64,{encoded}"}}
        ]

        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o",   # needs Vision capability
                messages=[{"role": "user", "content": content}],
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            raw = __import__("re").sub(
                r"^```(?:json)?|```$", "", raw, flags=__import__("re").MULTILINE
            ).strip()
            result = __import__("json").loads(raw)
            return {
                "passed": bool(result.get("passed", True)),
                "reason": result.get("reason", ""),
                "fix":    result.get("fix", "").upper()[:60],
            }
        except Exception as e:
            print(f"  ⚠️  Audit error: {e} — defaulting to passed.")
            return {"passed": True, "reason": "", "fix": ""}


# ── Module-level helpers ──────────────────────────────────────────────────────

def _safe_json(text: str) -> dict:
    """Parse JSON even if GPT wraps it in markdown fences."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"caption": text, "image_context": "", "platform": "unknown"}


def _encode_image(path: Path) -> str:
    """Base64-encode a local image file for GPT Vision."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
