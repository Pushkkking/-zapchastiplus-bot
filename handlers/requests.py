from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from database.cars import get_cars
from database.users import get_name, get_phone, get_username, save_phone
from database.requests import create_request, get_requests, get_request

from keyboards.keyboards import (
    main_menu,
    back_keyboard,
    request_phone_keyboard,
)

from config import OWNER_ID

from states import (
    MENU,
    REQUEST_CAR,
    REQUEST_VIN,
    REQUEST_TEXT,
    REQUEST_PHONE,
    REQUEST_LIST,
    REQUEST_DETAILS,
)


def car_title(car):
    _, make, model, year, _, _ = car

    title = f"🚗 {make} {model}"

    if year:
        title += f" {year}"

    return title


async def start_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    cars = get_cars(update.effective_user.id)

    if cars:
        context.user_data["cars"] = cars

        keyboard = [
            [car_title(car)]
            for car in cars
        ]

        keyboard.append(["➕ Другой автомобиль"])
        keyboard.append(["⬅️ Назад"])

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

    for car in context.user_data.get("cars", []):
        if text == car_title(car):
            context.user_data["request_car"] = {
                "car_id": car[0],
                "make": car[1],
                "model": car[2],
                "year": car[3],
                "vin": car[4],
                "plate": car[5],
            }

            await update.message.reply_text(
                "Что требуется подобрать?",
                reply_markup=back_keyboard(),
            )

            return REQUEST_TEXT

    return REQUEST_CAR


async def request_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()

    if vin == "⬅️ НАЗАД":
        return await back_to_menu(update, context)

    if vin == "⬅️ Назад":
        return await back_to_menu(update, context)

    if len(vin) != 17:
        await update.message.reply_text(
            "VIN должен состоять ровно из 17 символов."
        )

        return REQUEST_VIN

    context.user_data["request_car"] = {
        "car_id": None,
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
        await save_and_send(update, context, phone)

        await update.message.reply_text(
            "Заявка отправлена! ✅\n\n"
            "Мы свяжемся с вами после подбора.",
            reply_markup=main_menu(),
        )

        context.user_data.clear()

        return MENU

    await update.message.reply_text(
        "Оставьте номер телефона, чтобы мы могли с вами связаться.",
        reply_markup=request_phone_keyboard(),
    )

    return REQUEST_PHONE


async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    if phone == "⬅️ Назад":
        return await back_to_menu(update, context)

    if phone == "Пропустить":
        phone = "не указан"

    elif len(phone) < 5:
        await update.message.reply_text(
            "Введите номер телефона или воспользуйтесь "
            "кнопкой отправки номера."
        )

        return REQUEST_PHONE

    else:
        save_phone(
            update.effective_user.id,
            phone,
        )

    await save_and_send(update, context, phone)

    await update.message.reply_text(
        "Заявка отправлена! ✅\n\n"
        "Мы свяжемся с вами после подбора.",
        reply_markup=main_menu(),
    )

    context.user_data.clear()

    return MENU


async def save_and_send(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    phone: str,
):
    user_id = update.effective_user.id
    user = update.effective_user

    car = context.user_data.get("request_car", {})
    text = context.user_data.get("request_text", "")

    request_id = create_request(
        user_id,
        car.get("car_id"),
        car.get("make", ""),
        car.get("model", ""),
        car.get("year", ""),
        car.get("vin", ""),
        car.get("plate", ""),
        text,
        phone,
    )

    vehicle_lines = []

    fields = [
        ("Марка", "make"),
        ("Модель", "model"),
        ("Год", "year"),
        ("VIN", "vin"),
        ("Госномер", "plate"),
    ]

    for label, key in fields:
        if car.get(key):
            vehicle_lines.append(
                f"{label}: {car[key]}"
            )

    vehicle = "\n".join(vehicle_lines)

    if not vehicle:
        vehicle = "данные не указаны"

    username = get_username(user_id)

    if username:
        telegram_username = f"@{username}"
    else:
        telegram_username = "не указан"

    client_name = get_name(user_id) or "не указано"

    message = (
        "🔔 НОВАЯ ЗАЯВКА\n\n"
        f"📋 Заявка №{request_id}\n"
        "📌 Статус: 🆕 Новая\n\n"
        f"👤 Клиент: {client_name}\n"
        f"📱 Телефон: {phone}\n"
        f"💬 Telegram: {telegram_username}\n\n"
        "🚗 АВТОМОБИЛЬ\n"
        f"{vehicle}\n\n"
        "🔧 ЧТО НУЖНО:\n"
        f"{text}"
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=message,
    )


async def show_requests(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    rows = get_requests(update.effective_user.id)

    if not rows:
        await update.message.reply_text(
            "📋 У вас пока нет заявок.",
            reply_markup=main_menu(),
        )

        return MENU

    context.user_data["request_ids"] = [
        row[0]
        for row in rows
    ]

    keyboard = []

    for row in rows:
        request_id, make, model, year, text, status, created = row

        title = f"{make} {model}".strip()

        if not title:
            title = "Автомобиль по VIN"

        keyboard.append(
            [f"📋 №{request_id} — {title}"]
        )

    keyboard.append(["⬅️ Назад"])

    await update.message.reply_text(
        "📋 Мои заявки\n\n"
        "Выберите заявку:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )

    return REQUEST_LIST


async def request_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    if text == "⬅️ Назад":
        return await back_to_menu(update, context)

    try:
        request_id = int(
            text.split("№", 1)[1].split(" ", 1)[0]
        )

    except (ValueError, IndexError):
        return REQUEST_LIST

    if request_id not in context.user_data.get(
        "request_ids",
        [],
    ):
        return REQUEST_LIST

    row = get_request(
        request_id,
        update.effective_user.id,
    )

    if not row:
        await update.message.reply_text(
            "Заявка не найдена."
        )

        return REQUEST_LIST

    await send_request_details(
        update,
        row,
        False,
    )

    return REQUEST_DETAILS


async def send_request_details(
    update: Update,
    row,
    admin=False,
):
    (
        request_id,
        user_id,
        make,
        model,
        year,
        vin,
        plate,
        text,
        phone,
        status,
        created,
        updated,
    ) = row

    vehicle_lines = []

    fields = [
        ("Марка", make),
        ("Модель", model),
        ("Год", year),
        ("VIN", vin),
        ("Госномер", plate),
    ]

    for label, value in fields:
        if value:
            vehicle_lines.append(
                f"{label}: {value}"
            )

    vehicle = "\n".join(vehicle_lines)

    if not vehicle:
        vehicle = "не указан"

    message = (
        f"📋 Заявка №{request_id}\n\n"
        f"📅 Создана: {created}\n"
        f"📌 Статус: {status}\n\n"
        "🚗 Автомобиль:\n"
        f"{vehicle}\n\n"
        "🔧 Что требуется:\n"
        f"{text}\n\n"
        f"📱 Телефон: {phone or 'не указан'}"
    )

    if admin:
        message += (
            f"\n\n👤 Telegram ID внутренний: {user_id}"
        )

    if admin:
        keyboard = [
            ["🔎 Взять в работу"],
            ["💰 Предложение готово"],
            ["💬 Написать клиенту"],
            ["✅ Выполнена", "❌ Отменена"],
            ["⬅️ К заявкам"],
        ]

    else:
        keyboard = [
            ["⬅️ К заявкам"],
        ]

    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


async def request_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    if text == "⬅️ К заявкам":
        return await show_requests(update, context)

    return REQUEST_DETAILS


async def back_to_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    name = get_name(update.effective_user.id)

    await update.message.reply_text(
        f"Здравствуйте, {name or 'клиент'}! 👋\n\n"
        "Чем могу помочь?",
        reply_markup=main_menu(),
    )

    return MENU
