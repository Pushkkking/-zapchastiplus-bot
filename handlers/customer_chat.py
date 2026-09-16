import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database.messages import create_message, get_user_messages
from database.requests import get_request
from database.orders import get_order
from keyboards.keyboards import main_menu
from states import MENU, CUSTOMER_MESSAGE
from config import OWNER_ID
from database.users import get_name, get_phone, get_username

logger = logging.getLogger(__name__)


def chat_keyboard():
    return ReplyKeyboardMarkup([
        ['💬 Написать сообщение'],
        ['📖 История переписки'],
        ['⬅️ Назад'],
    ], resize_keyboard=True)


async def show_chat(update, context):
    await update.message.reply_text(
        '💬 Связаться с «Запчасти+»\n\n'
        'Здесь можно задать вопрос, уточнить вариант запчасти или обсудить заказ.',
        reply_markup=chat_keyboard(),
    )
    return MENU


def _context_for(user_id, target_type, target_id):
    request_id = target_id if target_type == 'request' else None
    order_id = target_id if target_type == 'order' else None
    request = get_request(target_id, user_id) if request_id else None
    order = get_order(target_id) if order_id else None
    if order and order[2] != user_id:
        order = None
    if request_id and not request:
        request_id = None
    if order_id and not order:
        order_id = None
    make = model = year = plate = None
    if order:
        make, model, year, plate = order[7], order[8], order[9], order[11]
    elif request:
        make, model, year, plate = request[2], request[3], request[4], request[6]
    car = ' '.join(str(x) for x in [make, model, year] if x).strip() or 'не указан'
    if plate:
        car += f' — {plate}'
    return request_id, order_id, car


async def start_customer_reply(update, context):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(':')
    if len(parts) != 3:
        return MENU
    target_type = parts[1]
    try:
        target_id = int(parts[2])
    except ValueError:
        return MENU
    user_id = update.effective_user.id
    request_id, order_id, car = _context_for(user_id, target_type, target_id)
    if target_type != 'general' and not (request_id or order_id):
        await query.message.reply_text('Это обращение больше недоступно. Напишите нам через раздел «Связаться с Запчасти+».')
        return MENU
    context.user_data['customer_message_request_id'] = request_id
    context.user_data['customer_message_order_id'] = order_id
    notified = False
    try:
        name = get_name(user_id) or update.effective_user.full_name or 'Клиент'
        phone = get_phone(user_id) or 'не указан'
        username = get_username(user_id)
        telegram_line = f'💬 Telegram: @{username}' if username else '💬 Telegram: не указан'
        context_line = f'🛒 Заказ №{order_id}' if order_id else (f'📋 Заявка №{request_id}' if request_id else '💬 Общее сообщение')
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                '💬 КЛИЕНТ ХОЧЕТ ЗАДАТЬ ВОПРОС\n\n'
                f'👤 Клиент: {name}\n📱 Телефон: {phone}\n{telegram_line}\n'
                f'{context_line}\n🚗 Автомобиль: {car}\n\n'
                'Клиент открыл форму сообщения и сейчас может написать вопрос.'
            ),
        )
        notified = True
    except Exception:
        logger.exception('Не удалось уведомить владельца о начале переписки, user_id=%s', user_id)
    await query.message.reply_text(
        ('💬 Я сообщил владельцу, что вы хотите связаться с «Запчасти+».\n\n' if notified else
         '⚠️ Не удалось сразу уведомить владельца, но вы всё равно можете оставить сообщение.\n\n')
        + 'Напишите ваш вопрос или сообщение следующим сообщением.',
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True),
    )
    return CUSTOMER_MESSAGE


async def receive_customer_message(update, context):
    user_id = update.effective_user.id
    request_id = context.user_data.get('customer_message_request_id')
    order_id = context.user_data.get('customer_message_order_id')
    if update.message.text:
        text = update.message.text.strip()
        message_type = 'text'; file_id = None
    elif update.message.photo:
        text = update.message.caption.strip() if update.message.caption else 'Фото от клиента'
        message_type = 'photo'; file_id = update.message.photo[-1].file_id
    elif update.message.document:
        text = update.message.caption.strip() if update.message.caption else f'Файл: {update.message.document.file_name or "без названия"}'
        message_type = 'document'; file_id = update.message.document.file_id
    else:
        await update.message.reply_text('Пожалуйста, отправьте текст, фотографию или файл.')
        return CUSTOMER_MESSAGE
    name = get_name(user_id) or update.effective_user.full_name or 'Клиент'
    phone = get_phone(user_id) or 'не указан'
    create_message(user_id, 'customer', text, request_id, order_id, message_type, file_id)
    context_line = f'🛒 Заказ №{order_id}' if order_id else (f'📋 Заявка №{request_id}' if request_id else '💬 Общее сообщение')
    header = ('💬 НОВОЕ СООБЩЕНИЕ ОТ КЛИЕНТА\n\n'
              f'👤 Клиент: {name}\n📱 Телефон: {phone}\n{context_line}\n\n💬 {text}')
    try:
        if message_type == 'photo':
            await context.bot.send_photo(chat_id=OWNER_ID, photo=file_id, caption=header)
        elif message_type == 'document':
            await context.bot.send_document(chat_id=OWNER_ID, document=file_id, caption=header)
        else:
            await context.bot.send_message(chat_id=OWNER_ID, text=header)
    except Exception:
        logger.exception('Не удалось отправить сообщение клиента владельцу, user_id=%s', user_id)
        await update.message.reply_text(
            '⚠️ Сообщение сохранено, но сейчас не удалось доставить его владельцу. Попробуйте отправить ещё раз чуть позже.',
            reply_markup=main_menu(),
        )
        return MENU
    await update.message.reply_text('✅ Сообщение отправлено. Мы ответим вам в этом чате.', reply_markup=main_menu())
    context.user_data.clear()
    return MENU
