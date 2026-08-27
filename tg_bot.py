import telebot, secret
from app import app, db, User, Verification
from telebot import types
from datetime import datetime,timezone

bot = telebot.TeleBot(secret.API_TG_KEY)


def phone_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Отправить мой номер телефона")
    keyboard.add(button)
    return keyboard



@bot.message_handler(commands=["start"])
def start(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.send_message( message.chat.id, "Этот бот используется для функций сайта " "«Теннисная Лавка».")
        return
    token = parts[1].strip()
    with app.app_context():
        verification = Verification.query.filter_by(token=token, method="telegram").first()

        if not verification:
            bot.send_message(message.chat.id, "❌ Ссылка недействительна или уже использована.")
            return
        if verification.expires_at < datetime.now(timezone.utc):
            db.session.delete(verification)
            db.session.commit()

            bot.send_message( message.chat.id,  "❌ Срок действия ссылки истёк.\n"  "Вернитесь на сайт и запросите новую.")
            return
        user = db.session.get(
            User,
            verification.user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
            return
        verification.telegram_id = str(message.from_user.id)
        db.session.commit()
        bot.send_message(
            message.chat.id,
            "Для подтверждения номера телефона "
            f"аккаунта «{user.name}»\n\n"
            "нажмите кнопку ниже и отправьте свой номер.",
            reply_markup=phone_keyboard()
        )

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    contact = message.contact
    if not contact:
        return
    telegram_id = str(message.from_user.id)
    phone = contact.phone_number
    print(
        f"Получен контакт: "
        f"telegram_id={telegram_id}, "
        f"phone={phone}"
    )
















if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)

