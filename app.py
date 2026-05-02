from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from datetime import datetime
import sqlite3
import hashlib
import os
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = "interview_prep_secret_2024"

DB_PATH = "users.db"

# ─────────────────────────────────────────────
#  Database Setup
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            joined   TEXT    NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            question   TEXT    NOT NULL,
            category   TEXT    NOT NULL,
            answer     TEXT    NOT NULL,
            score      INTEGER NOT NULL,
            grade      TEXT    NOT NULL,
            date       TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ─────────────────────────────────────────────
#  Login Required Decorator
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
#  Question Bank
# ─────────────────────────────────────────────
QUESTIONS = {
    "HR": [
        {"id": 1, "question": "Tell me about yourself.", "tips": "Cover your background, skills, and career goals in 2-3 minutes."},
        {"id": 2, "question": "What are your greatest strengths?", "tips": "Pick 2-3 strengths relevant to the job with examples."},
        {"id": 3, "question": "What is your biggest weakness?", "tips": "Mention a real weakness but show how you are improving it."},
        {"id": 4, "question": "Where do you see yourself in 5 years?", "tips": "Align your goals with the company's growth."},
        {"id": 5, "question": "Why do you want to work here?", "tips": "Research the company and mention specific reasons."},
        {"id": 6, "question": "Why should we hire you?", "tips": "Highlight your unique skills and how they match the role."},
    ],
    "Behavioral": [
        {"id": 7,  "question": "Tell me about a time you handled a difficult situation.", "tips": "Use the STAR method: Situation, Task, Action, Result."},
        {"id": 8,  "question": "Describe a time you worked in a team.", "tips": "Focus on collaboration, communication, and your specific role."},
        {"id": 9,  "question": "Give an example of a goal you achieved.", "tips": "Be specific about the goal, steps taken, and outcome."},
        {"id": 10, "question": "Tell me about a time you failed and what you learned.", "tips": "Be honest, focus on the lesson and how you improved."},
        {"id": 11, "question": "How do you handle stress and pressure?", "tips": "Give a real example with a positive outcome."},
    ],
    "Technical": [
        {"id": 12, "question": "Explain Object-Oriented Programming concepts.", "tips": "Cover Encapsulation, Inheritance, Polymorphism, Abstraction with examples."},
        {"id": 13, "question": "What is the difference between a list and a tuple in Python?", "tips": "Mention mutability, use cases, and performance differences."},
        {"id": 14, "question": "What is REST API and how does it work?", "tips": "Explain HTTP methods, statelessness, and endpoints."},
        {"id": 15, "question": "Explain the concept of database normalization.", "tips": "Cover 1NF, 2NF, 3NF with simple examples."},
        {"id": 16, "question": "What is the difference between SQL and NoSQL databases?", "tips": "Compare structure, scalability, and use cases."},
        {"id": 17, "question": "Explain how Git version control works.", "tips": "Cover commits, branches, merging, and pull requests."},
    ],
    "Leadership": [
        {"id": 18, "question": "Describe your leadership style.", "tips": "Mention your approach and give a real example."},
        {"id": 19, "question": "How do you motivate your team?", "tips": "Talk about recognition, clear goals, and support."},
        {"id": 20, "question": "Tell me about a time you resolved a conflict in your team.", "tips": "Focus on listening, fairness, and the positive outcome."},
    ],
}

# ─────────────────────────────────────────────
#  Smart Feedback Engine
# ─────────────────────────────────────────────
def analyze_answer(answer, question_id):
    score = 0
    feedback_points = []
    suggestions = []

    word_count = len(answer.split())
    char_count  = len(answer.strip())

    if char_count < 20:
        return {
            "score": 0, "grade": "F", "badge": "Too Short", "badge_color": "danger",
            "summary": "Your answer is too short to evaluate.",
            "feedback_points": ["Answer must be at least 20 characters long."],
            "suggestions": ["Try to elaborate more on your experience and skills."],
            "word_count": word_count,
        }

    if word_count >= 50:
        score += 30
        feedback_points.append("✅ Good answer length — detailed and informative.")
    elif word_count >= 20:
        score += 15
        feedback_points.append("⚠️ Answer is a bit short. Try to add more detail.")
        suggestions.append("Expand your answer with specific examples or experiences.")
    else:
        score += 5
        feedback_points.append("❌ Answer is too brief.")
        suggestions.append("Write at least 3-4 sentences for a complete answer.")

    positive_keywords = ["experience","skill","team","project","achieve","learn",
                         "improve","result","success","example","work","develop",
                         "manage","lead","create","build","solve","communicate"]
    found_keywords = [kw for kw in positive_keywords if kw.lower() in answer.lower()]

    if len(found_keywords) >= 5:
        score += 35
        feedback_points.append(f"✅ Great use of strong keywords: {', '.join(found_keywords[:5])}.")
    elif len(found_keywords) >= 2:
        score += 20
        feedback_points.append(f"⚠️ Some good keywords found: {', '.join(found_keywords)}.")
        suggestions.append("Include more action words like: achieve, develop, manage, solve.")
    else:
        score += 5
        feedback_points.append("❌ Missing strong keywords.")
        suggestions.append("Use action words: experience, achieve, lead, build, solve.")

    sentences = [s.strip() for s in answer.replace("!",".").replace("?",".").split(".") if s.strip()]
    if len(sentences) >= 4:
        score += 20
        feedback_points.append("✅ Well-structured answer with multiple points.")
    elif len(sentences) >= 2:
        score += 10
        feedback_points.append("⚠️ Try to structure your answer into more clear points.")
        suggestions.append("Break your answer into: Introduction → Main Point → Example → Conclusion.")
    else:
        suggestions.append("Structure your answer with a clear beginning, middle, and end.")

    confidence_words = ["confident","passionate","dedicated","motivated","enthusiastic",
                        "committed","proud","excited","strong","excellent"]
    found_confidence = [w for w in confidence_words if w.lower() in answer.lower()]
    if found_confidence:
        score += 15
        feedback_points.append(f"✅ Shows confidence: '{found_confidence[0]}' — great tone!")
    else:
        suggestions.append("Add confident language like: 'I am passionate about...', 'I excel at...'")

    score = min(score, 100)

    if score >= 85:
        grade, badge, badge_color = "A", "Excellent", "success"
        summary = "Outstanding answer! You're well-prepared for this question."
    elif score >= 70:
        grade, badge, badge_color = "B", "Good", "primary"
        summary = "Good answer! A few improvements will make it excellent."
    elif score >= 50:
        grade, badge, badge_color = "C", "Average", "warning"
        summary = "Decent attempt. Work on adding more detail and examples."
    elif score >= 30:
        grade, badge, badge_color = "D", "Needs Work", "orange"
        summary = "Your answer needs significant improvement."
    else:
        grade, badge, badge_color = "F", "Poor", "danger"
        summary = "Please review the tips and try again with a more complete answer."

    return {
        "score": score, "grade": grade, "badge": badge, "badge_color": badge_color,
        "summary": summary, "feedback_points": feedback_points,
        "suggestions": suggestions, "word_count": word_count,
    }

# ─────────────────────────────────────────────
#  Auth Routes
# ─────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        # Validation
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("Email already registered. Please login.", "warning")
            conn.close()
            return render_template("register.html")

        conn.execute(
            "INSERT INTO users (name, email, password, joined) VALUES (?, ?, ?, ?)",
            (name, email, hash_password(password), datetime.now().strftime("%b %d, %Y"))
        )
        conn.commit()
        conn.close()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "danger")
            return render_template("login.html")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["user_email"]= user["email"]
            flash(f"Welcome back, {user['name']}! 👋", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    name = session.get("user_name", "")
    session.clear()
    flash(f"Goodbye, {name}! See you soon. 👋", "info")
    return redirect(url_for("login"))

# ─────────────────────────────────────────────
#  Main Routes (Protected)
# ─────────────────────────────────────────────

@app.route("/")
@login_required
def home():
    user_id = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT score FROM history WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()

    attempts = len(rows)
    avg_score = round(sum(r["score"] for r in rows) / attempts, 1) if attempts else 0

    stats = {
        "attempts":      attempts,
        "avg_score":     avg_score,
        "history_count": attempts,
    }
    return render_template("index.html", categories=list(QUESTIONS.keys()), stats=stats)


@app.route("/practice/<category>")
@login_required
def practice(category):
    if category not in QUESTIONS:
        return redirect(url_for("home"))

    question = random.choice(QUESTIONS[category])
    session["current_question"] = question
    session["current_category"] = category
    return render_template("practice.html", question=question, category=category)


@app.route("/submit", methods=["POST"])
@login_required
def submit():
    answer   = request.form.get("answer", "").strip()
    question = session.get("current_question", {})
    category = session.get("current_category", "HR")

    if not question:
        return redirect(url_for("home"))

    result = analyze_answer(answer, question.get("id"))

    # Save to DB
    conn = get_db()
    conn.execute(
        "INSERT INTO history (user_id, question, category, answer, score, grade, date) VALUES (?,?,?,?,?,?,?)",
        (
            session["user_id"],
            question["question"],
            category,
            answer[:200] + "..." if len(answer) > 200 else answer,
            result["score"],
            result["grade"],
            datetime.now().strftime("%b %d, %Y %I:%M %p"),
        )
    )
    conn.commit()
    conn.close()

    return render_template("result.html", question=question, answer=answer,
                           result=result, category=category)


@app.route("/history")
@login_required
def history():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("history.html", history=rows)


@app.route("/tips")
@login_required
def tips():
    return render_template("tips.html")


@app.route("/profile")
@login_required
def profile():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    rows = conn.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    conn.close()

    scores = [r["score"] for r in rows]
    stats = {
        "attempts":  len(scores),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "best":      max(scores) if scores else 0,
        "a_count":   sum(1 for r in rows if r["grade"] == "A"),
    }
    return render_template("profile.html", user=user, history=rows, stats=stats)


@app.route("/reset")
@login_required
def reset():
    # Only clear practice session data, not login
    for key in ["current_question", "current_category"]:
        session.pop(key, None)
    flash("Session reset!", "info")
    return redirect(url_for("home"))


@app.route("/api/random-question")
@login_required
def random_question():
    all_questions = [q for qs in QUESTIONS.values() for q in qs]
    return jsonify(random.choice(all_questions))


if __name__ == "__main__":
    app.run(debug=True)
