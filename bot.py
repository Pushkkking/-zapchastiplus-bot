import logging
import sqlite3
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = "ВСТАВЬ_СЮДА_НОВЫЙ_ТОКЕН"
OWNER_ID = 440464150
DB_NAME = "zapchasti_plus.db"
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# =========================
# СОСТОЯНИЯ
# =========================
(
    NAME,
    MENU,
    CAR_SELECT,
    VIN,
    REQUEST,
    PHONE,
    CAR_MAKE,
    CAR_MODEL,
    CAR_YEAR,
    CAR_VIN,
    CAR_PLATE,
    DELETE_CAR,
    EDIT_NAME,
    EDIT_PHONE,
) = range(14)
# =========================
# БАЗА ДАННЫХ
# =========================
def db_connect():
    return sqlite3.connect(DB_NAME)
def init_db():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            phone TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year TEXT,
            vin TEXT,
            plate TEXT
        )
    """)
    # Добавляем отдельное поле для имени клиента
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
def save_user(telegram_user):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT telegram_id FROM users WHERE telegram_id = ?",
        (telegram_user.id,),
    )
    exists = cursor.fetchone()
    if exists:
        cursor.execute("""
            UPDATE users
            SET username = ?
            WHERE telegram_id = ?
        """, (
            telegram_user.username,
            telegram_user.id,
        ))
    else:
        cursor.execute("""
            INSERT INTO users
            (telegram_id, full_name, username, phone)
            VALUES (?, ?, ?, ?)
        """, (
            telegram_user.id,
            telegram_user.full_name,
            telegram_user.username,
            None,
        ))
    conn.commit()
    conn.close()
def get_customer_name(telegram_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None
def save_customer_name(telegram_id, name):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET name = ?
        WHERE telegram_id = ?
    """, (
        name,
        telegram_id,
    ))
    conn.commit()
    conn.close()
def get_phone(telegram_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT phone FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None
def save_phone(telegram_id, phone):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET phone = ?
        WHERE telegram_id = ?
    """, (
        phone,
        telegram_id,
    ))
    conn.commit()
    conn.close()
def get_cars(telegram_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, make, model, year, vin, plate
        FROM cars
        WHERE telegram_id = ?
        ORDER BY id DESC
    """, (telegram_id,))
    cars = cursor.fetchall()
    conn.close()
    return cars
def get_car(car_id, telegram_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, make, model, year, vin, plate
        FROM cars
        WHERE id = ? AND telegram_id = ?
    """, (
        car_id,
        telegram_id,
    ))
    car = cursor.fetchone()
    conn.close()
    return car
def save_car(telegram_id, make, model, year, vin, plate):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
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
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
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
def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["🔧 Подобрать запчасть"],
            ["🚗 Мои автомобили"],
            ["📱 Мой телефон"],
            ["👤 Мои данные"],
        ],
        resize_keyboard=True,
    )
def back_menu():
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"]],
        resize_keyboard=True,
    )
# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    save_user(user)
    name = get_customer_name(user.id)
    if not name:
        await update.message.reply_text(
            "Здравствуйте!\n\n"
            "Как я могу к вам обращаться?\n\n"
            "Напишите ваше имя:"
        )
        return NAME
    await update.message.reply_text(
        f"Здравствуйте, {name}! 👋\n\n"
        "Чем могу помочь?",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# СОХРАНЕНИЕ ИМЕНИ
# =========================
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text(
            "Пожалуйста, напишите имя ещё раз."
        )
        return NAME
    if len(name) > 50:
        await update.message.reply_text(
            "Имя слишком длинное. Напишите, пожалуйста, короче."
        )
        return NAME
    save_customer_name(
        update.effective_user.id,
        name,
    )
    await update.message.reply_text(
        f"Очень приятно, {name}! 👋\n\n"
        "Теперь вы можете выбрать нужное действие:",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# ГЛАВНОЕ МЕНЮ
# =========================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔧 Подобрать запчасть":
        return await start_request(update, context)
    if text == "🚗 Мои автомобили":
        return await my_cars(update, context)
    if text == "📱 Мой телефон":
        phone = get_phone(update.effective_user.id)
        if phone:
            await update.message.reply_text(
                f"Ваш сохранённый телефон:\n{phone}",
                reply_markup=ReplyKeyboardMarkup(
                    [
                        ["📱 Изменить телефон"],
                        ["⬅️ Назад"],
                    ],
                    resize_keyboard=True,
                ),
            )
            return MENU
        await update.message.reply_text(
            "У вас пока не сохранён номер телефона.\n\n"
            "Вы можете добавить его при оформлении заявки.",
            reply_markup=main_menu(),
        )
        return MENU
    if text == "👤 Мои данные":
        return await my_data(update, context)
    if text == "⬅️ Назад":
        name = get_customer_name(update.effective_user.id)
        await update.message.reply_text(
            f"Здравствуйте, {name}! 👋",
            reply_markup=main_menu(),
        )
        return MENU
    if text == "📱 Изменить телефон":
        await update.message.reply_text(
            "Введите новый номер телефона:",
            reply_markup=back_menu(),
        )
        return EDIT_PHONE
    return MENU
# =========================
# МОИ ДАННЫЕ
# =========================
async def my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = get_customer_name(user_id)
    phone = get_phone(user_id)
    phone_text = phone if phone else "не указан"
    keyboard = [
        ["✏️ Изменить имя"],
        ["📱 Изменить телефон"],
        ["⬅️ Назад"],
    ]
    await update.message.reply_text(
        "👤 Ваши данные\n\n"
        f"Имя: {name or 'не указано'}\n"
        f"Телефон: {phone_text}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return MENU
# =========================
# ИЗМЕНЕНИЕ ИМЕНИ
# =========================
async def edit_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите новое имя:",
        reply_markup=back_menu(),
    )
    return EDIT_NAME
async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if name == "⬅️ Назад":
        return await my_data(update, context)
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text(
            "Пожалуйста, введите корректное имя."
        )
        return EDIT_NAME
    save_customer_name(
        update.effective_user.id,
        name,
    )
    await update.message.reply_text(
        f"Имя сохранено: {name} ✅",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# ИЗМЕНЕНИЕ ТЕЛЕФОНА
# =========================
async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await my_data(update, context)
    save_phone(
        update.effective_user.id,
        text,
    )
    await update.message.reply_text(
        "Номер телефона сохранён ✅",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# НОВАЯ ЗАЯВКА
# =========================
async def start_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    cars = get_cars(update.effective_user.id)
    if cars:
        keyboard = []
        for car in cars:
            car_id, make, model, year, vin, plate = car
            title = f"🚗 {make} {model}"
            if year:
                title += f" {year}"
            keyboard.append([title])
        keyboard.append(["➕ Другой автомобиль"])
        keyboard.append(["⬅️ Назад"])
        context.user_data["cars"] = cars
        await update.message.reply_text(
            "Выберите автомобиль:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
            ),
        )
        return CAR_SELECT
    await update.message.reply_text(
        "Введите VIN автомобиля.\n\n"
        "VIN состоит из 17 символов.",
        reply_markup=back_menu(),
    )
    return VIN
# =========================
# ВЫБОР СОХРАНЁННОГО АВТО
# =========================
async def car_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ Другой автомобиль":
        await update.message.reply_text(
            "Введите VIN автомобиля.\n\n"
            "VIN состоит из 17 символов.",
            reply_markup=back_menu(),
        )
        return VIN
    if text == "⬅️ Назад":
        name = get_customer_name(update.effective_user.id)
        await update.message.reply_text(
            f"Здравствуйте, {name}! 👋",
            reply_markup=main_menu(),
        )
        return MENU
    cars = context.user_data.get("cars", [])
    for car in cars:
        car_id, make, model, year, vin, plate = car
        title = f"🚗 {make} {model}"
        if year:
            title += f" {year}"
        if text == title:
            context.user_data["car"] = {
                "make": make,
                "model": model,
                "year": year,
                "vin": vin,
                "plate": plate,
            }
            await update.message.reply_text(
                "Что требуется подобрать для этого автомобиля?",
                reply_markup=back_menu(),
            )
            return REQUEST
    return CAR_SELECT
# =========================
# VIN
# =========================
async def receive_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()
    if vin == "⬅️ Назад":
        return await start_request(update, context)
    if len(vin) != 17:
        await update.message.reply_text(
            "VIN должен состоять ровно из 17 символов.\n"
            "Проверьте VIN и отправьте его ещё раз."
        )
        return VIN
    context.user_data["car"] = {
        "make": "",
        "model": "",
        "year": "",
        "vin": vin,
        "plate": "",
    }
    await update.message.reply_text(
        "Что требуется подобрать для этого автомобиля?",
        reply_markup=back_menu(),
    )
    return REQUEST
# =========================
# ЗАПРОС ЗАПЧАСТИ
# =========================
async def receive_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await start_request(update, context)
    context.user_data["request"] = text
    phone = get_phone(update.effective_user.id)
    if phone:
        await send_request_to_owner(update, context, phone)
        await update.message.reply_text(
            "Заявка отправлена! ✅\n\n"
            "Мы свяжемся с вами после подбора.",
            reply_markup=main_menu(),
        )
        return MENU
    keyboard = [
        [
            KeyboardButton(
                "📱 Отправить мой номер",
                request_contact=True,
            )
        ],
        ["Пропустить"],
        ["⬅️ Назад"],
    ]
    await update.message.reply_text(
        "Оставьте номер телефона, чтобы мы могли связаться с вами.\n\n"
        "Можно отправить номер кнопкой ниже или ввести его вручную.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return PHONE
# =========================
# ТЕЛЕФОН
# =========================
async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        save_phone(
            update.effective_user.id,
            phone,
        )
        await send_request_to_owner(update, context, phone)
        await update.message.reply_text(
            "Заявка отправлена! ✅\n\n"
            "Мы свяжемся с вами после подбора.",
            reply_markup=main_menu(),
        )
        return MENU
    text = update.message.text.strip()
    if text == "Пропустить":
        await send_request_to_owner(
            update,
            context,
            "не указан",
        )
        await update.message.reply_text(
            "Заявка отправлена! ✅",
            reply_markup=main_menu(),
        )
        return MENU
    if text == "⬅️ Назад":
        return await start_request(update, context)
    save_phone(
        update.effective_user.id,
        text,
    )
    await send_request_to_owner(update, context, text)
    await update.message.reply_text(
        "Заявка отправлена! ✅\n\n"
        "Мы свяжемся с вами после подбора.",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# ОТПРАВКА ЗАЯВКИ ВЛАДЕЛЬЦУ
# =========================
async def send_request_to_owner(update, context, phone):
    user = update.effective_user
    user_id = user.id
    name = get_customer_name(user_id)
    car = context.user_data.get("car", {})
    request = context.user_data.get("request", "")
    make = car.get("make", "")
    model = car.get("model", "")
    year = car.get("year", "")
    vin = car.get("vin", "")
    plate = car.get("plate", "")
    vehicle_lines = []
    if make:
        vehicle_lines.append(f"Марка: {make}")
    if model:
        vehicle_lines.append(f"Модель: {model}")
    if year:
        vehicle_lines.append(f"Год: {year}")
    if vin:
        vehicle_lines.append(f"VIN: {vin}")
    if plate:
        vehicle_lines.append(f"Госномер: {plate}")
    vehicle_text = "\n".join(vehicle_lines)
    username = f"@{user.username}" if user.username else "не указан"
    message = (
        "🔔 НОВАЯ ЗАЯВКА\n\n"
        f"👤 Клиент: {name or 'не указано'}\n"
        f"📱 Телефон: {phone}\n"
        f"💬 Telegram: {username}\n"
        f"🆔 Telegram ID: {user_id}\n\n"
        "🚗 АВТОМОБИЛЬ\n"
        f"{vehicle_text or 'данные не указаны'}\n\n"
        "🔧 ЧТО НУЖНО:\n"
        f"{request}"
    )
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=message,
    )
# =========================
# МОИ АВТОМОБИЛИ
# =========================
async def my_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = get_cars(update.effective_user.id)
    if not cars:
        keyboard = [
            ["➕ Добавить автомобиль"],
            ["⬅️ Назад"],
        ]
        await update.message.reply_text(
            "У вас пока нет сохранённых автомобилей.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
            ),
        )
        return MENU
    keyboard = []
    for car in cars:
        car_id, make, model, year, vin, plate = car
        title = f"🚗 {make} {model}"
        if year:
            title += f" {year}"
        keyboard.append([title])
    keyboard.append(["➕ Добавить автомобиль"])
    keyboard.append(["🗑 Удалить автомобиль"])
    keyboard.append(["⬅️ Назад"])
    context.user_data["cars"] = cars
    await update.message.reply_text(
        "Ваши автомобили:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return MENU
# =========================
# ДОБАВЛЕНИЕ АВТО
# =========================
async def add_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите марку автомобиля:",
        reply_markup=back_menu(),
    )
    return CAR_MAKE
async def car_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await my_cars(update, context)
    context.user_data["new_car_make"] = text
    await update.message.reply_text(
        "Введите модель автомобиля:"
    )
    return CAR_MODEL
async def car_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_car_model"] = text
    await update.message.reply_text(
        "Введите год выпуска или нажмите «Пропустить»:",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["Пропустить"],
                ["⬅️ Назад"],
            ],
            resize_keyboard=True,
        ),
    )
    return CAR_YEAR
async def car_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await my_cars(update, context)
    if text == "Пропустить":
        text = ""
    context.user_data["new_car_year"] = text
    await update.message.reply_text(
        "Введите VIN автомобиля.\n\n"
        "VIN состоит из 17 символов.",
        reply_markup=back_menu(),
    )
    return CAR_VIN
async def car_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if text == "⬅️ Назад":
        return await my_cars(update, context)
    if len(text) != 17:
        await update.message.reply_text(
            "VIN должен состоять ровно из 17 символов."
        )
        return CAR_VIN
    context.user_data["new_car_vin"] = text
    await update.message.reply_text(
        "Введите госномер или нажмите «Пропустить»:",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["Пропустить"],
                ["⬅️ Назад"],
            ],
            resize_keyboard=True,
        ),
    )
    return CAR_PLATE
async def car_plate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await my_cars(update, context)
    if text == "Пропустить":
        text = ""
    save_car(
        update.effective_user.id,
        context.user_data.get("new_car_make", ""),
        context.user_data.get("new_car_model", ""),
        context.user_data.get("new_car_year", ""),
        context.user_data.get("new_car_vin", ""),
        text,
    )
    context.user_data.clear()
    await update.message.reply_text(
        "Автомобиль сохранён ✅",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# УДАЛЕНИЕ АВТО
# =========================
async def delete_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = get_cars(update.effective_user.id)
    if not cars:
        await update.message.reply_text(
            "У вас нет сохранённых автомобилей.",
            reply_markup=main_menu(),
        )
        return MENU
    keyboard = []
    for car in cars:
        car_id, make, model, year, vin, plate = car
        title = f"🚗 {make} {model}"
        if year:
            title += f" {year}"
        keyboard.append([title])
    keyboard.append(["⬅️ Назад"])
    context.user_data["delete_cars"] = cars
    await update.message.reply_text(
        "Выберите автомобиль для удаления:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return DELETE_CAR
async def delete_car_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ Назад":
        return await my_cars(update, context)
    cars = context.user_data.get("delete_cars", [])
    for car in cars:
        car_id, make, model, year, vin, plate = car
        title = f"🚗 {make} {model}"
        if year:
            title += f" {year}"
        if text == title:
            delete_car(
                car_id,
                update.effective_user.id,
            )
            context.user_data.clear()
            await update.message.reply_text(
                "Автомобиль удалён ✅",
                reply_markup=main_menu(),
            )
            return MENU
    return DELETE_CAR
# =========================
# ОТМЕНА
# =========================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    name = get_customer_name(update.effective_user.id)
    await update.message.reply_text(
        f"Здравствуйте, {name or ''}! 👋\n\n"
        "Вы вернулись в главное меню.",
        reply_markup=main_menu(),
    )
    return MENU
# =========================
# ЗАПУСК
# =========================
def main():
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
            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_name,
                )
            ],
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
                    menu_handler,
                ),
                MessageHandler(
                    filters.Regex("^👤 Мои данные$"),
                    my_data,
                ),
                MessageHandler(
                    filters.Regex("^✏️ Изменить имя$"),
                    edit_name_start,
                ),
                MessageHandler(
                    filters.Regex("^📱 Изменить телефон$"),
                    menu_handler,
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
                    menu_handler,
                ),
            ],
            CAR_SELECT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_select,
                )
            ],
            VIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_vin,
                )
            ],
            REQUEST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_request,
                )
            ],
            PHONE: [
                MessageHandler(
                    filters.CONTACT,
                    receive_phone,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_phone,
                ),
            ],
            CAR_MAKE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_make,
                )
            ],
            CAR_MODEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_model,
                )
            ],
            CAR_YEAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_year,
                )
            ],
            CAR_VIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_vin,
                )
            ],
            CAR_PLATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_plate,
                )
            ],
            DELETE_CAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    delete_car_handler,
                )
            ],
            EDIT_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    edit_name,
                )
            ],
            EDIT_PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    edit_phone,
                )
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
    )
    application.add_handler(conversation_handler)
    print("Бот запущен...")
    application.run_polling()
if __name__ == "__main__":
    main()