# 🎯 AI Interviewer

> **AI-powered mock interview simulator** — Paste a job description, answer 10 dynamic questions asked by an AI interviewer, and get a full scored report with feedback.

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)
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
| Database | SQLite |
| Frontend | HTML, CSS, Bootstrap 5, Vanilla JS |
| Auth | bcrypt password hashing |
| Testing | Selenium (automated end-to-end) |

---

## 📁 Project Structure

```
AI_interviewr/
│
├── app.py                  # Main Flask app — all routes and AI logic
├── requirements.txt        # Python dependencies
├── .env                    # Your API keys (never committed)
├── .env.example            # Template for environment variables
├── database.db             # SQLite database (auto-created on first run)
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Shared layout
│   ├── index.html          # Landing page
│   ├── login.html          # Login page
│   ├── signup.html         # Signup page
│   ├── setup.html          # Interview setup form
│   ├── interview.html      # Live interview chat
│   ├── result.html         # Score report
│   └── dashboard.html      # User dashboard
│
├── static/
│   ├── css/style.css       # Neo-brutalist pastel theme
│   └── js/interview.js     # Interview state machine
│
└── test_interview.py       # Selenium automated test
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

Copy the example file and fill in your keys:

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Now open `.env` and add your keys:

```env
GROQ_API_KEY=your_groq_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

**Get your free Groq API key →** https://console.groq.com

**Generate a Flask secret key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### Step 5 — Run the app

```bash
python app.py
```

Open your browser at:
```
http://localhost:5000
```

The database is created automatically on first run. ✅

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
| `FLASK_SECRET_KEY` | Flask session secret | ✅ Yes |

> ⚠️ Never commit your `.env` file. It is already in `.gitignore`.

---

## 👤 Author

**Varun Shetty**
GitHub → [@varunshetty1893](https://github.com/varunshetty1893)

---

## 📄 License

Copyright (c) 2026 Varun Shetty — All Rights Reserved.
See [LICENSE](./LICENSE) for details.
