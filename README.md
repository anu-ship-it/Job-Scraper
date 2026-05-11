# ⚡ AI Job Scraper — Powered by Ollama

A fully local, AI-powered personalized job scraper that:
1. **Reads your resume** (PDF/DOCX/TXT) and extracts your skills, roles, experience
2. **Scrapes LinkedIn, Indeed, Naukri** for jobs matching your profile
3. **Scores every job** against your resume using Ollama LLM (local, private)
4. **Reports weekly** on jobs ≥80% match — every Sunday at 8AM

---

## 🚀 Setup (5 Steps)

### Step 1 — Install Ollama
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Pull your model (llama3 recommended, ~4.7GB)
ollama pull llama3

# Start Ollama server
ollama serve
```

### Step 2 — Clone & Install Python deps
```bash
cd job-scraper
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Run the App
```bash
python app.py
```
Open: **http://localhost:5000**

### Step 4 — Upload Your Resume
- Go to the **Resume** tab
- Upload PDF, DOCX, or TXT
- Ollama will analyze it and extract your profile in ~30 seconds

### Step 5 — Run Pipeline / Wait for Sunday
- Go to **Dashboard** → click **"Run Full Pipeline Now"**
- OR wait for the auto-run every Sunday at 8:00 AM IST
- View results in the **Matches** and **Reports** tabs

---

## 🏗 Architecture

```
app.py                    ← Flask web server + UI
core/
  resume_parser.py        ← PDF/DOCX/TXT text extraction
  ollama_engine.py        ← All LLM calls (resume analysis + job scoring)
  pipeline.py             ← Orchestrates scrape → score → report
  database.py             ← SQLite storage (jobs, matches, reports)
scrapers/
  job_scrapers.py         ← LinkedIn, Indeed, Naukri scrapers
reports/
  report_generator.py     ← HTML weekly digest generator
scheduler/
  scheduler.py            ← APScheduler (cron: Sunday 8AM)
```

---

## ⚙️ Configuration (Settings tab in UI)

| Setting | Default | Description |
|---------|---------|-------------|
| Location | India | Job search geography |
| Score Threshold | 80% | Min match score to include in report |
| Jobs per Role | 10 | How many jobs to scrape per role per source |
| Ollama Model | llama3 | Switch to mistral, phi3, gemma, etc. |
| Schedule Day | Sunday | Which day to run the weekly pipeline |
| Schedule Hour | 8 | What hour (IST) to run |

---

## 🤖 How Scoring Works

Ollama receives:
- **Your profile**: skills, years of experience, seniority, education
- **Job posting**: title, company, full job description

It returns:
- `score` (0–100)
- `matched_skills` — what you already have
- `missing_skills` — what you'd need to learn
- `verdict` — excellent_fit / good_fit / partial_fit / poor_fit
- `reasoning` — 2–3 sentence explanation
- `apply_priority` — urgent / high / medium / low

Only jobs scoring **≥ 80%** appear in your weekly report.

---

## 🔒 Privacy

**Everything runs 100% locally.** Your resume and job data never leave your machine.
- Ollama runs offline
- SQLite stores data in `job_scraper.db` (local file)
- No API keys, no cloud services required

---

## 🛠 Troubleshooting

**Ollama not detected?**
```bash
ollama serve   # Make sure it's running on port 11434
ollama list    # Verify your model is pulled
```

**LinkedIn/Indeed blocking requests?**
- The scraper uses rotating user-agents and delays
- If blocked, reduce `max_per_role` or add longer delays in `scrapers/job_scrapers.py`

**Want to use Naukri for India-specific jobs?**
- Naukri is enabled by default in the scraper
- It works well for Indian tech job market

---

## 📦 Requirements

- Python 3.11+
- Ollama (running locally)
- 8GB RAM minimum (for llama3)
- ~5GB disk space for llama3 model
