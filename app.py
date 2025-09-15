# wa_flora_price_check_app.py
# Internal Price Check System with Admin/Staff Roles, CSV Import/Export,
# Barcode Search, Google Drive Backup (overwrite mode), and Daily Scheduler.

import os
import sqlite3
import csv
import io
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

# Google Drive API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

DB_NAME = "products.db"

# Google Drive config
google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# ---------------------------- DATABASE ----------------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Products table
        c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            packing TEXT NOT NULL,
            retail_price REAL NOT NULL,
            wholesale_price REAL NOT NULL,
            barcode TEXT
        )""")
        # Users table
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','staff'))
        )""")
        conn.commit()

init_db()

# ---------------------------- GOOGLE DRIVE BACKUP ----------------------------
def backup_to_google_drive():
    if not (google_credentials_json and google_drive_folder_id):
        return "Google Drive not configured"
    try:
        creds = service_account.Credentials.from_service_account_file(
            google_credentials_json,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': 'products_backup.db',
            'parents': [google_drive_folder_id]
        }
        media = MediaFileUpload(DB_NAME, mimetype='application/x-sqlite3', resumable=True)

        # Check if file exists already
        results = service.files().list(q=f"name='products_backup.db' and '{google_drive_folder_id}' in parents",
                                       fields="files(id)").execute()
        items = results.get('files', [])

        if items:
            # Update existing file
            file_id = items[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # Create new file
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return "Backup successful"
    except Exception as e:
        return f"Backup failed: {e}"

# Scheduler for daily backup
scheduler = BackgroundScheduler()
scheduler.add_job(func=backup_to_google_drive, trigger="interval", days=1)
scheduler.start()

# ---------------------------- AUTH ----------------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id, password, role FROM users WHERE username=?", (username,))
            user = c.fetchone()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['role'] = user[2]
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------- ROUTES ----------------------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    q = request.args.get('q','')
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if q:
            c.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{q}%", f"%{q}%"))
        else:
            c.execute("SELECT * FROM products")
        products = c.fetchall()
    return render_template_string(INDEX_TEMPLATE, products=products, role=session['role'], q=q, username=session['username'])

@app.route('/add', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash("Only admin can add products")
        return redirect(url_for('index'))
    name = request.form['name']
    packing = request.form['packing']
    retail = request.form['retail']
    wholesale = request.form['wholesale']
    barcode = request.form['barcode']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO products (name, packing, retail_price, wholesale_price, barcode) VALUES (?,?,?,?,?)",
                  (name, packing, retail, wholesale, barcode))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Only admin can delete")
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/export')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT name, packing, retail_price, wholesale_price, barcode FROM products")
        rows = c.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name","Packing","Retail Price","Wholesale Price","Barcode"])
    writer.writerows(rows)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="products.csv")

@app.route('/import', methods=['POST'])
def import_csv():
    if session.get('role') != 'admin':
        flash("Only admin can import")
        return redirect(url_for('index'))
    file = request.files['file']
    if not file:
        return redirect(url_for('index'))
    stream = io.StringIO(file.stream.read().decode("UTF8"))
    reader = csv.reader(stream)
    next(reader)
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        for row in reader:
            c.execute("INSERT INTO products (name, packing, retail_price, wholesale_price, barcode) VALUES (?,?,?,?,?)", row)
        conn.commit()
    return redirect(url_for('index'))

@app.route('/backup')
def manual_backup():
    if session.get('role') != 'admin':
        flash("Only admin can backup")
        return redirect(url_for('index'))
    result = backup_to_google_drive()
    flash(result)
    return redirect(url_for('index'))

# ---------------------------- HTML TEMPLATES ----------------------------
LOGIN_TEMPLATE = """
<!doctype html>
<title>Login</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<div class="container mt-5">
  <h2>Login</h2>
  <form method="post">
    <input name="username" class="form-control mb-2" placeholder="Username" required>
    <input type="password" name="password" class="form-control mb-2" placeholder="Password" required>
    <button class="btn btn-primary">Login</button>
  </form>
</div>
"""

INDEX_TEMPLATE = """
<!doctype html>
<title>Products</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<div class="container mt-4">
  <h3>Welcome, {{username}} ({{role}})</h3>
  <a href="{{ url_for('logout') }}" class="btn btn-secondary btn-sm">Logout</a>
  {% if role == 'admin' %}
    <form method="post" action="{{ url_for('add_product') }}" class="mt-3 row g-2">
      <input name="name" class="form-control col" placeholder="Product" required>
      <input name="packing" class="form-control col" placeholder="Packing" required>
      <input name="retail" class="form-control col" placeholder="Retail" required>
      <input name="wholesale" class="form-control col" placeholder="Wholesale" required>
      <input name="barcode" class="form-control col" placeholder="Barcode">
      <button class="btn btn-success col">Add</button>
    </form>
  {% endif %}

  <form method="get" class="mt-3">
    <input name="q" value="{{q}}" placeholder="Search" class="form-control">
  </form>

  <table class="table table-bordered table-sm mt-3">
    <tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th>{% if role=='admin' %}<th>Action</th>{% endif %}</tr>
    {% for p in products %}
      <tr>
        <td>{{p[1]}}</td><td>{{p[2]}}</td><td>{{p[3]}}</td><td>{{p[4]}}</td><td>{{p[5]}}</td>
        {% if role=='admin' %}
          <td><a href="{{ url_for('delete_product', pid=p[0]) }}" class="btn btn-danger btn-sm">Delete</a></td>
        {% endif %}
      </tr>
    {% endfor %}
  </table>

  <div class="mt-3">
    <a href="{{ url_for('export_csv') }}" class="btn btn-info btn-sm">Export CSV</a>
    {% if role=='admin' %}
      <form action="{{ url_for('import_csv') }}" method="post" enctype="multipart/form-data" style="display:inline-block">
        <input type="file" name="file" onchange="this.form.submit()" class="form-control form-control-sm">
      </form>
      <a href="{{ url_for('manual_backup') }}" class="btn btn-warning btn-sm">Backup Now</a>
    {% endif %}
  </div>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="alert alert-info mt-3">{{ messages[0] }}</div>
    {% endif %}
  {% endwith %}
</div>
"""

# ---------------------------- RUN ----------------------------
if __name__ == "__main__":
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if admin_pass:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username='admin'")
            if not c.fetchone():
                c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", (
                    'admin', generate_password_hash(admin_pass), 'admin'))
                conn.commit()
    app.run(debug=True)


