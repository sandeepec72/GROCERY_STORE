from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_restful import Api, Resource, reqparse
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
api = Api(app)
app.secret_key = 'your_secret_key'
DB = 'database.db'

fixed_manager_username = 'manager'
fixed_manager_password = 'manager_password'

@app.route('/')
def index():
    return render_template('login.html')

def create_database():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            user_type TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            expiry_date TEXT,
            rate_per_unit REAL,
            quantity_available INTEGER,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchased_items (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            total_cost REAL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (item_id) REFERENCES items (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cart (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (item_id) REFERENCES items (id)
        )
    ''')

    conn.commit()
    conn.close()
create_database()



@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None  # Initialize error as None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error = "Passwords do not match"  # Set error message
        else:
            hashed_password = generate_password_hash(password, method='sha256')

            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)',
                           (username, hashed_password, 'regular'))
            conn.commit()
            conn.close()

            return redirect(url_for('login'))

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        if username == fixed_manager_username and password == fixed_manager_password:
            session['manager_logged_in'] = True
            return redirect(url_for('manager_dashboard'))

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect(url_for('user_dashboard'))
        else:
            error = "Invalid username or password"  # Set error message
    else:
        error = "User not found"  # Set error message

    return render_template('login.html')


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' in session:
        return render_template('user_dashboard.html')
    else:
        return redirect(url_for('login'))


@app.route('/manager_dashboard')
def manager_dashboard():
    if 'manager_logged_in' in session and session['manager_logged_in']:
        return render_template('manager_dashboard.html')
    else:
        return redirect(url_for('login'))


# View categories
@app.route('/view_categories')
def view_categories():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return render_template('view_categories.html', categories=categories)

# Add category
@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form['category_name']
        if category_name:
            conn = sqlite3.connect(DB)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
            conn.commit()
            conn.close()
            return redirect(url_for('view_categories'))
    return render_template('add_category.html')

# Delete category
@app.route('/delete_category/<int:category_id>', methods=['GET', 'POST'])
def delete_category(category_id):
    if request.method == 'POST':
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('view_categories'))
    return render_template('delete_category.html', category_id=category_id)


@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        item_name = request.form['item_name']
        expiry_date = request.form['expiry_date']
        rate_per_unit = request.form['rate_per_unit']
        quantity_available = request.form['quantity_available']
        category_id = request.form['category_id']

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        # Check if an item with the same name and expiry date exists
        cursor.execute('SELECT * FROM items WHERE name = ? AND expiry_date = ?', (item_name, expiry_date))
        existing_item_expiry = cursor.fetchone()

        if existing_item_expiry:
            # Item with the same name and expiry date exists, update its rate and quantity_available
            updated_rate = rate_per_unit
            updated_quantity_available = existing_item_expiry[4] + int(quantity_available)
            cursor.execute('UPDATE items SET rate_per_unit = ?, quantity_available = ? WHERE id = ?', (updated_rate, updated_quantity_available, existing_item_expiry[0]))
        else:
            # Item with the same name doesn't exist or has a different expiry date, insert it as a new item
            cursor.execute('''
                INSERT INTO items (name, expiry_date, rate_per_unit, quantity_available, category_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_name, expiry_date, rate_per_unit, quantity_available, category_id))

        conn.commit()
        conn.close()
        return redirect(url_for('view_items'))

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    conn.close()

    return render_template('add_item.html', categories=categories)



@app.route('/view_items')
def view_items():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()
    return render_template('view_items.html', items=items)


@app.route('/delete_item/<int:item_id>', methods=['GET', 'POST'])
def delete_item(item_id):
    if request.method == 'POST':
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('view_items'))

    return render_template('delete_item.html', item_id=item_id)


@app.route('/view_categories_user')
def view_categories_user():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return render_template('view_categories_user.html', categories=categories)

@app.route('/view_items_user')
def view_items_user():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()
    return render_template('view_items_user.html', items=items)


# ... (previous code)

@app.route('/purchase_item/<int:item_id>', methods=['GET', 'POST'])
def purchase_item(item_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
    item = cursor.fetchone()

    if request.method == 'POST':
        user_id = session['user_id']
        quantity_to_purchase = 1

        if item[4] < quantity_to_purchase:
            conn.close()
            return "Item is out of stock."

        total_cost = item[3] * quantity_to_purchase

        # Insert the purchased item into the purchased_items table
        cursor.execute('INSERT INTO purchased_items (user_id, item_id, quantity, total_cost) VALUES (?, ?, ?, ?)',
                       (user_id, item_id, quantity_to_purchase, total_cost))

        # Insert the purchased item into the user's cart
        cursor.execute('INSERT INTO user_cart (user_id, item_id, quantity) VALUES (?, ?, ?)',
                       (user_id, item_id, quantity_to_purchase))

        # Update the quantity_available for the item in the items table
        updated_quantity_available = item[4] - quantity_to_purchase
        cursor.execute('UPDATE items SET quantity_available = ? WHERE id = ?', (updated_quantity_available, item_id))

        conn.commit()
        conn.close()

        return redirect(url_for('view_items_user'))

    conn.close()
    return render_template('purchase_item.html', item=item)



@app.route('/user_cart')
def user_cart():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT items.id, items.name, items.expiry_date, items.rate_per_unit, SUM(user_cart.quantity) as total_quantity, items.rate_per_unit * SUM(user_cart.quantity) as item_total_cost
            FROM user_cart
            JOIN items ON user_cart.item_id = items.id
            WHERE user_cart.user_id = ?
            GROUP BY items.id, items.name, items.expiry_date, items.rate_per_unit
        ''', (user_id,))

        cart_items = cursor.fetchall()

        # Calculate the total cost for the user's purchases
        total_cost = sum(item[5] for item in cart_items)

        conn.close()

        return render_template('user_cart.html', cart_items=cart_items, total_cost=total_cost)
    else:
        return redirect(url_for('login'))

# API Resources

class CategoryResource(Resource):
    def get(self):
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories')
        categories = cursor.fetchall()
        conn.close()
        return jsonify(categories)

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Category name is required')
        args = parser.parse_args()

        category_name = args['name']

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
        conn.commit()
        conn.close()
        return {'message': 'Category added successfully'}, 201

class ItemResource(Resource):
    def get(self):
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM items')
        items = cursor.fetchall()
        conn.close()
        return jsonify(items)

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Item name is required')
        parser.add_argument('expiry_date', type=str)
        parser.add_argument('rate_per_unit', type=float)
        parser.add_argument('quantity_available', type=int)
        parser.add_argument('category_id', type=int, required=True, help='Category ID is required')
        args = parser.parse_args()

        item_name = args['name']
        expiry_date = args['expiry_date']
        rate_per_unit = args['rate_per_unit']
        quantity_available = args['quantity_available']
        category_id = args['category_id']

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        # Check if an item with the same name and expiry date exists
        cursor.execute('SELECT * FROM items WHERE name = ? AND expiry_date = ?', (item_name, expiry_date))
        existing_item_expiry = cursor.fetchone()

        if existing_item_expiry:
            # Item with the same name and expiry date exists, update its rate and quantity_available
            updated_rate = rate_per_unit
            updated_quantity_available = existing_item_expiry[4] + int(quantity_available)
            cursor.execute('UPDATE items SET rate_per_unit = ?, quantity_available = ? WHERE id = ?', (updated_rate, updated_quantity_available, existing_item_expiry[0]))
        else:
            # Item with the same name doesn't exist or has a different expiry date, insert it as a new item
            cursor.execute('''
                INSERT INTO items (name, expiry_date, rate_per_unit, quantity_available, category_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_name, expiry_date, rate_per_unit, quantity_available, category_id))

        conn.commit()
        conn.close()
        return {'message': 'Item added successfully'}, 201

api.add_resource(CategoryResource, '/api/categories')
api.add_resource(ItemResource, '/api/items')


if __name__ == '__main__':
    create_database()
    app.run(debug=True)
