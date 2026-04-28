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
            review_prompt = (
                f"You are a strict social media content reviewer.\n"
                f"Rate this {platform.upper()} post from 0-10 on:\n"
                f"- Engagement potential\n"
                f"- Brand consistency\n"
                f"- Creativity\n"
                f"- Call-to-action quality\n"
                f"- Platform best practices\n\n"
                f"Post caption:\n{candidate.get('caption', '')}\n\n"
                f"Context summary:\n{context[:800]}\n\n"
                f"Respond ONLY with JSON — no markdown fences:\n"
                f'{{"score": <float 0-10>, "reason": "..."}}'
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
                             style_vibe: str = "") -> str:
        """
        Builds the instruction sent to DALL-E or the image edit endpoint.

        KEY DESIGN DECISION: caption is always included so the image and
        caption feel like one cohesive post, not two independent pieces.
        This is the main prompt engineering artifact for the image feature —
        a good candidate for a before/after in the report:
          Before: just image_context alone → generic image, no relation to caption
          After:  caption + image_context + style vibe → image that tells the
                  same story as the caption

        Args:
            caption:       The final caption text from _ab_loop()
            image_context: Visual description generated alongside the caption
            style_vibe:    Optional vibe from the style guide (e.g. "fun, summery")
        """
        prompt = (
            f"Create a vibrant, eye-catching social media image.\n\n"
            f"The accompanying post caption reads:\n\"{caption}\"\n\n"
            f"Visual direction:\n{image_context}\n"
        )
        if style_vibe:
            prompt += f"\nBrand vibe: {style_vibe}\n"
        prompt += (
            f"\nThe image should feel cohesive with the caption — "
            f"same mood, same energy. No text overlays unless specifically "
            f"described in the visual direction. Photorealistic style."
        )
        return prompt

    def _generate_image(self, caption: str, image_context: str,
                         style_vibe: str = "",
                         reference_images: list[Path] | None = None) -> bytes | None:
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

        image_prompt = self._build_image_prompt(caption, full_context, style_vibe)

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
                        style_vibe: str = "") -> bytes | None:
        """
        Enhances a real photo using OpenAI's image edit endpoint.

        Keeps the real photo intact and adds AI-generated elements
        (text effects, overlays, color grading) that match the caption.
        Caption is always passed so the enhancements tell the same story.

        Args:
            source_image_path: Path to the real .png or .jpg photo
            caption:           Final caption — used to guide what effects to add
            image_context:     Visual description from _ab_loop()
            style_vibe:        Optional brand vibe from style guide

        Returns:
            Raw PNG bytes of the enhanced image, or None if it failed.
        """
        edit_instruction = (
            f"Enhance this photo for a social media post.\n"
            f"The post caption reads: \"{caption}\"\n\n"
            f"Add elements that match the caption's energy and message — "
            f"for example expressive text effects, color grading, subtle overlays, "
            f"or graphic elements. Keep the real photo and people in it intact.\n\n"
            f"Visual direction: {image_context}\n"
        )
        if style_vibe:
            edit_instruction += f"Brand vibe: {style_vibe}"

        print(f"  🎨 Enhancing photo: {source_image_path.name}…")
        try:
            # The image edit endpoint needs a PNG with RGBA (supports transparency)
            # We open the file as bytes — OpenAI handles the rest
            with open(source_image_path, "rb") as img_file:
                response = self.openai_client.images.edit(
                    image=img_file,
                    prompt=edit_instruction,
                    size="1024x1024",
                    response_format="b64_json",
                    n=1,
                )
            image_b64 = response.data[0].b64_json
            return base64.b64decode(image_b64)
        except Exception as e:
            print(f"  ⚠️  Image enhancement failed: {e}")
            print(f"       Falling back to DALL-E generation…")
            # Graceful fallback — if enhancement fails, generate fresh
            return self._generate_image(
                caption, image_context, style_vibe,
                reference_images=[source_image_path]
            )

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
