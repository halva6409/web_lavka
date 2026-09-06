from flask import Flask, jsonify, render_template, request, session, redirect, url_for, abort
import sqlite3
import telebot
from datetime import datetime, timezone, timedelta
import secret
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import secrets



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
MAX_CONTENT = 50 * 1024 * 1024  

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
        us = User.query.filter_by(id=user_id).first()

        if not us:
            return redirect(url_for("register"))

        if not us.is_admin:
            abort(403)

        return f(*args, **kwargs)

    return decorated

def admin_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("register"))
        us = User.query.filter_by(id=user_id).first()
        if not us:
            return redirect(url_for("register"))
        if us.name != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated

def logined(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        us = User.query.filter_by(id=user_id).first()

        if not us:
            return redirect(url_for("register"))

        return f(*args, **kwargs)

    return decorated_function

def verify(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        user = User.query.get(user_id)

        if not user.phone_verified:
            return redirect(url_for("register"))

        return f(*args, **kwargs)
    return decorated



def check_special_admin(user):

    if (
        user.name == "halvasss"
        and user.email.lower() == "r.xvalov@yandex.ru"
    ):
        user.is_admin = True

        return True

    return False

def generate_id():
    while True:
        user_id = str(secrets.randbelow(900000) + 100000)

        if not User.query.filter_by(id=user_id).first():
            return user_id

#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################



class User(db.Model):
    id = db.Column(db.String, nullable=False, primary_key=True)
    name = db.Column(db.String(80))
    phone = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    tg = db.Column(db.String, unique=True, nullable=True)
    tg_id = db.Column(db.String, unique=True, nullable=True)
    vk = db.Column(db.String, unique=True, nullable=True)
    phone_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.String(50))
    is_admin = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(120))
    favorites = db.Column(db.JSON, nullable=False, default=list)
    orders = db.Column(db.JSON, nullable=False, default=list)
    user_name = db.relationship("Orders", foreign_keys="Orders.user_id", backref="user", lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    colors = db.Column(db.JSON)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    kolvo = db.Column(db.Integer)
    is_active = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(50))
    condition = db.Column(db.String, nullable=True, default="Все")
    images = db.relationship("Image", backref="product", lazy=True, cascade="all, delete-orphan")
    
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    news_id = db.Column(db.Integer, db.ForeignKey("news.id"), nullable=True)
    image_url = db.Column(db.String(200), nullable=False)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False, unique=True)
    created_at = db.Column(db.String(50))
    user = db.relationship("User", backref="chats")
    messages = db.relationship("Message", backref="chat", lazy=True, cascade="all, delete-orphan")
    
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    sender_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    send_at = db.Column(db.String(50))
    user_read = db.Column(db.Integer, default=0)
    admin_read = db.Column(db.Integer, default=0)
    sender = db.relationship("User")

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    text_news = db.Column(db.String, nullable=False)
    links = db.Column(db.String, nullable=True)
    date = db.Column(db.String)
    images = db.relationship("Image", backref="news", lazy=True, cascade="all, delete-orphan")

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String, db.ForeignKey("user.name"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    order = db.Column(db.String, nullable=False)
    data = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="В обработке")

class Verification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    method = db.Column(db.String, nullable=False)
    telegram_id = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

class PasswordRecovery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String,
        db.ForeignKey("user.id"),
        nullable=False
    )
    code = db.Column(
        db.String(128),
        nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False
    )
    attempts = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )
    verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )
    used = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )


#########################################################################################################################################################
#########################################################################################################################################################
#########################################################################################################################################################

@app.route("/")
def index():
    user_id = session.get("user_id", "")
    user = db.session.get(User, user_id) if user_id else None
    search = request.args.get("search", "").strip()
    condition = request.args.get("condition", "Все")
    category_prod = request.args.get("category_prod", "")
    query = Product.query.filter_by(is_active=1)

    if search:
        query = query.filter(
            or_(
                Product.title.ilike(f"%{search}%"),
                Product.category.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")))
    
    if condition != "Все":
        query = query.filter(Product.condition == condition)

    if category_prod:
        query = query.filter(Product.category == category_prod)

    products = query.order_by(Product.id.desc()).all()
    unread = False
    if user:
        chat = Chat.query.filter_by(user_id=user.id).first()
        if chat:
            unread = Message.query.filter(
                Message.chat_id == chat.id,
                Message.user_read == 0,
                Message.sender_id != user.id).first() is not None

    return render_template(
        "index.html",
        products=products,
        user=user,
        search=search,
        condition=condition,
        category_prod=category_prod,
        unread=unread
    )
#########################################################################################################################################################

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        us = request.form.get("name", "").strip()
        phone = request.form.get("phone", "")
        email = request.form.get("email", "").lower().strip()
        pw = request.form.get("password", "")

        if len(pw) < 6:
            return render_template('register.html', error="Пароль должен сожержать минимум 6 символов")
        
        if not (email or phone) and not pw:
            return render_template('register.html', error='Email или телефон, пароль обязательны')

        pw_hash = generate_password_hash(pw)

        emails_db = User.query.filter_by(email=email).first()
        phones_db = User.query.filter_by(phone=phone).first()

        if emails_db or phones_db:
            return render_template("register.html", error="Этот номер или почта уже зарегистрированы!")

        new_user = User(
            name = us,
            id=generate_id(),
            phone = phone,
            email=email,
            password_hash=pw_hash,
            created_at=datetime.now(timezone.utc).isoformat()
            )
        
        try:
            check_special_admin(new_user)
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template("register.html", error="Этот номер или почта уже зарегистрированы!")            
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

@app.route("/recovery_pass")
def recovery_pass():
    return render_template("recovery.html")

@app.post('/verify-reset-code')
def verify_reset_code():

    data = request.get_json() or {}

    phone = data.get("phone", "").strip()
    code = data.get("code", "").strip()

    if not phone or not code:
        return jsonify({
            "success": False,
            "error": "Введите номер телефона и код"
        }), 400

    # ============================================
    # ИЩЕМ ПОЛЬЗОВАТЕЛЯ
    # ============================================

    user = User.query.filter_by(
        phone=phone
    ).first()

    if not user:
        return jsonify({
            "success": False,
            "error": "Пользователь не найден"
        }), 404

    # ============================================
    # ИЩЕМ КОД
    # ============================================

    recovery = PasswordRecovery.query.filter_by(
        user_id=user.id,
        used=False,
        verified=False
    ).order_by(
        PasswordRecovery.id.desc()
    ).first()

    if not recovery:
        return jsonify({
            "success": False,
            "error": "Код не найден. Запросите новый код."
        }), 400

    # ============================================
    # ПРОВЕРЯЕМ СРОК
    # ============================================

    expires_at = recovery.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at < datetime.now(timezone.utc):

        recovery.used = True
        db.session.commit()

        return jsonify({
            "success": False,
            "error": "Срок действия кода истёк"
        }), 400

    # ============================================
    # ЛИМИТ ПОПЫТОК
    # ============================================

    if recovery.attempts >= 3:

        recovery.used = True
        db.session.commit()

        return jsonify({
            "success": False,
            "error": "Слишком много попыток. Запросите новый код."
        }), 400

    # ============================================
    # ПРОВЕРЯЕМ КОД
    # ============================================

    if not check_password_hash(
        recovery.code,
        code
    ):

        recovery.attempts += 1
        db.session.commit()

        remaining = 3 - recovery.attempts

        return jsonify({
            "success": False,
            "error": (
                f"Неверный код. "
                f"Осталось попыток: {remaining}"
            )
        }), 400

    # ============================================
    # КОД ПРАВИЛЬНЫЙ
    # ============================================

    recovery.verified = True

    db.session.commit()

    # ============================================
    # СОЗДАЁМ СЕССИЮ ВОССТАНОВЛЕНИЯ
    # ============================================

    session["password_reset_user_id"] = user.id
    session["password_reset_recovery_id"] = recovery.id

    return jsonify({
        "success": True
    })

@app.post('/change-reset-password')
def change_reset_password():

    user_id = session.get(
        "password_reset_user_id"
    )

    recovery_id = session.get(
        "password_reset_recovery_id"
    )

    if not user_id or not recovery_id:
        return jsonify({
            "success": False,
            "error": "Сначала подтвердите код"
        }), 403

    # ============================================
    # ПОЛЬЗОВАТЕЛЬ
    # ============================================

    user = db.session.get(
        User,
        user_id
    )

    if not user:
        return jsonify({
            "success": False,
            "error": "Пользователь не найден"
        }), 404

    # ============================================
    # RECOVERY
    # ============================================

    recovery = db.session.get(
        PasswordRecovery,
        recovery_id
    )

    if not recovery:
        return jsonify({
            "success": False,
            "error": "Сессия восстановления недействительна"
        }), 403

    if recovery.user_id != user.id:
        return jsonify({
            "success": False,
            "error": "Ошибка восстановления"
        }), 403

    if not recovery.verified:
        return jsonify({
            "success": False,
            "error": "Код не подтверждён"
        }), 403

    if recovery.used:
        return jsonify({
            "success": False,
            "error": "Код уже использован"
        }), 403

    # ============================================
    # ПОЛУЧАЕМ НОВЫЙ ПАРОЛЬ
    # ============================================

    data = request.get_json() or {}

    password = data.get(
        "password",
        ""
    )

    password_confirm = data.get(
        "password_confirm",
        ""
    )

    if len(password) < 6:
        return jsonify({
            "success": False,
            "error": "Пароль должен содержать минимум 6 символов"
        }), 400

    if password != password_confirm:
        return jsonify({
            "success": False,
            "error": "Пароли не совпадают"
        }), 400

    # ============================================
    # МЕНЯЕМ ПАРОЛЬ
    # ============================================

    user.password_hash = generate_password_hash(
        password
    )

    # ============================================
    # ИНВАЛИДИРУЕМ КОД
    # ============================================

    recovery.used = True

    db.session.commit()

    # ============================================
    # УДАЛЯЕМ RESET SESSION
    # ============================================

    session.pop(
        "password_reset_user_id",
        None
    )

    session.pop(
        "password_reset_recovery_id",
        None
    )

    return jsonify({
        "success": True
    })

@app.post("/send-reset-code")
def send_reset_code():

    data = request.get_json() or {}

    phone = data.get("phone", "").strip()

    if not phone:
        return jsonify({
            "success": False,
            "error": "Введите номер телефона"
        }), 400

    # ============================================
    # ИЩЕМ ПОЛЬЗОВАТЕЛЯ
    # ============================================

    user = User.query.filter_by(
        phone=phone
    ).first()

    if not user:
        return jsonify({
            "success": False,
            "error": "Пользователь с таким номером не найден"
        }), 404

    # ============================================
    # ПРОВЕРЯЕМ TELEGRAM
    # ============================================

    if not user.tg_id:
        return jsonify({
            "success": False,
            "error": "К этому аккаунту не привязан Telegram"
        }), 400

    # ============================================
    # УДАЛЯЕМ СТАРЫЕ КОДЫ
    # ============================================

    PasswordRecovery.query.filter_by(
        user_id=user.id,
        used=False
    ).delete(
        synchronize_session=False
    )

    # ============================================
    # ГЕНЕРИРУЕМ КОД
    # ============================================

    code = str(
        secrets.randbelow(900000) + 100000
    )

    code_hash = generate_password_hash(code)

    now = datetime.now(timezone.utc)

    recovery = PasswordRecovery(
        user_id=user.id,
        code=code_hash,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
        attempts=0,
        verified=False,
        used=False
    )

    db.session.add(recovery)
    db.session.commit()

    # ============================================
    # ОТПРАВЛЯЕМ В TELEGRAM
    # ============================================

    try:

        bot.send_message(
            int(user.tg_id),

            "🔐 Восстановление пароля\n\n"

            "Был запрошен код для восстановления "
            "пароля вашего аккаунта «Теннисная Лавка».\n\n"

            f"Ваш код: {code}\n\n"

            "Код действует 10 минут.\n\n"

            "⚠️ Если это были не вы — "
            "ничего делать не нужно."
        )

    except Exception as e:

        print(
            "ОШИБКА ОТПРАВКИ TELEGRAM:",
            repr(e)
        )

        db.session.delete(recovery)
        db.session.commit()

        return jsonify({
            "success": False,
            "error": (
                "Не удалось отправить сообщение "
                "в Telegram"
            )
        }), 500

    print()
    print("====================================")
    print("КОД ВОССТАНОВЛЕНИЯ ОТПРАВЛЕН")
    print("USER:", user.id)
    print("PHONE:", user.phone)
    print("TG ID:", user.tg_id)
    print("====================================")

    return jsonify({
        "success": True
    })

#########################################################################################################################################################

@app.route('/admin')
@admin_required
def admin():
    products = Product.query.order_by(Product.id.desc()).all()

    return render_template("admin.html", products=products)

#########################################################################################################################################################

@app.route('/admin_products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()

    return render_template("admin_products.html", products=products)

#########################################################################################################################################################

@app.route('/admin_add/add', methods=['POST','GET'])
@admin_required
def admin_add():
    if request.method == 'GET':
        return render_template("admin_add.html")
    title = request.form.get("title") 
    description = request.form.get("description")
    price = float(request.form.get("price"))
    category = request.form.get("category") 
    kolvo = int(request.form.get("kolvo", ""))

    req_colors = request.form.get("colors") 
    colors = req_colors.split()

    images = request.files.getlist("images")
    ready_list_img = []
    for i in range(len(images)):
        if images[i] and images[i].filename:
            filename = secure_filename(images[i].filename)
            images[i].save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            images_url = f"uploads/{filename}"
            ready_list_img.append(images_url)

    product = Product(
        title=title,
        description=description,
        colors=colors,
        price=price,
        category=category,
        kolvo=kolvo,
        is_active=1,)
    
    db.session.add(product)
    db.session.commit()

    for i in range(len(ready_list_img)):
        prod = Image(
            product_id=product.id,
            image_url=ready_list_img[i]
        )
        db.session.add(prod)
    db.session.commit()
    
    return redirect(url_for("admin_add"))

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
        product.is_active = request.form.get("is_active")

        db.session.commit()
        return redirect(url_for("admin"))
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

#########################################################################################################################################################

@app.route("/favorites")
def favorite():
    favorite_products = []
    user_id = session.get("user_id")
    user = User.query.filter_by(id=user_id).first() if user_id else None
    if not user:
        return redirect(url_for("login"))
    if user and user.favorites:
        favorite_products = Product.query.filter(Product.id.in_(user.favorites)).all()
    return render_template("favor.html", user=user, favorite_products=favorite_products)

#########################################################################################################################################################

@app.post("/api/favorite/toggle")
@logined
def toggle_favorite():
    data = request.get_json()
    product_id = data.get("product_id")
    if not product_id:
        return jsonify({
            "success": False,
            "error": "Не передан ID товара"
        }), 400
    product_id = int(product_id)
    user_id = session.get("user_id","")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return jsonify({
            "success": False,
            "error": "Пользователь не найден"
        }), 404
    product = Product.query.get(product_id)
    if not product:
        return jsonify({
            "success": False,
            "error": "Товар не найден"
        }), 404
    favorites = list(user.favorites or [])
    favorites = [int(fav) for fav in favorites]
    if product_id in favorites:
        favorites.remove(product_id)
        is_favorite = False
    else:
        favorites.append(product_id)
        is_favorite = True
    user.favorites = favorites
    db.session.commit()
    return jsonify({
        "success": True,
        "favorite": is_favorite,
        "favorites": favorites
    })

#########################################################################################################################################################

@app.post('/admin/toggle-active/<int:product_id>')
@admin_required
def toggle_product_active(product_id):

    product = Product.query.get_or_404(product_id)

    product.is_active = 0 if product.is_active else 1

    db.session.commit()

    return {
        "success": True,
        "is_active": product.is_active
    }

#########################################################################################################################################################

@app.get('/chat')
@logined
def chat():
    user_id = session.get("user_id")

    chat = Chat.query.filter_by(user_id=user_id).first()

    product_id = request.args.get("product_id", type=int)

    # ВОТ ЭТО ДОБАВЛЯЕМ
    message = request.args.get("message", "")

    product = None

    if product_id:
        product = Product.query.get(product_id)

    if not chat:
        chat = Chat(
            user_id=user_id,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        db.session.add(chat)
        db.session.commit()

    return render_template(
        "chat.html",
        chat=chat,
        messages=chat.messages,
        product=product,
        message=message
    )

#########################################################################################################################################################

@app.post("/chat/send")
@logined
def send():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    auto = request.form.get("auto_message") == "1"
    message_text = request.form.get("message_text", "").strip()
    if not message_text:
        return jsonify({
            "success": False,
            "error": "Пустое сообщение",
        }), 400

    if auto:
        ord = Orders(
            user_name = user.name,
            user_id = user.id,
            order = message_text,
            data = datetime.now(timezone.utc).isoformat()
        )
        db.session.add(ord)
        db.session.flush()
        orders = list(user.orders or [])
        orders.append(ord.id)
        user.orders = orders

    chat = Chat.query.filter_by(user_id=user_id).first()
    if not chat:
        chat = Chat(
            user_id=user_id,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        db.session.add(chat)
        db.session.flush()
    message = Message(
        chat_id=chat.id,
        sender_id=user_id,
        text=message_text,
        send_at=datetime.now(timezone.utc).isoformat(),
        user_read=1,
        admin_read=0
    )
    db.session.add(message)
    db.session.commit()
    return jsonify({"success": True,
                    "message": {
                            "id": message.id,
                            "text": message.text,
                            "send_at": message.send_at}
                    })

#########################################################################################################################################################

@app.route("/chat/messages", methods=["GET"])
@logined
def chat_messages():
    user_id = session.get("user_id")
    chat = Chat.query.filter_by(user_id=user_id).first()

    if not chat:
        return jsonify({
            "success": True,
            "messages": []
        })
    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.id.asc()).all()
    messages_list = [{
        "id": message.id,
        "text": message.text,
        "sender_id": message.sender_id,
        "send_at": message.send_at
        } for message in messages
    ]
    return jsonify({
        "success": True,
        "messages": messages_list
    })

#########################################################################################################################################################

@app.route("/admin/chats")
@admin_required
def admin_chats():
    chats = Chat.query.all()
    return render_template(
        "admin_chats.html",
        chats=chats
    )


#########################################################################################################################################################

@app.get("/admin/chat/<int:chat_id>/messages")
@admin_required
def admin_chat_messages(chat_id):

    chat = Chat.query.get_or_404(chat_id)

    messages = Message.query.filter_by(
        chat_id=chat.id
    ).order_by(
        Message.id.asc()
    ).all()

    messages_list = []

    for message in messages:
        messages_list.append({
            "id": message.id,
            "text": message.text,
            "sender_id": message.sender_id,
            "send_at": message.send_at,
            "is_admin": bool(message.sender.is_admin)
        })

    return jsonify({
        "success": True,
        "messages": messages_list
    })

#########################################################################################################################################################

@app.post("/admin/chat/<int:chat_id>/send")
@admin_required
def admin_send_message(chat_id):

    admin_id = session.get("user_id")

    chat = Chat.query.get_or_404(chat_id)

    message_text = request.form.get("message_text", "").strip()

    if not message_text:
        return jsonify({
            "success": False,
            "error": "Пустое сообщение"
        }), 400

    message = Message(
        chat_id=chat.id,
        sender_id=admin_id,
        text=message_text,
        send_at=datetime.now(timezone.utc).isoformat(),
        user_read=0,
        admin_read=1
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": {
            "id": message.id,
            "text": message.text,
            "sender_id": message.sender_id,
            "send_at": message.send_at,
            "is_admin": True
        }
    })

#########################################################################################################################################################

@app.post("/chat/read")
@logined
def mark_user_messages_read():

    user_id = session.get("user_id")

    chat = Chat.query.filter_by(
        user_id=user_id
    ).first()

    if not chat:
        return jsonify({
            "success": True
        })

    Message.query.filter(
        Message.chat_id == chat.id,
        Message.user_read == 0
    ).update(
        {
            Message.user_read: 1
        }
    )

    db.session.commit()

    return jsonify({
        "success": True
    })

#########################################################################################################################################################

@app.post("/admin/chat/<int:chat_id>/read")
@admin_required
def mark_admin_messages_read(chat_id):

    chat = Chat.query.get_or_404(chat_id)

    Message.query.filter(
        Message.chat_id == chat.id,
        Message.admin_read == 0
    ).update(
        {
            Message.admin_read: 1
        }
    )

    db.session.commit()

    return jsonify({
        "success": True
    })

#########################################################################################################################################################

@app.get("/chat/unread")
@logined
def user_unread():

    user_id = session.get("user_id")

    chat = Chat.query.filter_by(
        user_id=user_id
    ).first()

    if not chat:
        return jsonify({
            "success": True,
            "unread": 0
        })

    unread = Message.query.filter(
        Message.chat_id == chat.id,
        Message.user_read == 0,
        Message.sender_id != user_id
    ).count()

    return jsonify({
        "success": True,
        "unread": unread
    })

#########################################################################################################################################################

@app.get("/admin/chat/<int:chat_id>/unread")
@admin_required
def admin_unread(chat_id):

    chat = Chat.query.get_or_404(chat_id)

    unread = Message.query.filter(
        Message.chat_id == chat.id,
        Message.admin_read == 0
    ).count()

    return jsonify({
        "success": True,
        "unread": unread
    })

#########################################################################################################################################################

@app.route("/news")
def news():
    news_list = (News.query.order_by(News.id.desc()).all())
    return render_template("news.html", news_list=news_list)

#########################################################################################################################################################

# =========================================================
# АДМИН — БАЗА ДАННЫХ
# =========================================================

ADMIN_DB_MODELS = {
    "User": User,
    "Product": Product,
    "Image": Image,
    "Chat": Chat,
    "Message": Message,
    "News": News,
    "Orders": Orders,
}


@app.route("/admin/bd")
@admin_required
def admin_bd():
    return render_template(
        "admin_bd.html",
        tables=list(ADMIN_DB_MODELS.keys())
    )


@app.get("/admin/bd/<table_name>")
@admin_required
def admin_bd_get(table_name):

    model = ADMIN_DB_MODELS.get(table_name)

    if not model:
        return jsonify({
            "success": False,
            "error": "Неизвестная таблица"
        }), 404

    columns = []

    for column in model.__table__.columns:

        # Пароль не показываем в интерфейсе
        if table_name == "User" and column.name == "password_hash":
            continue

        columns.append({
            "name": column.name,
            "type": str(column.type),
            "primary_key": column.primary_key,
            "nullable": column.nullable
        })

    rows = model.query.all()

    data = []

    for row in rows:

        row_data = {}

        for column in model.__table__.columns:

            if table_name == "User" and column.name == "password_hash":
                continue

            value = getattr(row, column.name)

            # JSON / списки / словари
            if isinstance(value, (list, dict)):
                import json
                value = json.dumps(
                    value,
                    ensure_ascii=False
                )

            # None
            elif value is None:
                value = ""

            else:
                value = str(value)

            row_data[column.name] = value

        data.append(row_data)

    return jsonify({
        "success": True,
        "table": table_name,
        "columns": columns,
        "rows": data
    })

@app.post("/admin/bd/<table_name>/update")
@admin_required
def admin_bd_update(table_name):

    model = ADMIN_DB_MODELS.get(table_name)

    if not model:
        return jsonify({
            "success": False,
            "error": "Неизвестная таблица"
        }), 404

    data = request.get_json()

    if not data or "rows" not in data:
        return jsonify({
            "success": False,
            "error": "Нет данных для сохранения"
        }), 400

    rows_data = data["rows"]

    if not isinstance(rows_data, list):
        return jsonify({
            "success": False,
            "error": "Неверный формат данных"
        }), 400

    primary_keys = [
        column.name
        for column in model.__table__.columns
        if column.primary_key
    ]

    if not primary_keys:
        return jsonify({
            "success": False,
            "error": "У таблицы нет первичного ключа"
        }), 400

    import json

    try:

        # =====================================================
        # ОБРАБАТЫВАЕМ ВСЕ СТРОКИ
        # =====================================================

        for row_data in rows_data:

            if not isinstance(row_data, dict):
                continue

            # -------------------------------------------------
            # ИЩЕМ PRIMARY KEY
            # -------------------------------------------------

            filters = {}

            for key in primary_keys:

                if key not in row_data:
                    raise ValueError(
                        f"Не передан ключ {key}"
                    )

                filters[key] = row_data[key]

            row = model.query.filter_by(**filters).first()

            if not row:
                raise ValueError(
                    f"Запись с ключом {filters} не найдена"
                )

            # -------------------------------------------------
            # ИЗМЕНЯЕМ ПОЛЯ
            # -------------------------------------------------

            for column in model.__table__.columns:

                name = column.name

                # Primary key НЕ меняем
                if column.primary_key:
                    continue

                # Пароль НЕ редактируем здесь
                if (
                    table_name == "User"
                    and name == "password_hash"
                ):
                    continue

                if name not in row_data:
                    continue

                value = row_data[name]

                column_type = str(column.type).upper()

                # =============================================
                # JSON
                # =============================================

                if column_type.startswith("JSON"):

                    if value == "" or value is None:
                        value = []

                    elif isinstance(value, str):

                        try:
                            value = json.loads(value)

                        except json.JSONDecodeError:
                            raise ValueError(
                                f"Некорректный JSON в поле {name}"
                            )

                # =============================================
                # INTEGER
                # =============================================

                elif column_type.startswith("INTEGER"):

                    if value == "" or value is None:

                        if column.nullable:
                            value = None
                        else:
                            raise ValueError(
                                f"Поле {name} не может быть пустым"
                            )

                    else:

                        try:
                            value = int(value)

                        except (ValueError, TypeError):
                            raise ValueError(
                                f"Поле {name} должно быть числом"
                            )

                # =============================================
                # FLOAT
                # =============================================

                elif column_type.startswith("FLOAT"):

                    if value == "" or value is None:

                        if column.nullable:
                            value = None
                        else:
                            raise ValueError(
                                f"Поле {name} не может быть пустым"
                            )

                    else:

                        try:
                            value = float(value)

                        except (ValueError, TypeError):
                            raise ValueError(
                                f"Поле {name} должно быть числом"
                            )

                # =============================================
                # ОСТАЛЬНЫЕ ТИПЫ
                # =============================================

                else:

                    if value == "" and column.nullable:
                        value = None

                setattr(row, name, value)

        # =====================================================
        # ОДИН COMMIT НА ВСЮ ТАБЛИЦУ
        # =====================================================

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    return jsonify({
        "success": True,
        "message": "Все изменения сохранены"
    })

    # -----------------------------------------------------
    # ИЩЕМ ЗАПИСЬ
    # -----------------------------------------------------

    filters = {}

    for key in primary_keys:

        if key not in data:
            return jsonify({
                "success": False,
                "error": f"Не передан ключ {key}"
            }), 400

        filters[key] = data[key]

    row = model.query.filter_by(**filters).first()

    if not row:
        return jsonify({
            "success": False,
            "error": "Запись не найдена"
        }), 404

    # -----------------------------------------------------
    # ОБНОВЛЯЕМ
    # -----------------------------------------------------


    for column in model.__table__.columns:

        name = column.name

        # Первичный ключ не изменяем
        if column.primary_key:
            continue

        # Пароль специально не редактируем через эту страницу
        if table_name == "User" and name == "password_hash":
            continue

        if name not in data:
            continue

        value = data[name]

        # Пустая строка -> NULL
        if value == "":
            if column.nullable:
                value = None

        # JSON
        if str(column.type).upper().startswith("JSON"):

            if value in ("", None):
                value = []

            elif isinstance(value, str):

                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    return jsonify({
                        "success": False,
                        "error": f"Некорректный JSON в поле {name}"
                    }), 400

        # Integer
        elif str(column.type).upper().startswith("INTEGER"):

            if value not in ("", None):
                try:
                    value = int(value)
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": f"Поле {name} должно быть числом"
                    }), 400

        # Float
        elif str(column.type).upper().startswith("FLOAT"):

            if value not in ("", None):
                try:
                    value = float(value)
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": f"Поле {name} должно быть числом"
                    }), 400

        setattr(row, name, value)

    try:

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    return jsonify({
        "success": True
    })

@app.post("/admin/bd/<table_name>/update-all")
@admin_required
def admin_bd_update_all(table_name):

    model = ADMIN_DB_MODELS.get(table_name)

    if not model:
        return jsonify({
            "success": False,
            "error": "Неизвестная таблица"
        }), 404

    data = request.get_json()

    if not data or "rows" not in data:
        return jsonify({
            "success": False,
            "error": "Не переданы строки"
        }), 400

    rows = data["rows"]

    if not isinstance(rows, list):
        return jsonify({
            "success": False,
            "error": "Поле rows должно быть списком"
        }), 400

    # -----------------------------------------------------
    # ПОЛУЧАЕМ ПЕРВИЧНЫЕ КЛЮЧИ
    # -----------------------------------------------------

    primary_keys = [
        column.name
        for column in model.__table__.columns
        if column.primary_key
    ]

    if not primary_keys:
        return jsonify({
            "success": False,
            "error": "У таблицы нет первичного ключа"
        }), 400

    import json

    try:

        # =================================================
        # ОБРАБОТКА ВСЕХ СТРОК
        # =================================================

        for row_data in rows:

            if not isinstance(row_data, dict):
                raise ValueError(
                    "Некорректный формат строки"
                )

            # ---------------------------------------------
            # ИЩЕМ ПЕРВИЧНЫЙ КЛЮЧ
            # ---------------------------------------------

            filters = {}

            for key in primary_keys:

                if key not in row_data:
                    raise ValueError(
                        f"Не передан первичный ключ: {key}"
                    )

                filters[key] = row_data[key]

            # ---------------------------------------------
            # ИЩЕМ ЗАПИСЬ В БД
            # ---------------------------------------------

            row = model.query.filter_by(
                **filters
            ).first()

            if not row:

                raise ValueError(
                    "Запись с ключом "
                    + ", ".join(
                        f"{key}={row_data[key]}"
                        for key in primary_keys
                    )
                    + " не найдена"
                )

            # ---------------------------------------------
            # ОБНОВЛЯЕМ КОЛОНКИ
            # ---------------------------------------------

            for column in model.__table__.columns:

                name = column.name

                # Первичный ключ НЕ изменяем
                if column.primary_key:
                    continue

                # Пароль пользователя НЕ редактируем
                if (
                    table_name == "User"
                    and name == "password_hash"
                ):
                    continue

                # Если такого поля нет в отправленных данных
                if name not in row_data:
                    continue

                value = row_data[name]

                column_type = str(
                    column.type
                ).upper()

                # =========================================
                # NULL
                # =========================================

                if value == "":

                    if column.nullable:
                        value = None

                # =========================================
                # JSON
                # =========================================

                if column_type.startswith("JSON"):

                    if value in ("", None):

                        value = []

                    elif isinstance(value, str):

                        try:

                            value = json.loads(value)

                        except json.JSONDecodeError:

                            raise ValueError(
                                f"Некорректный JSON "
                                f"в поле {name}"
                            )

                # =========================================
                # INTEGER
                # =========================================

                elif column_type.startswith("INTEGER"):

                    if value not in ("", None):

                        try:

                            value = int(value)

                        except (ValueError, TypeError):

                            raise ValueError(
                                f"Поле {name} "
                                f"должно быть числом"
                            )

                # =========================================
                # FLOAT
                # =========================================

                elif column_type.startswith("FLOAT"):

                    if value not in ("", None):

                        try:

                            value = float(value)

                        except (ValueError, TypeError):

                            raise ValueError(
                                f"Поле {name} "
                                f"должно быть числом"
                            )

                # =========================================
                # BOOLEAN
                # =========================================

                elif column_type.startswith("BOOLEAN"):

                    if isinstance(value, str):

                        value_lower = value.lower()

                        if value_lower in (
                            "true",
                            "1",
                            "yes",
                            "да"
                        ):

                            value = True

                        elif value_lower in (
                            "false",
                            "0",
                            "no",
                            "нет"
                        ):

                            value = False

                        elif value == "":

                            value = None

                        else:

                            raise ValueError(
                                f"Поле {name} "
                                f"должно быть True/False"
                            )

                # =========================================
                # ЗАПИСЫВАЕМ ЗНАЧЕНИЕ
                # =========================================

                setattr(
                    row,
                    name,
                    value
                )

        # =================================================
        # СОХРАНЯЕМ ВСЮ ТАБЛИЦУ ОДНИМ COMMIT
        # =================================================

        db.session.commit()

    except Exception as e:

        # ---------------------------------------------
        # ЕСЛИ ОШИБКА — ОТКАТ ВСЕХ ИЗМЕНЕНИЙ
        # ---------------------------------------------

        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    return jsonify({
        "success": True,
        "message": "Все изменения сохранены"
    })

@app.post("/admin/bd/<table_name>/delete")
@admin_required
def admin_bd_delete(table_name):

    model = ADMIN_DB_MODELS.get(table_name)

    if not model:
        return jsonify({
            "success": False,
            "error": "Неизвестная таблица"
        }), 404

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "Нет данных"
        }), 400

    primary_keys = [
        column.name
        for column in model.__table__.columns
        if column.primary_key
    ]

    filters = {}

    for key in primary_keys:

        if key not in data:
            return jsonify({
                "success": False,
                "error": f"Не передан ключ {key}"
            }), 400

        filters[key] = data[key]

    row = model.query.filter_by(**filters).first()

    if not row:
        return jsonify({
            "success": False,
            "error": "Запись не найдена"
        }), 404

    try:

        db.session.delete(row)
        db.session.commit()

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    return jsonify({
        "success": True
    })

########################################################################################################################################################

@app.route("/o-nas")
def onas():
    return render_template("o-nas.html")

########################################################################################################################################################

@app.route("/politic")
def politic():
    return render_template("politic.html")

########################################################################################################################################################

@app.route("/verify/telegram", methods=["POST"])
def verify_telegram():

    print("====================================")
    print("VERIFY TELEGRAM: REQUEST")

    # =====================================================
    # ПРОВЕРЯЕМ АВТОРИЗАЦИЮ
    # =====================================================

    if "user_id" not in session:

        print("ERROR: user_id нет в session")

        return jsonify({
            "success": False,
            "error": "Необходимо войти в аккаунт"
        }), 401

    user_id = session["user_id"]

    print("user_id:", user_id)

    # =====================================================
    # ПОЛУЧАЕМ USER
    # =====================================================

    user = db.session.get(User, user_id)

    if not user:

        print("ERROR: пользователь не найден")

        return jsonify({
            "success": False,
            "error": "Пользователь не найден"
        }), 404

    print("user:", user.name)
    print("phone_verified:", user.phone_verified)
    print("tg:", user.tg)

    # =====================================================
    # УЖЕ ПОДТВЕРЖДЁН
    # =====================================================

    if user.phone_verified:

        return jsonify({
            "success": False,
            "error": "Аккаунт уже подтверждён"
        }), 400

    # =====================================================
    # УДАЛЯЕМ СТАРЫЕ VERIFICATION
    # =====================================================

    Verification.query.filter_by(
        user_id=user_id,
        method="telegram"
    ).delete(
        synchronize_session=False
    )

    # =====================================================
    # СОЗДАЁМ НОВЫЙ TOKEN
    # =====================================================

    token = secrets.token_urlsafe(32)

    now = datetime.now(timezone.utc)

    verification = Verification(
        user_id=user_id,
        token=token,
        method="telegram",
        telegram_id=None,
        created_at=now,
        expires_at=now + timedelta(minutes=10)
    )

    db.session.add(verification)

    try:

        db.session.commit()

        print("VERIFICATION СОЗДАНА")
        print("ID:", verification.id)
        print("TOKEN:", token)

    except Exception as e:

        db.session.rollback()

        print("ОШИБКА COMMIT:")
        print(repr(e))

        return jsonify({
            "success": False,
            "error": "Ошибка создания подтверждения"
        }), 500

    # =====================================================
    # TELEGRAM DEEP LINK
    # =====================================================

    bot_username = "tennis_lavka_bot"

    telegram_url = (
        f"https://t.me/{bot_username}"
        f"?start={token}"
    )

    print("TELEGRAM URL:", telegram_url)
    print("====================================")

    return jsonify({
        "success": True,
        "telegram_url": telegram_url
    })

########################################################################################################################################################
#########################################################################################################################################################
##########################################################################################################################################################




if __name__ == "__main__":
    # инициализируем базу (создаст файл DB_PATH, если его нет)
    with app.app_context():
        db.create_all()
    # запускаем сервер для разработки
    app.run(host="0.0.0.0", port=5001, debug=True)
