from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask_migrate import Migrate
from models import User, Dish, Order, Review, db
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db?timeout=10'  # Set timeout to 10 seconds
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'pizzapastawebtemplate\\static\\uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
os.chmod(upload_folder, 0o777)  # Set permissions to read/write for all user

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure tables are created
@app.before_request
def create_tables_and_users():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        User.create_default_users()

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id
            session['user_role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin'))
            elif user.role == 'operator':
                return redirect(url_for('operator'))
            elif user.role == 'customer':
                return redirect(url_for('customer'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

# Index route
@app.route('/')
def index():
    return render_template('index.html')

# About route
@app.route('/about')
def about():
    return render_template('about.html')

# Menu route
@app.route('/menu')
def menu():
    return render_template('menu.html')

# Admin route
@app.route('/admin')
@login_required
def admin():
    if current_user.role == 'admin':
        return render_template('admin.html')
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

# Add dish route
@app.route('/admin/add_dish', methods=['POST'])
@login_required
def admin_add_dish():
    if request.method == 'POST':
        dish_name = request.form['dish_name']
        description = request.form['dish_description']
        price = request.form['dish_price']
        Dish.add_dish(dish_name, description, price)
        flash('Dish added successfully!')
    
        return redirect(url_for('admin'))
    else:
        flash('Invalid request method', 'danger')
        return redirect(url_for('admin'))

# Customer route
@app.route('/customer')
@login_required
def customer():
    if current_user.role == 'customer':
        return render_template('customer.html')
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

@app.route('/customer_order', methods=['GET', 'POST'])
@login_required
def customer_order():
    if request.method == 'POST':
        try:
            customer_name = request.form['customer_name']
            phone_number = request.form.get('phone_number', '')
            order_details = "\n".join([f"{request.form.get(f'item_name_{i}')} x {request.form.get(f'quantity_{i}')}"
                                       for i in range(1, 6) if request.form.get(f'item_name_{i}')])
            payment_method = request.form['payment_method']
            credit_card_number = request.form.get('credit_card_number', '')
            expiration_date = request.form.get('expiration_date', '')
            cvv = request.form.get('cvv', '')
            delivery_option = request.form['delivery_option']
            delivery_address = request.form.get('address', '')

            # יצירת ההזמנה
            order_id = Order.create_order(customer_name, phone_number, order_details, payment_method,
                                          credit_card_number, expiration_date, cvv, delivery_option,
                                          delivery_address, current_user.id)

            # הנחת ש-Order.create_order מחזירה order_id
            if order_id:
                # הדפסה או רישום הנתונים שהתקבלו לפני שמירתם במסד הנתונים
                print(f"Received order data: customer_name={customer_name}, phone_number={phone_number}, order_details={order_details}, order_id={order_id}")

                # החזרת תגובת הצלחה ללקוח
                return jsonify({'success': True, 'order_id': order_id})
            else:
                print("Failed to create order: order_id is None")
                return jsonify({'success': False, 'error': 'Failed to create order'})

        except Exception as e:
            print(f"Error creating order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})

    dishes = Dish.query.all()  # Query all dishes from the database

    return render_template('customer_order.html', dishes=dishes)


# Customer review route
@app.route('/customer_review')
@login_required
def customer_review():
    return render_template('customer_review.html')

@app.route('/submit_review', methods=['POST'])
@login_required
def submit_review():
    try:
        customer_name = request.form['customer_name']
        review_text = request.form['review_text']
        rating = request.form['rating']
        review_image = None

        if 'review_image' in request.files:
            image = request.files['review_image']
            if image and image.filename != '':
                review_image = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], review_image)
                image.save(image_path)

        review_id = Review.create_review(customer_name, review_text, rating, review_image, current_user.id)
        
        if review_id:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Operator route
@app.route('/operator')
@login_required
def operator():
    if current_user.role == 'operator':
        orders = Order.query.all()  # Fetch all orders
        return render_template('operator.html', orders=orders)
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

@app.route('/close_order/<int:order_id>', methods=['POST'])
@login_required
def close_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = 'Closed'  # Change order status to Closed
    db.session.commit()
    flash(f'הזמנה {order_id} נסגרה בהצלחה', 'success')  # סוכם את סטטוס ההזמנה שנסגר
    return redirect(url_for('operator'))
@app.route('/send_whatsapp/<int:order_id>', methods=['POST'])
@login_required
def send_whatsapp(order_id):
    if request.method == 'POST':
        try:
            if Order.send_whatsapp_notification(order_id):
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to send WhatsApp message'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Invalid request method'})


if __name__ == '__main__':
    app.run(debug=True)
