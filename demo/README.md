# 🤖 Social Media Post AI Agent

An AI agent that researches companies and products, then creates consistent, on-brand social media posts. Returns visits are fast — just hit Enter through the research steps and go straight to generating new posts in the same style.

---

## 📁 File Overview

| File | Purpose |
|---|---|
| `AI_Agent.ipynb` | Main notebook — run this cell by cell |
| `agent_storage.py` | All file I/O and folder management |
| `agent_research.py` | ReAct + function calling research agent |
| `agent_base.py` | Base class shared by all platform agents |
| `agent_posts.py` | Instagram, Twitter, Blog agent classes |
| `agent_parallel.py` | Runs platform agents in parallel (ThreadPoolExecutor) |
| `agent_schedule.py` | Suggests posting dates + Google Calendar integration |
| `agent_logger.py` | Writes a log file after each run |
| `agent_utils.py` | Request parser, receipt editor, helper functions |
| `requirements.txt` | Python dependencies |
| `.env` | Your API keys — fill this in before running |
| `.gitignore` | Keeps your `.env` and credentials out of GitHub |

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Fill in your `.env` file

Open `.env` and replace the placeholder values:

```
OPENAI_API_KEY=sk-...         ← required
GCAL_ID=you@gmail.com         ← only needed for scheduling
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

Open `AI_Agent.ipynb` in VS Code and run cells top to bottom.

Change the request string in **Step 3** to whatever you want:

```python
USER_REQUEST = "Create 3 Instagram posts for Rita's Kiwi Melon in June + Schedule. Make it interactive please."
```

**More examples:**
```
Create 2 Twitter posts for Nike Air Max in July.
Create 1 Blog post for the Philly Food Festival event in August + Schedule.
Create 3 Instagram posts for Apple iPhone 16 in September.
```

**Tip — if the product isn't online yet or you have a specific URL:**

In Step 4 of the notebook, set these before running:
```python
provided_url  = "https://example.com/about"   # company or product page
uploaded_file = "my_product_brief.pdf"         # or a .txt file you drop in the folder
```

Leave them as `None` if you don't need them — the agent will search the web automatically.

---

## 🔄 What happens on return visits

The second time you run the agent for the same company and product:
- It loads the existing Company Report, Product Report, and Style Guide from your local folder
- You just hit Enter through the research steps
- Posts are generated in the same style and tone as before

---

## 📂 Output folder structure

Everything is saved inside an `AI Storage` folder that gets created automatically:

```
AI Storage/
  Rita's Water Ice/
    Rita's Water Ice Company Report.json
    Products/
      Kiwi Melon Product Report.json
    Style Guides/
      Kiwi Melon Style Guide.json
    Created Posts/
      2026-06-01 – Request Kiwi Melon/
        Post 1/
          caption.txt
          image_prompt.txt
        Post 2/
          caption.txt
        Receipt of Creation.txt
    Log Files/
      2026-06-01 – Rita's Water Ice – Kiwi Melon – Receipt.txt
```

---

## 🛠️ Things you can tweak

| What | Where | Default |
|---|---|---|
| A/B score threshold | `ab_threshold` in `agent_base.py` | 7.5 / 10 |
| A/B max attempts | `ab_max_tries` in `agent_base.py` | 3 |
| Max research steps | `MAX_STEPS` in `agent_research.py` | 6 |
| Main GPT model | `main_model` in `agent_base.py` | gpt-4o |
| Reviewer model | `review_model` in `agent_base.py` | gpt-3.5-turbo |
| Research prompt | `REACT_PROMPT` in `agent_research.py` | see file |

---

## 🐛 Common issues

**"OPENAI_API_KEY not found"**
You haven't filled in your `.env` file yet, or the `.env` file isn't in the same folder as the notebook.

**"No module named ddgs"**
Run `pip install -r requirements.txt` again.

**"Document not found" when uploading a file**
Make sure the file is in the same folder as `AI_Agent.ipynb`, then set `uploaded_file = "filename.pdf"` in Step 4.

**Google Calendar not working**
Make sure you shared your calendar with the service account email (step 7 of Calendar setup above) — this is the most commonly missed step.
