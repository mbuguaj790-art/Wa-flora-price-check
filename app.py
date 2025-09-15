# app.py
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey123"
DB_NAME = "wa_flora_price.db"

# ----------------------
# Database initialization
# ----------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # products
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                packing TEXT,
                retail_price REAL DEFAULT 0,
                wholesale_price REAL DEFAULT 0,
                barcode TEXT
            )
        """)
        # users (workers)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'worker'
            )
        """)
        conn.commit()

init_db()

# ----------------------
# Templates
# ----------------------
BASE_CSS = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { padding-bottom: 40px; }
</style>
"""

NAVBAR_HTML = """
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('dashboard') }}">Wa Flora Price List</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto mb-2 mb-lg-0">
        {% if session.get('role') == 'admin' %}
          <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">Admin Menu</a>
            <ul class="dropdown-menu">
              <li><a class="dropdown-item" href="{{ url_for('manage_products') }}">Products</a></li>
              <li><a class="dropdown-item" href="{{ url_for('manage_workers') }}">Workers</a></li>
            </ul>
          </li>
        {% endif %}
      </ul>
      <div class="d-flex">
        {% if session.get('username') %}
          <span class="navbar-text text-white me-3">{{ session.get('username') }} ({{ session.get('role') }})</span>
          <a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Logout</a>
        {% endif %}
      </div>
    </div>
  </div>
</nav>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Login - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body class="container py-5">
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="card shadow-sm">
        <div class="card-body">
          <h4 class="card-title mb-3">Login</h4>
          {% with messages = get_flashed_messages() %}
            {% if messages %}
              <div class="alert alert-danger">{{ messages[0] }}</div>
            {% endif %}
          {% endwith %}
          <form method="post">
            <div class="mb-3">
              <label>Username</label>
              <input class="form-control" name="username" required>
            </div>
            <div class="mb-3">
              <label>Password</label>
              <input type="password" class="form-control" name="password" required>
            </div>
            <div class="d-grid"><button class="btn btn-primary">Login</button></div>
          </form>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Dashboard - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3>Welcome, {{ session.get('username') }}</h3>
    <p>Use the menu to manage products or workers (if admin).</p>
    {% if session.get('role') == 'worker' %}
      <a class="btn btn-primary" href="{{ url_for('view_products') }}">View Products</a>
    {% endif %}
  </div>
</body>
</html>
"""

PRODUCTS_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Products - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3>Products</h3>
    {% if session.get('role') == 'admin' %}
    <form method="post" action="{{ url_for('add_product') }}" class="mb-3">
      <div class="row g-2">
        <div class="col"><input class="form-control" name="name" placeholder="Name" required></div>
        <div class="col"><input class="form-control" name="packing" placeholder="Packing"></div>
        <div class="col"><input class="form-control" name="retail" placeholder="Retail" type="number" step="0.01"></div>
        <div class="col"><input class="form-control" name="wholesale" placeholder="Wholesale" type="number" step="0.01"></div>
        <div class="col"><input class="form-control" name="barcode" placeholder="Barcode"></div>
        <div class="col"><button class="btn btn-success">Add</button></div>
      </div>
    </form>
    {% endif %}
    <table class="table table-striped">
      <thead><tr><th>ID</th><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th>{% if session.get('role')=='admin' %}<th>Actions</th>{% endif %}</tr></thead>
      <tbody>
        {% for p in products %}
        <tr>
          <td>{{ p[0] }}</td>
          <td>{{ p[1] }}</td>
          <td>{{ p[2] or '' }}</td>
          <td>{{ "%.2f"|format(p[3] or 0) }}</td>
          <td>{{ "%.2f"|format(p[4] or 0) }}</td>
          {% if session.get('role')=='admin' %}
          <td>
            <a class="btn btn-sm btn-warning" href="{{ url_for('edit_product', pid=p[0]) }}">Edit</a>
            <a class="btn btn-sm btn-danger" href="{{ url_for('delete_product', pid=p[0]) }}" onclick="return confirm('Delete?')">Delete</a>
          </td>
          {% endif %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

WORKERS_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Workers - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3>Workers</h3>
    <form method="post" action="{{ url_for('add_worker') }}" class="mb-3 row g-2">
      <div class="col"><input class="form-control" name="username" placeholder="Username" required></div>
      <div class="col"><input class="form-control" name="password" placeholder="Password" required></div>
      <div class="col"><button class="btn btn-success">Add Worker</button></div>
    </form>
    <table class="table table-striped">
      <thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Action</th></tr></thead>
      <tbody>
        {% for w in workers %}
        <tr>
          <td>{{ w[0] }}</td>
          <td>{{ w[1] }}</td>
          <td>{{ w[3] }}</td>
          <td>
            <a class="btn btn-sm btn-danger" href="{{ url_for('delete_worker', uid=w[0]) }}" onclick="return confirm('Delete?')">Delete</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

# ----------------------
# Helper
# ----------------------
def query_db(query, params=(), fetch=False, commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if commit:
            conn.commit()
            return
        if fetch:
            return c.fetchall()
        return c

# ----------------------
# Authentication
# ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or "").strip()
        password = (request.form.get('password') or "").strip()
        # Admin
        if username.lower() == "waflora" and password == "0725935410":
            session['user_id'] = 0
            session['role'] = 'admin'
            session['username'] = 'Waflora'
            return redirect(url_for('dashboard'))
        # Worker
        row = query_db("SELECT id, password, role FROM users WHERE username=?", (username,), fetch=True)
        if row and check_password_hash(row[0][1], password):
            session['user_id'] = row[0][0]
            session['role'] = row[0][2]
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE, base_css=BASE_CSS)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.before_request
def require_login():
    allowed = ['login', 'static']
    if request.endpoint not in allowed and 'user_id' not in session:
        return redirect(url_for('login'))

# ----------------------
# Dashboard
# ----------------------
@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE, base_css=BASE_CSS, navbar=NAVBAR_HTML)

# ----------------------
# Products
# ----------------------
@app.route('/manage_products')
def manage_products():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    products = query_db("SELECT * FROM products", fetch=True)
    return render_template_string(PRODUCTS_TEMPLATE, products=products, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    name = (request.form.get('name') or "").strip()
    packing = (request.form.get('packing') or "").strip()
    retail = float(request.form.get('retail') or 0)
    wholesale = float(request.form.get('wholesale') or 0)
    barcode = (request.form.get('barcode') or "").strip()
    query_db("INSERT INTO products (name, packing, retail_price, wholesale_price, barcode) VALUES (?,?,?,?,?)",
             (name, packing, retail, wholesale, barcode), commit=True)
    flash("Product added")
    return redirect(url_for('manage_products'))

@app.route('/edit_product/<int:pid>', methods=['GET', 'POST'])
def edit_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = (request.form.get('name') or "").strip()
        packing = (request.form.get('packing') or "").strip()
        retail = float(request.form.get('retail') or 0)
        wholesale = float(request.form.get('wholesale') or 0)
        barcode = (request.form.get('barcode') or "").strip()
        query_db("UPDATE products SET name=?, packing=?, retail_price=?, wholesale_price=?, barcode=? WHERE id=?",
                 (name, packing, retail, wholesale, barcode, pid), commit=True)
        flash("Product updated")
        return redirect(url_for('manage_products'))
    row = query_db("SELECT * FROM products WHERE id=?", (pid,), fetch=True)
    if not row:
        flash("Product not found")
        return redirect(url_for('manage_products'))
    p = row[0]
    return render_template_string("""
    <!doctype html><html><head><title>Edit Product</title>{{ base_css|safe }}</head><body>{{ navbar|safe }}
    <div class="container"><h3>Edit Product</h3>
    <form method="post">
      <input class="form-control mb-2" name="name" value="{{ p[1] }}" required>
      <input class="form-control mb-2" name="packing" value="{{ p[2] or '' }}">
      <input class="form-control mb-2" name="retail" value="{{ p[3] or 0 }}" type="number" step="0.01">
      <input class="form-control mb-2" name="wholesale" value="{{ p[4] or 0 }}" type="number" step="0.01">
      <input class="form-control mb-2" name="barcode" value="{{ p[5] or '' }}">
      <button class="btn btn-primary">Save</button>
    </form></div></body></html>
    """, p=p, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/delete_product/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    query_db("DELETE FROM products WHERE id=?", (pid,), commit=True)
    flash("Product deleted")
    return redirect(url_for('manage_products'))

@app.route('/view_products')
def view_products():
    products = query_db("SELECT * FROM products", fetch=True)
    return render_template_string(PRODUCTS_TEMPLATE, products=products, base_css=BASE_CSS, navbar=NAVBAR_HTML)

# ----------------------
# Workers
# ----------------------
@app.route('/manage_workers')
def manage_workers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    rows = query_db("SELECT * FROM users", fetch=True)
    workers = [(r[0], r[1], r[2], r[2] if len(r)>=3 else 'worker') for r in rows]
    return render_template_string(WORKERS_TEMPLATE, workers=workers, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/add_worker', methods=['POST'])
def add_worker():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    username = (request.form.get('username') or "").strip()
    password = (request.form.get('password') or "").strip()
    if not username or not password:
        flash("Provide username and password")
        return redirect(url_for('manage_workers'))
    pw_hash = generate_password_hash(password)
    try:
        query_db("INSERT INTO users (username, password, role) VALUES (?,?,?)", (username, pw_hash, 'worker'), commit=True)
        flash("Worker added")
    except Exception as e:
        flash("Error: " + str(e))
    return redirect(url_for('manage_workers'))

@app.route('/delete_worker/<int:uid>')
def delete_worker(uid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('dashboard'))
    query_db("DELETE FROM users WHERE id=?", (uid,), commit=True)
    flash("Worker deleted")
    return redirect(url_for('manage_workers'))

# ----------------------
# Run
# ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
