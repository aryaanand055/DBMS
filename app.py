import os
import functools
from datetime import datetime
import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")


def parse_db_host(value):
    if not value:
        return "localhost", 3306
    if ":" in value:
        host, port = value.rsplit(":", 1)
        try:
            return host, int(port)
        except ValueError:
            return value, 3306
    return value, 3306


db_host = os.environ.get("DB_HOST", "localhost")
db_port = int(os.environ.get("DB_PORT", 3306))
DB_CONFIG = {
    "host": db_host,
    "port": db_port,
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "db": os.environ.get("DB_NAME", "food_donation_db"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


app.teardown_appcontext(close_db)


def query(sql, args=(), one=False):
    cur = get_db().cursor()
    cur.execute(sql, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute(sql, args=()):
    cur = get_db().cursor()
    cur.execute(sql, args)
    lastrowid = cur.lastrowid
    cur.close()
    return lastrowid


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("Access denied.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.context_processor
def inject_current_user():
    current_user = None
    if "user_id" in session:
        current_user = {
            "user_id": session.get("user_id"),
            "name": session.get("name"),
            "email": session.get("email"),
            "role": session.get("role"),
        }
    return {"current_user": current_user}


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        total = query("SELECT COUNT(*) AS c FROM Food_Donations", one=True)["c"]
        delivered = query("SELECT COUNT(*) AS c FROM Food_Donations WHERE status='delivered'", one=True)["c"]
        active_users = query("SELECT COUNT(*) AS c FROM Users WHERE is_active=1", one=True)["c"]
        ngo_count = query("SELECT COUNT(*) AS c FROM Users WHERE role='ngo' AND is_active=1", one=True)["c"]
        recent_feedback = query(
            """
            SELECT f.rating, f.comments, f.created_at,
                   u.name AS reviewer_name, fd.food_type
            FROM Feedback f
            JOIN Users u ON f.user_id = u.user_id
            JOIN Food_Donations fd ON f.donation_id = fd.donation_id
            WHERE f.rating >= 4 AND f.comments IS NOT NULL AND f.comments != ''
            ORDER BY f.created_at DESC LIMIT 6
            """
        )
    except Exception:
        total = delivered = active_users = ngo_count = 0
        recent_feedback = []
    stats = {
        "total": total,
        "delivered": delivered,
        "active_users": active_users,
        "ngo_count": ngo_count,
    }
    return render_template("index.html", stats=stats, recent_feedback=recent_feedback)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]
        phone = request.form.get("phone", "").strip()

        if not name or not email or not password or not role:
            flash("All required fields must be filled.", "danger")
            return redirect(url_for("register"))

        existing = query("SELECT user_id FROM Users WHERE email=%s", (email,), one=True)
        if existing:
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        execute(
            "INSERT INTO Users (name, email, password, role, phone) VALUES (%s, %s, %s, %s, %s)",
            (name, email, hashed, role, phone or None),
        )
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = query("SELECT * FROM Users WHERE email=%s", (email,), one=True)
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))
        if not user["is_active"]:
            flash("Your account has been deactivated.", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["user_id"]
        session["name"] = user["name"]
        session["email"] = user["email"]
        session["role"] = user["role"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))
    return render_template("auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    if role == "donor":
        return redirect(url_for("donor_dashboard"))
    elif role == "ngo":
        return redirect(url_for("ngo_dashboard"))
    elif role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif role == "receiver":
        return redirect(url_for("receiver_dashboard"))
    return redirect(url_for("index"))


# ── Donor ────────────────────────────────────────────────────────────────────

@app.route("/donor/dashboard")
@role_required("donor")
def donor_dashboard():
    donor_id = session["user_id"]
    donations = query(
        "SELECT * FROM Food_Donations WHERE donor_id=%s ORDER BY created_at DESC",
        (donor_id,),
    )
    total = len(donations)
    pending = sum(1 for d in donations if d["status"] == "pending")
    active = sum(1 for d in donations if d["status"] in ("accepted", "in_transit"))
    delivered = sum(1 for d in donations if d["status"] == "delivered")
    return render_template(
        "donor/dashboard.html",
        donations=donations,
        total=total,
        pending=pending,
        active=active,
        delivered=delivered,
    )


@app.route("/donor/add", methods=["GET", "POST"])
@role_required("donor")
def donor_add():
    if request.method == "POST":
        food_type = request.form["food_type"].strip()
        quantity = request.form["quantity"].strip()
        location = request.form["location"].strip()
        expiry_time = request.form["expiry_time"]
        description = request.form.get("description", "").strip()

        execute(
            "INSERT INTO Food_Donations (donor_id, food_type, quantity, location, expiry_time, description) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (session["user_id"], food_type, quantity, location, expiry_time, description or None),
        )
        flash("Donation added successfully!", "success")
        return redirect(url_for("donor_dashboard"))
    return render_template("donor/add_donation.html")


@app.route("/donor/edit/<int:donation_id>", methods=["GET", "POST"])
@role_required("donor")
def donor_edit(donation_id):
    donation = query(
        "SELECT * FROM Food_Donations WHERE donation_id=%s AND donor_id=%s",
        (donation_id, session["user_id"]),
        one=True,
    )
    if not donation:
        flash("Donation not found or access denied.", "danger")
        return redirect(url_for("donor_dashboard"))

    if request.method == "POST":
        food_type = request.form["food_type"].strip()
        quantity = request.form["quantity"].strip()
        location = request.form["location"].strip()
        expiry_time = request.form["expiry_time"]
        description = request.form.get("description", "").strip()

        execute(
            "UPDATE Food_Donations SET food_type=%s, quantity=%s, location=%s, expiry_time=%s, description=%s "
            "WHERE donation_id=%s AND donor_id=%s",
            (food_type, quantity, location, expiry_time, description or None, donation_id, session["user_id"]),
        )
        flash("Donation updated successfully!", "success")
        return redirect(url_for("donor_dashboard"))
    return render_template("donor/edit_donation.html", donation=donation)


@app.route("/donor/delete/<int:donation_id>", methods=["POST"])
@role_required("donor")
def donor_delete(donation_id):
    donation = query(
        "SELECT * FROM Food_Donations WHERE donation_id=%s AND donor_id=%s AND status='pending'",
        (donation_id, session["user_id"]),
        one=True,
    )
    if not donation:
        flash("Cannot delete this donation.", "danger")
    else:
        execute("DELETE FROM Food_Donations WHERE donation_id=%s", (donation_id,))
        flash("Donation deleted.", "success")
    return redirect(url_for("donor_dashboard"))


# ── NGO ──────────────────────────────────────────────────────────────────────

@app.route("/ngo/dashboard")
@role_required("ngo")
def ngo_dashboard():
    ngo_id = session["user_id"]
    donations = query(
        """
        SELECT fd.*, u.name AS donor_name
        FROM Food_Donations fd
        JOIN Users u ON fd.donor_id = u.user_id
        WHERE fd.status IN ('pending', 'requested')
          AND fd.donation_id NOT IN (
              SELECT donation_id FROM Requests WHERE ngo_id = %s
          )
        ORDER BY fd.created_at DESC
        """,
        (ngo_id,),
    )
    return render_template("ngo/dashboard.html", donations=donations)


@app.route("/ngo/claim/<int:donation_id>", methods=["POST"])
@role_required("ngo")
def ngo_claim(donation_id):
    ngo_id = session["user_id"]
    donation = query(
        "SELECT * FROM Food_Donations WHERE donation_id=%s AND status IN ('pending', 'requested')",
        (donation_id,),
        one=True,
    )
    if not donation:
        flash("Donation not available.", "danger")
        return redirect(url_for("ngo_dashboard"))

    existing = query(
        "SELECT request_id FROM Requests WHERE donation_id=%s AND ngo_id=%s",
        (donation_id, ngo_id),
        one=True,
    )
    if existing:
        flash("You have already claimed this donation.", "warning")
        return redirect(url_for("ngo_dashboard"))

    request_id = execute(
        "INSERT INTO Requests (donation_id, ngo_id, request_status) VALUES (%s, %s, 'accepted')",
        (donation_id, ngo_id),
    )
    execute(
        "INSERT INTO Delivery (request_id, delivery_status) VALUES (%s, 'pending')",
        (request_id,),
    )
    execute(
        "UPDATE Food_Donations SET status='accepted' WHERE donation_id=%s",
        (donation_id,),
    )
    flash("Donation claimed successfully!", "success")
    return redirect(url_for("ngo_requests"))


@app.route("/ngo/requests")
@role_required("ngo")
def ngo_requests():
    ngo_id = session["user_id"]
    rows = query(
        """
        SELECT r.request_id, r.created_at AS request_date,
               fd.food_type, fd.quantity, fd.location, fd.expiry_time, fd.status AS donation_status,
               u.name AS donor_name,
               d.delivery_id, d.delivery_status, d.delivery_time
        FROM Requests r
        JOIN Food_Donations fd ON r.donation_id = fd.donation_id
        JOIN Users u ON fd.donor_id = u.user_id
        LEFT JOIN Delivery d ON d.request_id = r.request_id
        WHERE r.ngo_id = %s
        ORDER BY r.created_at DESC
        """,
        (ngo_id,),
    )
    return render_template("ngo/my_requests.html", rows=rows)


@app.route("/ngo/update_delivery/<int:delivery_id>", methods=["POST"])
@role_required("ngo")
def ngo_update_delivery(delivery_id):
    new_status = request.form["delivery_status"]
    ngo_id = session["user_id"]

    delivery = query(
        """
        SELECT d.delivery_id, d.request_id, r.donation_id
        FROM Delivery d
        JOIN Requests r ON d.request_id = r.request_id
        WHERE d.delivery_id = %s AND r.ngo_id = %s
        """,
        (delivery_id, ngo_id),
        one=True,
    )
    if not delivery:
        flash("Delivery not found or access denied.", "danger")
        return redirect(url_for("ngo_requests"))

    if new_status == "delivered":
        execute(
            "UPDATE Delivery SET delivery_status='delivered', delivery_time=NOW() WHERE delivery_id=%s",
            (delivery_id,),
        )
        execute(
            "UPDATE Food_Donations SET status='delivered' WHERE donation_id=%s",
            (delivery["donation_id"],),
        )
    else:
        execute(
            "UPDATE Delivery SET delivery_status=%s WHERE delivery_id=%s",
            (new_status, delivery_id),
        )
        if new_status == "in_transit":
            execute(
                "UPDATE Food_Donations SET status='in_transit' WHERE donation_id=%s",
                (delivery["donation_id"],),
            )

    flash("Delivery status updated.", "success")
    return redirect(url_for("ngo_requests"))


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    total_users = query("SELECT COUNT(*) AS c FROM Users", one=True)["c"]
    total_donations = query("SELECT COUNT(*) AS c FROM Food_Donations", one=True)["c"]
    pending_donations = query("SELECT COUNT(*) AS c FROM Food_Donations WHERE status='pending'", one=True)["c"]
    delivered_donations = query("SELECT COUNT(*) AS c FROM Food_Donations WHERE status='delivered'", one=True)["c"]
    recent = query(
        """
        SELECT fd.*, u.name AS donor_name
        FROM Food_Donations fd
        JOIN Users u ON fd.donor_id = u.user_id
        ORDER BY fd.created_at DESC LIMIT 10
        """
    )
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_donations=total_donations,
        pending_donations=pending_donations,
        delivered_donations=delivered_donations,
        recent=recent,
    )


@app.route("/admin/users")
@role_required("admin")
def admin_users():
    users = query("SELECT * FROM Users ORDER BY created_at DESC")
    return render_template("admin/users.html", users=users)


@app.route("/admin/toggle_user/<int:user_id>", methods=["POST"])
@role_required("admin")
def admin_toggle_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin_users"))
    user = query("SELECT is_active FROM Users WHERE user_id=%s", (user_id,), one=True)
    if user:
        new_status = 0 if user["is_active"] else 1
        execute("UPDATE Users SET is_active=%s WHERE user_id=%s", (new_status, user_id))
        flash("User status updated.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/reports")
@role_required("admin")
def admin_reports():
    statuses = query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM Food_Donations
        GROUP BY status
        """
    )
    top_donors = query(
        """
        SELECT u.name, COUNT(fd.donation_id) AS cnt
        FROM Food_Donations fd
        JOIN Users u ON fd.donor_id = u.user_id
        GROUP BY fd.donor_id
        ORDER BY cnt DESC LIMIT 10
        """
    )
    feedback_list = query(
        """
        SELECT f.rating, f.comments, f.created_at,
               u.name AS user_name, fd.food_type
        FROM Feedback f
        JOIN Users u ON f.user_id = u.user_id
        JOIN Food_Donations fd ON f.donation_id = fd.donation_id
        ORDER BY f.created_at DESC LIMIT 20
        """
    )
    total_donations = query("SELECT COUNT(*) AS c FROM Food_Donations", one=True)["c"]
    return render_template(
        "admin/reports.html",
        statuses=statuses,
        top_donors=top_donors,
        feedback_list=feedback_list,
        total_donations=total_donations,
    )


# ── Receiver ─────────────────────────────────────────────────────────────────

@app.route("/receiver/dashboard")
@role_required("receiver")
def receiver_dashboard():
    receiver_id = session["user_id"]
    available = query(
        """
        SELECT fd.*, u.name AS donor_name
        FROM Food_Donations fd
        JOIN Users u ON fd.donor_id = u.user_id
        WHERE fd.status = 'pending'
        ORDER BY fd.created_at DESC
        """
    )
    my_requests = query(
        """
        SELECT r.request_id, r.request_status, r.created_at,
               fd.food_type, fd.quantity, fd.location, fd.status AS donation_status,
               u.name AS donor_name,
               d.delivery_status
        FROM Requests r
        JOIN Food_Donations fd ON r.donation_id = fd.donation_id
        JOIN Users u ON fd.donor_id = u.user_id
        LEFT JOIN Delivery d ON d.request_id = r.request_id
        WHERE r.ngo_id = %s
        ORDER BY r.created_at DESC
        """,
        (receiver_id,),
    )
    return render_template("receiver/dashboard.html", available=available, my_requests=my_requests)


@app.route("/receiver/request/<int:donation_id>", methods=["POST"])
@role_required("receiver")
def receiver_request(donation_id):
    receiver_id = session["user_id"]
    donation = query(
        "SELECT * FROM Food_Donations WHERE donation_id=%s AND status='pending'",
        (donation_id,),
        one=True,
    )
    if not donation:
        flash("Donation not available.", "danger")
        return redirect(url_for("receiver_dashboard"))

    existing = query(
        "SELECT request_id FROM Requests WHERE donation_id=%s AND ngo_id=%s",
        (donation_id, receiver_id),
        one=True,
    )
    if existing:
        flash("You have already requested this donation.", "warning")
        return redirect(url_for("receiver_dashboard"))

    execute(
        "INSERT INTO Requests (donation_id, ngo_id, request_status) VALUES (%s, %s, 'pending')",
        (donation_id, receiver_id),
    )
    execute(
        "UPDATE Food_Donations SET status='requested' WHERE donation_id=%s",
        (donation_id,),
    )
    flash("Request submitted successfully! An NGO will pick it up for delivery.", "success")
    return redirect(url_for("receiver_dashboard"))


# ── Feedback ──────────────────────────────────────────────────────────────────

@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    user_id = session["user_id"]
    if request.method == "POST":
        donation_id = request.form["donation_id"]
        rating = request.form["rating"]
        comments = request.form.get("comments", "").strip()

        existing = query(
            "SELECT feedback_id FROM Feedback WHERE user_id=%s AND donation_id=%s",
            (user_id, donation_id),
            one=True,
        )
        if existing:
            flash("You have already submitted feedback for this donation.", "warning")
        else:
            execute(
                "INSERT INTO Feedback (user_id, donation_id, rating, comments) VALUES (%s, %s, %s, %s)",
                (user_id, donation_id, rating, comments or None),
            )
            flash("Feedback submitted! Thank you.", "success")
        return redirect(url_for("feedback"))

    delivered_donations = query(
        """
        SELECT fd.donation_id, fd.food_type, fd.location, u.name AS donor_name
        FROM Food_Donations fd
        JOIN Users u ON fd.donor_id = u.user_id
        WHERE fd.status = 'delivered'
        ORDER BY fd.created_at DESC
        """
    )
    existing_feedback = query(
        """
        SELECT f.rating, f.comments, f.created_at,
               fd.food_type, u.name AS reviewer_name
        FROM Feedback f
        JOIN Food_Donations fd ON f.donation_id = fd.donation_id
        JOIN Users u ON f.user_id = u.user_id
        ORDER BY f.created_at DESC LIMIT 20
        """
    )
    return render_template(
        "feedback.html",
        delivered_donations=delivered_donations,
        existing_feedback=existing_feedback,
    )


# ── Init DB ───────────────────────────────────────────────────────────────────

@app.route("/init-db")
def init_db():
    try:
        existing = query("SELECT COUNT(*) AS c FROM Users", one=True)["c"]
    except Exception:
        flash("Database not yet set up. Run schema.sql first.", "danger")
        return redirect(url_for("index"))

    if existing > 0:
        flash("Database already seeded.", "info")
        return redirect(url_for("index"))

    pwd = generate_password_hash("test123")
    users = [
        ("Admin User", "admin@fooddonation.com", pwd, "admin", "9000000000"),
        ("John Donor", "donor@test.com", pwd, "donor", "9111111111"),
        ("Hope NGO", "ngo@test.com", pwd, "ngo", "9222222222"),
        ("Alice Receiver", "receiver@test.com", pwd, "receiver", "9333333333"),
    ]
    for u in users:
        execute(
            "INSERT INTO Users (name, email, password, role, phone) VALUES (%s,%s,%s,%s,%s)",
            u,
        )

    donor_id = query("SELECT user_id FROM Users WHERE email='donor@test.com'", one=True)["user_id"]
    donations = [
        (donor_id, "Rice & Dal", "50 kg", "MG Road, Bangalore", "2025-12-31 18:00:00", "pending", "Surplus from event"),
        (donor_id, "Bread Loaves", "100 pieces", "HSR Layout, Bangalore", "2025-12-31 12:00:00", "pending", "Fresh bakery items"),
        (donor_id, "Fruits Basket", "30 kg", "Koramangala, Bangalore", "2025-12-30 10:00:00", "delivered", "Mixed fruits"),
    ]
    for d in donations:
        execute(
            "INSERT INTO Food_Donations (donor_id, food_type, quantity, location, expiry_time, status, description) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            d,
        )

    flash("Database seeded successfully! Demo credentials: admin@fooddonation.com / test123", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=os.environ.get("FLASK_DEBUG", "0") == "1")
