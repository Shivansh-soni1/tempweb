from flask import Flask, render_template, request, redirect, session, flash
from datetime import date

import mysql.connector
import hashlib

app = Flask(__name__)
app.secret_key = "mysecretkey"

# ---------- DATABASE CONNECTION ----------
MASTER_PASSWORD = "papa4321"   # change this

# def get_db_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="Shivanshr1@",
#         database="testdb",
#         auth_plugin="mysql_native_password"
#     )

import os

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        auth_plugin="mysql_native_password"
    )
 
@app.route("/gate", methods=["GET", "POST"])
def gate():
    if request.method == "POST":
        password = request.form["password"]

        if password == MASTER_PASSWORD:
            session["gate_passed"] = True

            # If already logged in → home
            if "user" in session:
                return redirect("/")
            return redirect("/login")
        else:
            flash("Invalid access password ❌")

    return render_template("gate.html")

def gate_required():
    return "gate_passed" not in session

# ---------- HOME ----------
@app.route("/")
def home():
    if gate_required():
        return redirect("/gate")

    if "user" in session:
        return render_template("home.html", username=session["user"])

    return redirect("/login")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if gate_required():
        return redirect("/gate")

    if "user" in session:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO auth_users (username, email, password) VALUES (%s,%s,%s)",
            (username, email, hashed_password)
        )
        conn.commit()
        conn.close()

        flash("Registration successful ✅ Please login")
        return redirect("/login")

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if gate_required():
        return redirect("/gate")

    if "user" in session:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM auth_users WHERE username=%s AND password=%s",
            (username, hashed_password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/")
        else:
            flash("Invalid username or password")

    return render_template("login.html")

# ---------- ADD ----------
@app.route("/add", methods=["GET", "POST"])
def add():
    if gate_required():
     return redirect("/gate")
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        amount = request.form["amount"]
        details = request.form["details"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO records (name, date, amount, details) VALUES (%s, %s, %s, %s)",
            (name, date, amount, details)
        )
        conn.commit()
        conn.close()

        flash("Data entered successfully ✅")
        return redirect("/add")   # stay on add page

    return render_template("add.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/gate")


# ---------- RUN ----------
 

@app.route("/search", methods=["GET", "POST"])
def search():
    if gate_required():
     return redirect("/gate")

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        date = request.form["date"]

        query = "SELECT * FROM records WHERE 1=1"
        params = []

        if name:
            query += " AND name LIKE %s"
            params.append(f"%{name}%")

        if amount:
            query += " AND amount = %s"
            params.append(amount)

        if date:
            query += " AND date = %s"
            params.append(date)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        # ----- DECISION LOGIC -----
        if len(results) == 1:
            return redirect(f"/record/{results[0][0]}")

        return render_template("search_results.html", records=results)

    return render_template("search.html")

@app.route("/record/<int:record_id>")
def record_detail(record_id):
    if gate_required():
     return redirect("/gate")
    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE id=%s", (record_id,))
    record = cursor.fetchone()
    conn.close()

    return render_template("record_detail.html", record=record)

@app.route("/pull/<int:record_id>", methods=["GET", "POST"])
def pull(record_id):
    if gate_required():
     return redirect("/gate")
    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE id=%s", (record_id,))
    record = cursor.fetchone()
    conn.close()

    result = None

    if request.method == "POST":
        monthly_rate = float(request.form["rate"])

        record_date = record[2]
        today = date.today()

        total_days = (today - record_date).days
        months = total_days / 30
        years = total_days / 360

        amount = float(record[3])

        daily_rate = monthly_rate / 30
        per_day_interest = (amount * daily_rate) / 100
        total_interest = per_day_interest * total_days
        total_amount = amount + total_interest

        result = {
            "rate": monthly_rate,
            "daily_rate": round(daily_rate, 4),
            "days": total_days,
            "months": round(months, 2),
            "years": round(years, 2),
            "per_day_interest": round(per_day_interest, 2),
            "interest": round(total_interest, 2),
            "total": round(total_amount)
        }

    return render_template("pull.html", record=record, result=result)

@app.route("/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    if gate_required():
     return redirect("/gate")
    if "user" not in session:
        return redirect("/login")

    # Values coming from pull page
    name = request.form["name"]
    total_amount = request.form["total"]
    interest_rate = request.form.get("rate", 0)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Get record details BEFORE deleting
    cursor.execute("SELECT * FROM records WHERE id=%s", (record_id,))
    record = cursor.fetchone()

    if record:
        # 2️⃣ Insert into delete_data_store
        cursor.execute("""
            INSERT INTO delete_data_store
            (original_id, name, record_date, amount, details, interest_rate, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            record[0],        # original_id
            record[1],        # name
            record[2],        # date
            record[3],        # amount
            record[4],        # details
            interest_rate,    # interest rate
            total_amount
        ))

        # 3️⃣ Delete from records table
        cursor.execute("DELETE FROM records WHERE id=%s", (record_id,))

        conn.commit()

    conn.close()

    # 4️⃣ Redirect to home with message
    flash(f"Record deleted successfully ✅ | Name: {name} | Total: {total_amount}")
    flash("Record deleted successfully ✅")
    return redirect("/")

    

if __name__ == "__main__":
    app.run(debug=True)