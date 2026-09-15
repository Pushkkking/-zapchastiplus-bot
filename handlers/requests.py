from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from database.cars import get_cars
from database.users import get_name, get_phone, get_username, save_phone
from database.requests import create_request, get_requests, get_request
from keyboards.keyboards import main_menu, back_keyboard, request_phone_keyboard
from config import OWNER_ID
from states import MENU, REQUEST_CAR, REQUEST_VIN, REQUEST_TEXT, REQUEST_PHONE, REQUEST_LIST, REQUEST_DETAILS


def car_title(car):
    _, make, model, year, _, _ = car
    return f'🚗 {make} {model}' + (f' {year}' if year else '')


async def start_request(update, context):
    context.user_data.clear()
    cars = get_cars(update.effective_user.id)
    if cars:
        context.user_data['cars'] = cars
        await update.message.reply_text(
            'Выберите автомобиль:',
            reply_markup=ReplyKeyboardMarkup(
                [[car_title(c)] for c in cars] + [['➕ Другой автомобиль'], ['⬅️ Назад']],
                resize_keyboard=True,
            ),
        )
        return REQUEST_CAR
    await update.message.reply_text(
        'Введите VIN автомобиля.\n\nVIN состоит из 17 символов.',
        reply_markup=back_keyboard(),
    )
    return REQUEST_VIN


async def request_car(update, context):
    t = update.message.text.strip()
    if t == '⬅️ Назад':
        return await back_to_menu(update, context)
    if t == '➕ Другой автомобиль':
        await update.message.reply_text(
            'Введите VIN автомобиля.\n\nVIN состоит из 17 символов.',
            reply_markup=back_keyboard(),
        )
        return REQUEST_VIN
    for c in context.user_data.get('cars', []):
        if t == car_title(c):
            context.user_data['request_car'] = {
                'car_id': c[0], 'make': c[1], 'model': c[2],
                'year': c[3], 'vin': c[4], 'plate': c[5],
            }
            await update.message.reply_text(
                'Что требуется подобрать?',
                reply_markup=back_keyboard(),
            )
            return REQUEST_TEXT
    return REQUEST_CAR


async def request_vin(update, context):
    vin = update.message.text.strip().upper()
    if vin == '⬅️ Назад':
        return await back_to_menu(update, context)
    if len(vin) != 17:
        await update.message.reply_text('VIN должен состоять ровно из 17 символов.')
        return REQUEST_VIN
    context.user_data['request_car'] = {
        'car_id': None, 'make': '', 'model': '', 'year': '', 'vin': vin, 'plate': ''
    }
    await update.message.reply_text('Что требуется подобрать?', reply_markup=back_keyboard())
    return REQUEST_TEXT


async def request_text(update, context):
    t = update.message.text.strip()
    if t == '⬅️ Назад':
        return await back_to_menu(update, context)
    if len(t) < 2:
        await update.message.reply_text('Напишите, пожалуйста, что требуется подобрать.')
        return REQUEST_TEXT
    context.user_data['request_text'] = t
    phone = get_phone(update.effective_user.id)
    if phone:
        await save_and_send(update, context, phone)
        await update.message.reply_text(
            'Заявка отправлена! ✅\n\nМы свяжемся с вами после подбора.',
            reply_markup=main_menu(),
        )
        context.user_data.clear()
        return MENU
    await update.message.reply_text(
        'Оставьте номер телефона, чтобы мы могли с вами связаться.',
        reply_markup=request_phone_keyboard(),
    )
    return REQUEST_PHONE


async def request_phone(update, context):
    if update.message.contact:
        phone = update.message.contact.phone_number
        save_phone(update.effective_user.id, phone)
    else:
        phone = update.message.text.strip()
    if phone == '⬅️ Назад':
        return await back_to_menu(update, context)
    if phone == 'Пропустить':
        phone = 'не указан'
    elif len(phone) < 5:
        await update.message.reply_text(
            'Введите номер телефона или воспользуйтесь кнопкой отправки номера.'
        )
        return REQUEST_PHONE
    else:
        save_phone(update.effective_user.id, phone)
    await save_and_send(update, context, phone)
    await update.message.reply_text(
        'Заявка отправлена! ✅\n\nМы свяжемся с вами после подбора.',
        reply_markup=main_menu(),
    )
    context.user_data.clear()
    return MENU


async def save_and_send(update, context, phone):
    uid = update.effective_user.id
    user = update.effective_user
    car = context.user_data.get('request_car', {})
    text = context.user_data.get('request_text', '')
    rid = create_request(
        uid,
        car.get('car_id'),
        car.get('make', ''),
        car.get('model', ''),
        car.get('year', ''),
        car.get('vin', ''),
        car.get('plate', ''),
        text,
        phone,
    )
    lines = [
        f'{k}: {car[v]}'
        for k, v in [('Марка', 'make'), ('Модель', 'model'), ('Год', 'year'), ('VIN', 'vin'), ('Госномер', 'plate')]
        if car.get(v)
    ]
    vehicle = '\n'.join(lines) or 'данные не указаны'
    tg = f'@{get_username(uid)}' if get_username(uid) else 'не указан'
    msg = (
        f'🔔 НОВАЯ ЗАЯВКА\n\n'
        f'📋 Заявка №{rid}\n'
        f'📌 Статус: 🆕 Новая\n\n'
        f'👤 Клиент: {get_name(uid) or "не указано"}\n'
        f'📱 Телефон: {phone}\n'
        f'💬 Telegram: {tg}\n\n'
        f'🚗 АВТОМОБИЛЬ\n{vehicle}\n\n'
        f'🔧 ЧТО НУЖНО:\n{text}'
    )
    await context.bot.send_message(chat_id=OWNER_ID, text=msg)


async def show_requests(update, context):
    rows = get_requests(update.effective_user.id)
    if not rows:
        await update.message.reply_text('📋 У вас пока нет заявок.', reply_markup=main_menu())
        return MENU
    context.user_data['request_ids'] = [r[0] for r in rows]
    kb = []
    for r in rows:
        rid, make, model, year, txt, status, created = r
        title = f'{make} {model}'.strip() or 'Автомобиль по VIN'
        kb.append([f'📋 №{rid} — {title}'])
    kb.append(['⬅️ Назад'])
    await update.message.reply_text(
        '📋 Мои заявки\n\nВыберите заявку:',
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )
    return REQUEST_LIST


async def request_list(update, context):
    t = update.message.text.strip()
    if t == '⬅️ Назад':
        return await back_to_menu(update, context)
    try:
        rid = int(t.split('№', 1)[1].split(' ', 1)[0])
    except (ValueError, IndexError):
        return REQUEST_LIST
    if rid not in context.user_data.get('request_ids', []):
        return REQUEST_LIST
    row = get_request(rid, update.effective_user.id)
    if not row:
        await update.message.reply_text('Заявка не найдена.')
        return REQUEST_LIST
    await send_request_details(update, row, False)
    return REQUEST_DETAILS


async def send_request_details(update, row, admin=False):
    rid, uid, make, model, year, vin, plate, text, phone, status, created, updated = row
    lines = []
    for label, val in [('Марка', make), ('Модель', model), ('Год', year), ('VIN', vin), ('Госномер', plate)]:
        if val:
            lines.append(f'{label}: {val}')
    vehicle = '\n'.join(lines) or 'не указан'
    msg = (
        f'📋 Заявка №{rid}\n\n'
        f'📅 Создана: {created}\n'
        f'📌 Статус: {status}\n\n'
        f'🚗 Автомобиль:\n{vehicle}\n\n'
        f'🔧 Что требуется:\n{text}\n\n'
        f'📱 Телефон: {phone or "не указан"}'
    )
    kb = [['⬅️ К заявкам']]
    await update.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )


async def request_details(update, context):
    t = update.message.text.strip()
    if t == '⬅️ К заявкам':
        return await show_requests(update, context)
    return REQUEST_DETAILS


async def back_to_menu(update, context):
    context.user_data.clear()
    name = get_name(update.effective_user.id)
    await update.message.reply_text(
        f'Здравствуйте, {name or "клиент"}! 👋\n\nЧем могу помочь?',
        reply_markup=main_menu(),
    )
    return MENU
