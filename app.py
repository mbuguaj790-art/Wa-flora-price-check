# app.py
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change_this_super_secret_key"  # change for production
DB_NAME = "wa_flora.db"

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
    <a class="navbar-brand" href="{{ url_for('index') }}">Wa Flora</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto mb-2 mb-lg-0">
        {% if session.get('user_id') %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Products</a></li>
          {% if session.get('role') == 'admin' %}
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_products') }}">Manage Products</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_workers') }}">Workers</a></li>
          {% endif %}
        {% endif %}
      </ul>
      <div class="d-flex">
        {% if session.get('username') %}
          <span class="navbar-text text-white me-3">{{ session.get('username') }} ({{ session.get('role') }})</span>
          <a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Logout</a>
        {% else %}
          <a class="btn btn-outline-light btn-sm" href="{{ url_for('login') }}">Login</a>
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
              <label class="form-label">Username</label>
              <input class="form-control" name="username" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Password</label>
              <input type="password" class="form-control" name="password" required>
            </div>
            <div class="d-grid">
              <button class="btn btn-primary">Login</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
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
    <h3 class="mb-3">Products</h3>
    <form class="row g-2 mb-3" method="get" action="{{ url_for('index') }}">
      <div class="col-md-8">
        <input class="form-control" name="q" placeholder="Search by name or barcode" value="{{ q }}">
      </div>
      <div class="col-md-4">
        <button class="btn btn-outline-primary">Search</button>
        {% if role=='admin' %}
          <a class="btn btn-success" href="{{ url_for('manage_products') }}">Manage Products</a>
        {% endif %}
      </div>
    </form>
    <div class="card shadow-sm">
      <div class="card-body">
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
  <title>Manage Products - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3 class="mb-3">Manage Products</h3>
    <div class="row">
      <div class="col-md-5">
        <div class="card shadow-sm mb-3">
          <div class="card-body">
            <h5>Add Product</h5>
            <form method="post" action="{{ url_for('add_product') }}">
              <div class="mb-2"><input class="form-control" name="name" placeholder="Name" required></div>
              <div class="mb-2"><input class="form-control" name="packing" placeholder="Packing"></div>
              <div class="mb-2"><input class="form-control" name="retail" placeholder="Retail price" type="number" step="0.01"></div>
              <div class="mb-2"><input class="form-control" name="wholesale" placeholder="Wholesale price" type="number" step="0.01"></div>
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
                      <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('edit_product', pid=p[0]) }}">Edit</a>
                      <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_product', pid=p[0]) }}" onclick="return confirm('Delete product?')">Delete</a>
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

EDIT_PRODUCT_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Edit Product - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3>Edit Product</h3>
    <div class="card shadow-sm">
      <div class="card-body">
        <form method="post">
          <div class="mb-2"><input class="form-control" name="name" value="{{ p[1] }}" required></div>
          <div class="mb-2"><input class="form-control" name="packing" value="{{ p[2] or '' }}"></div>
          <div class="mb-2"><input class="form-control" name="retail" value="{{ p[3] or 0 }}" type="number" step="0.01"></div>
          <div class="mb-2"><input class="form-control" name="wholesale" value="{{ p[4] or 0 }}" type="number" step="0.01"></div>
          <div class="mb-2"><input class="form-control" name="barcode" value="{{ p[5] or '' }}"></div>
          <div class="d-grid"><button class="btn btn-primary">Save Changes</button></div>
        </form>
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
  <title>Workers - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3 class="mb-3">Workers</h3>
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
# Helper
# ----------------------
def query_db(query, params=(), fetch=False, commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if commit:
            conn.commit()
            return None
        if fetch:
            return c.fetchall()
        return c

# ----------------------
# Auth
# ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or "").strip()
        password = (request.form.get('password') or "").strip()
        # Admin
        if username == "WaFlora" and password == "0725935410":
            session['user_id'] = 0
            session['role'] = 'admin'
            session['username'] = 'WaFlora'
            return redirect(url_for('index'))
        # Worker
        row = query_db("SELECT id, password, role FROM users WHERE username=?", (username,), fetch=True)
        if row:
            uid, pw_hash, role = row[0]
            if check_password_hash(pw_hash, password):
                session['user_id'] = uid
                session['role'] = role
                session['username'] = username
                return redirect(url_for('index'))
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
# Products
# ----------------------
@app.route('/')
def index():
    q = (request.args.get('q') or "").strip()
    if q:
        products = query_db("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{q}%", f"%{q}%"), fetch=True)
    else:
        products = query_db("SELECT * FROM products", fetch=True)
    return render_template_string(INDEX_TEMPLATE, products=products, role=session.get('role'), q=q, base_css=BASE_CSS, navbar=NAVBAR_HTML)

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
    try: retail = float(request.form.get('retail') or 0)
    except: retail = 0
    try: wholesale = float(request.form.get('wholesale') or 0)
    except: wholesale = 0
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
        try: retail = float(request.form.get('retail') or 0)
        except: retail = 0
        try: wholesale = float(request.form.get('wholesale') or 0)
        except: wholesale = 0
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
    return render_template_string(EDIT_PRODUCT_TEMPLATE, p=p, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/delete_product/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('manage_products'))
    query_db("DELETE FROM products WHERE id=?", (pid,), commit=True)
    flash("Product deleted")
    return redirect(url_for('manage_products'))

# ----------------------
# Workers
# ----------------------
@app.route('/manage_workers')
def manage_workers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    rows = query_db("SELECT * FROM users", fetch=True)
    workers = []
    for r in rows:
        if len(r) >= 4: workers.append((r[0], r[1], r[2], r[3]))
        else: workers.append((r[0], r[1], r[2], 'worker'))
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
        query_db("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                 (username, pw_hash, 'worker'), commit=True)
        flash("Worker added")
    except sqlite3.IntegrityError:
        flash("Username already exists")
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
    app.run(debug=True)
