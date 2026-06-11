# AI Interviewr — AI Mock Interviewer

Simple Flask web app. No React, no Node, no frontend build tools.

## Setup (one time only)

1. Install packages:
   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and paste your Groq API key:
   ```
   GROQ_API_KEY=your_key_here
   ```
   Get a free key at: https://console.groq.com

3. Generate a secure Flask secret key (optional but recommended):
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Paste the output as `FLASK_SECRET_KEY` in your `.env`.

## Run

```
python app.py
```

Then open your browser at: http://localhost:5000

## That's it!
- Sign up with any email/password
- Paste a job description
- Answer AI-generated questions
- Get a full scored report
