# 🧭 Help Guide — Social Media Post AI Agent

This guide explains what each agent does, how they interact, and what the important functions are. Written for someone who knows basic Python but isn't deep into agentic AI systems.

---

## 🗺️ How the system works (overview)

The agent system is a pipeline. Each step hands its output to the next:

```
Your Request (plain English)
        ↓
  Parse into receipt
        ↓
  Research company/product  ←── stores JSON reports locally
        ↓
  Generate style guide       ←── based on research + your reference screenshots
        ↓
  Select images (optional)
        ↓
  Generate posts (parallel)  ←── Instagram + Twitter run at the same time
        ↓
  Audit captions + images     ←── guardrail checks, escalating corrections
        ↓
  Save to disk + log files
        ↓
  Schedule (optional)        ←── pushes to Google Calendar
```

The notebook (`AI_Agent.ipynb`) and the terminal demo (`demo.py`) both follow this exact sequence. The notebook is for running and exploring; the demo is for a polished interactive experience.

---

## 🤖 The Agents

### `agent_research.py` — Research Agent

**What it does:** Looks up everything about a company and product, then writes two structured reports: a Company Report and a Product Report (both saved as JSON files).

**How it works:** Uses the **ReAct pattern** — a loop where the agent reasons about what to search for, picks a tool, gets a result, reasons about that result, and keeps going until it has enough to write a full report. Tools available: `web_search`, `fetch_url`, `read_document`, `ask` (to ask the user a clarifying question).

**Key functions:**

| Function | What it does |
|---|---|
| `resolve()` | Main entry point — resolves names, runs research, returns 4 things: company report, product report, resolved company name, resolved product name |
| `_run_react_loop()` | The ReAct loop — runs up to `MAX_STEPS` tool calls, then writes the report |
| `_resolve_official_name()` | Fuzzy-matches your typed company name against existing folders so "Rita's" → "Rita's Italian Ice" without re-researching |
| `resolve_style_guide()` | Generates a style guide JSON from the company/product reports + your reference screenshots |

**Important design decisions:**
- Uses **function calling** (structured `tool_calls`) instead of regex parsing. The class notebook used `ACTION_RE` to parse tool calls from raw text — this is more reliable.
- `MAX_STEPS = 6` — tunable tradeoff between research depth and time.
- If more than one field is still `null` after `MAX_STEPS`, it asks you for a URL or file to help.

---

### `agent_base.py` — Base Agent

**What it does:** The foundation all three platform agents build on. Handles everything that's shared: talking to OpenAI, scoring captions, generating/enhancing images, and auditing.

**Key functions:**

| Function | What it does |
|---|---|
| `_ab_loop()` | Draft → score → keep best → repeat up to `max_tries` times. This is the A/B scoring loop |
| `_chat()` | Plain text call to OpenAI — safe to call from threads |
| `_chat_content()` | Multimodal call — accepts text + images (used for vision-based caption drafting with reference screenshots) |
| `_audit_image()` | Calls GPT Vision to check the generated image — returns `passed`, `reason`, and `fix` |
| `_generate_image()` | Calls DALL-E 3 to create a new image from scratch |
| `_enhance_image()` | Calls the image edits endpoint to enhance a real photo |
| `_build_image_prompt()` | Builds the instruction string sent to DALL-E or the edit endpoint |

**Important prompts in this file:**
- `IMAGE_AUDIT_PROMPT` — what GPT Vision checks: logo accuracy, false claims, text legibility, text cutoff at edges
- `CAPTION_AUDIT_PROMPT` — narrow safety check: only fails for outright lies or harmful language

---

### `agent_posts.py` — Platform Agents

**What it does:** Three specialized agents — `InstagramAgent`, `TwitterAgent`, `BlogAgent` — each with their own caption style. They all inherit from `BaseAgent` and just add their own instructions.

**Key functions:**

| Function | What it does |
|---|---|
| `_run_caption_audit_loop()` | Generates a caption via A/B scoring, then runs the caption safety check before accepting |
| `_handle_image()` | Generates or enhances an image using that caption, then runs the image auditor with up to 4 escalating correction attempts |
| `execute()` | Called by each platform agent — runs the caption loop then the image loop, returns the finished post dict |

**The image audit escalation in `_handle_image()`:**

| Attempt | What's sent to the image model |
|---|---|
| 1 | Concise fix from auditor: `FIX: KEEP ALL TEXT FAR FROM TOP EDGE` |
| 2 | Emotional urgency: `DON'T LET TEXT BE CUT OFF OR I WILL BE FIRED` |
| 3 | Nuclear: `NO TEXT IN THE IMAGE AT ALL. ZERO WORDS. ZERO LETTERS` |
| 4 | Final audit — if still fails, no image is saved |

This escalation pattern mirrors `05_emotion_prompting.ipynb` from class — urgency at the top of the prompt changes model behavior.

---

### `agent_parallel.py` — Parallel Workflow

**What it does:** Runs multiple platform agents simultaneously using Python's `ThreadPoolExecutor`. Instagram and Twitter start at the same time — Twitter finishes quickly (no image), Instagram keeps working on its image in the background.

**Key functions:**

| Function | What it does |
|---|---|
| `ParallelWorkflow.run()` | Starts all agents in a round as parallel threads, collects results as they finish |
| `run_all_posts()` | Wrapper — groups platforms into rounds and runs each round |

**Grouping logic:** "1 Instagram and 2 Twitter" becomes:
- Round 1: [Instagram, Twitter] — run together
- Round 2: [Twitter] — alone

This mirrors `07_workflow_multitasking.ipynb` from class, which ran Twitter + LinkedIn + Blog together. The class used `asyncio`; this project uses `ThreadPoolExecutor` — same parallelism for I/O-bound API calls, without needing `async/await` everywhere.

---

### `agent_schedule.py` — Schedule Agent

**What it does:** Takes natural language date input, turns it into specific calendar dates, and pushes events to Google Calendar.

**Key functions:**

| Function | What it does |
|---|---|
| `run()` | Main flow — asks for dates, parses, fills gaps, confirms, pushes to Calendar |
| `_parse_dates()` | Sends your date input through `DATE_PARSE_PROMPT` to get structured `{date, count}` pairs |
| `_suggest_dates()` | GPT picks the remaining dates automatically (labels them `[auto]`) |
| `_get_calendar_service()` | Connects to Google Calendar API using service account credentials |

**`DATE_PARSE_PROMPT`** handles inputs like:
- `"June 5th"` → all posts on June 5th
- `"1 June 5th"` → 1 post on June 5th, rest auto-picked
- `"2 on June 5 and 1 two days later"` → 2 on June 5th, 1 on June 7th

---

### `agent_storage.py` — Storage

**What it does:** All file reading and writing. No AI calls here — purely folder management.

**Key functions:**

| Function | What it does |
|---|---|
| `company_exists()` / `product_exists()` | Check if reports already exist (determines if research is skipped) |
| `list_companies()` | Returns all company folders — used by fuzzy name matching |
| `validate_image()` | Guardrail — only `.png` and `.jpg/.jpeg` accepted |
| `add_image_to_library()` | Copies a photo into the product's image folder |
| `save_posts()` | Creates the output folder structure with caption files |
| `save_image()` | Saves generated image bytes to the post folder |

---

### `agent_utils.py` — Utilities

**What it does:** Request parsing and the receipt editor.

**Key functions:**

| Function | What it does |
|---|---|
| `parse_request()` | Turns plain English into a receipt dict using regex — extracts platform, count, company, product, month, schedule flag, image mode |
| `interactive_receipt_editor()` | Shows the receipt and lets you correct it with `modify <field> to <value>` |
| `confirm()` | Simple yes/no prompt helper |

---

### `agent_logger.py` — Logger

**What it does:** Writes one combined log file per run to the company's `Log Files` folder.

| Section | Contents |
|---|---|
| Receipt | What was requested, reports used, captions with A/B scores, output path |
| Content Audit | Caption pass/fail, image pass/fail, correction prompts sent per attempt, overall result |

---

## 🔗 How agents interact

```
agent_utils.py          → parse_request() creates the receipt
agent_research.py       → resolve() reads the receipt, writes JSON reports
agent_research.py       → resolve_style_guide() creates style guide
agent_posts.py          → each agent reads base_brief (context + images + style)
agent_base.py           → _ab_loop() scores captions (called by all agents)
agent_base.py           → _handle_image() generates + audits image (called by all agents)  
agent_parallel.py       → run_all_posts() coordinates all agents across rounds
agent_storage.py        → read/write throughout entire pipeline
agent_logger.py         → write() called at end of pipeline
agent_schedule.py       → run() called last if schedule=Yes
```

Data flows through a `base_brief` dict that carries everything the agents need:

```python
base_brief = {
    "context":                # full company/product/style summary
    "image_mode":             # Provided Images / AI Generated / No
    "selected_images":        # paths to photos in the image library
    "reference_images":       # style screenshots for vision-based drafting
    "style_vibe":             # e.g. "Nostalgic, sunny, summery"
    "logo_description":       # from company report — prevents DALL-E inventing logos
    "enhance_as_inspiration": # True = use photo as style inspiration, not direct enhance
    "brand_context":          # notes + style + product + company (for image generation)
}
```

---

## 🛡️ Guardrail system

Two independent audit layers run on every post:

**Layer 1 — Caption auditor** (text)
- Only fails for outright lies or hateful/harmful language
- Veto with retry — if failed, caption is regenerated

**Layer 2 — Image auditor** (visual)
- GPT Vision checks: logo correct, no false claims, all text fully visible and not clipped
- 4-attempt escalation with increasing urgency (see table above)
- If all attempts fail, no image is used — caption is saved alone
- User can choose to save the failed audit image anyway (marked as `Failed Audit`)

Both audit results are written to `Audit.txt` including the correction prompts sent on each attempt.

**Design philosophy:** "No image is better than a bad image." The auditor is conservative — it would rather produce a caption-only post than publish a post with clipped text or a wrong logo.

---

## 📝 Key prompts (where to find them)

| Prompt | File | Purpose |
|---|---|---|
| `REACT_PROMPT` | `agent_research.py` | Controls the ReAct research loop |
| `COMPANY_REPORT_PROMPT` | `agent_research.py` | What fields to extract for the company report |
| `PRODUCT_REPORT_PROMPT` | `agent_research.py` | What fields to extract for the product report |
| `IMAGE_AUDIT_PROMPT` | `agent_base.py` | GPT Vision audit criteria |
| `CAPTION_AUDIT_PROMPT` | `agent_base.py` | Caption safety check |
| `DATE_PARSE_PROMPT` | `agent_schedule.py` | Natural language date parsing |
| `AUTO_DATE_PROMPT` | `agent_schedule.py` | GPT date suggestion |
| `INTENT_PROMPT` | `demo.py` | Classifies user intent (create posts / manage files / quit) |
