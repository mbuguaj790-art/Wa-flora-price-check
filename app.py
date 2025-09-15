from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this for production

DB_FILE = "waflora.db"

# ----------------------
# Database setup
# ----------------------
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            packing TEXT,
            retail_price REAL DEFAULT 0,
            wholesale_price REAL DEFAULT 0,
            barcode TEXT
        )
        """)
        c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """)
        # Create default admin
        admin_username = "Waflora"
        admin_password = "0725935410"
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (admin_username, generate_password_hash(admin_password), "admin"))
        conn.commit()
        conn.close()

def query_db(query, args=(), fetch=False, commit=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, args)
    if commit:
        conn.commit()
    result = c.fetchall() if fetch else None
    conn.close()
    return result

init_db()

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
input[type=text], input[type=number], input[type=password] { padding:5px; margin:2px; }
button { padding:5px 10px; margin:2px; }
</style>
"""

NAVBAR_HTML = """
<div class="navbar">
{% if session.get('role')=='admin' %}
<a href="{{ url_for('manage_products') }}">Manage Products</a>
<a href="{{ url_for('manage_workers') }}">Manage Workers</a> | 
{% endif %}
<a href="{{ url_for('index') }}">Products</a> | <a href="{{ url_for('logout') }}">Logout</a>
</div>
"""

LOGIN_TEMPLATE = BASE_CSS + """
<h2>Login</h2>
<form method="POST">
Username: <input type="text" name="username" required><br>
Password: <input type="password" name="password" required><br>
<button type="submit">Login</button>
</form>
{% for msg in get_flashed_messages() %}
<div class="flash">{{ msg }}</div>
{% endfor %}
"""

INDEX_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2>Product List</h2>
<form method="GET">
Search: <input type="text" name="q" value="{{ request.args.get('q','') }}">
<button type="submit">Go</button>
</form>
<table>
<tr><th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th></tr>
{% for p in products %}
{% if not request.args.get('q') or request.args.get('q').lower() in p[1].lower() %}
<tr>
<td>{{ p[1] }}</td>
<td>{{ p[2] }}</td>
<td>{{ p[3] }}</td>
<td>{{ p[4] }}</td>
<td>{{ p[5] }}</td>
</tr>
{% endif %}
{% endfor %}
</table>
"""

MANAGE_PRODUCTS_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2>Manage Products</h2>
<form method="POST" action="{{ url_for('add_product') }}">
Name: <input type="text" name="name" required>
Packing: <input type="text" name="packing">
Retail: <input type="number" step="0.01" name="retail">
Wholesale: <input type="number" step="0.01" name="wholesale">
Barcode: <input type="text" name="barcode">
<button type="submit">Add Product</button>
</form>

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
<a href="{{ url_for('delete_product', pid=p[0]) }}">Delete</a>
</td>
</tr>
{% endfor %}
</table>
{% for msg in get_flashed_messages() %}
<div class="flash">{{ msg }}</div>
{% endfor %}
"""

EDIT_PRODUCT_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2>Edit Product</h2>
<form method="POST">
Name: <input type="text" name="name" value="{{ p[1] }}" required>
Packing: <input type="text" name="packing" value="{{ p[2] }}">
Retail: <input type="number" step="0.01" name="retail" value="{{ p[3] }}">
Wholesale: <input type="number" step="0.01" name="wholesale" value="{{ p[4] }}">
Barcode: <input type="text" name="barcode" value="{{ p[5] }}">
<button type="submit">Update</button>
</form>
"""

MANAGE_WORKERS_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2>Manage Workers</h2>
<form method="POST" action="{{ url_for('add_worker') }}">
Username: <input type="text" name="username" required>
Password: <input type="password" name="password" required>
<button type="submit">Add Worker</button>
</form>
<table>
<tr><th>Username</th><th>Role</th><th>Actions</th></tr>
{% for w in workers %}
<tr>
<td>{{ w[1] }}</td>
<td>{{ w[3] }}</td>
<td><a href="{{ url_for('delete_worker', uid=w[0]) }}">Delete</a></td>
</tr>
{% endfor %}
</table>
{% for msg in get_flashed_messages() %}
<div class="flash">{{ msg }}</div>
{% endfor %}
"""

# ----------------------
# Authentication
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        row = query_db("SELECT id,password,role FROM users WHERE username=?", (username,), fetch=True)
        if row:
            uid, pw_hash, role = row[0]
            if check_password_hash(pw_hash, password):
                session['user_id'] = uid
                session['role'] = role
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
    q = request.args.get('q','').strip()
    products = query_db("SELECT * FROM products ORDER BY name ASC", fetch=True)
    return render_template_string(INDEX_TEMPLATE, products=products)

@app.route("/manage_products")
def manage_products():
    if session.get('role') != 'admin':
        flash("Admin only")
        return redirect(url_for('index'))
    products = query_db("SELECT * FROM products ORDER BY name ASC", fetch=True)
    return render_template_string(MANAGE_PRODUCTS_TEMPLATE, products=products)

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
        query_db(
            "INSERT INTO products (name,packing,retail_price,wholesale_price,barcode) VALUES (?,?,?,?,?)",
            (name, packing, retail, wholesale, barcode),
            commit=True
        )
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
    if request.method == "POST":
        name = (request.form.get('name') or "").strip()
        packing = (request.form.get('packing') or "").strip()
        retail = float(request.form.get('retail') or 0)
        wholesale = float(request.form.get('wholesale') or 0)
        barcode = (request.form.get('barcode') or "").strip()
        query_db(
            "UPDATE products SET name=?, packing=?, retail_price=?, wholesale_price=?, barcode=? WHERE id=?",
            (name, packing, retail, wholesale, barcode, pid),
            commit=True
        )
        flash("Product updated")
        return redirect(url_for('manage_products'))
    return render_template_string(EDIT_PRODUCT_TEMPLATE, p=p)

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
    return render_template_string(MANAGE_WORKERS_TEMPLATE, workers=workers)

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
# Run app
# ----------------------
if __name__=="__main__":
    app.run(debug=True)
