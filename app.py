import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session, flash

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_NAME = "wa_flora.db"

# ---------------------- DATABASE SETUP ----------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Products table
        c.execute("""CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        packing TEXT,
                        retail_price REAL,
                        wholesale_price REAL,
                        barcode TEXT
                    )""")
        # Workers table
        c.execute("""CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT
                    )""")
        # Customers table
        c.execute("""CREATE TABLE IF NOT EXISTS customers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        location TEXT,
                        driver TEXT,
                        balance REAL DEFAULT 0
                    )""")
        # Sales table
        c.execute("""CREATE TABLE IF NOT EXISTS sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER,
                        total_cost REAL,
                        payment_method TEXT,
                        mpesa_name TEXT,
                        status TEXT,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )""")
        conn.commit()

init_db()

# ---------------------- TEMPLATES ----------------------
LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Login - Wa Flora</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="container py-5">
  <h2 class="mb-4">Login to Wa Flora</h2>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="alert alert-danger">{{ messages[0] }}</div>
    {% endif %}
  {% endwith %}
  <form method="post">
    <div class="mb-3">
      <label class="form-label">Username</label>
      <input type="text" class="form-control" name="username" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Password</label>
      <input type="password" class="form-control" name="password" required>
    </div>
    <button type="submit" class="btn btn-primary">Login</button>
  </form>
</body>
</html>
"""

NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('index') }}">Wa Flora</a>
    <div class="d-flex">
      <span class="navbar-text text-white me-3">Logged in as: {{ session['username'] }} ({{ session['role'] }})</span>
      <a class="btn btn-outline-light" href="{{ url_for('logout') }}">Logout</a>
    </div>
  </div>
</nav>
"""

INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Wa Flora Products</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h2 class="mb-3">Product List</h2>
    <form method="get" class="mb-3">
      <input type="text" name="q" class="form-control" placeholder="Search by name or barcode" value="{{ q }}">
    </form>
    <table class="table table-striped">
      <tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th>
      {% if role == 'admin' %}<th>Actions</th>{% endif %}</tr>
      {% for p in products %}
        <tr>
          <td>{{ p[1] }}</td>
          <td>{{ p[2] }}</td>
          <td>{{ p[3] }}</td>
          <td>{{ p[4] }}</td>
          <td>{{ p[5] }}</td>
          {% if role == 'admin' %}
          <td>
            <a href="{{ url_for('edit_product', pid=p[0]) }}" class="btn btn-sm btn-warning">Edit</a>
            <a href="{{ url_for('delete_product', pid=p[0]) }}" class="btn btn-sm btn-danger">Delete</a>
          </td>
          {% endif %}
        </tr>
      {% endfor %}
    </table>
    {% if role == 'admin' %}
    <h4>Add Product</h4>
    <form method="post" action="{{ url_for('add_product') }}" class="row g-2">
      <div class="col"><input class="form-control" name="name" placeholder="Name"></div>
      <div class="col"><input class="form-control" name="packing" placeholder="Packing"></div>
      <div class="col"><input class="form-control" name="retail" placeholder="Retail"></div>
      <div class="col"><input class="form-control" name="wholesale" placeholder="Wholesale"></div>
      <div class="col"><input class="form-control" name="barcode" placeholder="Barcode"></div>
      <div class="col"><button class="btn btn-success">Add</button></div>
    </form>
    {% endif %}
    <hr>
    <a class="btn btn-primary" href="{{ url_for('customers') }}">Manage Customers</a>
    {% if role == 'admin' %}
      <a class="btn btn-secondary" href="{{ url_for('workers') }}">Manage Workers</a>
    {% endif %}
  </div>
</body>
</html>
"""

CUSTOMERS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Customers - Wa Flora</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h2>Customers</h2>
    <table class="table table-striped">
      <tr><th>Name</th><th>Location</th><th>Driver</th><th>Balance</th>
      {% if role == 'admin' %}<th>Actions</th>{% endif %}</tr>
      {% for c in customers %}
        <tr>
          <td {% if c[4] > 0 %}style="color:red;font-weight:bold"{% endif %}>{{ c[1] }}</td>
          <td>{{ c[2] }}</td>
          <td>{{ c[3] }}</td>
          <td>{{ c[4] }}</td>
          {% if role == 'admin' %}
          <td><a href="{{ url_for('delete_customer', cid=c[0]) }}" class="btn btn-sm btn-danger">Delete</a></td>
          {% endif %}
        </tr>
      {% endfor %}
    </table>
    {% if role == 'admin' %}
    <h4>Add Customer</h4>
    <form method="post" action="{{ url_for('add_customer') }}" class="row g-2">
      <div class="col"><input class="form-control" name="name" placeholder="Name"></div>
      <div class="col"><input class="form-control" name="location" placeholder="Location"></div>
      <div class="col"><input class="form-control" name="driver" placeholder="Driver"></div>
      <div class="col"><button class="btn btn-success">Add</button></div>
    </form>
    <hr>
    <h4>Record Payment</h4>
    <form method="post" action="{{ url_for('record_payment') }}" class="row g-2">
      <div class="col">
        <select name="customer_id" class="form-control">
          {% for c in customers %}
            <option value="{{ c[0] }}">{{ c[1] }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col"><input class="form-control" name="amount" placeholder="Amount"></div>
      <div class="col"><button class="btn btn-primary">Record Payment</button></div>
    </form>
    {% endif %}
    <hr>
    <h4>Record Sale</h4>
    <form method="post" action="{{ url_for('record_sale') }}" class="row g-2">
      <div class="col">
        <select name="customer_id" class="form-control">
          {% for c in customers %}
            <option value="{{ c[0] }}">{{ c[1] }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col"><input class="form-control" name="total_cost" placeholder="Total Cost"></div>
      <div class="col">
        <select name="payment_method" class="form-control">
          <option>Cash</option>
          <option>Mpesa</option>
          <option>Credit</option>
        </select>
      </div>
      <div class="col"><input class="form-control" name="mpesa_name" placeholder="Mpesa Name (if Mpesa)"></div>
      <div class="col"><button class="btn btn-success">Record Sale</button></div>
    </form>
  </div>
</body>
</html>
"""

WORKERS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Workers - Wa Flora</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    <h2>Workers</h2>
    <table class="table table-striped">
      <tr><th>Username</th><th>Actions</th></tr>
      {% for w in workers %}
        <tr>
          <td>{{ w[1] }}</td>
          <td><a href="{{ url_for('delete_worker', wid=w[0]) }}" class="btn btn-sm btn-danger">Delete</a></td>
        </tr>
      {% endfor %}
    </table>
    <h4>Add Worker</h4>
    <form method="post" action="{{ url_for('add_worker') }}" class="row g-2">
      <div class="col"><input class="form-control" name="username" placeholder="Username"></div>
      <div class="col"><input class="form-control" name="password" placeholder="Password"></div>
      <div class="col"><button class="btn btn-success">Add</button></div>
    </form>
  </div>
</body>
</html>
"""

# ---------------------- AUTH ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Fixed admin login
        if username == "WaFlora" and password == "0725935410":
            session['user_id'] = 0
            session['role'] = 'admin'
            session['username'] = username
            return redirect(url_for('index'))
        # Check worker login
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id,password FROM users WHERE username=?", (username,))
            u = c.fetchone()
        if u and password == u[1]:
            session['user_id'] = u[0]
            session['role'] = 'worker'
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
    allowed = ['login']
    if request.endpoint not in allowed and 'user_id' not in session:
        return redirect(url_for('login'))

# ---------------------- PRODUCTS ----------------------
@app.route('/')
def index():
    q = request.args.get('q','')
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if q:
            c.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{q}%", f"%{q}%"))
        else:
            c.execute("SELECT * FROM products")
        products = c.fetchall()
    return render_template_string(INDEX_TEMPLATE, products=products, role=session['role'], q=q, username=session['username'], navbar=NAVBAR)

@app.route('/add', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash("Only admin can add products")
        return redirect(url_for('index'))
    data = (request.form['name'], request.form['packing'], request.form['retail'], request.form['wholesale'], request.form['barcode'])
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO products (name,packing,retail_price,wholesale_price,barcode) VALUES (?,?,?,?,?)", data)
        conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Only admin can delete products")
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:pid>', methods=['GET','POST'])
def edit_product(pid):
    if session.get('role') != 'admin':
        flash("Only admin can edit products")
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            data = (request.form['name'], request.form['packing'], request.form['retail'], request.form['wholesale'], request.form['barcode'], pid)
            c.execute("UPDATE products SET name=?,packing=?,retail_price=?,wholesale_price=?,barcode=? WHERE id=?", data)
            conn.commit()
            return redirect(url_for('index'))
        c.execute("SELECT * FROM products WHERE id=?", (pid,))
        p = c.fetchone()
    return f"""
    <html><body class='container'>
    <h3>Edit Product</h3>
    <form method="post">
      Name: <input name="name" value="{p[1]}"><br>
      Packing: <input name="packing" value="{p[2]}"><br>
      Retail: <input name="retail" value="{p[3]}"><br>
      Wholesale: <input name="wholesale" value="{p[4]}"><br>
      Barcode: <input name="barcode" value="{p[5]}"><br>
      <button>Save</button>
    </form></body></html>
    """

# ---------------------- CUSTOMERS ----------------------
@app.route('/customers')
def customers():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM customers")
        customers = c.fetchall()
    return render_template_string(CUSTOMERS_TEMPLATE, customers=customers, role=session['role'], navbar=NAVBAR)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    if session.get('role') != 'admin':
        flash("Only admin can add customers")
        return redirect(url_for('customers'))
    data = (request.form['name'], request.form['location'], request.form['driver'])
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO customers (name,location,driver) VALUES (?,?,?)", data)
        conn.commit()
    return redirect(url_for('customers'))

@app.route('/delete_customer/<int:cid>')
def delete_customer(cid):
    if session.get('role') != 'admin':
        flash("Only admin can delete customers")
        return redirect(url_for('customers'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM customers WHERE id=?", (cid,))
        conn.commit()
    return redirect(url_for('customers'))

@app.route('/record_sale', methods=['POST'])
def record_sale():
    customer_id = request.form['customer_id']
    total_cost = float(request.form['total_cost'])
    method = request.form['payment_method']
    mpesa_name = request.form['mpesa_name']
    status = "Paid" if method != "Credit" else "Credit"
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sales (customer_id,total_cost,payment_method,mpesa_name,status) VALUES (?,?,?,?,?)",
                  (customer_id, total_cost, method, mpesa_name, status))
        if method == "Credit":
            c.execute("UPDATE customers SET balance=balance+? WHERE id=?", (total_cost, customer_id))
        conn.commit()
    return redirect(url_for('customers'))

@app.route('/record_payment', methods=['POST'])
def record_payment():
    if session.get('role') != 'admin':
        flash("Only admin can record payments")
        return redirect(url_for('customers'))
    cid = request.form['customer_id']
    amount = float(request.form['amount'])
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE customers SET balance=balance-? WHERE id=?", (amount, cid))
        conn.commit()
    return redirect(url_for('customers'))

# ---------------------- WORKERS ----------------------
@app.route('/workers')
def workers():
    if session.get('role') != 'admin':
        flash("Only admin can manage workers")
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        workers = c.fetchall()
    return render_template_string(WORKERS_TEMPLATE, workers=workers, navbar=NAVBAR)

@app.route('/add_worker', methods=['POST'])
def add_worker():
    if session.get('role') != 'admin':
        flash("Only admin can add workers")
        return redirect(url_for('workers'))
    data = (request.form['username'], request.form['password'])
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username,password) VALUES (?,?)", data)
            conn.commit()
        except:
            flash("Worker already exists")
    return redirect(url_for('workers'))

# ---------------------------- PRODUCT DELETE ----------------------------
@app.route('/delete/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Only admin can delete products")
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
    flash("Product deleted")
    return redirect(url_for('index'))

# ---------------------------- CUSTOMERS ----------------------------
@app.route('/customers')
def customers():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM customers")
        customers = c.fetchall()
    return render_template_string(CUSTOMERS_TEMPLATE, customers=customers, role=session['role'], username=session['username'])

@app.route('/customers/add', methods=['POST'])
def add_customer():
    if session.get('role') != 'admin':
        flash("Only admin can add customers")
        return redirect(url_for('customers'))
    name = request.form['name']
    location = request.form['location']
    driver = request.form['driver']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO customers (name, location, driver, balance) VALUES (?,?,?,0)", (name, location, driver))
        conn.commit()
    flash("Customer added")
    return redirect(url_for('customers'))

@app.route('/customers/delete/<int:cid>')
def delete_customer(cid):
    if session.get('role') != 'admin':
        flash("Only admin can delete customers")
        return redirect(url_for('customers'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM customers WHERE id=?", (cid,))
        conn.commit()
    flash("Customer deleted")
    return redirect(url_for('customers'))

# ---------------------------- SALES ----------------------------
@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM customers")
        customers = c.fetchall()
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        total = float(request.form['total'])
        method = request.form['method']
        mpesa_name = request.form.get('mpesa_name', '')

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_id, total, method, mpesa_name) VALUES (?,?,?,?)",
                      (customer_id, total, method, mpesa_name))
            # Update customer balance if credit
            if method == "Credit":
                c.execute("UPDATE customers SET balance = balance + ? WHERE id=?", (total, customer_id))
            conn.commit()
        flash("Sale recorded")
        return redirect(url_for('sales'))

    return render_template_string(SALES_TEMPLATE, customers=customers, role=session['role'], username=session['username'])

# ---------------------------- PAYMENTS ----------------------------
@app.route('/payments', methods=['POST'])
def payments():
    if session.get('role') != 'admin':
        flash("Only admin can record payments")
        return redirect(url_for('customers'))
    customer_id = request.form['customer_id']
    amount = float(request.form['amount'])
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE customers SET balance = balance - ? WHERE id=?", (amount, customer_id))
        conn.commit()
    flash("Payment recorded")
    return redirect(url_for('customers'))

# ---------------------------- RUN APP ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
