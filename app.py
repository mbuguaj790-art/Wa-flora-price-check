# app.py
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change_this_super_secret_key"
DB_NAME = "wa_flora_price_list.db"

# ----------------------
# Database initialization
# ----------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # products table
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
        # users table
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
# Helper functions
# ----------------------
def query_db(query, params=(), fetch=False, commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if commit:
            conn.commit()
        if fetch:
            return c.fetchall()
        return c

# ----------------------
# Templates
# ----------------------
BASE_CSS = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { padding-bottom: 40px; }
  .side-panel { max-height: 80vh; overflow-y: auto; }
</style>
"""

NAVBAR_HTML = """
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('index') }}">Wa Flora</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto mb-2 mb-lg-0">
        {% if session.get('user_id') %}
          {% if session.get('role')=='admin' %}
          <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">Admin Menu</a>
            <ul class="dropdown-menu">
              <li><a class="dropdown-item" href="{{ url_for('manage_products') }}">Products</a></li>
              <li><a class="dropdown-item" href="{{ url_for('manage_workers') }}">Workers</a></li>
            </ul>
          </li>
          {% endif %}
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

INDEX_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Wa Flora Price List</title>
  {{ base_css|safe }}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <div class="row">
      <!-- Left: Login / Admin info -->
      <div class="col-md-4 side-panel">
        {% if not session.get('user_id') %}
        <div class="card shadow-sm mb-3">
          <div class="card-body">
            <h5>Login</h5>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="alert alert-danger">{{ messages[0] }}</div>
              {% endif %}
            {% endwith %}
            <form method="post" action="{{ url_for('login') }}">
              <div class="mb-2"><input class="form-control" name="username" placeholder="Username" required></div>
              <div class="mb-2"><input class="form-control" type="password" name="password" placeholder="Password" required></div>
              <div class="d-grid"><button class="btn btn-primary">Login</button></div>
            </form>
          </div>
        </div>
        {% else %}
        <div class="card shadow-sm mb-3">
          <div class="card-body">
            <h5>Welcome, {{ session.get('username') }}</h5>
            <p>Role: {{ session.get('role') }}</p>
          </div>
        </div>
        {% endif %}
      </div>

      <!-- Right: Products List -->
      <div class="col-md-8 side-panel">
        <h4>Products</h4>
        <table class="table table-striped">
          <thead>
            <tr><th>ID</th><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th></tr>
          </thead>
          <tbody>
            {% for p in products %}
            <tr>
              <td>{{ p[0] }}</td>
              <td>{{ p[1] }}</td>
              <td>{{ p[2] or '' }}</td>
              <td>{{ "%.2f"|format(p[3] or 0) }}</td>
              <td>{{ "%.2f"|format(p[4] or 0) }}</td>
              <td>{{ p[5] or '' }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>
"""

MANAGE_PRODUCTS_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Manage Products</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3>Manage Products</h3>
    <div class="row">
      <div class="col-md-5">
        <div class="card shadow-sm mb-3">
          <div class="card-body">
            <h5>Add Product</h5>
            <form method="post" action="{{ url_for('add_product') }}">
              <div class="mb-2"><input class="form-control" name="name" placeholder="Name" required></div>
              <div class="mb-2"><input class="form-control" name="packing" placeholder="Packing"></div>
              <div class="mb-2"><input class="form-control" name="retail" type="number" step="0.01" placeholder="Retail"></div>
              <div class="mb-2"><input class="form-control" name="wholesale" type="number" step="0.01" placeholder="Wholesale"></div>
              <div class="mb-2"><input class="form-control" name="barcode" placeholder="Barcode"></div>
              <div class="d-grid"><button class="btn btn-success">Add Product</button></div>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-7">
        <div class="card shadow-sm">
          <div class="card-body">
            <h5>Existing Products</h5>
            <table class="table table-sm">
              <thead><tr><th>ID</th><th>Name</th><th>Actions</th></tr></thead>
              <tbody>
                {% for p in products %}
                <tr>
                  <td>{{ p[0] }}</td>
                  <td>{{ p[1] }}</td>
                  <td>
                    <a class="btn btn-sm btn-warning" href="{{ url_for('edit_product', pid=p[0]) }}">Edit</a>
                    <a class="btn btn-sm btn-danger" href="{{ url_for('delete_product', pid=p[0]) }}" onclick="return confirm('Delete product?')">Delete</a>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

MANAGE_WORKERS_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Manage Workers</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3>Manage Workers</h3>
    <div class="row">
      <div class="col-md-5">
        <div class="card shadow-sm mb-3">
          <div class="card-body">
            <h5>Add Worker</h5>
            <form method="post" action="{{ url_for('add_worker') }}">
              <div class="mb-2"><input class="form-control" name="username" placeholder="Username" required></div>
              <div class="mb-2"><input class="form-control" name="password" placeholder="Password" required></div>
              <div class="d-grid"><button class="btn btn-success">Add Worker</button></div>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-7">
        <div class="card shadow-sm">
          <div class="card-body">
            <h5>Existing Workers</h5>
            <table class="table table-sm">
              <thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Action</th></tr></thead>
              <tbody>
                {% for w in workers %}
                <tr>
                  <td>{{ w[0] }}</td>
                  <td>{{ w[1] }}</td>
                  <td>{{ w[3] }}</td>
                  <td>
                    <a class="btn btn-sm btn-danger" href="{{ url_for('delete_worker', uid=w[0]) }}" onclick="return confirm('Delete worker?')">Delete</a>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# ----------------------
# Authentication
# ----------------------
@app.route('/login', methods=['POST'])
def login():
    username = (request.form.get('username') or "").strip()
    password = (request.form.get('password') or "").strip()
    # Admin hardcoded
    if username == "admin" and password == "admin123":
        session['user_id'] = 0
        session['role'] = 'admin'
        session['username'] = 'admin'
        return redirect(url_for('index'))
    row = query_db("SELECT id, password, role FROM users WHERE username=?", (username,), fetch=True)
    if row and check_password_hash(row[0][1], password):
        session['user_id'] = row[0][0]
        session['role'] = row[0][2]
        session['username'] = username
        return redirect(url_for('index'))
    flash("Invalid credentials")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ----------------------
# Pages
# ----------------------
@app.route('/')
def index():
    products = query_db("SELECT * FROM products", fetch=True)
    return render_template_string(INDEX_TEMPLATE, products=products, base_css=BASE_CSS, navbar=NAVBAR_HTML)

# Manage Products (admin)
@app.route('/manage_products')
def manage_products():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    products = query_db("SELECT * FROM products", fetch=True)
    return render_template_string(MANAGE_PRODUCTS_TEMPLATE, products=products, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('manage_products'))
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
        return redirect(url_for('index'))
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
    return render_template_string(MANAGE_PRODUCTS_TEMPLATE, products=[p], base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/delete_product/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('manage_products'))
    query_db("DELETE FROM products WHERE id=?", (pid,), commit=True)
    flash("Product deleted")
    return redirect(url_for('manage_products'))

# Manage Workers (admin)
@app.route('/manage_workers')
def manage_workers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    rows = query_db("SELECT * FROM users", fetch=True)
    workers = []
    for r in rows:
        workers.append((r[0], r[1], r[2], r[2]))
    return render_template_string(MANAGE_WORKERS_TEMPLATE, workers=workers, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/add_worker', methods=['POST'])
def add_worker():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('manage_workers'))
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
        return redirect(url_for('manage_workers'))
    query_db("DELETE FROM users WHERE id=?", (uid,), commit=True)
    flash("Worker deleted")
    return redirect(url_for('manage_workers'))

# ----------------------
# Run
# ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
