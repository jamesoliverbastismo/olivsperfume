import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

class Perfume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    image = db.Column(db.String(100))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    fullname = db.Column(db.String(100))
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)

# Auto-create tables and seed perfumes
with app.app_context():
    db.create_all()
    if not Perfume.query.first():
        sample_perfumes = [
            Perfume(name='Oliv Sweet', category='Sweet', price=499.0, description='Soft and romantic scent.', image='sweet.jpg'),
            Perfume(name='Oliv Men', category='Masculine', price=549.0, description='Bold and confident.', image='men.jpg'),
            Perfume(name='Oliv Unisex', category='Neutral', price=579.0, description='Balanced and versatile.', image='unisex.jpg'),
            Perfume(name='Oliv Women', category='Feminine', price=529.0, description='Elegant and graceful.', image='women.jpg')
        ]
        db.session.add_all(sample_perfumes)
        db.session.commit()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/products')
def products():
    perfumes = Perfume.query.all()
    lang = session.get('lang', 'en')
    return render_template('products.html', perfumes=perfumes, lang=lang)

@app.route('/add_to_cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    cart = session.get('cart', {})
    cart[str(id)] = cart.get(str(id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('products'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        perfume = Perfume.query.get(int(pid))
        if perfume:
            perfume.qty = qty
            perfume.subtotal = perfume.price * qty
            total += perfume.subtotal
            cart_items.append(perfume)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:id>')
def remove_from_cart(id):
    cart = session.get('cart', {})
    cart.pop(str(id), None)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        pass
    return render_template('contact.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    perfumes = Perfume.query.all()
    total_orders = Order.query.count()
    return render_template('admin.html', perfumes=perfumes, total_orders=total_orders)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form['description']
        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join('static', filename))
        perfume = Perfume(name=name, category=category, price=price, description=description, image=filename)
        db.session.add(perfume)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_product.html')

@app.route('/delete/<int:id>')
@login_required
def delete_product(id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    perfume = Perfume.query.get_or_404(id)
    db.session.delete(perfume)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Username already exists"
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        address = request.form['address']
        phone = request.form['phone']
        notes = request.form['notes']
        order = Order(user_id=current_user.id, fullname=fullname, email=email, address=address, phone=phone, notes=notes)
        db.session.add(order)
        db.session.commit()
        session['cart'] = {}
        return render_template('confirmation.html')
    return render_template('checkout.html')

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    orders = Order.query.all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)