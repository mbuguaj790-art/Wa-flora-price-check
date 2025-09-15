# app.py
from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "change_this_super_secret_key"  # change this in production

DB_NAME = "wa_flora_full.db"

# --------------------- DB Init ---------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # products
        c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                packing TEXT,
                retail_price REAL,
                wholesale_price REAL,
                barcode TEXT
            )
        ''')
        # users (workers)
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        # customers
        c.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                driver TEXT,
                balance REAL DEFAULT 0
            )
        ''')
        # sales/payments
        c.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                total_cost REAL NOT NULL,
                payment_method TEXT,
                mpesa_name TEXT,
                status TEXT,
                date TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        ''')
        conn.commit()

init_db()

# --------------------- Utilities ---------------------
def db_query(query, params=(), fetch=False, commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if commit:
            conn.commit()
            return None
        if fetch:
            return c.fetchall()
        return c

def current_user_role():
    return session.get('role')

# --------------------- Templates (Bootstrap) ---------------------
BASE_HEAD = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .credit { color: #c82333; font-weight: 700; } /* red bold for credit */
  .mt-10 { margin-top: 1rem; }
</style>
"""

NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('index') }}">Wa Flora</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto">
        {% if session.get('user_id') %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Products</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('sales') }}">Record Sale</a></li>
          {% if session.get('role') == 'admin' %}
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_products') }}">Manage Products</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_workers') }}">Workers</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_customers') }}">Customers</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('payments') }}">Record Payment</a></li>
          {% endif %}
        {% endif %}
      </ul>
      <span class="navbar-text text-white me-3">
        {% if session.get('username') %} {{ session.get('username') }} ({{ session.get('role') }}) {% endif %}
      </span>
      {% if session.get('user_id') %}
        <a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Logout</a>
      {% endif %}
    </div>
  </div>
</nav>
"""

# --------------------- Authentication ---------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    LOGIN_TEMPLATE = f"""
    <!doctype html>
    <html>
    <head><title>Login - Wa Flora</title>{BASE_HEAD}</head>
    <body class="container">
      {NAVBAR}
      <div class="row justify-content-center">
        <div class="col-md-5">
          <div class="card">
            <div class="card-body">
              <h4 class="card-title">Login to Wa Flora</h4>
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
          <p class="mt-3 text-muted small">Admin: WaFlora / 0725935410</p>
        </div>
      </div>
    </body>
    </html>
    """
    if request.method == 'POST':
        username = (request.form.get('username') or "").strip()
        password = (request.form.get('password') or "").strip()
        # Hardcoded admin
        if username == "WaFlora" and password == "0725935410":
            session['user_id'] = 0
            session['role'] = 'admin'
            session['username'] = 'WaFlora'
            return redirect(url_for('index'))
        # Else check workers table
        row = db_query("SELECT id, password, role FROM users WHERE username = ?", (username,), fetch=True)
        if row:
            user = row[0]
            if check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['role'] = user[2]
                session['username'] = username
                return redirect(url_for('index'))
        flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.before_request
def require_login():
    allowed = ['login', 'static']
    if request.endpoint not in allowed and 'user_id' not in session:
        return redirect(url_for('login'))

# --------------------- Index / Product view ---------------------
@app.route('/')
def index():
    q = (request.args.get('q') or "").strip()
    if q:
        products = db_query("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{q}%", f"%{q}%"), fetch=True)
    else:
        products = db_query("SELECT * FROM products", fetch=True)
    page = f"""
    <!doctype html>
    <html>
    <head><title>Products - Wa Flora</title>{BASE_HEAD}</head>
    <body class="container">
      {NAVBAR}
      <div class="row">
        <div class="col-12">
          <form class="d-flex mb-3" method="get" action="/">
            <input class="form-control me-2" name="q" placeholder="Search by name or barcode" value="{{{{ q }}}}">
            <button class="btn btn-outline-primary">Search</button>
          </form>
        </div>
        <div class="col-12">
          <div class="card mb-3">
            <div class="card-body">
              <h5 class="card-title">Products</h5>
              <table class="table table-striped table-sm">
                <thead>
                  <tr><th>ID</th><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th><th>Actions</th></tr>
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
                    <td>
                      {% if session.get('role') == 'admin' %}
                        <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('edit_product', pid=p[0]) }}">Edit</a>
                        <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_product', pid=p[0]) }}" onclick="return confirm('Delete product?')">Delete</a>
                      {% else %}
                        <span class="text-muted small">Read-only</span>
                      {% endif %}
                    </td>
                  </tr>
                {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return render_template_string(page, products=products, q=q)

# --------------------- Manage Products ---------------------
@app.route('/manage/products')
def manage_products():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    products = db_query("SELECT * FROM products", fetch=True)
    page = f"""
    <!doctype html>
    <html>
    <head><title>Manage Products - Wa Flora</title>{BASE_HEAD}</head>
    <body class="container">
      {NAVBAR}
      <div class="row">
        <div class="col-md-6">
          <div class="card mb-3">
            <div class="card-body">
              <h5>Add Product</h5>
              <form method="post" action="{{{{ url_for('add_product') }}}}">
                <div class="mb-2"><input class="form-control" name="name" placeholder="Name" required></div>
                <div class="mb-2"><input class="form-control" name="packing" placeholder="Packing (pcs/dozen/kg)"></div>
                <div class="mb-2"><input class="form-control" name="retail" placeholder="Retail price" type="number" step="0.01" required></div>
                <div class="mb-2"><input class="form-control" name="wholesale" placeholder="Wholesale price" type="number" step="0.01"></div>
                <div class="mb-2"><input class="form-control" name="barcode" placeholder="Barcode"></div>
                <div class="d-grid"><button class="btn btn-success">Add</button></div>
              </form>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card">
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
    </body>
    </html>
    """
    return render_template_string(page, products=products)

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    name = (request.form.get('name') or "").strip()
    packing = (request.form.get('packing') or "").strip()
    retail = request.form.get('retail') or 0
    wholesale = request.form.get('wholesale') or 0
    barcode = (request.form.get('barcode') or "").strip()
    try:
        db_query("INSERT INTO products (name, packing, retail_price, wholesale_price, barcode) VALUES (?,?,?,?,?)",
                 (name, packing, float(retail), float(wholesale), barcode), commit=True)
        flash("Product added")
    except Exception as e:
        flash("Error adding product: " + str(e))
    return redirect(url_for('manage_products'))

@app.route('/edit/product/<int:pid>', methods=['GET', 'POST'])
def edit_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = (request.form.get('name') or "").strip()
        packing = (request.form.get('packing') or "").strip()
        retail = request.form.get('retail') or 0
        wholesale = request.form.get('wholesale') or 0
        barcode = (request.form.get('barcode') or "").strip()
        try:
            db_query("UPDATE products SET name=?, packing=?, retail_price=?, wholesale_price=?, barcode=? WHERE id=?",
                     (name, packing, float(retail), float(wholesale), barcode, pid), commit=True)
            flash("Product updated")
            return redirect(url_for('manage_products'))
        except Exception as e:
            flash("Error updating product: " + str(e))
            return redirect(url_for('edit_product', pid=pid))
    else:
        row = db_query("SELECT * FROM products WHERE id=?", (pid,), fetch=True)
        if not row:
            flash("Product not found")
            return redirect(url_for('manage_products'))
        p = row[0]
        form = f"""
        <!doctype html>
        <html>
        <head><title>Edit Product</title>{BASE_HEAD}</head>
        <body class="container">
          {NAVBAR}
          <div class="card">
            <div class="card-body">
              <h5>Edit Product</h5>
              <form method="post">
                <div class="mb-2"><input class="form-control" name="name" value="{{{{ p[1] }}}}" required></div>
                <div class="mb-2"><input class="form-control" name="packing" value="{{{{ p[2] or '' }}}}"></div>
                <div class="mb-2"><input class="form-control" name="retail" value="{{{{ p[3] or 0 }}}}" type="number" step="0.01" required></div>
                <div class="mb-2"><input class="form-control" name="wholesale" value="{{{{ p[4] or 0 }}}}" type="number" step="0.01"></div>
                <div class="mb-2"><input class="form-control" name="barcode" value="{{{{ p[5] or '' }}}}"></div>
                <div class="d-grid"><button class="btn btn-primary">Save</button></div>
              </form>
            </div>
          </div>
        </body>
        </html>
        """
        return render_template_string(form, p=p)

@app.route('/delete/product/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    db_query("DELETE FROM products WHERE id=?", (pid,), commit=True)
    flash("Product deleted")
    return redirect(url_for('manage_products'))

# --------------------- Workers (admin) ---------------------
@app.route('/manage/workers')
def manage_workers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    workers = db_query("SELECT id, username, role FROM users", fetch=True)
    page = f"""
    <!doctype html>
    <html>
    <head><title>Workers - Wa Flora</title>{BASE_HEAD}</head>
    <body class="container">
      {NAVBAR}
      <div class="row">
        <div class="col-md-5">
          <div class="card">
            <div class="card-body">
              <h5>Add Worker</h5>
              <form method="post" action="{{{{ url_for('add_worker') }}}}">
                <div class="mb-2"><input class="form-control" name="username" placeholder="Username" required></div>
                <div class="mb-2"><input class="form-control" name="password" placeholder="Password" required></div>
                <div class="d-grid"><button class="btn btn-success">Add Worker</button></div>
              </form>
            </div>
          </div>
        </div>
        <div class="col-md-7">
          <div class="card">
            <div class="card-body">
              <h5>Existing Workers</h5>
              <table class="table table-sm">
                <thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Action</th></tr></thead>
                <tbody>
                {% for w in workers %}
                  <tr>
                    <td>{{ w[0] }}</td>
                    <td>{{ w[1] }}</td>
                    <td>{{ w[2] }}</td>
                    <td><a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_worker', uid=w[0]) }}" onclick="return confirm('Delete worker?')">Delete</a></td>
                  </tr>
                {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return render_template_string(page, workers=workers)

@app.route('/add_worker', methods=['POST'])
def add_worker():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    username = (request.form.get('username') or "").strip()
    password = (request.form.get('password') or "").strip()
    if not username or not password:
        flash("Provide username and password")
        return redirect(url_for('manage_workers'))
    try:
        hashed = generate_password_hash(password)
        db_query("INSERT INTO users (username, password, role) VALUES (?,?,?)", (username, hashed, 'worker'), commit=True)
        flash("Worker added")
    except Exception as e:
        flash("Error adding worker: " + str(e))
    return redirect(url_for('manage_workers'))

@app.route('/delete/worker/<int:uid>')
def delete_worker(uid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    db_query("DELETE FROM users WHERE id=?", (uid,), commit=True)
    flash("Worker deleted")
    return redirect(url_for('manage_workers'))

# --------------------- Customers (admin) ---------------------
@app.route('/manage/customers')
def manage_customers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    customers = db_query("SELECT * FROM customers", fetch=True)
    page = f"""
    <!doctype html>
    <html>
    <head><title>Customers - Wa Flora</title>{BASE_HEAD}</head>
    <body class="container">
      {NAVBAR}
      <div class="row">
        <div class="col-md-5">
          <div class="card mb-3">
            <div class="card-body">
              <h5>Add Customer</h5>
              <form method="post" action="{{{{ url_for('add_customer') }}}}">
                <div class="mb-2"><input class="form-control" name="name" placeholder="Customer name" required></div>
                <div class="mb-2"><input class="form-control" name="location" placeholder="Location"></div>
                <div class="mb-2"><input class="form-control" name="driver" placeholder="Driver"></div>
                <div class="d-grid"><button class="btn btn-success">Add Customer</button></div>
              </form>
            </div>
          </div>
        </div>
        <div class="col-md-7">
          <div class="card">
            <div class="card-body">
              <h5>Existing Customers</h5>
              <table class="table table-sm">
                <thead><tr><th>ID</th><th>Name</th><th>Location</th><th>Driver</th><th>Balance</th><th>Action</th></tr></thead>
                <tbody>
                {% for c in customers %}
                  <tr>
                    <td>{{ c[0] }}</td>
                    <td>{% if c[4] > 0 %}<span class="credit">{{ c[1] }}</span>{% else %}{{ c[1] }}{% endif %}</td>
                    <td>{{ c[2] or '' }}</td>
     
