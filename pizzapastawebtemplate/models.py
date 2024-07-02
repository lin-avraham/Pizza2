from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from twilio.rest import Client
import os
from dotenv import load_dotenv



db = SQLAlchemy()
env_file = 'pizzapastawebtemplate\\whatsapp.env'
load_dotenv(env_file)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def create_default_users():
        admin = User(username='admin', role='admin')
        admin.set_password('adminpass')

        operator = User(username='operator', role='operator')
        operator.set_password('operatorpass')

        customer = User(username='customer', role='customer')
        customer.set_password('customerpass')

        db.session.add(admin)
        db.session.add(operator)
        db.session.add(customer)
        db.session.commit()

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dish_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    @staticmethod
    def add_dish(dish_name, description, price):
        dish = Dish(dish_name=dish_name, description=description, price=price)
        db.session.add(dish)
        db.session.commit()

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    order_details = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    credit_card_number = db.Column(db.String(16), nullable=True)
    expiration_date = db.Column(db.String(10), nullable=True)
    cvv = db.Column(db.String(4), nullable=True)
    delivery_option = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Open')  # Add status field


    
    @staticmethod
    def create_order(customer_name, phone_number, order_details, payment_method,
                      credit_card_number, expiration_date, cvv, delivery_option, delivery_address, user_id):
        order = Order(customer_name=customer_name, phone_number=phone_number, order_details=order_details,
                     payment_method=payment_method, credit_card_number=credit_card_number,
                     expiration_date=expiration_date, cvv=cvv, delivery_option=delivery_option,
                     delivery_address=delivery_address, user_id=user_id)
        db.session.add(order)
        db.session.commit()
        return order.id
    @staticmethod
    def send_whatsapp_notification(order_id):
        order = Order.query.get(order_id)
        if order:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            client = Client(account_sid, auth_token)

            message = client.messages.create (
            from_='whatsapp:+14155238886',
            body=f"Hi, your order number {order_id} is ready \n We will be happy to write a review of your order, \n enjoy your meal !",
            to='whatsapp:+972525661997'
            )

            print(message.sid)

# בצע את הקריאה לשורה זו רק אם אתה משתמש ב- Flask Migrate
# db.create_all()
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    review_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_image = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @classmethod
    def create_review(cls, customer_name, review_text, rating, review_image, user_id):
        try:
            review = cls(customer_name=customer_name, review_text=review_text, rating=rating,
                         review_image=review_image, user_id=user_id)
            db.session.add(review)
            db.session.commit()
            return review.id
        except Exception as e:
            print("Error creating review:", e)  # Debugging
            return None
