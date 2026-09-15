from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import OWNER_ID
from database.requests import get_request, get_offer
from database.orders import create_order, get_order_by_request, get_order_spent
from database.cashback import get_balance
from database.loyalty import parse_amount
from keyboards.keyboards import main_menu, order_confirm_keyboard
from states import MENU, PROMO_CODE, PROFILE_MENU


def _cashback_max(user_id, offer_text):
    amount = parse_amount(offer_text)
    balance = get_balance(user_id)
    return round(min(balance, amount * 0.5), 2)


async def cashback_use_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if not request or request[9] != '💰 Предложение готово':
        await query.edit_message_text('Предложение уже недоступно для оформления.')
        return MENU
    offer = get_offer(request_id) or ''
    max_cashback = _cashback_max(user_id, offer)
    if max_cashback <= 0:
        await query.edit_message_text('Сейчас доступного кешбэка для этого заказа нет.')
        return MENU
    balance = get_balance(user_id)
    # Для подтверждения используем inline-кнопки прямо под сообщением.
    await query.edit_message_text(
        '💳 Использовать кешбэк?\n\n'
        f'Доступно на карте: {balance:,.2f} ₽\n'.replace(',', ' ')
        + f'Можно списать: до {max_cashback:,.2f} ₽\n\n'.replace(',', ' ')
          + 'Ограничение — не более 50% стоимости заказа.\n'
            'Списываем максимально доступную сумму.',
        reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f'✅ Списать {max_cashback:,.2f} ₽'.replace(',', ' '),
            callback_data=f'order_create:{request_id}:{max_cashback}',
        )],
        [InlineKeyboardButton('↩️ Без кешбэка', callback_data=f'order_create:{request_id}:0')],
        [InlineKeyboardButton('❌ Отказаться', callback_data=f'order_decline:{request_id}')],
    ]))
    return MENU


async def order_create_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return MENU
    await query.answer()
    parts = query.data.split(':')
    try:
        request_id = int(parts[1])
        cashback_used = float(parts[2]) if len(parts) > 2 else 0.0
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
            await query.edit_message_text(f'🛒 Заказ №{existing[0]} уже оформлен.\n\nСтатус: {existing[3]}')
        else:
            await query.edit_message_text('Эта заявка сейчас недоступна для оформления заказа.')
        return MENU

    offer_text = get_offer(request_id) or ''
    max_cashback = _cashback_max(user_id, offer_text)
    cashback_used = min(max(0.0, cashback_used), max_cashback)
    promo = context.user_data.pop(f'promo_{request_id}', None)
    order_id, created = create_order(request_id, user_id, cashback_used, promo)
    if not created:
        await query.edit_message_text(f'🛒 Заказ №{order_id} уже оформлен.\n\nМы свяжемся с вами для подтверждения деталей.')
        return MENU

    spent = get_order_spent(order_id)
    price = parse_amount(offer_text)
    paid = max(0.0, price - spent)
    await query.edit_message_text(
        f'🛒 Заказ №{order_id} оформлен! ✅\n\n'
        + (f'💳 Кешбэк списан: {spent:,.2f} ₽\n💰 К оплате: {paid:,.2f} ₽\n\n'.replace(',', ' ') if spent else '')
        + 'Мы получили ваш заказ и свяжемся с вами для подтверждения деталей.'
    )

    request_text = request[7]
    make, model, year, phone = request[2], request[3], request[4], request[8]
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
                + (f'\n\n💰 ЦЕНА / ПРЕДЛОЖЕНИЕ:\n{offer_text}' if offer_text else '\n\n💰 ЦЕНА / ПРЕДЛОЖЕНИЕ: не указано')
                + (f'\n\n💳 Кешбэк списан: {spent:,.2f} ₽\n💵 К оплате: {paid:,.2f} ₽'.replace(',', ' ') if spent else '')
            ),
        )
    except Exception:
        pass
    await update.effective_chat.send_message('Главное меню:', reply_markup=main_menu())
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
    await query.edit_message_text('Хорошо. Заказ не оформлен.\n\nЕсли захотите вернуться к предложению, напишите нам.')
    return MENU


async def promo_enter_handler(update, context):
    query = update.callback_query
    if not query:
        return PROMO_CODE
    await query.answer()
    try:
        request_id = int(query.data.split(':')[1])
    except Exception:
        return MENU
    request = get_request(request_id, update.effective_user.id)
    if not request or request[9] != '💰 Предложение готово':
        await query.edit_message_text('Предложение уже недоступно для оформления.')
        return MENU
    context.user_data['promo_request_id'] = request_id
    await query.edit_message_text('🎟 Введите промокод сообщением.\n\nЕсли передумали, просто нажмите «⬅️ Назад» после возврата в меню.')
    return PROMO_CODE


async def promo_apply_handler(update, context):
    code = update.message.text.strip().upper()
    request_id = context.user_data.get('promo_request_id')
    if not request_id:
        return MENU
    offer = get_offer(request_id) or ''
    from database.promos import validate_promo
    promo, error = validate_promo(code, update.effective_user.id, parse_amount(offer))
    if error:
        await update.message.reply_text(error + '\n\nВведите другой промокод.')
        return PROMO_CODE
    context.user_data[f'promo_{request_id}'] = promo
    context.user_data.pop('promo_request_id', None)
    balance = get_balance(update.effective_user.id)
    max_cashback = round(min(balance, max(0.0, parse_amount(offer) - promo['discount']) * 0.5), 2)
    await update.message.reply_text(
        f'🎟 Промокод {promo["code"]} применён!\n\nСкидка: {promo["discount"]:,.2f} ₽\n\nТеперь выберите вариант оформления заказа.'.replace(',', ' '),
        reply_markup=order_confirm_keyboard(request_id, balance, max_cashback))
    return MENU
