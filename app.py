from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_PATH = "app.db"

# ----------------------
# Database helpers
# ----------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), fetch=False, commit=False):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
        conn.close()
        return
    if fetch:
        rows = cur.fetchall()
        conn.close()
        return [tuple(r) for r in rows]
    conn.close()
    return

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # products table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        packing TEXT,
        retail_price REAL,
        wholesale_price REAL,
        barcode TEXT
    )
    """)
    # users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------------
# Templates
# ----------------------
NAVBAR_HTML = """
<nav>
  {% if session.get('role')=='admin' %}
    <a href="{{url_for('manage_products')}}">Manage Products</a> |
    <a href="{{url_for('manage_workers')}}">Manage Workers</a> |
  {% endif %}
  <a href="{{url_for('index')}}">Products</a> |
  <a href="{{url_for('logout')}}">Logout</a>
</nav>
<hr>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Products</title></head>
<body>
{{ navbar|safe }}
<h2>Products</h2>
<form method="GET">
Search: <input name="q" value="{{request.args.get('q','')}}">
<button>Go</button>
</form>
<table border="1">
<tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th></tr>
{% for p in products or [] %}
{% if not request.args.get('q') or request.args.get('q').lower() in p[1].lower() %}
<tr>
<td>{{p[1]}}</td><td>{{p[2]}}</td><td>{{p[3]}}</td><td>{{p[4]}}</td><td>{{p[5]}}</td>
</tr>
{% endif %}
{% endfor %}
</table>
</body>
</html>
"""

MANAGE_PRODUCTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Manage Products</title></head>
<body>
{{ navbar|safe }}
<h2>Manage Products</h2>
<form method="POST" action="{{ url_for('add_product') }}">
<input name="name" placeholder="Product Name" required>
<input name="packing" placeholder="Packing">
<input name="retail" placeholder="Retail Price">
<input name="wholesale" placeholder="Wholesale Price">
<input name="barcode" placeholder="Barcode">
<button>Add Product</button>
</form>
<table border="1">
<tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th><th>Actions</th></tr>
{% for p in products or [] %}
<tr>
<td>{{p[1]}}</td><td>{{p[2]}}</td><td>{{p[3]}}</td><td>{{p[4]}}</td><td>{{p[5]}}</td>
<td>
<a href="{{url_for('edit_product', pid=p[0])}}">Edit</a> |
<a href="{{url_for('delete_product', pid=p[0])}}">Delete</a>
</td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

MANAGE_WORKERS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Manage Workers</title></head>
<body>
{{ navbar|safe }}
<h2>Manage Workers</h2>
<form method="POST" action="{{ url_for('add_worker') }}">
<input name="username" placeholder="Username" required>
<input name="password" placeholder="Password" required>
<button>Add Worker</button>
</form>
<table border="1">
<tr><th>Username</th><th>Role</th><th>Actions</th></tr>
{% for w in workers %}
<tr>
<td>{{w[1]}}</td><td>{{w[3]}}</td>
<td><a href="{{ url_for('delete_worker', uid=w[0]) }}">Delete</a></td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

EDIT_PRODUCT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Edit Product</title></head>
<body>
{{ navbar|safe }}
<h2>Edit Product</h2>
<form method="POST">
<input name="name" value="{{p[1]}}" required>
<input name="packing" value="{{p[2]}}">
<input name="retail" value="{{p[3]}}">
<input name="wholesale" value="{{p[4]}}">
<input name="barcode" value="{{p[5]}}">
<button>Update</button>
</form>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
<h2>Login</h2>
<form method="POST">
<input name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button>Login</button>
</form>
{% with messages = get_flashed_messages() %}
{% if messages %}
<ul>{% for m in messages %}<li>{{m}}</li>{% endfor %}</ul>
{% endif %}
{% endwith %}
</body>
</html>
"""

# ----------------------
# Login & Logout
# ----------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        # hardcoded admin
        if username=="Waflora" and password=="0725935410":
            session['user_id']=0
            session['role']='admin'
            session['username']="Waflora"
            return redirect(url_for('index'))
        # worker login
        row = query_db("SELECT id,password,role FROM users WHERE username=?", (username,), fetch=True)
        if row and check_password_hash(row[0][1], password):
            session['user_id'] = row[0][0]
            session['role'] = row[0][2]
            session['username'] = username
            return redirect(url_for('index'))
        flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE)

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
    q = (request.args.get("q") or "").strip()
    products = query_db("SELECT * FROM products ORDER BY name ASC", fetch=True) or []
    return render_template_string(INDEX_TEMPLATE, products=products, navbar=NAVBAR_HTML, request=request)

@app.route("/manage_products")
def manage_products():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    products = query_db("SELECT * FROM products ORDER BY name ASC", fetch=True) or []
    return render_template_string(MANAGE_PRODUCTS_TEMPLATE, products=products, navbar=NAVBAR_HTML)

@app.route("/add_product", methods=["POST"])
def add_product():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    name = (request.form.get('name') or "").strip()
    packing = (request.form.get('packing') or "").strip()
    retail = float(request.form.get('retail') or 0)
    wholesale = float(request.form.get('wholesale') or 0)
    barcode = (request.form.get('barcode') or "").strip()
    if name:
        query_db("INSERT INTO products (name,packing,retail_price,wholesale_price,barcode) VALUES (?,?,?,?,?)",
                 (name,packing,retail,wholesale,barcode), commit=True)
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
        retail = float(request.form.get('retail') or 0)
        wholesale = float(request.form.get('wholesale') or 0)
        barcode = (request.form.get('barcode') or "").strip()
        query_db("UPDATE products SET name=?,packing=?,retail_price=?,wholesale_price=?,barcode=? WHERE id=?",
                 (name,packing,retail,wholesale,barcode,pid), commit=True)
        flash("Product updated")
        return redirect(url_for('manage_products'))
    return render_template_string(EDIT_PRODUCT_TEMPLATE, p=p, navbar=NAVBAR_HTML)

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
    rows = query_db("SELECT * FROM users", fetch=True) or []
    workers = [(r[0], r[1], r[2], r[2]) for r in rows]
    return render_template_string(MANAGE_WORKERS_TEMPLATE, workers=workers, navbar=NAVBAR_HTML)

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
        query_db("INSERT INTO users (username,password,role) VALUES (?,?,?)", (username,pw_hash,'worker'), commit=True)
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
