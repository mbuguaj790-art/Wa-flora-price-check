# app.py
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change_this_super_secret_key"  # change for production
DB_NAME = "wa_flora_full.db"

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
        # customers
        c.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                driver TEXT,
                balance REAL DEFAULT 0
            )
        """)
        # sales/payments log
        c.execute("""
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
        """)
        conn.commit()

init_db()

# ----------------------
# Templates (Bootstrap)
# ----------------------
BASE_CSS = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .credit { color: #c82333; font-weight: 700; } /* red bold for credit balances */
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
          <li class="nav-item"><a class="nav-link" href="{{ url_for('sales_form') }}">Record Sale</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('customers_page') }}">Customers</a></li>
          {% if session.get('role') == 'admin' %}
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_products') }}">Manage Products</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('manage_workers') }}">Workers</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('payments_page') }}">Payments</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('sales_history') }}">Sales History</a></li>
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
          <h4 class="card-title mb-3">Login to Wa Flora</h4>
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
          <p class="mt-3 text-muted small">Admin credentials: <strong>WaFlora</strong> / <strong>0725935410</strong></p>
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
            <tr><th>ID</th><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th>{% if role=='admin' %}<th>Actions</th>{% endif %}</tr>
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
                {% if role=='admin' %}
                  <td>
                    <a class="btn btn-sm btn-warning" href="{{ url_for('edit_product', pid=p[0]) }}">Edit</a>
                    <a class="btn btn-sm btn-danger" href="{{ url_for('delete_product', pid=p[0]) }}" onclick="return confirm('Delete product?')">Delete</a>
                  </td>
                {% endif %}
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
            <h5 class="card-title">Add Product</h5>
            <form method="post" action="{{ url_for('add_product') }}">
              <div class="mb-2"><input class="form-control" name="name" placeholder="Name" required></div>
              <div class="mb-2"><input class="form-control" name="packing" placeholder="Packing (pcs/dozen/kg)"></div>
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
            <h5 class="card-title">Existing Products</h5>
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
          <div class="mb-2">
            <label class="form-label">Name</label>
            <input class="form-control" name="name" value="{{ p[1] }}" required>
          </div>
          <div class="mb-2">
            <label class="form-label">Packing</label>
            <input class="form-control" name="packing" value="{{ p[2] or '' }}">
          </div>
          <div class="mb-2">
            <label class="form-label">Retail price</label>
            <input class="form-control" name="retail" value="{{ p[3] or 0 }}" type="number" step="0.01">
          </div>
          <div class="mb-2">
            <label class="form-label">Wholesale price</label>
            <input class="form-control" name="wholesale" value="{{ p[4] or 0 }}" type="number" step="0.01">
          </div>
          <div class="mb-2">
            <label class="form-label">Barcode</label>
            <input class="form-control" name="barcode" value="{{ p[5] or '' }}">
          </div>
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

CUSTOMERS_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Customers - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3 class="mb-3">Customers</h3>

    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h5>Customer List</h5>
        <table class="table table-sm">
          <thead><tr><th>ID</th><th>Name</th><th>Location</th><th>Driver</th><th>Balance</th>{% if role=='admin' %}<th>Action</th>{% endif %}</tr></thead>
          <tbody>
            {% for c in customers %}
              <tr>
                <td>{{ c[0] }}</td>
                <td>{% if c[4] > 0 %}<span class="credit">{{ c[1] }}</span>{% else %}{{ c[1] }}{% endif %}</td>
                <td>{{ c[2] or '' }}</td>
                <td>{{ c[3] or '' }}</td>
                <td>{% if c[4] > 0 %}<span class="credit">{{ "%.2f"|format(c[4]) }}</span>{% else %}{{ "%.2f"|format(c[4]) }}{% endif %}</td>
                {% if role=='admin' %}
                  <td><a class="btn btn-sm btn-danger" href="{{ url_for('delete_customer', cid=c[0]) }}" onclick="return confirm('Delete customer?')">Delete</a></td>
                {% endif %}
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    {% if role=='admin' %}
    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <h5>Add Customer</h5>
        <form method="post" action="{{ url_for('add_customer') }}" class="row g-2">
          <div class="col-md-4"><input class="form-control" name="name" placeholder="Name" required></div>
          <div class="col-md-3"><input class="form-control" name="location" placeholder="Location"></div>
          <div class="col-md-3"><input class="form-control" name="driver" placeholder="Driver"></div>
          <div class="col-md-2"><button class="btn btn-success">Add</button></div>
        </form>
      </div>
    </div>

    <div class="card shadow-sm">
      <div class="card-body">
        <h5>Record Payment (Admin only)</h5>
        <form method="post" action="{{ url_for('record_payment') }}" class="row g-2">
          <div class="col-md-6">
            <select class="form-control" name="customer_id" required>
              <option value="">-- Select customer --</option>
              {% for c in customers %}
                <option value="{{ c[0] }}">{{ c[1] }} (Balance: {{ "%.2f"|format(c[4]) }})</option>
              {% endfor %}
            </select>
          </div>
          <div class="col-md-4"><input class="form-control" name="amount" placeholder="Amount" type="number" step="0.01" required></div>
          <div class="col-md-2"><button class="btn btn-primary">Record Payment</button></div>
        </form>
      </div>
    </div>
    {% endif %}

    <hr>
    <h5>Quick Record Sale</h5>
    <form method="post" action="{{ url_for('record_sale') }}" class="row g-2">
      <div class="col-md-4">
        <select class="form-control" name="customer_id" required>
          <option value="">-- Select customer --</option>
          {% for c in customers %}
            <option value="{{ c[0] }}">{{ c[1] }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2"><input class="form-control" name="total_cost" placeholder="Total" type="number" step="0.01" required></div>
      <div class="col-md-3">
        <select class="form-control" name="payment_method" id="pmethod" onchange="toggleMpesa()">
          <option value="Cash">Cash</option>
          <option value="Mpesa">M-Pesa</option>
          <option value="Credit">Credit</option>
        </select>
      </div>
      <div class="col-md-3"><input class="form-control" name="mpesa_name" id="mpesa_name" placeholder="Mpesa name (if Mpesa)"></div>
      <div class="col-md-12 mt-2"><button class="btn btn-success">Record Sale</button></div>
    </form>

    <script>
      function toggleMpesa(){
        var v = document.getElementById('pmethod').value;
        document.getElementById('mpesa_name').style.display = (v === 'Mpesa') ? 'block' : 'block';
      }
    </script>

  </div>
</body>
</html>
"""

SALES_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Record Sale - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3 class="mb-3">Record Sale</h3>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-success">{{ messages[0] }}</div>
      {% endif %}
    {% endwith %}
    <div class="card shadow-sm">
      <div class="card-body">
        <form method="post">
          <div class="mb-2">
            <label class="form-label">Customer</label>
            <select class="form-control" name="customer_id" required>
              <option value="">-- Select customer --</option>
              {% for c in customers %}
                <option value="{{ c[0] }}">{{ c[1] }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="mb-2">
            <label class="form-label">Total sale amount</label>
            <input class="form-control" name="total_cost" type="number" step="0.01" required>
          </div>
          <div class="mb-2">
            <label class="form-label">Payment method</label>
            <select class="form-control" name="payment_method" id="pmethod2" onchange="toggleMpesa2()">
              <option value="Cash">Cash</option>
              <option value="Mpesa">M-Pesa</option>
              <option value="Credit">Credit</option>
            </select>
          </div>
          <div class="mb-2" id="mpesaDiv2" style="display:none;">
            <label class="form-label">M-Pesa name (sender)</label>
            <input class="form-control" name="mpesa_name">
          </div>
          <div class="d-grid"><button class="btn btn-primary">Save Sale</button></div>
        </form>
      </div>
    </div>
  </div>

<script>
function toggleMpesa2(){
  var v = document.getElementById('pmethod2').value;
  document.getElementById('mpesaDiv2').style.display = (v === 'Mpesa') ? 'block' : 'none';
}
</script>

</body>
</html>
"""

SALES_HISTORY_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Sales History - Wa Flora</title>
  {{ base_css|safe }}
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h3 class="mb-3">Sales & Payments History</h3>
    <div class="card shadow-sm">
      <div class="card-body">
        <table class="table table-sm">
          <thead><tr><th>ID</th><th>Customer</th><th>Amount</th><th>Method</th><th>Mpesa name</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {% for r in rows %}
              <tr>
                <td>{{ r[0] }}</td>
                <td>{{ r[1] or 'Unknown' }}</td>
                <td>{{ "%.2f"|format(r[2] or 0) }}</td>
                <td>{{ r[3] or '' }}</td>
                <td>{{ r[4] or '' }}</td>
                <td>{{ r[5] or '' }}</td>
                <td>{{ r[6] or '' }}</td>
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

# ----------------------
# Helper functions
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
# Authentication routes
# ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or "").strip()
        password = (request.form.get('password') or "").strip()
        # Admin hardcoded
        if username == "WaFlora" and password == "0725935410":
            session['user_id'] = 0
            session['role'] = 'admin'
            session['username'] = 'WaFlora'
            return redirect(url_for('index'))
        # worker lookup
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
# Products - public view (workers/admin)
# ----------------------
@app.route('/')
def index():
    q = (request.args.get('q') or "").strip()
    if q:
        products = query_db("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{q}%", f"%{q}%"), fetch=True)
    else:
        products = query_db("SELECT * FROM products", fetch=True)
    return render_template_string(INDEX_TEMPLATE, products=products, role=session.get('role'), q=q, base_css=BASE_CSS, navbar=NAVBAR_HTML)

# Manage products (admin)
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
    try:
        retail = float(request.form.get('retail') or 0)
    except:
        retail = 0
    try:
        wholesale = float(request.form.get('wholesale') or 0)
    except:
        wholesale = 0
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
        try:
            retail = float(request.form.get('retail') or 0)
        except:
            retail = 0
        try:
            wholesale = float(request.form.get('wholesale') or 0)
        except:
            wholesale = 0
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
# Workers (admin)
# ----------------------
@app.route('/manage_workers')
def manage_workers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    rows = query_db("SELECT * FROM users", fetch=True)
    # rows: id, username, password, role
    # ensure role column exists for backward compatibility - default 'worker' used on insertion
    # We'll display (id, username, role) by indexing
    workers = []
    for r in rows:
        # if role column missing (older DB) handle gracefully
        if len(r) >= 4:
            workers.append((r[0], r[1], r[2], r[3]))
        else:
            workers.append((r[0], r[1], r[2], 'worker'))
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
        flash("Error adding worker: " + str(e))
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
# Customers & Sales & Payments
# ----------------------
@app.route('/customers_page')
def customers_page():
    # accessible to both admin and workers
    rows = query_db("SELECT * FROM customers", fetch=True)
    return render_template_string(CUSTOMERS_TEMPLATE, customers=rows, role=session.get('role'), base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('customers_page'))
    name = (request.form.get('name') or "").strip()
    location = (request.form.get('location') or "").strip()
    driver = (request.form.get('driver') or "").strip()
    if not name:
        flash("Customer name required")
        return redirect(url_for('customers_page'))
    query_db("INSERT INTO customers (name, location, driver, balance) VALUES (?,?,?,?)", (name, location, driver, 0), commit=True)
    flash("Customer added")
    return redirect(url_for('customers_page'))

@app.route('/delete_customer/<int:cid>')
def delete_customer(cid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('customers_page'))
    query_db("DELETE FROM customers WHERE id=?", (cid,), commit=True)
    flash("Customer deleted")
    return redirect(url_for('customers_page'))

@app.route('/record_sale', methods=['POST'])
def record_sale():
    # workers and admin can record sales
    if session.get('role') not in ('admin', 'worker'):
        flash("Unauthorized")
        return redirect(url_for('index'))
    try:
        customer_id = int(request.form.get('customer_id'))
    except:
        flash("Select a customer")
        return redirect(url_for('customers_page'))
    try:
        total_cost = float(request.form.get('total_cost') or 0)
    except:
        flash("Invalid amount")
        return redirect(url_for('customers_page'))
    payment_method = (request.form.get('payment_method') or "").strip()
    mpesa_name = (request.form.get('mpesa_name') or "").strip() if payment_method == "Mpesa" else None
    status = 'Paid' if payment_method in ('Cash', 'Mpesa') else 'Credit'
    date = datetime.now().isoformat(timespec='seconds')
    query_db("INSERT INTO sales (customer_id, total_cost, payment_method, mpesa_name, status, date) VALUES (?,?,?,?,?,?)",
             (customer_id, total_cost, payment_method, mpesa_name, status, date), commit=True)
    if payment_method == 'Credit':
        query_db("UPDATE customers SET balance = COALESCE(balance,0) + ? WHERE id=?", (total_cost, customer_id), commit=True)
    flash("Sale recorded")
    return redirect(url_for('customers_page'))

@app.route('/sales_form', methods=['GET', 'POST'])
def sales_form():
    # dedicated sales page
    if session.get('role') not in ('admin', 'worker'):
        flash("Unauthorized")
        return redirect(url_for('index'))
    customers = query_db("SELECT id, name FROM customers", fetch=True)
    if request.method == 'POST':
        return record_sale()
    return render_template_string(SALES_TEMPLATE, customers=customers, base_css=BASE_CSS, navbar=NAVBAR_HTML)

@app.route('/record_payment', methods=['POST'])
def record_payment():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('customers_page'))
    try:
        customer_id = int(request.form.get('customer_id'))
        amount = float(request.form.get('amount') or 0)
    except:
        flash("Invalid data")
        return redirect(url_for('customers_page'))
    # subtract amount (but not negative)
    row = query_db("SELECT balance FROM customers WHERE id=?", (customer_id,), fetch=True)
    if not row:
        flash("Customer not found")
        return redirect(url_for('customers_page'))
    current = row[0][0] or 0
    newbal = current - amount
    if newbal < 0:
        newbal = 0.0
    query_db("UPDATE customers SET balance=? WHERE id=?", (newbal, customer_id), commit=True)
    # log payment as negative sale for traceability
    date = datetime.now().isoformat(timespec='seconds')
    query_db("INSERT INTO sales (customer_id, total_cost, payment_method, mpesa_name, status, date) VALUES (?,?,?,?,?,?)",
             (customer_id, -abs(amount), 'Payment', None, 'Paid', date), commit=True)
    flash("Payment recorded")
    return redirect(url_for('customers_page'))

# ----------------------
# Payments page (admin)
# ----------------------
@app.route('/payments_page')
def payments_page():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    customers = query_db("SELECT id, name, balance FROM customers", fetch=True)
    return render_template_string(CUSTOMERS_TEMPLATE, customers=customers, role='admin', base_css=BASE_CSS, navbar=NAVBAR_HTML)

# ----------------------
# Sales history (admin)
# ----------------------
@app.route('/sales_history')
def sales_history():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    rows = query_db("""
        SELECT s.id, c.name, s.total_cost, s.payment_method, s.mpesa_name, s.status, s.date
        FROM sales s LEFT JOIN customers c ON s.customer_id = c.id
        ORDER BY s.date DESC
    """, fetch=True)
    return render_template_string(SALES_HISTORY_TEMPLATE, rows=rows, base_css=BASE_CSS, navbar=NAVBAR_HTML)

# ----------------------
# Utility / run
# ----------------------
if __name__ == '__main__':
    # production: set debug=False
    app.run(host='0.0.0.0', port=5000, debug=False)

