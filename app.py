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

def logined(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        us = User.query.filter_by(id=user_id).first()

        if not us:
            return redirect(url_for("register"))

        return f(*args, **kwargs)

    return decorated_function

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
    created_at = db.Column(db.String(50))
    is_admin = db.Column(db.Integer, default=0)
    password_hash = db.Column(db.String(120))
    favorites = db.Column(db.JSON, nullable=False, default=list)
    orders = db.Column(db.JSON, nullable=False, default=list)

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
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey("news.id"), nullable=False)
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
        product.is_active = request.form.get("is_active")

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

    message_text = request.form.get("message_text", "").strip()
    if not message_text:
        return jsonify({
            "success": False,
            "error": "Пустое сообщение",
        }), 400
    
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
    print("уууааа.    ",chats)
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
#########################################################################################################################################################
#########################################################################################################################################################




if __name__ == "__main__":
    # инициализируем базу (создаст файл DB_PATH, если его нет)
    with app.app_context():
        db.create_all()
    # запускаем сервер для разработки
    app.run(host="0.0.0.0", port=5001, debug=True)
