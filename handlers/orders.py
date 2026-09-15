from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID
from database.requests import get_request
from database.orders import create_order, get_order_by_request
from keyboards.keyboards import main_menu, order_confirm_keyboard
from states import MENU


async def order_create_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return MENU

    await query.answer()

    try:
        request_id = int(query.data.split(':', 1)[1])
    except (ValueError, IndexError):
        return MENU

    user_id = update.effective_user.id
    request = get_request(request_id, user_id)

    if not request:
        await query.edit_message_text('Заявка не найдена.')
        return MENU

    status = request[9]
    if status != '💰 Предложение готово':
        existing = get_order_by_request(request_id, user_id)
        if existing:
            await query.edit_message_text(
                f'🛒 Заказ №{existing[0]} уже оформлен.\n\n'
                f'Статус: {existing[3]}'
            )
        else:
            await query.edit_message_text(
                'Эта заявка сейчас недоступна для оформления заказа.'
            )
        return MENU

    order_id, created = create_order(request_id, user_id)

    if not created:
        await query.edit_message_text(
            f'🛒 Заказ №{order_id} уже оформлен.\n\n'
            'Мы свяжемся с вами для подтверждения деталей.'
        )
        return MENU

    await query.edit_message_text(
        f'🛒 Заказ №{order_id} оформлен! ✅\n\n'
        'Мы получили ваш заказ и свяжемся с вами для подтверждения деталей.'
    )

    request_text = request[7]
    make = request[2]
    model = request[3]
    year = request[4]
    phone = request[8]
    car = ' '.join(str(x) for x in [make, model, year] if x).strip() or 'автомобиль по VIN'

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                '🛒 НОВЫЙ ЗАКАЗ\n\n'
                f'🛒 Заказ №{order_id}\n'
                f'📋 Заявка №{request_id}\n'
                '📌 Статус: 🆕 Новый\n\n'
                f'👤 Клиент: {update.effective_user.full_name}\n'
                f'📱 Телефон: {phone or "не указан"}\n'
                f'🚗 Автомобиль: {car}\n\n'
                f'🔧 Что требуется: {request_text}'
            ),
        )
    except Exception:
        pass

    await update.effective_chat.send_message(
        'Главное меню:',
        reply_markup=main_menu(),
    )
    return MENU


async def order_decline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return MENU

    await query.answer()

    try:
        request_id = int(query.data.split(':', 1)[1])
    except (ValueError, IndexError):
        return MENU

    request = get_request(request_id, update.effective_user.id)
    if not request:
        await query.edit_message_text('Заявка не найдена.')
        return MENU

    await query.edit_message_text(
        'Хорошо. Заказ не оформлен.\n\n'
        'Если захотите вернуться к предложению, напишите нам.'
    )
    return MENU
