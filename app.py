"""
InterviewQuest — AI Mock Interviewer
Dynamic conversation-based interview engine
Run: python app.py → http://localhost:5000
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from functools import wraps

import bcrypt
from groq import Groq
from flask import (Flask, redirect, render_template, request,
                   session, url_for, jsonify)

# ── .env loader ───────────────────────────────────────────────────────────────
def load_env():
    path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS interviews (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            jd               TEXT NOT NULL,
            role             TEXT,
            experience       TEXT,
            skills           TEXT,
            -- legacy cols kept for compat
            course           TEXT,
            branch           TEXT,
            subjects         TEXT,
            -- dynamic interview state
            conversation_json TEXT NOT NULL DEFAULT '[]',
            current_index    INTEGER NOT NULL DEFAULT 0,
            total_questions  INTEGER NOT NULL DEFAULT 10,
            status           TEXT NOT NULL DEFAULT 'in_progress',
            -- result
            report_json      TEXT,
            total_score      INTEGER,
            created_at       TEXT NOT NULL,
            completed_at     TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_interviews_user ON interviews(user_id);
    """)
    conn.commit()
    conn.close()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ── Auth ──────────────────────────────────────────────────────────────────────
def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    row  = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?", (uid,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return f(*a, **kw)
    return w

def login_required_json(f):
    @wraps(f)
    def w(*a, **kw):
        if not session.get("user_id"):
            return jsonify({"error": "Not authenticated"}), 401
        return f(*a, **kw)
    return w

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"

def get_groq():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    return Groq(api_key=key)

def ask_groq(system_msg, user_msg, temperature=0.75):
    client = get_groq()
    r = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=temperature,
    )
    return r.choices[0].message.content

def extract_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise

# ── Interview stages ──────────────────────────────────────────────────────────
STAGES = [
    {"id": "intro",      "label": "Introduction",        "q_range": (1, 3)},
    {"id": "project",    "label": "Project Deep Dive",   "q_range": (4, 6)},
    {"id": "technical",  "label": "Technical Assessment","q_range": (7, 8)},
    {"id": "behavioral", "label": "Behavioral",          "q_range": (9, 9)},
    {"id": "career",     "label": "Career & Role Fit",   "q_range": (10, 10)},
]

def get_stage(q_number):
    """Return stage dict for 1-based question number."""
    for s in STAGES:
        lo, hi = s["q_range"]
        if lo <= q_number <= hi:
            return s
    return STAGES[-1]

def prev_stage(q_number):
    if q_number <= 1:
        return None
    return get_stage(q_number - 1)

def needs_transition(q_number):
    """True when moving into a new stage."""
    if q_number <= 1:
        return False
    return get_stage(q_number)["id"] != get_stage(q_number - 1)["id"]

# ── AI functions ──────────────────────────────────────────────────────────────

def build_memory(conversation):
    """
    Scan conversation for projects, techs, claims mentioned by candidate.
    Returns a compact memory string to include in prompts.
    """
    if not conversation:
        return "No answers yet."
    lines = []
    for turn in conversation:
        if turn["role"] == "candidate" and turn.get("answer"):
            lines.append(turn["answer"][:300])
    text = " | ".join(lines)
    # Truncate to avoid huge prompts
    return text[:1200] if text else "No answers yet."

def build_transcript(conversation):
    parts = []
    for t in conversation:
        if t["role"] == "interviewer":
            parts.append(f"Interviewer: {t['text']}")
        elif t["role"] == "candidate":
            ans = t.get("answer") or "(skipped)"
            parts.append(f"Candidate: {ans}")
    return "\n".join(parts)

def generate_opening(role, experience, skills, jd):
    system = (
        "You are Alex, a warm and professional interviewer. "
        "Write a short, friendly opening greeting for a mock interview. "
        "Introduce yourself as Alex, welcome the candidate, briefly mention the role, "
        "and let them know you will conduct a structured 10-question interview. "
        "End by asking them to introduce themselves. "
        "Keep it to 3-4 sentences. Do NOT number the question."
    )
    user = (
        f"Role: {role or 'Software Developer'}\n"
        f"Experience: {experience or 'fresher'}\n"
        f"Skills: {skills or 'general'}\n"
        f"JD snippet: {jd[:300]}"
    )
    return ask_groq(system, user, temperature=0.6)

def generate_next_question(jd, role, experience, skills, conversation, q_number, total=10):
    """
    Dynamically generate the next question based on full conversation history.
    q_number is 1-based.
    """
    import random, time
    salt = random.randint(1000, 9999)

    stage      = get_stage(q_number)
    transition = ""
    if needs_transition(q_number):
        prev = prev_stage(q_number)
        transitions = {
            "project":    "Great, thanks for that background. Now I'd like to dive deeper into your project work.",
            "technical":  "Thanks for sharing that. Let's move on to some technical questions now.",
            "behavioral": "Good. Let's switch gears — I'd like to understand how you work with others.",
            "career":     "Almost done. Finally, I'd like to understand your career goals and fit for this role.",
        }
        transition = transitions.get(stage["id"], "")

    memory     = build_memory(conversation)
    transcript = build_transcript(conversation)

    # Build list of already-asked questions to avoid repetition
    asked = [t["text"] for t in conversation if t["role"] == "interviewer"]
    asked_str = "\n".join(f"- {q}" for q in asked[-6:]) if asked else "None yet."

    stage_guides = {
        "intro": (
            "Ask about: self-introduction, education background, internship or work experience, "
            "key projects. Keep it conversational and welcoming."
        ),
        "project": (
            "Explore the candidate's projects in depth. Ask about: technical decisions made, "
            "challenges they overcame, their specific role, tools/technologies used, "
            "and what they learned. Reference specific projects they mentioned if possible."
        ),
        "technical": (
            "Test conceptual understanding relevant to the role. Ask about: "
            "how technologies work, differences between concepts, when to use what, "
            "how they've applied technical knowledge. "
            "NEVER ask to write code. Ask about CONCEPTS and EXPERIENCE only."
        ),
        "behavioral": (
            "Explore soft skills and work style. Ask about: teamwork, handling disagreements, "
            "dealing with pressure, communication, learning from failure."
        ),
        "career": (
            "Explore motivation and long-term fit. Ask about: why this role, career goals, "
            "what they bring to the team, why they'd be a good hire."
        ),
    }

    system = (
        "You are Alex, a sharp but empathetic interviewer conducting a real job interview. "
        "Your job is to generate the NEXT single question for the interview. "
        "RULES: "
        "1. Generate exactly ONE question. No preamble, no numbering. "
        "2. NEVER ask to write code, implement algorithms, or show syntax. "
        "3. If the candidate mentioned something interesting, follow up on it. "
        "4. Challenge vague or weak answers with a clarifying question. "
        "5. Never repeat a question already asked. "
        "6. Keep the question conversational and concise (1-2 sentences max). "
        "7. If a stage transition is provided, start your question with that transition phrase naturally woven in. "
        "8. Respond with ONLY the question text. Nothing else."
    )

    user = f"""INTERVIEW CONTEXT (seed {salt}-{int(time.time())}):
Role: {role or 'Software Developer'}
Experience: {experience or 'fresher'}
Skills: {skills or 'general'}
JD: {jd[:400]}

CURRENT STAGE: {stage['label']} (Q{q_number} of {total})
STAGE GUIDE: {stage_guides[stage['id']]}

TRANSITION TO USE (if any): {transition or 'None — continue naturally'}

CANDIDATE MEMORY (what they've mentioned so far):
{memory}

RECENT TRANSCRIPT:
{transcript[-2000:]}

QUESTIONS ALREADY ASKED (do NOT repeat these):
{asked_str}

Generate the next single question for Q{q_number}. Probe deeper if the candidate made a claim worth exploring."""

    return ask_groq(system, user, temperature=0.8)


def evaluate_interview(jd, role, experience, conversation):
    """Evaluate the full conversation and return a scored report."""

    # Build clean QA pairs from conversation
    qa_pairs = []
    turns = list(conversation)
    for idx, turn in enumerate(turns):
        if turn["role"] == "interviewer" and turn.get("q_num"):
            # Find the very next candidate turn
            next_ans = next(
                (t.get("answer", "") for t in turns[idx+1:] if t["role"] == "candidate"),
                ""
            )
            qa_pairs.append({
                "q_num":  turn["q_num"],
                "stage":  turn.get("stage", "general"),
                "q":      turn["text"],
                "a":      next_ans or "(skipped)",
            })

    qa_str = "\n\n".join(
        f"Q{p['q_num']} [{p['stage'].upper()}]: {p['q']}\nCANDIDATE: {p['a']}"
        for p in qa_pairs
    )

    skipped = sum(1 for p in qa_pairs if not p["a"] or p["a"] == "(skipped)")
    answered = len(qa_pairs) - skipped

    system = (
        "You are a strict but fair senior interviewer and hiring coach. "
        "Your job is to evaluate a mock interview transcript honestly and helpfully. "
        "You penalise vague, generic, or skipped answers. "
        "You reward specific, structured, and confident answers. "
        "RULES: "
        "1. Be specific in feedback — mention actual things the candidate said or failed to say. "
        "2. Do NOT give inflated scores. A fresher with decent answers scores 55-70. "
        "   Strong answers score 70-85. Outstanding answers score 85+. "
        "3. Skipped answers significantly lower scores. "
        "4. Respond with STRICT VALID JSON only — no prose, no markdown."
    )

    user = f"""ROLE: {role or 'Software Developer'}
EXPERIENCE LEVEL: {experience or 'fresher'}
JOB DESCRIPTION: {jd[:500]}

INTERVIEW TRANSCRIPT:
{qa_str}

STATS: {answered} of {len(qa_pairs)} questions answered. {skipped} skipped.

─── SCORING DIMENSIONS (each 0-100) ───
technical_score     : Accuracy and depth of technical answers. Penalise vague or wrong answers.
communication_score : Clarity, structure, and articulation. Was the answer easy to follow?
confidence_score    : Did they speak with ownership? Or were answers hedged and uncertain?
hr_score            : Quality of HR/behavioral/career answers. Were they specific and genuine?
subject_score       : How relevant and accurate was domain knowledge to the JD?

Compute total_score = integer average of all 5.

─── ALSO PROVIDE ───
strengths               : list of 3-5 strings. Reference SPECIFIC things they said.
weaknesses              : list of 3-5 strings. Be honest and specific.
improvement_suggestions : list of 3-5 actionable strings a student can actually do.
recommended_topics      : list of 5-6 topic name strings relevant to the JD and weak areas.
recommended_courses     : list of 3 objects {{"title":"...","provider":"...","url":"https://..."}}
                          Use REAL free resources: Coursera free audit, freeCodeCamp, GeeksForGeeks,
                          Python docs, MDN, YouTube channels like Corey Schafer, CS Dojo, etc.
per_answer_feedback     : list of {len(qa_pairs)} objects:
  {{"q_index": 0-based int, "rating": "Strong|Average|Weak", "comment": "1-2 specific sentences"}}
  Rate EVERY question. Reference what the candidate actually said.

Respond with ONE JSON object only."""

    raw  = ask_groq(system, user, temperature=0.25)
    data = extract_json(raw)
    if not isinstance(data, dict):
        raise ValueError("Did not return a report object")

    def _int(v):
        try:
            return max(0, min(100, int(round(float(v)))))
        except Exception:
            return 0

    for key in ("technical_score", "communication_score", "confidence_score", "hr_score", "subject_score"):
        data[key] = _int(data.get(key, 0))

    # Penalise skipped answers in total score
    skip_penalty = skipped * 3
    if "total_score" not in data:
        raw_total = (
            data["technical_score"] + data["communication_score"] +
            data["confidence_score"] + data["hr_score"] + data["subject_score"]
        ) // 5
    else:
        raw_total = _int(data["total_score"])

    data["total_score"] = max(0, raw_total - skip_penalty)
    data["answered"]    = answered
    data["skipped"]     = skipped
    data["total_q"]     = len(qa_pairs)

    for key in ("strengths", "weaknesses", "improvement_suggestions",
                "recommended_topics", "recommended_courses", "per_answer_feedback"):
        data.setdefault(key, [])

    return data

# ── Page routes ───────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html", user=current_user())

@app.route("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("login.html", user=None)

@app.route("/signup")
def signup_page():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("signup.html", user=None)

@app.route("/setup")
@login_required
def setup_page():
    return render_template("setup.html", user=current_user())

@app.route("/interview/<int:interview_id>")
@login_required
def interview_page(interview_id):
    user = current_user()
    if not user:
        return redirect(url_for("login_page"))
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM interviews WHERE id = ? AND user_id = ?",
        (interview_id, user["id"])
    ).fetchone()
    conn.close()
    if not row:
        return "Not found", 404
    if row["status"] == "completed":
        return redirect(url_for("result_page", interview_id=interview_id))
    interview = dict(row)
    interview["conversation"] = json.loads(interview["conversation_json"])
    return render_template("interview.html", user=user, interview=interview)

@app.route("/result/<int:interview_id>")
@login_required
def result_page(interview_id):
    user = current_user()
    if not user:
        return redirect(url_for("login_page"))
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM interviews WHERE id = ? AND user_id = ?",
        (interview_id, user["id"])
    ).fetchone()
    conn.close()
    if not row:
        return "Not found", 404
    interview = dict(row)
    interview["conversation"] = json.loads(interview["conversation_json"])
    interview["report"]       = json.loads(interview["report_json"]) if interview["report_json"] else None
    if not interview["report"]:
        return redirect(url_for("interview_page", interview_id=interview_id))
    return render_template("result.html", user=user, interview=interview)

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login_page"))
    conn = get_db()
    rows = conn.execute(
        "SELECT id, role, experience, status, total_score, created_at, completed_at FROM interviews WHERE user_id = ? ORDER BY id DESC",
        (user["id"],)
    ).fetchall()
    conn.close()
    interviews = [dict(r) for r in rows]
    completed  = [i for i in reversed(interviews) if i["total_score"] is not None]
    progress   = [{"n": idx + 1, "score": it["total_score"]} for idx, it in enumerate(completed)]
    return render_template("dashboard.html", user=user, interviews=interviews, progress=progress)

# ── Auth routes ───────────────────────────────────────────────────────────────
@app.route("/auth/signup", methods=["POST"])
def signup():
    d        = request.form
    name     = (d.get("name") or "").strip()
    email    = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    if not name or not email or not password:
        return render_template("signup.html", user=None, error="All fields are required.")
    if len(password) < 6:
        return render_template("signup.html", user=None, error="Password must be at least 6 characters.")
    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        conn.close()
        return render_template("signup.html", user=None, error="Email already registered.")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, hash_password(password), now_iso())
    )
    conn.commit()
    session["user_id"] = cur.lastrowid
    conn.close()
    return redirect(url_for("setup_page"))

@app.route("/auth/login", methods=["POST"])
def login():
    d        = request.form
    email    = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    if not email or not password:
        return render_template("login.html", user=None, error="Email and password required.")
    conn = get_db()
    row  = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row or not verify_password(password, row["password_hash"]):
        return render_template("login.html", user=None, error="Invalid email or password.")
    session["user_id"] = row["id"]
    return redirect(url_for("dashboard"))

@app.route("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ── Interview API ──────────────────────────────────────────────────────────────
@app.route("/interview/start", methods=["POST"])
@login_required
def start_interview():
    user_id    = session["user_id"]
    f          = request.form
    jd         = (f.get("jd") or "").strip()
    role       = (f.get("role") or "").strip()
    experience = (f.get("experience") or "fresher").strip()
    skills     = (f.get("skills") or "").strip()

    if len(jd) < 20:
        return render_template("setup.html", user=current_user(),
                               error="Please paste a Job Description (at least 20 characters).",
                               form={"jd": jd, "role": role, "experience": experience, "skills": skills})
    try:
        opening = generate_opening(role, experience, skills, jd)
    except Exception as e:
        return render_template("setup.html", user=current_user(),
                               error=f"Could not start interview: {e}",
                               form={"jd": jd, "role": role, "experience": experience, "skills": skills})

    # Conversation starts with the opening message (which ends with the first question)
    conversation = [{"role": "interviewer", "text": opening, "stage": "intro"}]

    conn = get_db()
    cur  = conn.execute(
        "INSERT INTO interviews (user_id, jd, role, experience, skills, course, branch, subjects, conversation_json, current_index, total_questions, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_progress', ?)",
        (user_id, jd, role, experience, skills, role, experience, "", json.dumps(conversation), 1, 10, now_iso())
    )
    conn.commit()
    interview_id = cur.lastrowid
    conn.close()
    return redirect(url_for("interview_page", interview_id=interview_id))


@app.route("/interview/<int:interview_id>/answer", methods=["POST"])
@login_required_json
def submit_answer(interview_id):
    """
    Receives candidate answer, saves it, generates + returns next AI message.
    Response: { ok, message, stage_label, q_number, total, done }
    """
    user_id     = session["user_id"]
    data        = request.get_json(silent=True) or {}
    answer_text = (data.get("answer") or "").strip()

    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM interviews WHERE id = ? AND user_id = ?", (interview_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    if row["status"] != "in_progress":
        conn.close()
        return jsonify({"error": "Interview already completed"}), 400

    conversation   = json.loads(row["conversation_json"])
    current_index  = row["current_index"]   # number of AI turns so far (= questions asked so far)
    total          = row["total_questions"]

    # Save candidate answer turn
    conversation.append({
        "role":   "candidate",
        "answer": answer_text,
        "q_num":  current_index,
    })

    done = current_index >= total

    next_msg      = None
    next_stage    = None
    next_q_number = current_index + 1

    if not done:
        try:
            next_q_text = generate_next_question(
                row["jd"], row["role"], row["experience"], row["skills"],
                conversation, next_q_number, total
            )
            stage       = get_stage(next_q_number)
            next_stage  = stage["label"]
            next_msg    = next_q_text
            conversation.append({
                "role":  "interviewer",
                "text":  next_q_text,
                "stage": stage["id"],
                "q_num": next_q_number,
            })
        except Exception as e:
            next_msg   = "Could you tell me more about your experience with the technologies you've mentioned?"
            next_stage = get_stage(next_q_number)["label"]
            conversation.append({
                "role":  "interviewer",
                "text":  next_msg,
                "stage": get_stage(next_q_number)["id"],
                "q_num": next_q_number,
            })

    conn.execute(
        "UPDATE interviews SET conversation_json = ?, current_index = ? WHERE id = ?",
        (json.dumps(conversation), current_index + 1, interview_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "ok":          True,
        "message":     next_msg,
        "stage_label": get_stage(next_q_number)["id"],  # id for JS mapping
        "q_number":    next_q_number,
        "total":       total,
        "done":        done,
    })


@app.route("/interview/<int:interview_id>/finish", methods=["POST"])
@login_required_json
def finish_interview(interview_id):
    user_id = session["user_id"]
    conn    = get_db()
    row     = conn.execute(
        "SELECT * FROM interviews WHERE id = ? AND user_id = ?", (interview_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    conversation = json.loads(row["conversation_json"])

    try:
        report = evaluate_interview(row["jd"], row["role"], row["experience"], conversation)
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Evaluation failed: {e}"}), 500

    conn.execute(
        "UPDATE interviews SET status='completed', report_json=?, total_score=?, completed_at=? WHERE id=?",
        (json.dumps(report), int(report.get("total_score", 0)), now_iso(), interview_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "redirect": url_for("result_page", interview_id=interview_id)})


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("\n App running at http://localhost:5000\n")
    app.run(debug=True, port=5000)
