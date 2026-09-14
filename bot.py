import os
import logging
import sqlite3
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = 440464150
DB_FILE = "zapchasti_plus.db"
# Состояния
MENU, CAR_SELECT, VIN, REQUEST, PHONE = range(5)
# Добавление автомобиля
CAR_MAKE, CAR_MODEL, CAR_YEAR, CAR_VIN, CAR_PLATE = range(5, 10)
# Удаление автомобиля
CAR_DELETE = 10
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
# =========================
# БАЗА ДАННЫХ
# =========================
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            phone TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year TEXT NOT NULL,
            vin TEXT NOT NULL,
            plate TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    conn.commit()
    conn.close()
    logger.info("База данных готова.")
def save_user(user, phone=None):
    conn = get_db()
    username = user.username or ""
    full_name = user.full_name or ""
    existing = conn.execute(
        "SELECT phone FROM users WHERE telegram_id = ?",
        (user.id,),
    ).fetchone()
    if existing:
        if phone:
            conn.execute("""
                UPDATE users
                SET full_name = ?, username = ?, phone = ?
                WHERE telegram_id = ?
            """, (
                full_name,
                username,
                phone,
                user.id,
            ))
        else:
            conn.execute("""
                UPDATE users
                SET full_name = ?, username = ?
                WHERE telegram_id = ?
            """, (
                full_name,
                username,
                user.id,
            ))
    else:
        conn.execute("""
            INSERT INTO users
            (telegram_id, full_name, username, phone)
            VALUES (?, ?, ?, ?)
        """, (
            user.id,
            full_name,
            username,
            phone or "",
        ))
    conn.commit()
    conn.close()
def get_phone(telegram_id):
    conn = get_db()
    row = conn.execute(
        "SELECT phone FROM users WHERE telegram_id = ?",
        (telegram_id,),
    ).fetchone()
    conn.close()
    if row:
        return row["phone"]
    return ""
def get_cars(telegram_id):
    conn = get_db()
    cars = conn.execute("""
        SELECT *
        FROM cars
        WHERE telegram_id = ?
        ORDER BY id DESC
    """, (telegram_id,)).fetchall()
    conn.close()
    return cars
def get_car(car_id, telegram_id):
    conn = get_db()
    car = conn.execute("""
        SELECT *
        FROM cars
        WHERE id = ? AND telegram_id = ?
    """, (car_id, telegram_id)).fetchone()
    conn.close()
    return car
def add_car(telegram_id, make, model, year, vin, plate):
    conn = get_db()
    conn.execute("""
        INSERT INTO cars
        (telegram_id, make, model, year, vin, plate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        make,
        model,
        year,
        vin,
        plate,
    ))
    conn.commit()
    conn.close()
def delete_car(car_id, telegram_id):
    conn = get_db()
    conn.execute("""
        DELETE FROM cars
        WHERE id = ? AND telegram_id = ?
    """, (
        car_id,
        telegram_id,
    ))
    conn.commit()
    conn.close()
# =========================
# КЛАВИАТУРЫ
# =========================
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🔧 Подобрать запчасть"],
            ["🚗 Мои автомобили"],
            ["📱 Мой телефон"],
        ],
        resize_keyboard=True,
    )
def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [["❌ Отменить"]],
        resize_keyboard=True,
    )
def phone_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 Отправить номер",
                    request_contact=True,
                )
            ],
            ["⏭ Пропустить"],
            ["❌ Отменить"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
# =========================
# /START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    save_user(user)
    await update.message.reply_text(
        "👋 Здравствуйте!\n\n"
        "Вы обратились в «Запчасти+».\n"
        "Поможем подобрать запчасти для вашего автомобиля.\n\n"
        "Выберите действие:",
        reply_markup=main_keyboard(),
    )
    return MENU
# =========================
# ГЛАВНОЕ МЕНЮ
# =========================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🚗 Мои автомобили":
        return await my_cars(update, context)
    if text == "🔧 Подобрать запчасть":
        return await start_request(update, context)
    if text == "📱 Мой телефон":
        return await my_phone(update, context)
    return MENU
# =========================
# МОИ АВТОМОБИЛИ
# =========================
async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cars = get_cars(user.id)
    buttons = []
    if cars:
        text = "🚗 <b>Ваши автомобили:</b>\n\n"
        for i, car in enumerate(cars, 1):
            plate = car["plate"] or "не указан"
            text += (
                f"<b>{i}. {car['make']} {car['model']}</b>\n"
                f"📅 {car['year']}\n"
                f"🔑 VIN: {car['vin']}\n"
                f"🔢 Госномер: {plate}\n\n"
            )
        buttons.append(["➕ Добавить автомобиль"])
        buttons.append(["🗑 Удалить автомобиль"])
        buttons.append(["⬅️ Назад"])
    else:
        text = (
            "🚗 <b>Мои автомобили</b>\n\n"
            "У вас пока нет сохранённых автомобилей.\n\n"
            "Добавьте автомобиль один раз — "
            "и при следующих обращениях VIN вводить не придётся."
        )
        buttons.append(["➕ Добавить автомобиль"])
        buttons.append(["⬅️ Назад"])
    keyboard = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
    )
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return MENU
# =========================
# ДОБАВЛЕНИЕ АВТОМОБИЛЯ
# =========================
async def add_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_car"] = {}
    await update.message.reply_text(
        "🚗 Добавляем автомобиль.\n\n"
        "Напишите марку автомобиля.\n\n",
        reply_markup=cancel_keyboard(),
    )
    return CAR_MAKE
async def get_car_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_car"]["make"] = update.message.text.strip()
    await update.message.reply_text(
        "Теперь напишите модель.\n\n",
        reply_markup=cancel_keyboard(),
    )
    return CAR_MODEL
async def get_car_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_car"]["model"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 Напишите год выпуска.\n\n",
        reply_markup=cancel_keyboard(),
    )
    return CAR_YEAR
async def get_car_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year = update.message.text.strip()
    if not year.isdigit() or len(year) != 4:
        await update.message.reply_text(
            "⚠️ Введите год четырьмя цифрами.\n\n"
        )
        return CAR_YEAR
    context.user_data["new_car"]["year"] = year
    await update.message.reply_text(
        "🔑 Теперь отправьте VIN автомобиля.\n\n"
        "VIN обычно состоит из 17 символов.",
        reply_markup=cancel_keyboard(),
    )
    return CAR_VIN
async def get_car_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()
    if len(vin) != 17:
        await update.message.reply_text(
            "⚠️ VIN должен состоять из 17 символов.\n\n"
            "Проверьте VIN и отправьте его ещё раз."
        )
        return CAR_VIN
    context.user_data["new_car"]["vin"] = vin
    await update.message.reply_text(
        "🔢 Укажите госномер автомобиля.\n\n"
        "Например: А123АА163\n\n"
        "Если не хотите указывать номер — напишите «нет».",
        reply_markup=cancel_keyboard(),
    )
    return CAR_PLATE
async def get_car_plate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plate = update.message.text.strip()
    if plate.lower() == "нет":
        plate = ""
    context.user_data["new_car"]["plate"] = plate.upper()
    data = context.user_data["new_car"]
    user = update.effective_user
    add_car(
        user.id,
        data["make"],
        data["model"],
        data["year"],
        data["vin"],
        data["plate"],
    )
    context.user_data.pop("new_car", None)
    await update.message.reply_text(
        "✅ Автомобиль сохранён!\n\n"
        f"🚗 {data['make']} {data['model']}\n"
        f"📅 {data['year']}\n"
        f"🔑 VIN: {data['vin']}\n"
        f"🔢 Госномер: {data['plate'] or 'не указан'}",
        reply_markup=main_keyboard(),
    )
    return MENU
# =========================
# УДАЛЕНИЕ АВТОМОБИЛЯ
# =========================
async def delete_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cars = get_cars(user.id)
    if not cars:
        await update.message.reply_text(
            "У вас нет сохранённых автомобилей.",
            reply_markup=main_keyboard(),
        )
        return MENU
    buttons = []
    for i, car in enumerate(cars, 1):
        buttons.append([
            f"{i}. {car['make']} {car['model']}"
        ])
    buttons.append(["❌ Отменить"])
    await update.message.reply_text(
        "🗑 Выберите автомобиль, который хотите удалить:",
        reply_markup=ReplyKeyboardMarkup(
            buttons,
            resize_keyboard=True,
        ),
    )
    context.user_data["delete_cars"] = [car["id"] for car in cars]
    return CAR_DELETE
async def delete_car_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отменить":
        context.user_data.pop("delete_cars", None)
        await update.message.reply_text(
            "Отмена.",
            reply_markup=main_keyboard(),
        )
        return MENU
    try:
        number = int(text.split(".")[0])
    except ValueError:
        await update.message.reply_text(
            "⚠️ Выберите автомобиль кнопкой."
        )
        return CAR_DELETE
    car_ids = context.user_data.get("delete_cars", [])
    if number < 1 or number > len(car_ids):
        await update.message.reply_text(
            "⚠️ Такого автомобиля нет."
        )
        return CAR_DELETE
    car_id = car_ids[number - 1]
    user = update.effective_user
    delete_car(car_id, user.id)
    context.user_data.pop("delete_cars", None)
    await update.message.reply_text(
        "🗑 Автомобиль удалён.",
        reply_markup=main_keyboard(),
    )
    return MENU
# =========================
# НОВАЯ ЗАЯВКА
# =========================
async def start_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cars = get_cars(user.id)
    context.user_data.clear()
    if cars:
        buttons = []
        for i, car in enumerate(cars, 1):
            buttons.append([
                f"{i}. {car['make']} {car['model']} {car['year']}"
            ])
        buttons.append(["➕ Другой автомобиль"])
        buttons.append(["❌ Отменить"])
        context.user_data["request_cars"] = [
            car["id"] for car in cars
        ]
        await update.message.reply_text(
            "🚗 Для какого автомобиля нужна запчасть?",
            reply_markup=ReplyKeyboardMarkup(
                buttons,
                resize_keyboard=True,
            ),
        )
        return CAR_SELECT
    await update.message.reply_text(
        "🚗 Отправьте VIN автомобиля.\n\n"
        "Например:\n"
        "XTA12345678901234",
        reply_markup=cancel_keyboard(),
    )
    return VIN
# =========================
# ВЫБОР АВТОМОБИЛЯ
# =========================
async def select_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отменить":
        return await cancel(update, context)
    if text == "➕ Другой автомобиль":
        await update.message.reply_text(
            "🚗 Отправьте VIN автомобиля.\n\n"
            "Например:\n"
            "XTA12345678901234",
            reply_markup=cancel_keyboard(),
        )
        return VIN
    try:
        number = int(text.split(".")[0])
    except ValueError:
        await update.message.reply_text(
            "⚠️ Выберите автомобиль кнопкой."
        )
        return CAR_SELECT
    car_ids = context.user_data.get("request_cars", [])
    if number < 1 or number > len(car_ids):
        await update.message.reply_text(
            "⚠️ Такого автомобиля нет."
        )
        return CAR_SELECT
    user = update.effective_user
    car = get_car(car_ids[number - 1], user.id)
    if not car:
        await update.message.reply_text(
            "⚠️ Автомобиль не найден. Попробуйте ещё раз."
        )
        return CAR_SELECT
    context.user_data["car"] = dict(car)
    await update.message.reply_text(
        "✅ Автомобиль выбран:\n\n"
        f"🚗 {car['make']} {car['model']} {car['year']}\n"
        f"🔑 VIN: {car['vin']}\n"
        f"🔢 Госномер: {car['plate'] or 'не указан'}\n\n"
        "🔧 Теперь напишите, какие запчасти вам нужны.",
        reply_markup=cancel_keyboard(),
    )
    return REQUEST
# =========================
# VIN ДЛЯ НОВОЙ ЗАЯВКИ
# =========================
async def get_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()
    if len(vin) != 17:
        await update.message.reply_text(
            "⚠️ VIN должен состоять из 17 символов.\n\n"
            "Проверьте VIN и отправьте его ещё раз."
        )
        return VIN
    context.user_data["vin"] = vin
    await update.message.reply_text(
        "✅ VIN получил.\n\n"
        "🔧 Теперь напишите, какие запчасти вам нужны.\n\n"
        "Можно указать несколько деталей одним сообщением.",
        reply_markup=cancel_keyboard(),
    )
    return REQUEST
# =========================
# ЗАПРОС ЗАПЧАСТЕЙ
# =========================
async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.message.text.strip()
    context.user_data["request"] = request
    user = update.effective_user
    phone = get_phone(user.id)
    if phone:
        return await send_request(update, context)
    await update.message.reply_text(
        "📱 Хотите оставить номер телефона, чтобы мы могли "
        "быстрее связаться с вами?\n\n"
        "Можно отправить свой номер кнопкой ниже "
        "или пропустить этот шаг.",
        reply_markup=phone_keyboard(),
    )
    return PHONE
# =========================
# ТЕЛЕФОН
# =========================
async def get_phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.message.contact:
        phone = update.message.contact.phone_number
        save_user(
            user,
            phone=phone,
        )
        await update.message.reply_text(
            "✅ Номер сохранён.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return await send_request(update, context)
    text = update.message.text.strip()
    if text == "⏭ Пропустить":
        return await send_request(update, context)
    if text == "❌ Отменить":
        return await cancel(update, context)
    # Если клиент ввёл номер вручную
    save_user(
        user,
        phone=text,
    )
    await update.message.reply_text(
        "✅ Номер сохранён.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return await send_request(update, context)
# =========================
# ОТПРАВКА ЗАЯВКИ ВЛАДЕЛЬЦУ
# =========================
async def send_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    request = context.user_data.get(
        "request",
        "не указан",
    )
    phone = get_phone(user.id)
    car = context.user_data.get("car")
    if car:
        car_info = (
            f"🚗 Автомобиль:\n"
            f"{car['make']} {car['model']} {car['year']}\n"
            f"🔑 VIN: {car['vin']}\n"
            f"🔢 Госномер: {car['plate'] or 'не указан'}"
        )
    else:
        vin = context.user_data.get(
            "vin",
            "не указан",
        )
        car_info = (
            f"🚗 VIN:\n{vin}"
        )
    username = (
        f"@{user.username}"
        if user.username
        else "нет username"
    )
    owner_message = (
        "🔔 НОВАЯ ЗАЯВКА «ЗАПЧАСТИ+»\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Клиент: {user.full_name}\n"
        f"📱 Username: {username}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"☎️ Телефон: {phone or 'не указан'}\n\n"
        f"{car_info}\n\n"
        f"🔧 Что требуется:\n{request}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=owner_message,
        )
        logger.info(
            "Заявка успешно отправлена владельцу. Клиент ID: %s",
            user.id,
        )
        await update.message.reply_text(
            "✅ Заявка получена!\n\n"
            "Мы проверим запчасти по вашему автомобилю, "
            "уточним наличие и цену.\n\n"
            "Спасибо, что обратились в «Запчасти+»! 🚗🔧",
            reply_markup=main_keyboard(),
        )
    except Exception as error:
        logger.exception(
            "❌ НЕ УДАЛОСЬ ОТПРАВИТЬ ЗАЯВКУ ВЛАДЕЛЬЦУ: %s",
            error,
        )
        await update.message.reply_text(
            "⚠️ Заявка принята, но произошла ошибка "
            "при передаче менеджеру.\n\n"
            "Пожалуйста, попробуйте ещё раз немного позже.",
            reply_markup=main_keyboard(),
        )
    context.user_data.clear()
    return MENU
# =========================
# МОЙ ТЕЛЕФОН
# =========================
async def my_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    phone = get_phone(user.id)
    if phone:
        await update.message.reply_text(
            f"📱 Ваш сохранённый номер:\n\n"
            f"{phone}\n\n"
            "Если хотите изменить номер — "
            "отправьте новый.",
            reply_markup=phone_keyboard(),
        )
    else:
        await update.message.reply_text(
            "📱 У вас пока не сохранён номер телефона.\n\n"
            "Отправьте его кнопкой ниже.",
            reply_markup=phone_keyboard(),
        )
    return PHONE
# =========================
# ОТМЕНА
# =========================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Действие отменено.",
        reply_markup=main_keyboard(),
    )
    return MENU
# =========================
# ОШИБКИ
# =========================
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Ошибка при обработке обновления:",
        exc_info=context.error,
    )
# =========================
# ЗАПУСК
# =========================
def main():
    logger.info("Запускаем бота «Запчасти+»...")
    init_db()
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
        ],
        states={
            # Главное меню
            MENU: [
                MessageHandler(
                    filters.Regex("^🔧 Подобрать запчасть$"),
                    start_request,
                ),
                MessageHandler(
                    filters.Regex("^🚗 Мои автомобили$"),
                    my_cars,
                ),
                MessageHandler(
                    filters.Regex("^📱 Мой телефон$"),
                    my_phone,
                ),
                MessageHandler(
                    filters.Regex("^➕ Добавить автомобиль$"),
                    add_car_start,
                ),
                MessageHandler(
                    filters.Regex("^🗑 Удалить автомобиль$"),
                    delete_car_start,
                ),
                MessageHandler(
                    filters.Regex("^⬅️ Назад$"),
                    start,
                ),
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
            ],
            # Выбор автомобиля для заявки
            CAR_SELECT: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    select_car,
                ),
            ],
            # VIN
            VIN: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_vin,
                ),
            ],
            # Что требуется
            REQUEST: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_request,
                ),
            ],
            # Телефон
            PHONE: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.CONTACT,
                    get_phone_handler,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_phone_handler,
                ),
            ],
            # Добавление автомобиля
            CAR_MAKE: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_car_make,
                ),
            ],
            CAR_MODEL: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_car_model,
                ),
            ],
            CAR_YEAR: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_car_year,
                ),
            ],
            CAR_VIN: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_car_vin,
                ),
            ],
            CAR_PLATE: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_car_plate,
                ),
            ],
            # Удаление автомобиля
            CAR_DELETE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    delete_car_select,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )
    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)
    logger.info("Бот запущен!")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )
if __name__ == "__main__":
    main()