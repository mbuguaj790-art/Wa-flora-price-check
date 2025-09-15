from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_FILE = "app.db"

# ----------------------
# Database helpers
# ----------------------
def query_db(query, args=(), fetch=False, commit=False):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
        conn.close()
        return
    rows = cur.fetchall()
    conn.close()
    if fetch:
        return rows
    return None

# ----------------------
# Initialize DB
# ----------------------
def init_db():
    query_db("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        packing TEXT,
        retail_price REAL DEFAULT 0,
        wholesale_price REAL DEFAULT 0,
        barcode TEXT
    )""", commit=True)
    query_db("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )""", commit=True)
    # Add default admin if not exists
    row = query_db("SELECT * FROM users WHERE username='Waflora'", fetch=True)
    if not row:
        query_db("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                 ("Waflora", generate_password_hash("0725935410"), "admin"), commit=True)

# ----------------------
# Templates
# ----------------------
BASE_CSS = """
<style>
body { font-family: Arial; margin: 20px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { cursor: pointer; background-color: #f2f2f2; }
input { padding: 5px; margin: 5px; }
button { padding: 5px 10px; margin: 5px; }
.navbar { margin-bottom: 15px; }
.navbar a { margin-right: 10px; text-decoration: none; }
</style>
"""

NAVBAR_HTML = """
<div class='navbar'>
{% if session.get('role')=='admin' %}
<a href='/manage_products'>Products</a>
<a href='/manage_workers'>Workers</a>
{% elif session.get('role')=='worker' %}
<a href='/'>Products</a>
{% endif %}
<a href='/logout'>Logout</a>
</div>
"""

LOGIN_TEMPLATE = BASE_CSS + """
<h2 style='text-align:center;'>Login</h2>
<form method='POST' style='text-align:center;'>
<input type='text' name='username' placeholder='Username' required>
<input type='password' name='password' placeholder='Password' required>
<button type='submit'>Login</button>
</form>
{% with messages = get_flashed_messages() %}
{% if messages %}
<ul>
{% for m in messages %}<li>{{m}}</li>{% endfor %}
</ul>
{% endif %}
{% endwith %}
"""

INDEX_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2 style='text-align:center;'>Products</h2>
<input type='text' id='search' placeholder='Search products'>
<table id='productTable'>
<thead>
<tr>
<th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th>
</tr>
</thead>
<tbody>
{% for p in products %}
<tr>
<td>{{p[1]}}</td>
<td>{{p[2]}}</td>
<td>{{p[3]}}</td>
<td>{{p[4]}}</td>
<td>{{p[5]}}</td>
</tr>
{% endfor %}
</tbody>
</table>

<script>
document.getElementById('search').addEventListener('keyup', function(){
    let filter = this.value.toLowerCase();
    let rows = document.querySelectorAll('#productTable tbody tr');
    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
});
</script>
"""

MANAGE_PRODUCTS_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2 style='text-align:center;'>Manage Products</h2>
<div style='text-align:center; margin-bottom: 10px;'>
<form method='POST' action='/add_product'>
<input type='text' name='name' placeholder='Product Name' required>
<input type='text' name='packing' placeholder='Packing'>
<input type='number' step='any' name='retail' placeholder='Retail Price'>
<input type='number' step='any' name='wholesale' placeholder='Wholesale Price'>
<input type='text' name='barcode' placeholder='Barcode'>
<button type='submit'>Add Product</button>
</form>
</div>

<input type='text' id='search' placeholder='Search products'>
<table id='productTable'>
<thead>
<tr>
<th>Name</th><th>Packing</th><th>Retail</th><th>Wholesale</th><th>Barcode</th><th>Actions</th>
</tr>
</thead>
<tbody>
{% for p in products %}
<tr>
<td>{{p[1]}}</td><td>{{p[2]}}</td><td>{{p[3]}}</td><td>{{p[4]}}</td><td>{{p[5]}}</td>
<td>
<a href='/edit_product/{{p[0]}}'>Edit</a> |
<a href='/delete_product/{{p[0]}}'>Delete</a>
</td>
</tr>
{% endfor %}
</tbody>
</table>

<script>
document.getElementById('search').addEventListener('keyup', function(){
    let filter = this.value.toLowerCase();
    let rows = document.querySelectorAll('#productTable tbody tr');
    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
});
</script>
"""

MANAGE_WORKERS_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2 style='text-align:center;'>Manage Workers</h2>
<div style='text-align:center; margin-bottom:10px;'>
<form method='POST' action='/add_worker'>
<input type='text' name='username' placeholder='Username' required>
<input type='password' name='password' placeholder='Password' required>
<button type='submit'>Add Worker</button>
</form>
</div>
<table>
<thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Actions</th></tr></thead>
<tbody>
{% for w in workers %}
<tr>
<td>{{w[0]}}</td><td>{{w[1]}}</td><td>{{w[3]}}</td>
<td><a href='/delete_worker/{{w[0]}}'>Delete</a></td>
</tr>
{% endfor %}
</tbody>
</table>
"""

EDIT_PRODUCT_TEMPLATE = BASE_CSS + NAVBAR_HTML + """
<h2 style='text-align:center;'>Edit Product</h2>
<form method='POST' style='text-align:center;'>
<input type='text' name='name' value='{{p[1]}}' required>
<input type='text' name='packing' value='{{p[2]}}'>
<input type='number' step='any' name='retail' value='{{p[3]}}'>
<input type='number' step='any' name='wholesale' value='{{p[4]}}'>
<input type='text' name='barcode' value='{{p[5]}}'>
<button type='submit'>Update</button>
</form>
"""

# ----------------------
# Routes
# ----------------------
@app.before_request
def require_login():
    allowed = ['login','static']
    if request.endpoint not in allowed and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        # Check admin hardcoded
        row = query_db("SELECT id,password,role FROM users WHERE username=?", (username,), fetch=True)
        if row:
            uid,pw_hash,role = row[0]
            if check_password_hash(pw_hash,password):
                session['user_id']=uid
                session['role']=role
                session['username']=username
                return redirect(url_for('index'))
        flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------------
# Products
# ----------------------
@app.route("/")
def index():
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
    if session.get('role')!='admin':
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
    if session.get('role')!='admin':
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
    return render_template_string(EDIT_PRODUCT_TEMPLATE, p=p)

@app.route("/delete_product/<int:pid>")
def delete_product(pid):
    if session.get('role')!='admin':
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
    if session.get('role')!='admin':
        flash("Admin only")
        return redirect(url_for('index'))
    rows = query_db("SELECT * FROM users", fetch=True)
    workers = [(r[0], r[1], r[2], r[3] if len(r)>=4 else 'worker') for r in rows]
    return render_template_string(MANAGE_WORKERS_TEMPLATE, workers=workers)

@app.route("/add_worker", methods=["POST"])
def add_worker():
    if session.get('role')!='admin':
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
    if session.get('role')!='admin':
        flash("Admin only")
        return redirect(url_for('manage_workers'))
    query_db("DELETE FROM users WHERE id=?", (uid,), commit=True)
    flash("Worker deleted")
    return redirect(url_for('manage_workers'))

# ----------------------
# Run App
# ----------------------
if __name__=="__main__":
    init_db()
    app.run(debug=True)
