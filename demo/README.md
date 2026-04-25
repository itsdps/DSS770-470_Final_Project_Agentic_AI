# 🤖 Social Media Post AI Agent

An AI-powered agent that creates, scores, and schedules social media posts for any company/product — and remembers past work for consistent branding.

---

## 📁 File Overview

| File | Purpose |
|---|---|
| `AI_Agent.ipynb` | Main notebook — run this |
| `agent_storage.py` | All file I/O and folder management |
| `agent_research.py` | Web search + GPT → Company/Product/Style reports |
| `agent_posts.py` | Post generation with A/B scoring loop |
| `agent_schedule.py` | Date suggestion + Google Calendar integration |
| `agent_logger.py` | Log file writer |
| `agent_utils.py` | Request parser, receipt editor, helpers |
| `requirements.txt` | Python dependencies |

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get API keys

| Key | Where to get it |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `SERPER_API_KEY` | https://serper.dev (100 free searches/month) |
| Google Calendar | Google Cloud Console → Service Account → Download JSON |

### 3. Set environment variables (or paste directly into Step 1 of the notebook)
```bash
export OPENAI_API_KEY="sk-..."
export SERPER_API_KEY="..."
export GCAL_ID="your-email@gmail.com"
export GCAL_CREDENTIALS="credentials.json"
```

### 4. Google Calendar credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Calendar API**
3. Create a **Service Account** → Download `credentials.json`
4. Share your calendar with the service account email

---

## 🚀 Usage

Open `AI_Agent.ipynb` in VS Code or Jupyter and run cells top to bottom.

**Example requests:**
```
Create 3 Instagram posts for Rita's Kiwi Melon in June + Schedule. Make it interactive please.
Create 2 Twitter posts for Apple iPhone 16 in July.
Create 1 Blog post for Nike Air Max in August + Schedule.
```

---

## 📂 Output Structure

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
        Receipt of Creation.txt
    Log Files/
      2026-06-01 – Rita's Water Ice – Kiwi Melon – Receipt.txt
```

---

## 🔄 Returning for Future Posts

When you run the agent again for the same company/product, it will:
- Load the existing Company and Product reports
- Load the existing Style Guide (keeping brand consistency)
- Generate new posts in the same style

---

## 🛠️ Customization

- **Change A/B threshold**: Edit `ab_threshold` in `PostAgent` (default: 7.5/10)
- **Change A/B attempts**: Edit `ab_max_tries` (default: 3)
- **Add platforms**: Add a new `_platform_instructions()` function in `agent_posts.py`
- **Change models**: Edit `main_model` / `review_model` in `PostAgent`
