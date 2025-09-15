from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ----------------------
# Templates
# ----------------------

BASE_CSS = """
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background-color: #f2f2f2; }
.flash { color: red; }
.navbar { margin-bottom: 15px; }
.navbar a { margin-right: 10px; }
</style>
"""

NAVBAR_HTML = """
<div class="navbar">
  {% if session.get('role')=='admin' %}
    <a href="{{ url_for('manage_products') }}">Manage Products</a>
    <a href="{{ url_for('manage_workers') }}">Manage Workers</a> |
  {% endif %}
  <a href="{{ url_for('index') }}">Products</a> |
  <a href="{{ url_for('logout') }}">Logout</a>
</div>
"""

LOGIN_TEMPLATE = """
{{ base_css }}
<h2>Login</h2>
{% for message in get_flashed_messages() %}
  <div class="flash">{{ message }}</div>
{% endfor %}
<form method="post">
  Username: <input type="text" name="username"><br><br>
  Password: <input type="password" name="password"><br><br>
  <input type="submit" value="Login">
</form>
"""

INDEX_TEMPLATE = """
{{ base_css }}
{{ navbar }}
<h2>Product List</h2>
<form method="get" action="{{ url_for('index') }}">
Search: <input type="text" name="q" value="{{ request.args.get('q','') }}">
<input type="submit" value="Go">
</form>
<table>
  <tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th></tr>
  {% for p in products %}
    <tr>
      <td>{{ p[1] }}</td>
      <td>{{ p[2] }}</td>
      <td>{{ p[3] }}</td>
      <td>{{ p[4] }}</td>
      <td>{{ p[5] }}</td>
    </tr>
  {% endfor %}
</table>
"""

MANAGE_PRODUCTS_TEMPLATE = """
{{ base_css }}
{{ navbar }}
<h2>Manage Products</h2>
{% for message in get_flashed_messages() %}
  <div class="flash">{{ message }}</div>
{% endfor %}
<h3>Add Product</h3>
<form method="post" action="{{ url_for('add_product') }}">
  Name: <input type="text" name="name"> 
  Packing: <input type="text" name="packing"> 
  Retail: <input type="number" step="0.01" name="retail"> 
  Wholesale: <input type="number" step="0.01" name="wholesale"> 
  Barcode: <input type="text" name="barcode">
  <input type="submit" value="Add">
</form>

<h3>Existing Products</h3>
<table>
<tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th><th>Actions</th></tr>
{% for p in products %}
<tr>
<td>{{ p[1] }}</td>
<td>{{ p[2] }}</td>
<td>{{ p[3] }}</td>
<td>{{ p[4] }}</td>
<td>{{ p[5] }}</td>
<td>
  <a href="{{ url_for('edit_product', pid=p[0]) }}">Edit</a> | 
  <a href="{{ url_for('delete_product', pid=p[0]) }}" onclick="return confirm('Delete?')">Delete</a>
</td>
</tr>
{% endfor %}
</table>
"""

EDIT_PRODUCT_TEMPLATE = """
{{ base_css }}
{{ navbar }}
<h2>Edit Product</h2>
<form method="post">
  Name: <input type="text" name="name" value="{{ p[1] }}"> 
  Packing: <input type="text" name="packing" value="{{ p[2] }}"> 
  Retail: <input type="number" step="0.01" name="retail" value="{{ p[3] }}"> 
  Wholesale: <input type="number" step="0.01" name="wholesale" value="{{ p[4] }}"> 
  Barcode: <input type="text" name="barcode" value="{{ p[5] }}">
  <input type="submit" value="Update">
</form>
"""

MANAGE_WORKERS_TEMPLATE = """
{{ base_css }}
{{ navbar }}
<h2>Manage Workers</h2>
{% for message in get_flashed_messages() %}
  <div class="flash">{{ message }}</div>
{% endfor %}
<h3>Add Worker</h3>
<form method="post" action="{{ url_for('add_worker') }}">
  Username: <input type="text" name="username">
  Password: <input type="password" name="password">
  <input type="submit" value="Add Worker">
</form>

<h3>Existing Workers</h3>
<table>
<tr><th>ID</th><th>Username</th><th>Role</th><th>Actions</th></tr>
{% for w in workers %}
<tr>
<td>{{ w[0] }}</td>
<td>{{ w[1] }}</td>
<td>{{ w[2] }}</td>
<td>
  <a href="{{ url_for('delete_worker', uid=w[0]) }}" onclick="return confirm('Delete?')">Delete</a>
</td>
</tr>
{% endfor %}
</table>
"""

# ----------------------
# Database helper
# ----------------------
def query_db(query, args=(), fetch=False, commit=False):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute(query, args)
    if commit:
        conn.commit()
    result = c.fetchall() if fetch else None
    conn.close()
    return result

# Initialize tables
def init_db():
    query_db("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        packing TEXT,
        retail_price REAL,
        wholesale_price REAL,
        barcode TEXT
    )""", commit=True)
    query_db("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""", commit=True)
init_db()

# ----------------------
# Routes
# ----------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        # Hardcoded admin
        if username=="Waflora" and password=="0725935410":
            session['user_id'] = 0
            session['role'] = 'admin'
            session['username'] = "Waflora"
            return redirect(url_for('index'))
        # Worker check
        row = query_db("SELECT id,password,role FROM users WHERE username=?", (username,), fetch=True)
        if row:
            uid, pw_hash, role = row[0]
            if check_password_hash(pw_hash, password):
                session['user_id'] = uid
                session['role'] = role
                session['username'] = username
                return redirect(url_for('index'))
        flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE, base_css=BASE_CSS)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.before_request
def require_login():
    allowed = ['login','static']
    if request.endpoint not in allowed and 'user_id' not in session:
        return redirect(url_for('login'))

# ----------------------
# Products
# ----------------------
@app.route("/")
def index():
    q = request.args.get('q','').strip()
    if q:
        products = query_db("SELECT * FROM products WHERE name LIKE ? ORDER BY name ASC", ('%'+q+'%',), fetch=True)
    else:
        products = query_db("SELECT * FROM products ORDER BY name ASC", fetch=True)
    return render_template_string(INDEX_TEMPLATE, products=products, navbar=NAVBAR_HTML, base_css=BASE_CSS)

@app.route("/manage_products")
def manage_products():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    products = query_db("SELECT * FROM products ORDER BY name ASC", fetch=True)
    return render_template_string(MANAGE_PRODUCTS_TEMPLATE, products=products, navbar=NAVBAR_HTML, base_css=BASE_CSS)

@app.route("/add_product", methods=["POST"])
def add_product():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    name = (request.form.get('name') or "").strip()
    packing = (request.form.get('packing') or "").strip()
    retail = request.form.get('retail') or 0
    wholesale = request.form.get('wholesale') or 0
    barcode = (request.form.get('barcode') or "").strip()
    if name:
        query_db("INSERT INTO products (name,packing,retail_price,wholesale_price,barcode) VALUES (?,?,?,?,?)",
                 (name, packing, retail, wholesale, barcode), commit=True)
        flash("Product added")
    return redirect(url_for('manage_products'))

@app.route("/edit_product/<int:pid>", methods=["GET","POST"])
def edit_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    p = query_db("SELECT * FROM products WHERE id=?", (pid,), fetch=True)
    if not p:
        flash("Product not found")
        return redirect(url_for('manage_products'))
    p = p[0]
    if request.method=="POST":
        name = (request.form.get('name') or "").strip()
        packing = (request.form.get('packing') or "").strip()
        retail = request.form.get('retail') or 0
        wholesale = request.form.get('wholesale') or 0
        barcode = (request.form.get('barcode') or "").strip()
        query_db("UPDATE products SET name=?, packing=?, retail_price=?, wholesale_price=?, barcode=? WHERE id=?",
                 (name, packing, retail, wholesale, barcode, pid), commit=True)
        flash("Product updated")
        return redirect(url_for('manage_products'))
    return render_template_string(EDIT_PRODUCT_TEMPLATE, p=p, navbar=NAVBAR_HTML, base_css=BASE_CSS)

@app.route("/delete_product/<int:pid>")
def delete_product(pid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    query_db("DELETE FROM products WHERE id=?", (pid,), commit=True)
    flash("Product deleted")
    return redirect(url_for('manage_products'))

# ----------------------
# Workers
# ----------------------
@app.route("/manage_workers")
def manage_workers():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    rows = query_db("SELECT * FROM users", fetch=True)
    workers = [(r[0], r[1], r[2], r[3] if len(r)>=4 else 'worker') for r in rows]
    return render_template_string(MANAGE_WORKERS_TEMPLATE, workers=workers, navbar=NAVBAR_HTML, base_css=BASE_CSS)

@app.route("/add_worker", methods=["POST"])
def add_worker():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('manage_workers'))
    username = (request.form.get('username') or "").strip()
    password = (request.form.get('password') or "").strip()
    if not username or not password:
        flash("Username & password required")
        return redirect(url_for('manage_workers'))
    pw_hash = generate_password_hash(password)
    try:
        query_db("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                 (username, pw_hash, 'worker'), commit=True)
        flash("Worker added")
    except sqlite3.IntegrityError:
        flash("Username already exists")
    return redirect(url_for('manage_workers'))

@app.route("/delete_worker/<int:uid>")
def delete_worker(uid):
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('manage_workers'))
    query_db("DELETE FROM users WHERE id=?", (uid,), commit=True)
    flash("Worker deleted")
    return redirect(url_for('manage_workers'))

# ----------------------
# Run App
# ----------------------
if __name__=="__main__":
    app.run(debug=True)
