from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change if you like

DB_NAME = "store.db"

# ---------------------------- INIT DB ----------------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Create products table if it doesn't exist
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
        conn.commit()

init_db()

# ---------------------------- LOGIN TEMPLATE ----------------------------
LOGIN_TEMPLATE = """
<!doctype html>
<html>
<head><title>Login</title></head>
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

# ---------------------------- INDEX TEMPLATE ----------------------------
INDEX_TEMPLATE = """
<!doctype html>
<html>
<head><title>Wa Flora Products</title></head>
<body>
  <h2>Welcome {{ username }}</h2>
  <form method="get" action="/">
    <input type="text" name="q" value="{{ q }}" placeholder="Search products...">
    <button type="submit">Search</button>
  </form>

  <h3>Products</h3>
  <table border="1" cellpadding="5">
    <tr>
      <th>ID</th><th>Name</th><th>Packing</th>
      <th>Retail Price</th><th>Wholesale Price</th>
      <th>Barcode</th><th>Actions</th>
    </tr>
    {% for p in products %}
    <tr>
      <td>{{ p[0] }}</td>
      <td>{{ p[1] }}</td>
      <td>{{ p[2] }}</td>
      <td>{{ p[3] }}</td>
      <td>{{ p[4] }}</td>
      <td>{{ p[5] }}</td>
      <td><a href="/delete/{{ p[0] }}">Delete</a></td>
    </tr>
    {% endfor %}
  </table>

  <h3>Add Product</h3>
  <form method="post" action="/add">
    <label>Name:</label><br><input type="text" name="name"><br>
    <label>Packing:</label><br><input type="text" name="packing"><br>
    <label>Retail Price:</label><br><input type="number" step="0.01" name="retail"><br>
    <label>Wholesale Price:</label><br><input type="number" step="0.01" name="wholesale"><br>
    <label>Barcode:</label><br><input type="text" name="barcode"><br><br>
    <button type="submit">Add</button>
  </form>

  <p><a href="/logout">Logout</a></p>
</body>
</html>
"""

# ---------------------------- ROUTES ----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # ✅ Fixed credentials
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

# ---------------------------- MAIN ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
