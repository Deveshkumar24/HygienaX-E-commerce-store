from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' 

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:kumar2924@localhost/hygienax_db'


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    cart_items = db.relationship('Cart', backref='customer', lazy=True)
    orders = db.relationship('Order', backref='customer', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    cart_items = db.relationship('Cart', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Nayi Line
    phone_number = db.Column(db.String(20), nullable=False) # Nayi Line
    address_line1 = db.Column(db.String(255), nullable=False) # Nayi Line
    address_line2 = db.Column(db.String(255), nullable=True) # Nayi Line
    city = db.Column(db.String(100), nullable=False) # Nayi Line
    state = db.Column(db.String(100), nullable=False) # Nayi Line
    pincode = db.Column(db.String(10), nullable=False) # Nayi Line
    landmark = db.Column(db.String(255), nullable=True) # Nayi Line
    order_date = db.Column(db.DateTime, server_default=db.func.now())
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_cart_item_count():
    if current_user.is_authenticated:
        item_count = sum(item.quantity for item in current_user.cart_items)
        return dict(cart_item_count=item_count)
    return dict(cart_item_count=0)


@app.route('/')
def home():
    search_query = request.args.get('search')
    if search_query:
        products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()
    else:
        products = Product.query.all()
    
    return render_template('index.html', products=products, search_query=search_query)

@app.route('/product/<int:product_id>')
def product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists.', 'error')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, username=name, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'error')
            return redirect(url_for('login'))
        
        login_user(user)
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product.id).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        new_item = Cart(user_id=current_user.id, product_id=product.id, quantity=1)
        db.session.add(new_item)
    
    db.session.commit()
    flash(f'{product.name} has been added to your cart.', 'success')
    return redirect(request.referrer or url_for('home'))

@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    total_quantity = sum(item.quantity for item in cart_items)
    
    discount = 0
    offer_applied = False
    
    if total_quantity >= 4:
        discount = subtotal * 0.15
        offer_applied = True
        
    total_price = subtotal - discount
    
    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal, discount=discount, total_price=total_price, offer_applied=offer_applied)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item_to_remove = Cart.query.get_or_404(item_id)
    if item_to_remove.user_id != current_user.id:
        return redirect(url_for('cart'))
    
    db.session.delete(item_to_remove)
    db.session.commit()
    flash('Item removed from your cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:item_id>/<action>', methods=['POST'])
@login_required
def update_cart(item_id, action):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return redirect(url_for('cart'))

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            db.session.delete(cart_item)
            flash('Item removed from your cart.', 'success')
            db.session.commit()
            return redirect(url_for('cart'))

    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "info")
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        address_line1 = request.form.get('address_line1')
        address_line2 = request.form.get('address_line2')
        city = request.form.get('city')
        state = request.form.get('state')
        pincode = request.form.get('pincode')
        landmark = request.form.get('landmark')
        
        session['name'] = name
        session['phone_number'] = phone_number
        session['address_line1'] = address_line1
        session['address_line2'] = address_line2
        session['city'] = city
        session['state'] = state
        session['pincode'] = pincode
        session['landmark'] = landmark
        return redirect(url_for('payment'))

    return render_template('address.html') 

@app.route('/payment')
@login_required
def payment():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "info")
        return redirect(url_for('home'))

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    total_quantity = sum(item.quantity for item in cart_items)

    discount = 0
    offer_applied = False

    if total_quantity >= 4:
        discount = subtotal * 0.15
        offer_applied = True

    total_price = subtotal - discount

    return render_template('payment.html', cart_items=cart_items, subtotal=subtotal, discount=discount, total_price=total_price, offer_applied=offer_applied)


@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        return redirect(url_for('home'))

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    total_quantity = sum(item.quantity for item in cart_items)

    discount = 0
    if total_quantity >= 4:
        discount = subtotal * 0.15

    total_price = subtotal - discount
    name = session.get('name')
    phone_number = session.get('phone_number')
    address_line1 = session.get('address_line1')
    address_line2 = session.get('address_line2')
    city = session.get('city')
    state = session.get('state')
    pincode = session.get('pincode')
    landmark = session.get('landmark')


    if not address_line1 or not city or not state or not pincode:
        flash("Please provide your complete shipping address.", "error")
        return redirect(url_for('checkout'))

    new_order = Order(user_id=current_user.id, total_price=total_price, name=name, phone_number=phone_number, address_line1=address_line1, address_line2=address_line2, city=city, state=state, pincode=pincode, landmark=landmark)
    db.session.add(new_order)
    db.session.commit()

    for item in cart_items:
        order_item = OrderItem(order_id=new_order.id, product_id=item.product_id, quantity=item.quantity, price=item.product.price)
        db.session.add(order_item)
        db.session.delete(item)
    
    db.session.commit()
    session.pop('name', None)
    session.pop('phone_number', None)
    session.pop('address_line1', None)
    session.pop('address_line2', None)
    session.pop('city', None)
    session.pop('state', None)
    session.pop('pincode', None)
    session.pop('landmark', None)
    
    flash('Your order has been placed successfully!', 'success')
    return redirect(url_for('checkout_success'))


@app.route('/checkout/success')
@login_required
def checkout_success():
    return render_template('checkout_success.html')

# --- Info Pages Routes ---
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('orders.html', orders=user_orders)

# --- DB Command ---
@app.cli.command("init-db")
def init_db_command():
    """Initializes the database."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        if Product.query.first() is None:
            products_data = [
                {"name": "White Phenyl (5L)", "description": "Our classic White Phenyl is a powerful disinfectant designed to eliminate germs and leave your floors sparkling clean. Its timeless, fresh fragrance ensures a hygienic and pleasant environment.", "price": 180.00, "image_file": "floor-cleaner-white.png"},
                {"name": "Rose Flavoured Phenyl (5L)", "description": "Experience deep cleaning with the enchanting aroma of fresh roses. This floor cleaner not only removes tough stains but also leaves a long-lasting, soothing floral fragrance.", "price": 240.00, "image_file": "floor-cleaner-rose.png"},
                {"name": "Toilet Cleaner (5L)", "description": "With 10x cleaning power, our Toilet Cleaner effortlessly removes the toughest stains and limescale. Its advanced formula kills 99.9% of germs, ensuring a sparkling clean and hygienic toilet.", "price": 350.00, "image_file": "toilet-cleaner.png"},
                {"name": "Dishwash Liquid (5L)", "description": "Tough on grease but gentle on hands, our Active Lemon Dishwash Liquid makes your utensils shine. Its powerful formula cuts through grime, leaving a refreshing lemon scent.", "price": 350.00, "image_file": "dishwash.jpg"},
                {"name": "Glass Cleaner (5L)", "description": "Get a streak-free shine every time with our Glass Cleaner. Its unique formula quickly removes dirt, grime, and fingerprints from glass surfaces, leaving them crystal clear.", "price": 350.00, "image_file": "glass-cleaner.png"},
                {"name": "Rose Handwash (5L)", "description": "Infused with the delicate fragrance of rose petals, this handwash cleanses gently while moisturizing your skin. It leaves your hands feeling soft, fresh, and beautifully scented.", "price": 350.00, "image_file": "handwash-rose.png"},
                {"name": "Apple Handwash (5L)", "description": "Fresh and pure anti-bacterial handwash with the crisp scent of green apples. It effectively cleanses and protects your hands, leaving them feeling refreshed and hygienic.", "price": 350.00, "image_file": "handwash-apple.jpg"},
                {"name": "Herbal Handwash (5L)", "description": "5x more power with a fresh herbal fragrance. This anti-bacterial handwash is enriched with natural extracts to keep your hands safe, clean, and smelling great.", "price": 350.00, "image_file": "handwash-herbal.png"},
                {"name": "Orange Handwash (5L)", "description": "Safe-to-use multi-purpose handwash with a zesty orange fragrance. Its rich lather cleanses thoroughly while being gentle on the skin, perfect for the whole family.", "price": 350.00, "image_file": "handwash-orange.png"}
            ]

            for p_data in products_data:
                product = Product(name=p_data['name'], description=p_data['description'], price=p_data['price'], image_file=p_data['image_file'])
                db.session.add(product)
            
            db.session.commit()
            print("Database initialized and products added.")
        else:
            print("Database already contains products.")

if __name__ == '__main__':
    app.run(debug=True)
