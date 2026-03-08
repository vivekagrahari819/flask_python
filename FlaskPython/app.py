












from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
import pytz
import razorpay
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from sqlalchemy import desc
from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16 MB

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'mysql+pymysql://root:Agr%40hari567%23@localhost/flask_data')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['RAZORPAY_KEY_ID'] = os.getenv('RAZORPAY_KEY_ID')
app.config['RAZORPAY_SECRET_KEY'] = os.getenv('RAZORPAY_SECRET_KEY')
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

app.config['GOOGLE_REDIRECT_URI'] = os.getenv('GOOGLE_REDIRECT_URI')
from datetime import datetime, timezone


from flask_migrate import Migrate


db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_SECRET_KEY'])
)

oauth = OAuth(app)
google = oauth.register(
    'google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri=app.config['GOOGLE_REDIRECT_URI'],
    client_kwargs={'scope': 'openid profile email'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
)

ist = pytz.timezone('Asia/Kolkata')
# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationship to access the product from CartItem
    product = db.relationship('Product', backref=db.backref('cart_items', lazy=True))
    
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.String(100), nullable=False, unique=True)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref=db.backref('orders', lazy=True))

    

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    # Relationships for easy access
    order = db.relationship('Order', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))



    

def get_cart_item_count():
    if 'user_id' in session:
        return CartItem.query.filter_by(user_id=session['user_id']).count()
    return 0

@app.context_processor
def inject_cart_item_count():
    return dict(cart_item_count=get_cart_item_count())

# Routes
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route("/laqshya")
def laqshya():
    return render_template('laqshya.html')


@app.route("/students")
def students():
    return render_template('students.html')

@app.route('/chatbot', methods=['POST'])
def chatbot_post():
    data = request.get_json()
    user_message = data.get('message')
    
    # Define top 100 responses based on keywords or questions
    faq_responses = {
        'hello': 'Hi there! How can I help you today?',
        'hii': 'what"s up !! ?',
        'hi': 'what"s up !! ?',
        'hiii': 'whats up !! ?',
        'good': 'yes how can i help you',
        'how are you': 'I am just a bot, but I am doing great! How about you?',
        'bye': 'Goodbye! Have a great day!',
        'what is your name': 'I am your virtual assistant!',
        'what can you do': 'I can answer your questions, assist with tasks, and provide information.',
        'what is the weather like': 'Please use a weather service for up-to-date information.',
        'tell me a joke': 'Why don’t scientists trust atoms? Because they make up everything!',
        'how do I reset my password': 'To reset your password, go to the settings page and click "Reset Password".',
        'how can I contact support': 'You can contact support at support@example.com.',
        'where is my order': 'Please provide your order ID to track your order.',
        'can I change my shipping address': 'Yes, you can change your shipping address in the account settings.',
        'what is the refund policy': 'Our refund policy allows returns within 30 days of purchase.',
        'how do I cancel my order': 'To cancel your order, go to your order history and click "Cancel Order".',
        'do you ship internationally': 'Yes, we ship to select countries. Please check the shipping policy for more details.',
        'what payment methods do you accept': 'We accept credit cards, PayPal, and several other payment options.',
        'how do I update my profile': 'You can update your profile in the "Account Settings" section.',
        'can I get a discount': 'Check our promotions page for the latest discounts and offers!',
        'what is the delivery time': 'Standard delivery takes 5-7 business days.',
        'is my data secure': 'Yes, we use encryption and follow industry standards to keep your data secure.',
        'can I return an item': 'You can return items within 30 days of purchase. Visit our return policy page for more information.',
        'how do I track my order': 'You can track your order in the "My Orders" section using your order ID.',
        'can I modify my order after placing it': 'You can modify your order within the first 24 hours by contacting support.',
        'how can I change my email address': 'You can change your email address in the account settings section.',
        'what are your working hours': 'Our support team is available from 9 AM to 6 PM, Monday to Friday.',
        'do you offer express shipping': 'Yes, we offer express shipping at an additional cost.',
        'what should I do if I received a damaged item': 'If you received a damaged item, please contact support for assistance.',
        'can I pay in installments': 'Yes, we offer installment payments through selected payment methods.',
        'how can I delete my account': 'To delete your account, go to settings and click "Delete Account".',
        'how do I subscribe to your newsletter': 'You can subscribe to our newsletter by entering your email on our homepage.',
        'how do I unsubscribe from the newsletter': 'Click the "Unsubscribe" link at the bottom of any newsletter email.',
        'what is the warranty on your products': 'Most of our products come with a one-year warranty. Check the product page for details.',
        'do you offer gift cards': 'Yes, you can purchase gift cards from our store.',
        'how can I redeem a gift card': 'To redeem a gift card, enter the code at checkout.',
        'can I use multiple discount codes': 'Only one discount code can be used per order.',
        'how do I change my payment method after ordering': 'Unfortunately, payment methods cannot be changed once an order has been placed.',
        'what if I forget my password': 'You can reset your password by clicking "Forgot Password" on the login page.',
        'what should I do if my payment fails': 'If your payment fails, try using another payment method or contact your bank.',
        'can I order items that are out of stock': 'You can sign up for restock notifications on the product page.',
        'how do I apply a discount code': 'You can apply a discount code at checkout.',
        'is there a mobile app available': 'Yes, we have a mobile app available for both Android and iOS.',
        'how do I download your mobile app': 'You can download the app from the App Store or Google Play.',
        'do you offer free returns': 'Yes, we offer free returns for most items within 30 days of delivery.',
        'how do I contact customer service': 'You can contact customer service via email, phone, or live chat.',
        'how can I leave a product review': 'You can leave a product review on the product page under the reviews section.',
        'what is your privacy policy': 'You can view our privacy policy on the "Privacy Policy" page.',
        'do you offer live chat support': 'Yes, we offer live chat support during business hours.',
        'how do I change my subscription plan': 'You can change your subscription plan in the "Account Settings" section.',
        'can I upgrade my shipping after placing an order': 'Upgrading shipping after placing an order is not possible. Please contact support for help.',
        'how do I use store credit': 'You can apply store credit during the checkout process.',
        'do you offer military discounts': 'Yes, we offer discounts for military personnel with valid identification.',
        'how do I report an issue with my order': 'You can report issues by contacting our customer support team.',
        'what if I receive the wrong item': 'If you receive the wrong item, please contact our support team for a replacement.',
        'how do I know if an item is eligible for a return': 'Items eligible for returns will have that information listed on the product page.',
        'what is your exchange policy': 'We offer exchanges for most items within 30 days of purchase.',
        'can I combine my orders into one shipment': 'If your orders were placed separately, they cannot be combined.',
        'can I schedule my delivery time': 'We do not offer delivery scheduling at this time.',
        'what happens if my package is lost': 'If your package is lost, contact support, and we will investigate and issue a replacement or refund if necessary.',
        'can I cancel my subscription at any time': 'Yes, you can cancel your subscription anytime from the "Account Settings" page.',
        'do you have a referral program': 'Yes, we have a referral program. You can refer friends and earn rewards!',
        'what is your price match policy': 'We offer price matching for identical products sold by authorized retailers.',
        'how can I change my shipping method': 'You can change the shipping method before completing the checkout process.',
        'can I ship to a PO box': 'We do not ship to PO boxes at this time.',
        'do you offer corporate discounts': 'Yes, we offer corporate discounts for bulk orders.',
        'how do I update my shipping information': 'You can update your shipping information in the "My Account" section.',
        'do you offer rewards points': 'Yes, we offer a rewards points system for every purchase.',
        'what if I miss my delivery': 'If you miss your delivery, the courier will leave a notice for rescheduling or pickup.',
        'how do I return a gift': 'You can return a gift by following the standard return process and including the gift receipt.',
        'what should I do if my order is delayed': 'If your order is delayed, contact customer service for assistance.',
        'what are your accepted currencies': 'We accept payments in multiple currencies. Select your preferred currency at checkout.',
        'how do I apply for a job': 'Visit our "Careers" page to apply for job opportunities.',
        'what should I do if I forgot my order ID': 'You can find your order ID in the confirmation email sent to you after purchase.',
        'do you have student discounts': 'Yes, we offer student discounts. Verify your student status to claim the discount.',
        'can I change the currency I’m billed in': 'No, you are billed in the currency selected at checkout.',
        'what should I do if I don’t receive a confirmation email': 'If you don’t receive a confirmation email, check your spam folder or contact support.',
        'how do I know if my order went through': 'You will receive a confirmation email once your order is successfully placed.',
        'how can I cancel a return request': 'To cancel a return request, contact customer support for assistance.',
        'how do I redeem loyalty points': 'You can redeem loyalty points during the checkout process.',
        'what happens if I receive a defective item': 'If you receive a defective item, contact customer support for a replacement or refund.',
        'can I change the recipient after placing an order': 'Unfortunately, recipient details cannot be changed after an order is placed.',
        'what are your shipping rates': 'Shipping rates vary depending on the location and shipping method chosen at checkout.',
        'how do I know if my return was received': 'You will receive a confirmation email once your return has been processed.',
        'can I order a custom product': 'We offer customization on select products. Check the product page for more details.',
        'what do I do if I have multiple discount codes': 'You can only apply one discount code per order.',
        'can I split payment between two cards': 'Currently, we do not support split payments between multiple cards.',
        'how can I become a supplier': 'You can apply to become a supplier by visiting the "Become a Supplier" page on our website.',
        'can I pick up my order in-store': 'At this time, we do not offer in-store pickup.',
        'what should I do if my package is damaged upon delivery': 'If your package is damaged upon delivery, contact customer support for assistance.',
        'how do I re-order previous purchases': 'You can re-order previous purchases by visiting your order history.',
        'how do I contact the delivery carrier': 'Carrier contact information can be found in your shipping confirmation email.',
        'what are your accepted payment methods': 'We accept major credit cards, PayPal, and other payment options listed at checkout.',
        'how do I update my billing information': 'You can update your billing information in the "Account Settings" section.',
        'how do I dispute a charge': 'To dispute a charge, contact customer support or your bank for assistance.',
        'how do I access my invoices': 'You can access your invoices by logging into your account and viewing your order history.',
        'can I use PayPal': 'Yes, PayPal is one of the accepted payment methods during checkout.',
        'can I set up recurring payments': 'Yes, you can set up recurring payments for subscription services.',
        'how do I verify my account': 'You will receive a verification email after registration. Follow the link to verify your account.',
        'can I order from multiple stores at once': 'Currently, we do not support multi-store orders.',
        'do you offer eco-friendly packaging': 'Yes, we offer eco-friendly packaging options during checkout.'
    }
    
    # Get user message in lowercase for better matching
    user_message_lower = user_message.lower()
    
    # Find the response based on the user message
    bot_response = faq_responses.get(user_message_lower, 'Sorry, I did not understand that. Can you please rephrase?')
    
    return jsonify({'response': bot_response})



@app.route('/blogs')
def blogs():
    if 'user_id' in session:
        return render_template('blogs.html')
    else:
        flash('You need to login first.', 'danger')
        return redirect(url_for('login'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('You need to login first.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cart_item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = CartItem(user_id=user_id, product_id=product_id)
        db.session.add(new_cart_item)
    
    db.session.commit()
    flash('Product added to cart!', 'success')
    return redirect(url_for('index'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    action = request.form.get('action')
    if 'user_id' not in session:
        flash('You need to login first.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()

    if action == 'increase':
        if cart_item:
            cart_item.quantity += 1
            db.session.commit()
    elif action == 'decrease':
        if cart_item and cart_item.quantity > 1:
            cart_item.quantity -= 1
            db.session.commit()
    elif action == 'remove':
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
    else:
        flash('Invalid action.', 'danger')

    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('You need to login first.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)




@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        flash('You need to login first.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    
    if total_amount == 0:
        flash('Your cart is empty.', 'danger')
        return redirect(url_for('view_cart'))

    try:
        # Create a Razorpay order
        order = razorpay_client.order.create(dict(
            amount=int(total_amount * 100),  # Amount in paise
            currency='INR',
            payment_capture='1'
        ))
        order_id = order['id']

        # Save the order in the database
        new_order = Order(
            user_id=user_id,
            order_id=order_id,
            total_amount=total_amount,
            payment_status='Pending',
            created_at=datetime.now(ist) 
        )
        db.session.add(new_order)
        db.session.commit()

        return render_template('checkout.html', 
                                order_id=order_id, 
                                total_amount=total_amount, 
                                cart_items=cart_items, 
                                user_name=session.get('username'), 
                                user_email=session.get('email'))

    except Exception as e:
        print(f"Error creating payment order: {e}")
        flash(f'An error occurred while processing your payment. Please try again.', 'danger')
        return redirect(url_for('view_cart'))


@app.route('/payment_success', methods=['POST'])
def payment_success():
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_signature = request.form.get('razorpay_signature')

    print(f"Received Order ID: {razorpay_order_id}")
    print(f"Received Payment ID: {razorpay_payment_id}")
    print(f"Received Signature: {razorpay_signature}")

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # Verify the payment signature
        razorpay_client.utility.verify_payment_signature(params_dict)
        print("Payment signature verified successfully!")

        # Update order status to Success
        order = Order.query.filter_by(order_id=razorpay_order_id).first()

        if order:
            order.payment_status = 'Success'
            order.updated_at = datetime.now(ist)
            db.session.commit()

            # Move cart items to OrderItem table
            cart_items = CartItem.query.filter_by(user_id=order.user_id).all()
            for item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.product.price
                )
                db.session.add(order_item)

            # Clear the cart
            CartItem.query.filter_by(user_id=order.user_id).delete()
            db.session.commit()

            flash('Payment successful! Your order has been placed.', 'success')
            return redirect(url_for('my_orders'))

        else:
            flash('Order not found!', 'danger')
            return redirect(url_for('index'))

    except razorpay.errors.SignatureVerificationError as e:
        print(f"Payment Verification Failed: {e}")
        flash('Payment verification failed. Please try again.', 'danger')
        return redirect(url_for('index'))

    except Exception as e:
        print(f"An error occurred: {e}")
        flash('An error occurred. Please try again later.', 'danger')
        return redirect(url_for('index'))



@app.route('/contact')
def contact():
    if 'user_id' in session:
        return render_template('contact.html')
    else:
        flash('You need to login first.', 'danger')
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()

        if existing_user:
            flash('Username or email already in use. Choose a different one.', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

# Google OAuth Routes

import binascii

@app.route('/google_login')
def google_login():
    # Generate a nonce
    nonce = binascii.b2a_hex(os.urandom(16)).decode('utf-8')
    session['nonce'] = nonce

    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)


@app.route('/google_authorize')
def google_authorize():
    try:
        # Exchange the authorization code for a token
        token = google.authorize_access_token()
        nonce = session.get('nonce')

        # Fetch user info from the token with nonce
        user_info = google.parse_id_token(token, nonce=nonce)
        email = user_info['email']
        username = user_info['name']

        # Check if the user exists in the database
        user = User.query.filter_by(email=email).first()
        if not user:
            # Register the new user if not found
            user = User(
                username=username,
                email=email,
                password=generate_password_hash('')  # Default or empty password
            )
            db.session.add(user)
            db.session.commit()
        
        # Log the user in
        session['user_id'] = user.id
        session['username'] = user.username
        flash('Login successful!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('login'))



# Admin dashboard
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to access this page.', 'danger')
        return redirect(url_for('index'))

    users = User.query.all()
    products = Product.query.all()
    return render_template('admin_dashboard.html', users=users, products=products)

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to perform this action.', 'danger')
        return redirect(url_for('index'))

    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])

    image = request.files.get('image')
    if image:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    else:
        image_filename = None

    new_product = Product(name=name, description=description, price=price, image=image_filename)
    db.session.add(new_product)
    db.session.commit()
    
    flash('Product added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to perform this action.', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    product.name = request.form['name']
    product.description = request.form['description']
    product.price = float(request.form['price'])

    image = request.files.get('image')
    if image:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        product.image = image_filename

    db.session.commit()
    
    flash('Product updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to perform this action.', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/manage_users')
def manage_users():
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to access this page.', 'danger')
        return redirect(url_for('index'))

    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to perform this action.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_users'))

    user.username = request.form['username']
    user.email = request.form['email']
    db.session.commit()

    flash('User details updated successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('You need to be an admin to perform this action.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_users'))
    try:
        CartItem.query.filter_by(user_id = user.id).delete() 
        db.session.delete(user)
        db.session.commit()

        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"error deleted user : {str(e)}",'danger')   
         
    return redirect(url_for('manage_users'))



# Decorator to check if user is logged in and is admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('You are not authorized to view this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        flash('You are not authorized to access this page.', 'error')
        return redirect(url_for('index'))

    # Convert time to IST before passing to the template
    ist = pytz.timezone('Asia/Kolkata')
    orders = Order.query.order_by(desc(Order.created_at)).all()
    for order in orders:
        order.created_at_ist = order.created_at.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')

    return render_template('admin_orders.html', orders=orders)



@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash('Please log in to view your orders.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # Ensure successful orders are fetched
    orders = Order.query.filter_by(user_id=user_id, payment_status='Success').order_by(Order.created_at.desc()).all()

    if not orders:
        flash('No orders found.', 'info')

    # Convert UTC to IST
    ist = pytz.timezone('Asia/Kolkata')
    for order in orders:
        if order.created_at:
            order.created_at_ist = order.created_at.replace(tzinfo=pytz.utc).astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')

    return render_template('my_orders.html', orders=orders)









# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Check if the admin user already exists using email
        if not User.query.filter_by(email='admin@example.com').first():
            hashed_password = generate_password_hash('admin_password', method='pbkdf2:sha256')
            admin = User(username='admin', email='admin@example.com', password=hashed_password, is_admin=True)
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists.")
        
        app.run(port=5001, debug=True)




#  flask db migrate
# flask db upgrade



# pip install flask
# pip install flask_sqlalchemy
# pip install flask_migrate
# pip install flask_wtf
# pip install flask_login
# pip install werkzeug
# pip install pymysql
# pip install razorpay
# pip install flask-dotenv
# pip install flask-cors
# pip install flask-bcrypt
# pip install python-dotenv
# pip install authlib
# pip install pytz
# pip install requests
#pip install mysqlclient
# python.exe -m pip install python-dotenv
#python -m pip install setuptools


