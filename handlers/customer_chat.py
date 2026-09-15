from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from database.messages import create_message, get_user_messages
from database.requests import get_request
from database.orders import get_order
from keyboards.keyboards import main_menu
from states import MENU, CUSTOMER_MESSAGE
from config import OWNER_ID
from database.users import get_name, get_phone


def chat_keyboard():
    return ReplyKeyboardMarkup([
        ['💬 Написать сообщение'],
        ['📖 История переписки'],
        ['⬅️ Назад'],
    ], resize_keyboard=True)


async def show_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '💬 Связаться с «Запчасти+»\n\n'
        'Здесь можно задать вопрос, уточнить вариант запчасти или обсудить заказ.',
        reply_markup=chat_keyboard(),
    )
    return MENU


async def start_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['customer_message_request_id'] = None
    context.user_data['customer_message_order_id'] = None
    await update.message.reply_text(
        '💬 Напишите сообщение для «Запчасти+».\n\n'
        'Например: уточнить производителя, цену, наличие или предложить другой вариант.\n\n'
        'Для отмены нажмите /cancel',
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True),
    )
    return CUSTOMER_MESSAGE


async def start_customer_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(':')
    if len(parts) != 3:
        return MENU
    target_type, target_id = parts[1], int(parts[2])
    context.user_data['customer_message_request_id'] = target_id if target_type == 'request' else None
    context.user_data['customer_message_order_id'] = target_id if target_type == 'order' else None
    await query.message.reply_text(
        '💬 Напишите ваш вопрос или ответ для «Запчасти+».',
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True),
    )
    return CUSTOMER_MESSAGE


async def receive_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    request_id = context.user_data.get('customer_message_request_id')
    order_id = context.user_data.get('customer_message_order_id')

    if update.message.text:
        text = update.message.text.strip()
        message_type = 'text'
        file_id = None
    elif update.message.photo:
        text = update.message.caption.strip() if update.message.caption else 'Фото от клиента'
        message_type = 'photo'
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        text = update.message.caption.strip() if update.message.caption else f'Файл: {update.message.document.file_name or "без названия"}'
        message_type = 'document'
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text('Пожалуйста, отправьте текст, фотографию или файл.')
        return CUSTOMER_MESSAGE

    create_message(user_id, 'customer', text, request_id, order_id, message_type, file_id)
    name = get_name(user_id) or update.effective_user.full_name or 'Клиент'
    phone = get_phone(user_id) or 'не указан'
    context_line = f'🛒 Заказ №{order_id}' if order_id else (f'📋 Заявка №{request_id}' if request_id else '💬 Общее сообщение')
    header = (
        '💬 НОВОЕ СООБЩЕНИЕ ОТ КЛИЕНТА\n\n'
        f'👤 Клиент: {name}\n📱 Телефон: {phone}\n{context_line}\n\n'
        f'💬 {text}'
    )
    try:
        if message_type == 'photo':
            await context.bot.send_photo(chat_id=OWNER_ID, photo=file_id, caption=header)
        elif message_type == 'document':
            await context.bot.send_document(chat_id=OWNER_ID, document=file_id, caption=header)
        else:
            await context.bot.send_message(chat_id=OWNER_ID, text=header)
    except Exception:
        pass
    await update.message.reply_text('✅ Сообщение отправлено. Мы ответим вам в этом чате.', reply_markup=main_menu())
    context.user_data.clear()
    return MENU


async def show_chat_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_user_messages(update.effective_user.id, 60)
    if not rows:
        await update.message.reply_text('📖 История переписки пока пуста.', reply_markup=chat_keyboard())
        return MENU
    chunks = []
    for _, sender, text, message_type, file_id, request_id, order_id, created in rows:
        who = 'Вы' if sender == 'customer' else 'Запчасти+'
        if message_type == 'photo': text = '📷 ' + text
        elif message_type == 'document': text = '📎 ' + text
        context_text = ''
        if order_id:
            context_text = f' · заказ №{order_id}'
        elif request_id:
            context_text = f' · заявка №{request_id}'
        chunks.append(f'[{created}] {who}{context_text}:\n{text}')
    message = '📖 История переписки\n\n' + '\n\n'.join(chunks)
    if len(message) > 3900:
        message = message[-3900:]
        message = '…\n\n' + message
    await update.message.reply_text(message, reply_markup=chat_keyboard())
    return MENU
