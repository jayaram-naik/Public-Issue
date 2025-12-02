# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
UPLOADS.mkdir(exist_ok=True)

ALLOWED = {"png", "jpg", "jpeg", "gif"}
DB = BASE / "issues.db"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = str(UPLOADS)
# In real deployment use a secret from environment. This is fine for local testing.
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret")

# simple admin credentials (change if you want)
ADMIN_USER = os.environ.get("ADMIN_USER", "Teju@2004")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "1306")

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # create table with latitude and longitude columns
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                description TEXT,
                image_path TEXT,
                location TEXT,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'open',
                created_at TEXT
            )
        """)
init_db()

def allowed_file(name):
    return '.' in name and name.rsplit('.', 1)[1].lower() in ALLOWED

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['POST'])
def report():
    email = request.form.get('email', '').strip()
    issue_type = request.form.get('issue_type', '').strip()
    description = request.form.get('description', '').strip()
    location = request.form.get('location', '').strip()
    lat = request.form.get('latitude', '').strip()
    lon = request.form.get('longitude', '').strip()

    if not email or not issue_type:
        flash("Email and issue type required!", "danger")
        return redirect(url_for('index'))

    image_name = None
    photo = request.files.get('photo')
    if photo and photo.filename:
        if not allowed_file(photo.filename):
            flash("File type not allowed. Use png/jpg/jpeg/gif", "danger")
            return redirect(url_for('index'))
        image_name = f"{int(datetime.utcnow().timestamp())}_{secure_filename(photo.filename)}"
        photo.save(UPLOADS / image_name)

    created = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO issues (email, issue_type, description, image_path, location, latitude, longitude, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (email, issue_type, description, image_name, location or '', float(lat) if lat else None, float(lon) if lon else None, created)
        )

    flash("Issue reported successfully! Thank you.", "success")
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- admin routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('user', '')
        pw = request.form.get('pass', '')
        if user == ADMIN_USER and pw == ADMIN_PASS:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Invalid username or password", "danger")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM issues ORDER BY created_at DESC").fetchall()
    return render_template('admin.html', issues=rows)

@app.route('/admin/update/<int:issue_id>', methods=['POST'])
def admin_update(issue_id):
    if not session.get('is_admin'):
        flash("Unauthorized", "danger")
        return redirect(url_for('admin_login'))
    status = request.form.get('status', 'open')
    with get_conn() as conn:
        conn.execute("UPDATE issues SET status = ? WHERE id = ?", (status, issue_id))
    flash("Status updated", "success")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    # for local development
    app.run(debug=True)
