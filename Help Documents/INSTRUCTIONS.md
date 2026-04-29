# 🤖 Social Media Post AI Agent — Instructions

An AI agent that researches companies and products, then creates consistent, on-brand social media posts. Return visits are fast — just hit Enter through the research steps and go straight to generating new posts in the same style.

---

## 📁 File Overview

| File | Purpose |
|---|---|
| `AI_Agent.ipynb` | Main notebook — run this cell by cell |
| `demo.py` | Terminal demo — same steps, interactive CLI |
| `agent_storage.py` | All file I/O and folder management |
| `agent_research.py` | ReAct + function calling research agent |
| `agent_base.py` | Base class shared by all platform agents |
| `agent_posts.py` | Instagram, Twitter, Blog agent classes |
| `agent_parallel.py` | Runs platform agents in parallel (ThreadPoolExecutor) |
| `agent_schedule.py` | Natural language date parsing + Google Calendar |
| `agent_logger.py` | Writes Receipt and Audit log files after each run |
| `agent_utils.py` | Request parser, receipt editor, helper functions |
| `requirements.txt` | Python dependencies |
| `.env` | Your API keys — fill this in before running |
| `.gitignore` | Keeps your `.env` and `credentials.json` out of GitHub |

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Fill in your `.env` file

Open `.env` and replace the placeholder values:

```
OPENAI_API_KEY=sk-...              ← required
GCAL_ID=you@gmail.com              ← only needed for scheduling
GCAL_CREDENTIALS=credentials.json  ← only needed for scheduling
```

Get your OpenAI key at: https://platform.openai.com/api-keys

### 3. (Optional) Google Calendar setup

Only needed if you want the agent to schedule posts. Skip this on your first run.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → search "Google Calendar API" → Enable it
3. Go to **Credentials** → **+ Create Credentials** → **Service Account**
4. Give it a name → Done
5. Click the service account → **Keys** tab → **Add Key** → **Create new key** → JSON
6. Rename the downloaded file to `credentials.json` and put it in your project folder
7. Open Google Calendar → Settings → your calendar → **Share with specific people**
8. Add the service account email (looks like `name@your-project.iam.gserviceaccount.com`)
9. Give it **"Make changes to events"** permission

---

## 🚀 Running the agent

### Option A — Jupyter Notebook
Open `AI_Agent.ipynb` in VS Code and run cells top to bottom.

### Option B — Terminal Demo
```bash
python demo.py
```
Same steps as the notebook in an interactive command-line interface.

---

## ✏️ Writing your request

Change the request string in **Step 3** to whatever you want:

```python
USER_REQUEST = "Create 1 Instagram and 2 Twitter posts for Rita's Kiwi Melon in June + Schedule. Make it an interactive post."
```

**More examples:**
```
Create 2 Twitter posts for Nike Air Max in July.
Create 1 Blog post for the Philly Food Festival event in August + Schedule.
Create 3 Instagram posts for Apple iPhone 16 in September.
Create 1 Instagram and 2 Twitter posts for Starbucks Pumpkin Spice Latte in October.
```

### Request format tips

| Element | Example | Notes |
|---|---|---|
| Platform + count | `2 Twitter posts` | Instagram, Twitter, Blog supported |
| Multiple platforms | `1 Instagram and 2 Twitter` | Runs in parallel |
| Company + product | `for Rita's Kiwi Melon` | Apostrophe+s signals company boundary |
| Month | `in June` | Sets the seasonal context for captions |
| Scheduling | `+ Schedule` | Pushes to Google Calendar after generation |
| Image override | `without image` or `AI generated images` | Overrides platform default |

---

## 📸 Image modes

| Mode | Behavior |
|---|---|
| **Provided Images** | Uses photos from your image library (default for Instagram) |
| **AI Generated** | Generates new images using DALL-E 3 |
| **No** | Caption only, no image (default for Twitter and Blog) |

To add photos to your image library, follow the prompts in Step 7.6.

---

## 🔗 Providing a reference URL or file

If the product isn't online yet or you have a specific page you want researched, set these in Step 4 before running:

```python
company_url   = "https://example.com/about"    # company or product page
uploaded_file = "my_product_brief.pdf"          # or a .txt file in the same folder
```

Leave them as `None` to let the agent search the web automatically.

---

## 🔄 Return visits

The second time you run the agent for the same company and product:
- It loads the existing Company Report, Product Report, and Style Guide from your local folder
- Hit Enter through the research steps to skip re-researching
- Posts are generated in the same style and tone as before

---

## 📂 Output folder structure

Everything is saved inside an `AI Storage` folder created automatically next to the notebook:

```
AI Storage/
  Rita's Italian Ice/
    Rita's Italian Ice Company Report.json
    Products/
      Kiwi Melon Product Report.json
    Style Guides/
      Kiwi Melon Style Guide.json
    Images/
      Kiwi Melon/
        photo1.jpg
        references/
          example_post.jpg
    Created Posts/
      2026-06-01 – Request Kiwi Melon/
        Post 1/
          caption.txt
          post_image.png
        Post 2/
          caption.txt
        Receipt of Creation.txt
    Log Files/
      2026-06-01 – Rita's Italian Ice – Kiwi Melon – Receipt.txt
```

---

## 🛠️ Things you can tweak

| What | Where | Default |
|---|---|---|
| A/B score threshold | `ab_threshold` in `agent_base.py` | 9.0 / 10 |
| A/B max attempts | `ab_max_tries` in `agent_base.py` | 3 |
| Image audit retries | `MAX_AUDIT_RETRIES` in `agent_base.py` | 3 (4 total attempts) |
| Max research steps | `MAX_STEPS` in `agent_research.py` | 6 |
| Main GPT model | `main_model` in `agent_base.py` | gpt-4o |
| Reviewer model | `review_model` in `agent_base.py` | gpt-3.5-turbo |
| Research prompt | `REACT_PROMPT` in `agent_research.py` | see file |
| Date parse prompt | `DATE_PARSE_PROMPT` in `agent_schedule.py` | see file |

---

## 🐛 Common issues

**"OPENAI_API_KEY not found"**
You haven't filled in your `.env` file yet, or the `.env` file isn't in the same folder as the notebook/demo.

**"No module named ddgs"**
Run `pip install -r requirements.txt` again.

**"File not found" when uploading a photo**
Make sure the file path is correct and the file is a `.png` or `.jpg`. Paste the path directly into the image selection prompt — quotes around the path are handled automatically.

**Company not recognized on return visit**
The fuzzy match checks existing folders. If you previously used a slightly different name (e.g. "Rita's" vs "Rita's Italian Ice"), the agent will ask which one you meant. Just confirm and it will load the right folder.

**Google Calendar not working**
Make sure you shared your calendar with the service account email (step 8 of Calendar setup above) — this is the most commonly missed step.
