from flask import Flask, render_template, request, redirect,session
import sqlite3
from datetime import date, datetime, timedelta

app = Flask(__name__)

app.secret_key = "mysecretkey"

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id=?
        ORDER BY due_date
        """,
        (user_id,)
    )

    tasks = cursor.fetchall()

    print("Tasks:", tasks)

    total_tasks = len(tasks)
    print("Total:", total_tasks)

    completed_tasks = sum(
    1 for task in tasks if task[2] == 1
    )

    print("Completed:", completed_tasks)

    pending_tasks = total_tasks - completed_tasks

    progress = 0

    if total_tasks > 0:
        progress = int((completed_tasks / total_tasks) * 100)

    print("Progress:", progress)
    today = str(date.today())

    overdue_tasks = 0

    for task in tasks:
        if task[3] and task[3] < today and task[2] == 0:
            overdue_tasks += 1

    score = (
    completed_tasks * 10
    - overdue_tasks * 5)

    score = max(score, 0)

    cursor.execute(
    """
    SELECT current_streak,
           best_streak
    FROM streaks
    WHERE user_id=?
    """,
    (session["user_id"],))

    streak = cursor.fetchone()

    if streak:
        current_streak = streak[0]
        best_streak = streak[1]
    else:
        current_streak = 0
        best_streak = 0

    productivity_score = (
    completed_tasks * 10
    ) + (
    current_streak * 5)

    conn.close()
    
    return render_template(
        "index.html", 
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        progress=progress,
        today=today,
        productivity_score=productivity_score,
        score=score,
        current_streak=current_streak,
        best_streak=best_streak)


@app.route("/add", methods=["POST"])
def add_task():

    task = request.form["task"]
    due_date = request.form["due_date"]
    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
    """
    INSERT INTO tasks(task, due_date,user_id)
    VALUES(?, ?,?)
    """,
    (task, due_date,user_id)
)

    conn.commit()
    conn.close()

    return redirect("/")
@app.route("/delete/<int:id>")
def delete_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id=? AND user_id=?",
        (id,session['user_id'])
    )

    conn.commit()
    conn.close()

    return redirect("/")
@app.route("/complete/<int:id>")
def complete_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tasks SET completed=1 WHERE id=? AND user_id=?",
        (id,session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/")
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        new_task = request.form["task"]
        new_due_date = request.form["due_date"]


        cursor.execute(
        """
        UPDATE tasks
        SET task=?, due_date=?
        WHERE id=? AND user_id=?
        """,
        (new_task, new_due_date,id,session["user_id"])
        )

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute(
        "SELECT * FROM tasks WHERE id=?",
        (id,)
    )

    task = cursor.fetchone()

    conn.close()

    return render_template(
        "edit.html",
        task=task
    )
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users(username, password)
            VALUES(?, ?)
            """,
            (username, password)
        )
        user_id = cursor.lastrowid
        cursor.execute(
        """
        INSERT INTO streaks(user_id)
        VALUES(?)
        """,(user_id,))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username=? AND password=?
            """,
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/")

        return "Invalid username or password"

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
@app.route("/toggle/<int:id>")
def toggle_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT completed
        FROM tasks
        WHERE id=? AND user_id=?
        """,
        (id, session["user_id"])
    )

    task = cursor.fetchone()

    if task:

        new_status = 0 if task[0] == 1 else 1

        if new_status == 1:

            today = str(date.today())

            cursor.execute(
                """
                SELECT current_streak,
               best_streak,
               last_completed_date
                FROM streaks
                WHERE user_id=?
                """,
                (session["user_id"],)
                )

            streak = cursor.fetchone()

            if streak is None:

                cursor.execute(
                """
                INSERT INTO streaks(user_id)
                VALUES(?)
                """,
                (session["user_id"],)
    )

                current_streak = 0
                best_streak = 0
                last_date = None

            else:

                current_streak = streak[0]
                best_streak = streak[1]
                last_date = streak[2]

            if last_date is None:
                current_streak = 1
            elif last_date == str(date.today() - timedelta(days=1)):
                current_streak += 1
            elif last_date == today:
                current_streak = current_streak
            else:
                current_streak=1
            
            best_streak = max(
            best_streak,
            current_streak)

            cursor.execute(
            """
            UPDATE streaks
            SET current_streak=?,
            best_streak=?,
            last_completed_date=?
            WHERE user_id=?
            """,
            (
                current_streak,best_streak,today,session["user_id"]
            )
            )

        cursor.execute(
            """
            UPDATE tasks
            SET completed=?
            WHERE id=? AND user_id=?
            """,
            (new_status, id, session["user_id"])
        )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/achievements")
def achievements():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id=?
        """,
        (user_id,)
    )

    tasks = cursor.fetchall()

    completed_tasks = sum(
        1 for task in tasks if task[2] == 1
    )

    cursor.execute(
        """
        SELECT current_streak,
               best_streak
        FROM streaks
        WHERE user_id=?
        """,
        (user_id,)
    )

    streak = cursor.fetchone()

    current_streak = streak[0] if streak else 0
    best_streak = streak[1] if streak else 0

    productivity_score = completed_tasks * 10 + current_streak * 5
    level = (productivity_score // 100) + 1

    achievements = []

    if completed_tasks >= 1:
        achievements.append("🏆 First Task Completed")

    if completed_tasks >= 5:
            achievements.append("⭐ Task Starter")

    if completed_tasks >= 10:
        achievements.append("⚡ Productivity Machine")

    if completed_tasks >= 25:
        achievements.append("🚀 Task Crusher")

    if completed_tasks >= 50:
        achievements.append("👑 Task Master")

    if current_streak >= 3:
        achievements.append("🔥 3 Day Streak")

    if current_streak >= 7:
        achievements.append("🔥🔥 Weekly Warrior")

    if current_streak >= 15:
        achievements.append("🌟 Consistency Champion")

    if current_streak >= 30:
        achievements.append("🏅 30 Day Legend")

    if productivity_score >= 50:
        achievements.append("⚡ Score 50")

    if productivity_score >= 100:
        achievements.append("🚀 Score 100")

    if productivity_score >= 200:
        achievements.append("👑 Productivity King")

    if level >= 2:
        achievements.append("🌱 Reached Level 2")

    if level >= 3:
        achievements.append("⚔️ Task Warrior")

    if level >= 4:
        achievements.append("🥷 Productivity Ninja")

    if level >= 5:
        achievements.append("👑 Ultimate Legend")

    total_achievements = 14
    unlocked = len(achievements)

    achievement_percentage = int(
    (unlocked / total_achievements) * 100
    )

    conn.close()

    return render_template(
        "achievements.html",
        completed_tasks=completed_tasks,
        current_streak=current_streak,
        best_streak=best_streak,
        productivity_score=productivity_score,
        level=level,
        achievements=achievements,
        unlocked=unlocked,
        total_achievements=total_achievements,
        achievement_percentage=achievement_percentage
    )

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id=?
        """,
        (user_id,)
    )

    tasks = cursor.fetchall()

    total_tasks = len(tasks)

    completed_tasks = sum(
        1 for task in tasks if task[2] == 1
    )

    pending_tasks = total_tasks - completed_tasks

    cursor.execute(
        """
        SELECT current_streak,
               best_streak
        FROM streaks
        WHERE user_id=?
        """,
        (user_id,)
    )

    streak = cursor.fetchone()

    current_streak = streak[0] if streak else 0
    best_streak = streak[1] if streak else 0

    productivity_score = (
        completed_tasks * 10
        + current_streak * 5
    )

    xp = productivity_score

    level = (xp // 100) + 1

    conn.close()

    return render_template(
        "profile.html",
        username=session["username"],
        current_streak=current_streak,
        best_streak=best_streak,
        productivity_score=productivity_score,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        level=level,
        xp=xp
    )


if __name__ == "__main__":
    app.run(debug=True)