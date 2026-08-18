from flask import Flask, jsonify, render_template, request, session, redirect, url_for, abort
import sqlite3
import telebot
from datetime import datetime, timezone
import secret
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError




#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################



sql_db = "store.db"
bot = telebot.TeleBot(secret.API_TG_KEY)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = "KUTS_QWERTY_64"
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXT = {'png','jpg','jpeg','gif'}
MAX_CONTENT = 12 * 1024 * 1024  # 8 MB, при необходимости поменяй

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT



#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################



def get_db_connection():
    conn = sqlite3.connect(sql_db, timeout=1)
    conn.row_factory = sqlite3.Row
    
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login"))        # не залогинен — на страницу входа

        us = User.query.filter_by(id=user_id).first()

        if not us or not us.is_admin:
            return abort(403)

        return f(*args, **kwargs)
    return decorated




#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    phone = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.String(50))
    is_admin = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(120))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    colors = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50))
    kolvo = db.Column(db.Integer)
    is_active = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(50))



#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################


@app.route("/")
def index():
    products = Product.query.filter_by(is_active=1).order_by(Product.id.desc()).all()
    return render_template("index.html", products=products)

#########################################################################################################################################################

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        us = request.form.get("name", "").strip()
        phone = request.form.get("phone", "")
        email = request.form.get("email", "").lower().strip()
        pw = request.form.get("password", "")
        
        if not(email or phone) and not pw:
            return render_template('register.html', error='Email или телефон, пароль обязательны')
            
        pw_hash = generate_password_hash(pw)

        new_user = User(
            name = us,
            phone = phone,
            email=email,
            password_hash=pw_hash,
            created_at=datetime.now(timezone.utc).isoformat()
            )

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template("register.html", error="Вы уже зарегестрированы!")            
        return redirect(url_for('login'))
    return render_template('register.html')

#########################################################################################################################################################

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get("phone", "")  
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')

        if phone != '':
            user = User.query.filter_by(phone=phone).first()
        else:
            user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return render_template("login.html", error="Неверный email или пароль", email=email)
        else:
            session.clear()
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')

#########################################################################################################################################################

@app.route('/admin')
@admin_required
def admin_():
    products = Product.query.order_by(Product.id.desc()).all()

    return render_template("admin.html", products=products)

#########################################################################################################################################################

@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add():
    title = request.form.get("title") 
    description = request.form.get("description")
    colors = request.form.get("colors") 
    price = float(request.form.get("price"))
    category = request.form.get("category") 
    kolvo = int(request.form.get("kolvo"))

    image = request.files.get("image")
    image_url = None
    if image and image.filename:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        image_url = f"uploads/{filename}"

    product = Product(
        title=title,
        description=description,
        colors=colors,
        price=price,
        category=category,
        kolvo=kolvo,
        image_url=image_url,
        is_active=1,)
    
    db.session.add(product)
    db.session.commit()

    return redirect(url_for("admin_"))

#########################################################################################################################################################

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':

        product.title = request.form.get("title")
        product.description = request.form.get("description")
        product.colors = request.form.get("colors")
        product.price = request.form.get("price")
        product.category = request.form.get("category")
        product.kolvo = request.form.get("kolvo")

        db.session.commit()
        return redirect(url_for("admin_"))
    return render_template(
        "edit_product.html",
        product=product
    )

#########################################################################################################################################################

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):

    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("admin_"))






#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################




if __name__ == "__main__":
    # инициализируем базу (создаст файл DB_PATH, если его нет)
    with app.app_context():
        db.create_all()
    # запускаем сервер для разработки
    app.run(debug=True)
