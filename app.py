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
MAX_CONTENT = 8 * 1024 * 1024  # 8 MB, при необходимости поменяй

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT



#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################



def get_db_connection():
    conn = sqlite3.connect(sql_db, timeout=10)
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

        conn = get_db_connection()
        row = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()

        if not row or not row["is_admin"]:
            # Для HTML-страниц — 403. Для API можно вернуть JSON + статус.
            return abort(403)

        return f(*args, **kwargs)
    return decorated




#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    password_hash = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_admin = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(50))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
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
    return render_template("index.html")

#########################################################################################################################################################

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        us = request.form.get("name", "").strip()
        email = request.form.get("email", "").lower().strip()
        pw = request.form.get("password", "")
        
        if not email or not pw:
            return render_template('register.html', error='Email и пароль обязательны')
            
        pw_hash = generate_password_hash(pw)

        new_user = User(
            name = us,
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

@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add():
    title = request.form.get('title', '').strip()
    desc = request.form.get('description', '').strip()
    try:
        price = float(request.form.get('price', 0) or 0)
    except ValueError:
        price = 0.0
    category = request.form.get('category', '').strip()
    try:
        kolvo = int(request.form.get('kolvo', 0) or 0)
    except ValueError:
        kolvo = 0
    image = request.files.get('image')
    image_url = ''

    if image and image.filename:
        if not allowed_file(image.filename):
            return "Неподдерживаемый формат файла", 400
        filename = secure_filename(image.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        image.save(save_path)
        image_url = f"/{save_path.replace(os.path.sep,'/')}"
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO products (image_url, title, description, price, category, kolvo, is_active, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (image_url, title, desc, price, category, kolvo, 1, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

#########################################################################################################################################################

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return render_template("login.html", error="Неверный email или пароль", email=email)
        else:
            session.clear()
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')

#########################################################################################################################################################

@app.get("/api/products")
def get_products():
    """API для фронтенда: возвращает список активных товаров в JSON.

    Пример ответа: [{"id":1,"title":"Хлеб","price":140,...}, ...]
    """
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, title, description, price, image_url, category, kolvo FROM products WHERE is_active = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()

    products = [dict(row) for row in rows]
    # map DB column 'kolvo' to JSON 'stock' expected by frontend
    for p in products:
        p['stock'] = p.get('kolvo', 0)
    return jsonify(products)

#########################################################################################################################################################

@app.post("/api/products/by-bot")
def add_product_by_bot():
    """Endpoint для Telegram-бота.

    Ожидает заголовок `X-Api-Key` для простого контроля доступа.
    Тело — JSON с полями: title (строка), price (число),
    опционально description, image_url, category, stock.

    Пример JSON:
    {
      "title": "Хлеб",
      "price": 140,
      "description": "Домашний",
      "image_url": "https://...",
      "category": "Выпечка",
      "stock": 30
    }
    """
    api_key = request.headers.get("X-Api-Key", "")
    if api_key != secret.API_TG_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    # простая валидация
    if not data.get("title") or not data.get("price"):
        return jsonify({"error": "Missing title or price"}), 400

    try:
        price = float(data["price"])
        stock = int(data.get("stock", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "price must be a number and stock an integer"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO products (title, description, price, image_url, category, kolvo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            data["title"],
            data.get("description", ""),
            price,
            data.get("image_url", ""),
            data.get("category", "Без категории"),
            stock,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()

    return jsonify({"ok": True, "product_id": product_id}), 201

#########################################################################################################################################################

@app.post("/api/products/<int:product_id>/deactivate")
def deactivate_product(product_id: int):
    """Простой endpoint для скрытия товара с витрины.

    Тоже требует `X-Api-Key`.
    """
    api_key = request.headers.get("X-Api-Key", "")
    if api_key != secret.API_TG_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    conn.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})




#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################




if __name__ == "__main__":
    # инициализируем базу (создаст файл DB_PATH, если его нет)
    with app.app_context():
        db.create_all()
    # запускаем сервер для разработки
    app.run(debug=True)
