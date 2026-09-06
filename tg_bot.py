import telebot
import secret

from telebot import types

from datetime import datetime, timezone

from app import app, db, User, Verification


# =========================================================
# TELEGRAM BOT
# =========================================================

bot = telebot.TeleBot(
    secret.API_TG_KEY
)


# =========================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# =========================================================

def get_verification(token):

    verification = Verification.query.filter_by(
        token=token,
        method="telegram"
    ).first()

    return verification


# =========================================================
# ПРОВЕРКА СРОКА
# =========================================================

def verification_expired(verification):

    now = datetime.now(timezone.utc)

    expires_at = verification.expires_at

    # SQLite может вернуть naive datetime
    if expires_at.tzinfo is None:

        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    return expires_at < now


# =========================================================
# /START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    print()
    print("========================================")
    print("TELEGRAM START")
    print("telegram_id:", message.from_user.id)
    print("username:", message.from_user.username)
    print("message:", message.text)
    print("========================================")

    # =====================================================
    # ПОЛУЧАЕМ TOKEN
    # =====================================================

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) == 1:

        bot.send_message(
            message.chat.id,
            "👋 Добро пожаловать!\n\n"
            "Этот бот используется для подтверждения "
            "аккаунтов сайта «Теннисная Лавка»."
        )

        return

    token = parts[1].strip()

    if not token:

        bot.send_message(
            message.chat.id,
            "❌ Некорректная ссылка подтверждения."
        )

        return

    # =====================================================
    # РАБОТА С БД
    # =====================================================

    with app.app_context():

        verification = get_verification(token)

        # =================================================
        # TOKEN НЕ НАЙДЕН
        # =================================================

        if not verification:

            print("ERROR: Verification не найдена")

            bot.send_message(
                message.chat.id,

                "❌ Ссылка подтверждения недействительна "
                "или уже использована.\n\n"
                "Вернитесь на сайт и создайте новую."
            )

            return

        # =================================================
        # ПРОВЕРЯЕМ СРОК
        # =================================================

        if verification_expired(verification):

            print("ERROR: token expired")

            db.session.delete(verification)
            db.session.commit()

            bot.send_message(
                message.chat.id,

                "❌ Срок действия ссылки истёк.\n\n"
                "Вернитесь на сайт и запросите "
                "новое подтверждение."
            )

            return

        # =================================================
        # ПОЛУЧАЕМ USER
        # =================================================

        user = db.session.get(
            User,
            verification.user_id
        )

        if not user:

            print("ERROR: пользователь не найден")

            db.session.delete(verification)
            db.session.commit()

            bot.send_message(
                message.chat.id,
                "❌ Пользователь сайта не найден."
            )

            return

        # =================================================
        # ПРОВЕРЯЕМ АККАУНТ
        # =================================================

        if user.phone_verified:

            print(
                "INFO: аккаунт уже подтверждён"
            )

            db.session.delete(verification)
            db.session.commit()

            bot.send_message(
                message.chat.id,

                "ℹ️ Этот аккаунт уже подтверждён."
            )

            return

        # =================================================
        # TELEGRAM ID
        # =================================================

        telegram_id = str(
            message.from_user.id
        )

        # =================================================
        # ПРОВЕРЯЕМ, НЕ ПРИВЯЗАН ЛИ TELEGRAM
        # =================================================
        #
        # Ищем другого пользователя с этим Telegram ID.
        #

        existing_user = User.query.filter(
            User.tg == telegram_id,
            User.id != user.id
        ).first()

        if existing_user:

            print(
                "ERROR: Telegram уже привязан"
            )

            bot.send_message(
                message.chat.id,

                "❌ Этот Telegram-аккаунт уже "
                "привязан к другому аккаунту "
                "«Теннисная Лавка»."
            )

            return

        # =================================================
        # ЕСЛИ TOKEN УЖЕ ПРИВЯЗАН К ДРУГОМУ TELEGRAM
        # =================================================

        if (
            verification.telegram_id
            and verification.telegram_id != telegram_id
        ):

            print(
                "ERROR: token уже используется "
                "другим Telegram"
            )

            bot.send_message(
                message.chat.id,

                "❌ Эта ссылка подтверждения уже "
                "открыта в другом Telegram-аккаунте.\n\n"
                "Создайте новую ссылку на сайте."
            )

            return

        # =================================================
        # ПРИВЯЗЫВАЕМ TOKEN К TELEGRAM
        # =================================================

        if not verification.telegram_id:

            verification.telegram_id = telegram_id

            db.session.commit()

            print(
                "Verification привязана к Telegram:",
                telegram_id
            )

        # =================================================
        # КНОПКА ПОДТВЕРЖДЕНИЯ
        # =================================================

        keyboard = types.InlineKeyboardMarkup()

        confirm_button = types.InlineKeyboardButton(
            "✅ Подтвердить аккаунт",
            callback_data=f"verify:{verification.id}"
        )

        cancel_button = types.InlineKeyboardButton(
            "❌ Отмена",
            callback_data=f"cancel:{verification.id}"
        )

        keyboard.add(confirm_button)
        keyboard.add(cancel_button)

        # =================================================
        # СООБЩЕНИЕ
        # =================================================

        bot.send_message(
            message.chat.id,

            f"🔐 Подтверждение аккаунта\n\n"

            f"Вы хотите подтвердить аккаунт "
            f"«{user.name}» на сайте "
            f"«Теннисная Лавка»?\n\n"

            f"Если это ваш аккаунт, нажмите "
            f"«Подтвердить аккаунт».",

            reply_markup=keyboard
        )


# =========================================================
# CALLBACK КНОПОК
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith(
        ("verify:", "cancel:")
    )
)
def callback_handler(call):

    print()
    print("========================================")
    print("CALLBACK")
    print("telegram_id:", call.from_user.id)
    print("callback:", call.data)
    print("========================================")

    # =====================================================
    # РАЗБИРАЕМ CALLBACK
    # =====================================================

    try:

        action, verification_id = (
            call.data.split(":", 1)
        )

        verification_id = int(
            verification_id
        )

    except Exception:

        bot.answer_callback_query(
            call.id,
            "❌ Некорректный запрос."
        )

        return

    # =====================================================
    # CANCEL
    # =====================================================

    if action == "cancel":

        with app.app_context():

            verification = db.session.get(
                Verification,
                verification_id
            )

            if verification:

                telegram_id = str(
                    call.from_user.id
                )

                # Удаляем только если
                # этот Telegram открыл verification

                if (
                    verification.telegram_id
                    == telegram_id
                ):

                    db.session.delete(
                        verification
                    )

                    db.session.commit()

        bot.answer_callback_query(
            call.id,
            "Подтверждение отменено."
        )

        try:

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,

                text=(
                    "❌ Подтверждение аккаунта отменено.\n\n"
                    "Если захотите подтвердить аккаунт, "
                    "создайте новую ссылку на сайте."
                )
            )

        except Exception as e:

            print(
                "Не удалось изменить сообщение:",
                repr(e)
            )

        return

    # =====================================================
    # VERIFY
    # =====================================================

    with app.app_context():

        verification = db.session.get(
            Verification,
            verification_id
        )

        # =================================================
        # VERIFICATION НЕ НАЙДЕНА
        # =================================================

        if not verification:

            bot.answer_callback_query(
                call.id,
                "❌ Подтверждение недействительно.",
                show_alert=True
            )

            return

        # =================================================
        # ПРОВЕРЯЕМ СРОК
        # =================================================

        if verification_expired(
            verification
        ):

            db.session.delete(
                verification
            )

            db.session.commit()

            bot.answer_callback_query(
                call.id,
                "❌ Срок действия истёк.",
                show_alert=True
            )

            try:

                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,

                    text=(
                        "❌ Срок действия подтверждения "
                        "истёк.\n\n"
                        "Вернитесь на сайт и запросите "
                        "новую ссылку."
                    )
                )

            except Exception as e:

                print(
                    "Ошибка изменения сообщения:",
                    repr(e)
                )

            return

        # =================================================
        # TELEGRAM ID
        # =================================================

        telegram_id = str(
            call.from_user.id
        )

        # =================================================
        # ПРОВЕРЯЕМ, ЧТО ЭТО ТОТ ЖЕ TELEGRAM
        # =================================================

        if verification.telegram_id != telegram_id:

            print(
                "ERROR: Telegram ID не совпадает"
            )

            bot.answer_callback_query(
                call.id,

                "❌ Это подтверждение "
                "открыто другим Telegram-аккаунтом.",

                show_alert=True
            )

            return

        # =================================================
        # ПОЛУЧАЕМ USER
        # =================================================

        user = db.session.get(
            User,
            verification.user_id
        )

        if not user:

            bot.answer_callback_query(
                call.id,
                "❌ Пользователь не найден.",
                show_alert=True
            )

            return

        # =================================================
        # ПРОВЕРЯЕМ, НЕ ПОДТВЕРЖДЁН ЛИ УЖЕ
        # =================================================

        if user.phone_verified:

            db.session.delete(
                verification
            )

            db.session.commit()

            bot.answer_callback_query(
                call.id,
                "Аккаунт уже подтверждён."
            )

            return

        # =================================================
        # ПРОВЕРЯЕМ TELEGRAM НА УНИКАЛЬНОСТЬ
        # =================================================

        existing_user = User.query.filter(
            User.tg == telegram_id,
            User.id != user.id
        ).first()

        if existing_user:

            print(
                "ERROR: Telegram уже привязан "
                "к другому пользователю"
            )

            bot.answer_callback_query(
                call.id,

                "❌ Этот Telegram уже привязан "
                "к другому аккаунту.",

                show_alert=True
            )

            return

        # =================================================
        # ПОДТВЕРЖДАЕМ АККАУНТ
        # =================================================

        user.tg = call.from_user.username
        user.tg_id = str(call.from_user.id)

        user.phone_verified = True

        # =================================================
        # УДАЛЯЕМ VERIFICATION
        # =================================================

        db.session.delete(
            verification
        )

        # =================================================
        # СОХРАНЯЕМ
        # =================================================

        try:

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print(
                "ОШИБКА COMMIT:",
                repr(e)
            )

            bot.answer_callback_query(
                call.id,

                "❌ Не удалось подтвердить аккаунт. "
                "Попробуйте ещё раз.",

                show_alert=True
            )

            return

        # =================================================
        # УСПЕХ
        # =================================================

        print()
        print("========================================")
        print("АККАУНТ ПОДТВЕРЖДЁН")
        print("USER ID:", user.id)
        print("USER NAME:", user.name)
        print("TELEGRAM ID:", telegram_id)
        print("phone_verified:", user.phone_verified)
        print("========================================")

        bot.answer_callback_query(
            call.id,
            "✅ Аккаунт подтверждён!"
        )

        # =================================================
        # МЕНЯЕМ СООБЩЕНИЕ
        # =================================================

        try:

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,

                text=(
                    "✅ Аккаунт успешно подтверждён!\n\n"

                    f"Аккаунт: «{user.name}»\n\n"

                    "Теперь ваш аккаунт "
                    "«Теннисная Лавка» подтверждён."
                )
            )

        except Exception as e:

            print(
                "Ошибка изменения сообщения:",
                repr(e)
            )


# =========================================================
# ЗАПУСК
# =========================================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("TELEGRAM BOT STARTED")
    print("========================================")

    bot.infinity_polling(
        skip_pending=True
    )