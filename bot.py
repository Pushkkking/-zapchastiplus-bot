import logging
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
# =========================================================
# НАСТРОЙКИ
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 440464150
DB_NAME = "zapchasti_plus.db"
# =========================================================
# ЛОГИ
# =========================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# =========================================================
# СОСТОЯНИЯ БОТА
# =========================================================
(
    NAME,
    MENU,
    REQUEST_CAR,
    REQUEST_VIN,
    REQUEST_TEXT,
    REQUEST_PHONE,
    CAR_MAKE,
    CAR_MODEL,
    CAR_YEAR,
    CAR_VIN,
    CAR_PLATE,
    DELETE_CAR,
    EDIT_NAME,
    EDIT_PHONE,
) = range(14)
# =========================================================
# БАЗА ДАННЫХ
# =========================================================
def db():
    return sqlite3.connect(DB_NAME)
def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            telegram_name TEXT,
            username TEXT,
            name TEXT,
            phone TEXT
        )
    """)
    cur.execute("""
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
    # Миграция старой базы
    try:
        cur.execute("ALTER TABLE users ADD COLUMN telegram_name TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
# =========================================================
# ПОЛЬЗОВАТЕЛИ
# =========================================================
def save_user(user):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT telegram_id FROM users WHERE telegram_id = ?",
        (user.id,),
    )
    exists = cur.fetchone()
    if exists:
        cur.execute("""
            UPDATE users
            SET telegram_name = ?,
                username = ?
            WHERE telegram_id = ?
        """, (
            user.full_name,
            user.username,
            user.id,
        ))
    else:
        cur.execute("""
            INSERT INTO users
            (telegram_id, telegram_name, username, name, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user.id,
            user.full_name,
            user.username,
            None,
            None,
        ))
    conn.commit()
    conn.close()
def get_name(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM users WHERE telegram_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None
def save_name(user_id, name):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET name = ?
        WHERE telegram_id = ?
    """, (
        name,
        user_id,
    ))
    conn.commit()
    conn.close()
def get_phone(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT phone FROM users WHERE telegram_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None
def save_phone(user_id, phone):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET phone = ?
        WHERE telegram_id = ?
    """, (
        phone,
        user_id,
    ))
    conn.commit()
    conn.close()
def get_username(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username FROM users WHERE telegram_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None
# =========================================================
# АВТОМОБИЛИ
# =========================================================
def get_cars(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, make, model, year, vin, plate
        FROM cars
        WHERE telegram_id = ?
        ORDER BY id DESC
    """, (user_id,))
    cars = cur.fetchall()
    conn.close()
    return cars
def save_car(user_id, make, model, year, vin, plate):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cars
        (telegram_id, make, model, year, vin, plate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        make,
        model,
        year,
        vin,
        plate,
    ))
    conn.commit()
    conn.close()
def delete_car(car_id, user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM cars
        WHERE id = ?
        AND telegram_id = ?
    """, (
        car_id,
        user_id,
    ))
    conn.commit()
    conn.close()
# =========================================================
# КЛАВИАТУРЫ
# =========================================================
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
def back_keyboard():
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"]],
        resize_keyboard=True,
    )
# =========================================================
# START
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    save_user(user)
    name = get_name(user.id)
    if not name:
        await update.message.reply_text(
            "Здравствуйте! 👋\n\n"
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
# =========================================================
# ИМЯ
# =========================================================
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text(
            "Пожалуйста, напишите ваше имя."
        )
        return NAME
    if len(name) > 50:
        await update.message.reply_text(
            "Имя получилось слишком длинным.\n"
            "Введите его ещё раз."
        )
        return NAME
    save_name(
        update.effective_user.id,
        name,
    )
    await update.message.reply_text(
        f"Очень приятно, {name}! 👋\n\n"
        "Теперь выберите нужное действие:",
        reply_markup=main_menu(),
    )
    return MENU
# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔧 Подобрать запчасть":
        return await start_request(update, context)
    if text == "🚗 Мои автомобили":
        return await show_cars(update, context)
    if text == "📱 Мой телефон":
        phone = get_phone(update.effective_user.id)
        if phone:
            await update.message.reply_text(
                f"📱 Ваш телефон:\n{phone}",
                reply_markup=ReplyKeyboardMarkup(
                    [
                        ["📱 Изменить телефон"],
                        ["⬅️ Назад"],
                    ],
                    resize_keyboard=True,
                ),
            )
        else:
            await update.message.reply_text(
                "📱 Номер телефона пока не указан.",
                reply_markup=main_menu(),
            )
        return MENU
    if text == "👤 Мои данные":
        return await show_my_data(update, context)
    if text == "✏️ Изменить имя":
        await update.message.reply_text(
            "Введите новое имя:",
            reply_markup=back_keyboard(),
        )
        return EDIT_NAME
    if text == "📱 Изменить телефон":
        await update.message.reply_text(
            "Введите новый номер телефона:",
            reply_markup=back_keyboard(),
        )
        return EDIT_PHONE
    if text == "➕ Добавить автомобиль":
        return await add_car_start(update, context)
    if text == "🗑 Удалить автомобиль":
        return await delete_car_start(update, context)
    if text == "⬅️ Назад":
        name = get_name(update.effective_user.id)
        await update.message.reply_text(
            f"Здравствуйте, {name}! 👋",
            reply_markup=main_menu(),
        )
        return MENU
    return MENU
# =========================================================
# МОИ ДАННЫЕ
# =========================================================
async def show_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = get_name(user_id)
    phone = get_phone(user_id)
    await update.message.reply_text(
        "👤 Мои данные\n\n"
        f"Имя: {name or 'не указано'}\n"
        f"Телефон: {phone or 'не указан'}",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["✏️ Изменить имя"],
                ["📱 Изменить телефон"],
                ["⬅️ Назад"],
            ],
            resize_keyboard=True,
        ),
    )
    return MENU
# =========================================================
# ИЗМЕНЕНИЕ ИМЕНИ
# =========================================================
async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await show_my_data(update, context)
    if len(text) < 2 or len(text) > 50:
        await update.message.reply_text(
            "Пожалуйста, введите корректное имя."
        )
        return EDIT_NAME
    save_name(
        update.effective_user.id,
        text,
    )
    await update.message.reply_text(
        "Имя успешно изменено ✅",
        reply_markup=main_menu(),
    )
    return MENU
# =========================================================
# ИЗМЕНЕНИЕ ТЕЛЕФОНА
# =========================================================
async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
    if phone == "⬅️ Назад":
        return await show_my_data(update, context)
    save_phone(
        update.effective_user.id,
        phone,
    )
    await update.message.reply_text(
        "Номер телефона сохранён ✅",
        reply_markup=main_menu(),
    )
    return MENU
# =========================================================
# НОВАЯ ЗАЯВКА
# =========================================================
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
        return REQUEST_CAR
    await update.message.reply_text(
        "Введите VIN автомобиля.\n\n"
        "VIN состоит из 17 символов.",
        reply_markup=back_keyboard(),
    )
    return REQUEST_VIN
# =========================================================
# ВЫБОР АВТО
# =========================================================
async def request_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await back_to_menu(update, context)
    if text == "➕ Другой автомобиль":
        await update.message.reply_text(
            "Введите VIN автомобиля.\n\n"
            "VIN состоит из 17 символов.",
            reply_markup=back_keyboard(),
        )
        return REQUEST_VIN
    cars = context.user_data.get("cars", [])
    for car in cars:
        car_id, make, model, year, vin, plate = car
        title = f"🚗 {make} {model}"
        if year:
            title += f" {year}"
        if text == title:
            context.user_data["request_car"] = {
                "make": make,
                "model": model,
                "year": year,
                "vin": vin,
                "plate": plate,
            }
            await update.message.reply_text(
                "Что требуется подобрать?",
                reply_markup=back_keyboard(),
            )
            return REQUEST_TEXT
    return REQUEST_CAR
# =========================================================
# VIN ДЛЯ НОВОЙ ЗАЯВКИ
# =========================================================
async def request_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()
    if vin == "⬅️ Назад":
        return await back_to_menu(update, context)
    if len(vin) != 17:
        await update.message.reply_text(
            "VIN должен состоять ровно из 17 символов."
        )
        return REQUEST_VIN
    context.user_data["request_car"] = {
        "make": "",
        "model": "",
        "year": "",
        "vin": vin,
        "plate": "",
    }
    await update.message.reply_text(
        "Что требуется подобрать?",
        reply_markup=back_keyboard(),
    )
    return REQUEST_TEXT
# =========================================================
# ТРЕБУЕМАЯ ЗАПЧАСТЬ
# =========================================================
async def request_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await back_to_menu(update, context)
    if len(text) < 2:
        await update.message.reply_text(
            "Напишите, пожалуйста, что требуется подобрать."
        )
        return REQUEST_TEXT
    context.user_data["request_text"] = text
    phone = get_phone(update.effective_user.id)
    if phone:
        await send_request(update, context, phone)
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
        "Оставьте номер телефона, чтобы мы могли с вами связаться.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return REQUEST_PHONE
# =========================================================
# ТЕЛЕФОН ПРИ ЗАЯВКЕ
# =========================================================
async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        save_phone(
            update.effective_user.id,
            phone,
        )
        await send_request(update, context, phone)
        await update.message.reply_text(
            "Заявка отправлена! ✅\n\n"
            "Мы свяжемся с вами после подбора.",
            reply_markup=main_menu(),
        )
        return MENU
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await back_to_menu(update, context)
    if text == "Пропустить":
        await send_request(
            update,
            context,
            "не указан",
        )
        await update.message.reply_text(
            "Заявка отправлена! ✅",
            reply_markup=main_menu(),
        )
        return MENU
    if len(text) < 5:
        await update.message.reply_text(
            "Введите номер телефона или воспользуйтесь кнопкой отправки номера."
        )
        return REQUEST_PHONE
    save_phone(
        update.effective_user.id,
        text,
    )
    await send_request(update, context, text)
    await update.message.reply_text(
        "Заявка отправлена! ✅\n\n"
        "Мы свяжемся с вами после подбора.",
        reply_markup=main_menu(),
    )
    return MENU
# =========================================================
# ОТПРАВКА ЗАЯВКИ ВЛАДЕЛЬЦУ
# =========================================================
async def send_request(update, context, phone):
    user = update.effective_user
    user_id = user.id
    customer_name = get_name(user_id)
    username = get_username(user_id)
    car = context.user_data.get("request_car", {})
    request_text_value = context.user_data.get(
        "request_text",
        "",
    )
    vehicle_lines = []
    if car.get("make"):
        vehicle_lines.append(
            f"Марка: {car['make']}"
        )
    if car.get("model"):
        vehicle_lines.append(
            f"Модель: {car['model']}"
        )
    if car.get("year"):
        vehicle_lines.append(
            f"Год: {car['year']}"
        )
    if car.get("vin"):
        vehicle_lines.append(
            f"VIN: {car['vin']}"
        )
    if car.get("plate"):
        vehicle_lines.append(
            f"Госномер: {car['plate']}"
        )
    vehicle_text = "\n".join(vehicle_lines)
    telegram_text = (
        f"@{username}"
        if username
        else "не указан"
    )
    message = (
        "🔔 НОВАЯ ЗАЯВКА\n\n"
        f"👤 Клиент: {customer_name or 'не указано'}\n"
        f"📱 Телефон: {phone}\n"
        f"💬 Telegram: {telegram_text}\n\n"
        "🚗 АВТОМОБИЛЬ\n"
        f"{vehicle_text or 'данные не указаны'}\n\n"
        "🔧 ЧТО НУЖНО:\n"
        f"{request_text_value}"
    )
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=message,
    )
# =========================================================
# МОИ АВТОМОБИЛИ
# =========================================================
async def show_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cars = get_cars(update.effective_user.id)
    if not cars:
        await update.message.reply_text(
            "У вас пока нет сохранённых автомобилей.",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["➕ Добавить автомобиль"],
                    ["⬅️ Назад"],
                ],
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
    await update.message.reply_text(
        "Ваши автомобили:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return MENU
# =========================================================
# ДОБАВЛЕНИЕ АВТО
# =========================================================
async def add_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_car"] = {}
    await update.message.reply_text(
        "Введите марку автомобиля:",
        reply_markup=back_keyboard(),
    )
    return CAR_MAKE
async def car_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await show_cars(update, context)
    if len(text) < 1:
        await update.message.reply_text(
            "Введите марку автомобиля."
        )
        return CAR_MAKE
    context.user_data["new_car"]["make"] = text
    await update.message.reply_text(
        "Введите модель автомобиля:",
        reply_markup=back_keyboard(),
    )
    return CAR_MODEL
async def car_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await show_cars(update, context)
    if len(text) < 1:
        await update.message.reply_text(
            "Введите модель автомобиля."
        )
        return CAR_MODEL
    context.user_data["new_car"]["model"] = text
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
        return await show_cars(update, context)
    if text == "Пропустить":
        text = ""
    context.user_data["new_car"]["year"] = text
    await update.message.reply_text(
        "Введите VIN автомобиля.\n\n"
        "VIN состоит из 17 символов.",
        reply_markup=back_keyboard(),
    )
    return CAR_VIN
async def car_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if text == "⬅️ Назад":
        return await show_cars(update, context)
    if len(text) != 17:
        await update.message.reply_text(
            "VIN должен состоять ровно из 17 символов."
        )
        return CAR_VIN
    context.user_data["new_car"]["vin"] = text
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
        return await show_cars(update, context)
    if text == "Пропустить":
        text = ""
    new_car = context.user_data.get("new_car", {})
    save_car(
        update.effective_user.id,
        new_car.get("make", ""),
        new_car.get("model", ""),
        new_car.get("year", ""),
        new_car.get("vin", ""),
        text,
    )
    context.user_data.clear()
    await update.message.reply_text(
        "Автомобиль сохранён ✅",
        reply_markup=main_menu(),
    )
    return MENU
# =========================================================
# УДАЛЕНИЕ АВТО
# =========================================================
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
async def delete_car_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()
    if text == "⬅️ Назад":
        return await show_cars(update, context)
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
# =========================================================
# НАЗАД В МЕНЮ
# =========================================================
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    name = get_name(update.effective_user.id)
    await update.message.reply_text(
        f"Здравствуйте, {name}! 👋\n\n"
        "Чем могу помочь?",
        reply_markup=main_menu(),
    )
    return MENU
# =========================================================
# ОТМЕНА
# =========================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await back_to_menu(update, context)
# =========================================================
# ЗАПУСК
# =========================================================
def main():
    init_db()
    if not BOT_TOKEN:
        raise ValueError(
            "Не найдена переменная BOT_TOKEN в Railway."
        )
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )
    conversation = ConversationHandler(
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
                    filters.TEXT & ~filters.COMMAND,
                    menu_handler,
                )
            ],
            REQUEST_CAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_car,
                )
            ],
            REQUEST_VIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_vin,
                )
            ],
            REQUEST_TEXT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_text,
                )
            ],
            REQUEST_PHONE: [
                MessageHandler(
                    filters.CONTACT,
                    request_phone,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_phone,
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
                    filters.CONTACT,
                    edit_phone,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    edit_phone,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
    )
    application.add_handler(conversation)
    print("Бот запущен...")
    application.run_polling()
if __name__ == "__main__":
    main()