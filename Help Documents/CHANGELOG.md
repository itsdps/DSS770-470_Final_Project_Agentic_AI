# 📋 CHANGELOG
## Social Media Post AI Agent

All notable changes to this project are documented here.
Changes are grouped by feature area and listed from most recent to earliest.

---

## 🔵 Recent fixes (post-documentation)

### Notebook — Enhance question missing (Step 7.6)
- Added `1. Enhance / 2. Use as inspiration` question to notebook Cell 22 after image selection
- Was already in `demo.py` but never added to the notebook — now consistent

### Notebook — Platform cycling bug
- Fixed: "1 Instagram and 2 Twitter" was producing `[Instagram, Twitter, Instagram]`
- Now reads per-platform counts from `_raw_request` regex — same logic as `demo.py`
- Produces correct `[Instagram, Twitter, Twitter]` → Round 1: [Insta+Twitter], Round 2: [Twitter]

### Logging — Merged Receipt + Audit into one file
- Removed separate `Audit.txt` file — audit section now appended to `Receipt.txt`
- Single log file per run: Receipt → Captions → Content Audit → Overall result
- `_raw_request` hidden from log file receipt section

---

## 🔴 Guardrails & Audit System

### Image Auditor — 4-Attempt Escalating Correction Loop
- Added `IMAGE_AUDIT_PROMPT` with GPT Vision checks for logo accuracy, factual claims, and text legibility
- Returns separate `reason` (human-readable) and `fix` (short uppercase model command) fields
- Audit loop now runs up to 4 attempts with escalating correction intensity:
  - **Attempt 1:** Concise actionable fix from auditor (`FIX: KEEP ALL TEXT FAR FROM EDGES`)
  - **Attempt 2:** Emotional urgency (`DON'T LET TEXT BE CUT OFF OR I WILL BE FIRED`)
  - **Attempt 3:** Nuclear — strips all text requirements (`NO TEXT IN THE IMAGE AT ALL`)
  - **Attempt 4:** Final audit on nuclear image — if still fails, no image is saved
- Correction history stored on `audit_result` and written to the audit log
- Added `last_image_bytes` so user can choose to save a failed audit image anyway

### Caption Auditor
- Added `CAPTION_AUDIT_PROMPT` as a second guardrail layer (text vs. image)
- Checks only two things: outright lies and hateful/harmful language
- Veto with retry loop — same pattern as image auditor
- Both auditors run before saving; audit results written to `Audit.txt` log

### Recovery Options After Image Audit Failure
- After all attempts exhaust, user is offered 3 choices:
  1. Try a different image from the library
  2. Use the final failed image anyway (saved as `post_image (Failed Audit).png`)
  3. Skip — caption only
- Recovery menu shown after parallel execution completes (not mid-thread)

### Image Generation Prompt Improvements
- Raised text margin from 60px → 100px → 120px/150px from edges
- Added explicit ascender/descender language to prevent letter-top clipping
- Logo description from company report passed to DALL-E to prevent invented logos
- `additional_info` from receipt takes priority over company logo description
- `brand_context` string (notes + style + product + company) now passed to generation

### Correction Prompts
- Correction prompts shortened to one punchy uppercase command per issue
- Each prior rejection stacked as a separate `FIX:` line (emotion prompting pattern)
- Matched `05_emotion_prompting.ipynb` from class — urgency at top of prompt

---

## 🟡 Prompt Engineering

### A/B Scorer — 3-Stage Iteration
- **V1:** Too lenient — all captions scored ~9.5, threshold 7.5 (always passed first attempt)
- **V2:** Too harsh — "strict and honest", scores clustered 6.5–7.5
- **V3 (current):** "Fair but discerning" — 7.5–8.5 band for solid professional posts, 9.0+ for exceptional only
- Threshold raised to 9.0 so all 3 attempts are used in most cases

### Photo Auditor — 3-Stage Iteration
- **V1:** Vague 3-criteria prompt — passed images with text clearly cut off
- **V2:** Added ~20% cutoff rule + specific failure reason required — still too lenient
- **V3 (current):** Zero tolerance — any pixel of any letter at any edge = fail, ascenders/descenders explicitly mentioned

### Research Agent Iterations
- Observation truncation raised 300 → 2000 chars (null fields fix)
- "Do not invent facts" rule relaxed — allow general knowledge fill
- Added "must do at least one tool call" + retry if results thin
- `MAX_STEPS` raised from 3 → 6 (time vs. quality tradeoff, then tunable)
- Added null field check after product report — if >1 null after MAX_STEPS, ask user for URL/file
- Company context grounding: company report passed into ReAct loop opening message
- Logo description added to `COMPANY_REPORT_PROMPT` and research query

### Date Parsing
- Added `DATE_PARSE_PROMPT` for natural language scheduling input
- Handles: bare date (all posts), count+date, multiple date instructions
- Auto-fills remaining slots with `AUTO_DATE_PROMPT` if fewer dates than posts

### Style Guide Update Classification
- Replaced numbered menu (1/2/3) with current numbered approach
- Future work: upgrade to free-form GPT classification (same sentiment_analysis pattern)

---

## 🟢 Architecture & Agents

### Platform Agents
- Added `InstagramAgent`, `TwitterAgent`, `BlogAgent` inheriting from `BaseAgent`
- Each platform has its own image mode default (`IMAGE_PLATFORM_DEFAULTS`)
- Platform agents resolve their own `image_mode` before calling `_handle_image()`
- Twitter and Blog default to no image unless explicitly requested

### Parallel Execution
- `agent_parallel.py` uses `ThreadPoolExecutor` (class used `asyncio.gather()`)
- Platform grouping: all platforms per round run simultaneously
  - "1 Instagram + 2 Twitter" → Round 1: [Instagram, Twitter], Round 2: [Twitter]
  - Correct platform list now built from per-platform counts in request
- `input()` calls removed from threads — all user input before parallel execution
- `enhance_as_inspiration` question asked once in Step 7.6, passed via `base_brief`

### Research Agent
- Upgraded from regex ReAct (class `ACTION_RE`) to structured function calling (`tool_calls`)
- Fuzzy name resolution: `SequenceMatcher(ratio > 0.6)` + substring containment
- `skip_name_resolution=True` param prevents double-asking in demo vs. notebook
- Separate `company_url`/`product_url` params so each new entity can have its own reference
- Logo description field added to company report JSON

### Image System
- `_pick_image()` cycles through selected images using thread-safe module-level counter
- Counter initialized randomly each run (no always-first-image problem)
- `_enhance_image()` and `_generate_image()` both accept `previous_rejections` list
- `brand_context` passed through `product_brief` → `_handle_image()` → image methods

### Scheduling
- Natural language date parsing via GPT
- Auto-fills remaining dates and labels them `[auto]`
- Single confirmation before pushing to Google Calendar

---

## 🔵 Demo & Notebook

### Demo (demo.py)
- Rewritten to mirror notebook step order exactly (Steps 3–11)
- Steps 0/1/2 shown under banner at startup
- `Request:` prompt in cyan (not `You:`)
- `_stream_print()` mirrors `generate_text_stream()` / `demo_streaming()` from class
- Step 4: fuzzy name resolution runs before `resolve()` — `skip_name_resolution=True` prevents double-asking
- Step 7.6: enhance vs. inspire asked once before parallel execution
- Image selection: single unified loop (no two-stage redundancy)
- `_raw_request` internal field hidden from receipt display

### Image Selection UI
- `all` command selects all images and continues immediately
- Auto-select on add: new images auto-selected when added to library
- Single unified command loop with consistent command list shown each time
- `remove <number>` available in quick select prompt

### Receipt Editor
- `num_posts` locked when multiple platforms specified (sum from per-platform counts)
- Internal `_raw_request` field hidden from receipt display

### Notebook (AI_Agent.ipynb)
- All steps follow same order as demo
- Cell ordering fixed (reference_images captured before detection cell)
- Missing setup cell for `agents_per_post` restored
- Style guide update detection uses `refs_before_loop` snapshot (before vs. after)
- `USER_REQUEST` updated to: `"Create 1 Instagram and 2 Twitter posts for Rita's Kiwi Melon in June + Schedule. Make it an interactive post."`

---

## ⚫ Storage & Logging

### Storage
- `references_dir()` added for style reference screenshots
- Image validation guardrail: `.png` and `.jpg/.jpeg` only
- `validate_image()` strips surrounding quotes (handles paths with spaces)
- `save_image()` accepts `filename` param — failed audit images saved as `post_image (Failed Audit).png`

### Logging
- Two log files per run: `Receipt.txt` and `Audit.txt`
- `Audit.txt` includes: A/B score, caption audit result, image audit result, correction history
- `went_nuclear` flag noted in audit log if nuclear corrections were applied

---

## 🟣 Bug Fixes

| Bug | Fix |
|-----|-----|
| `_handle_image()` returning single value vs tuple | All paths return `(image_bytes, audit_result)` |
| `input()` inside thread causing conflict | Moved all user input before parallel execution |
| `agents_per_post` setup cell missing | Restored in notebook Step 8 |
| `reference_images` undefined (wrong cell order) | Fixed cell ordering in notebook |
| `image_mode` undefined in platform execute() | Added resolution block to all 3 agents |
| `_safe_json` wrong import location | Moved to `agent_base.py` |
| `num_posts` parsing "1 Instagram and 2 Twitter" = 2 | Fixed: now sums per-platform counts |
| Company "Rita's" not matching "Rita's Italian Ice" | Fixed: `AI Storage` path uses `Path(__file__).parent` |
| Duplicate "reference added" print | Removed from loop (storage already prints) |
| `enhance or inspire` question mid-thread | Moved to Step 7.6 before parallel execution |
| Image always using first selected photo | Counter initialized randomly each run |
| Image correction prompts too long | Shortened to punchy uppercase single-sentence commands |
