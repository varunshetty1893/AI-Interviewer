# 🎯 AI Interviewer

> **AI-powered mock interview simulator** — Paste a job description, answer 10 dynamic questions asked by an AI interviewer, and get a full scored report with feedback.

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-hosted-336791?style=flat-square&logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)
![License](https://img.shields.io/badge/License-All_Rights_Reserved-red?style=flat-square)

---

## ✨ Features

- 🤖 **Dynamic AI Interviewer** — Questions adapt based on your previous answers
- 📋 **JD-based questions** — Tailored to the exact job description you paste
- 🎓 **Experience levels** — Fresher, Intern, Junior, Mid, Senior, Lead
- 📊 **Detailed score report** — 5 skill dimensions: Technical, Communication, Confidence, HR, Subject
- 💡 **Actionable feedback** — Strengths, weaknesses, topics to study, free course links
- 📈 **Progress tracking** — Dashboard with score history chart
- 🔐 **User accounts** — Signup, login, personal interview history

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| AI Engine | Groq API (LLaMA 3.3 70B) |
| Database | PostgreSQL when hosted (Vercel), SQLite file for local use |
| Frontend | HTML, CSS, Bootstrap 5, Vanilla JS |
| Auth | bcrypt password hashing |

---

## 📁 Project Structure

```
AI-Interviewer-main/
│
├── app.py                  # Flask app - all routes and AI logic (Vercel entrypoint)
├── requirements.txt        # Python dependencies
├── .python-version         # Python version used on Vercel
├── .env.example            # Template for environment variables
├── .vercelignore           # Files never uploaded to Vercel
├── Procfile                # Only for Render/Heroku-style hosts
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html  index.html  login.html  signup.html
│   ├── setup.html  interview.html  result.html  dashboard.html
│
└── public/static/          # CSS + JS (served by Vercel's CDN, and by Flask locally)
    ├── css/style.css
    └── js/interview.js
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip
- Google Chrome (for Selenium tests only)

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/varunshetty1893/AI-Interviewr.git
cd AI-Interviewr
```

---

### Step 2 — Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Set up environment variables

```bash
# Windows (PowerShell / CMD)
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Open `.env` and fill in:

```env
GROQ_API_KEY=your_groq_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
DATABASE_URL=
```

- **GROQ_API_KEY** - free key from https://console.groq.com
- **FLASK_SECRET_KEY** - generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- **DATABASE_URL** - **leave empty locally.** The app then uses a local SQLite file (`database.db`, created automatically). Fill it only if you want to run locally against PostgreSQL.

---

### Step 5 — Run the app

```bash
python app.py
```

Open http://localhost:5000 - tables are created automatically. ✅

---

## ▲ Deploy to Vercel

Vercel's filesystem is read-only, so a hosted app needs a **PostgreSQL** database. Neon has a free plan.

**1. Create the database**
- Easiest: in Vercel go to **Storage → Create → Neon** (Marketplace) and connect it to your project. It adds `DATABASE_URL` for you.
- Or create a free database at https://neon.tech (or Supabase) and copy the **pooled** connection string. It looks like `postgresql://user:pass@host/db?sslmode=require`.

**2. Push the project to GitHub** (the `.env` file is git-ignored, so your keys are not uploaded).

**3. Import it in Vercel**
- Vercel dashboard → **Add New → Project** → pick the repo.
- Framework Preset should show **Flask** (auto-detected from `app.py`).
- Add these **Environment Variables**:

| Name | Value |
|---|---|
| `GROQ_API_KEY` | your Groq key |
| `FLASK_SECRET_KEY` | a long random string (see Step 4) |
| `DATABASE_URL` | your PostgreSQL connection string (skip if the Neon integration added it) |

- Click **Deploy**. Tables are created automatically on the first visit.

**Using the Vercel CLI instead**
```bash
npm i -g vercel
vercel          # first deploy (preview)
vercel --prod   # production
```

**Troubleshooting**

| Symptom | Fix |
|---|---|
| Page says "Setup problem: DATABASE_URL is not set" | Add `DATABASE_URL` in Project → Settings → Environment Variables, then **Redeploy** |
| Page says "FLASK_SECRET_KEY is not set" | Add it the same way, then Redeploy |
| "Evaluation failed" after the last question | Report generation can take 10-20 s. Raise **Function Max Duration** in Project → Settings → Functions, and check `GROQ_API_KEY` |
| Logged out right after login | Make sure you open the `https://` URL (secure cookies) and that `FLASK_SECRET_KEY` is the same in every environment |
| Database connection errors | Use the **pooled** connection string and keep `?sslmode=require` |

---

## 🚀 How to Use

```
1. Sign up with any name, email, and password
      ↓
2. Click "New Interview" on the dashboard
      ↓
3. Paste a job description and fill in your details
      ↓
4. Answer 10 AI-generated questions in the chat
      ↓
5. Click "Generate Report" to see your full score breakdown
```

---


## 📊 Score Report Breakdown

| Dimension | What it measures |
|---|---|
| Technical | Accuracy and depth of technical answers |
| Communication | Clarity and structure of responses |
| Confidence | Ownership and conviction in answers |
| HR | Quality of behavioral and career answers |
| Subject | Domain knowledge relevant to the JD |

Final score = average of all 5 dimensions (skipped questions are penalised).

---

## 🔐 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key | ✅ Yes |
| `FLASK_SECRET_KEY` | Flask session secret | ✅ Yes (required on Vercel) |
| `DATABASE_URL` | PostgreSQL connection string | ✅ On Vercel · empty = local SQLite |

> ⚠️ Never commit your `.env` file. It is already in `.gitignore`.

---

## 👤 Author

**Varun Shetty**
GitHub → [@varunshetty1893](https://github.com/varunshetty1893)

---

## 📄 License

Copyright (c) 2026 Varun Shetty — All Rights Reserved.
See [LICENSE](./LICENSE) for details.
