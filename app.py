from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"   # required for sessions

DB_NAME = "wa_flora.db"

# ---------------------------- LOGIN ----------------------------
LOGIN_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Login - Wa Flora</title>
</head>
<body>
  <h2>Login to Wa Flora</h2>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <p style="color:red;">{{ messages[0] }}</p>
    {% endif %}
  {% endwith %}
  <form method="post">
    <label>Username:</label><br>
    <input type="text" name="username"><br><br>
    <label>Password:</label><br>
    <input type="password" name="password"><br><br>
    <button type="submit">Login</button>
  </form>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # ✅ Fixed username/password (no DB check)
        if username == "WaFlora" and password == "0725935410":
            session['user_id'] = 1
            session['role'] = 'admin'
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.before_request
def require_login():
    allowed_routes = ['login']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

# ---------------------------- MAIN PAGE ----------------------------
INDEX_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Wa Flora Products</title>
</head>
<body>
  <h2>Welcome, {{ username }} (Role: {{ role }})</h2>
  <a href="{{ url_for('logout') }}">Logout</a>
  <h3>Product List</h3>
  <form method="get" action="/">
    <input type="text" name="q" placeholder="Search by name or barcode" value="{{ q }}">
    <button type="submit">Search</button>
  </form>
  <table border="1" cellpadding="5">
    <tr>
      <th>ID</th>
      <th>Name</th>
      <th>Packing</th>
      <th>Retail Price</th>
      <th>Wholesale Price</th>
      <th>Barcode</th>
      <th>Action</th>
    </tr>
    {% for p in products %}
    <tr>
      <td>{{ p[0] }}</td>
      <td>{{ p[1] }}</td>
      <td>{{ p[2] }}</td>
      <td>{{ p[3] }}</td>
      <td>{{ p[4] }}</td>
      <td>{{ p[5] }}</td>
      <td>
        <a href="{{ url_for('delete_product', pid=p[0]) }}">Delete</a>
      </td>
    </tr>
    {% endfor %}
  </table>

  <h3>Add Product</h3>
  <form method="post" action="{{ url_for('add_product') }}">
    <input type="text" name="name" placeholder="Name" required>
    <input type="text" name="packing" placeholder="Packing" required>
    <input type="number" step="0.01" name="retail" placeholder="Retail Price" required>
    <input type="number" step="0.01" name="wholesale" placeholder="Wholesale Price" required>
    <input type="text" name="barcode" placeholder="Barcode">
    <button type="submit">Add</button>
  </form>
</body>
</html>
"""

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
    return render_template_string(INDEX_TEMPLATE, products=products, role=session['role'], q=q, username=session['username'])

@app.route('/add', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash("Only admin can add products")
        return redirect(url_for('index'))
    name = request.form['name']
    packing = request.form['packing']
    retail = request.form['retail']
    wholesale = request.form['wholesale']
    barcode = request.form['barcode']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO products (name, packing, retail_price, wholesale_price, barcode) VALUES (?,?,?,?,?)",
                  (name, packing, retail, wholesale, barcode))
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

# ---------------------------- INIT DB ----------------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            packing TEXT,
            retail_price REAL,
            wholesale_price REAL,
            barcode TEXT
        )
        """)
        conn.commit()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
