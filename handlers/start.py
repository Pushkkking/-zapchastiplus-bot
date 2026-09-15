from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID

from database.users import (
    save_user,
    get_name,
    has_consent,
    save_consent,
    save_name,
    get_user_by_card_token,
)
from keyboards.keyboards import main_menu, consent_keyboard, admin_menu
from states import CONSENT, NAME, MENU, ADMIN_MENU


async def show_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Здравствуйте! 👋\n\n'
        'Для работы бота потребуется обработка персональных данных.\n\n'
        'Перед продолжением ознакомьтесь с политикой '
        'и подтвердите согласие отдельной кнопкой.',
        reply_markup=consent_keyboard(),
    )
    return CONSENT


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    save_user(user)

    # QR-карта постоянного клиента открывает этот deep-link на телефоне
    # сотрудника. Только владелец бота может увидеть данные клиента.
    if context.args and context.args[0].startswith('card_') and user.id == OWNER_ID:
        token = context.args[0][5:]
        customer = get_user_by_card_token(token)
        if not customer:
            await update.message.reply_text('❌ Карта не найдена.', reply_markup=admin_menu())
            return ADMIN_MENU
        from database.cashback import get_balance
        from database.loyalty import get_level, parse_amount
        from database.orders import get_user_orders
        from database.cashback import get_order_spent
        customer_id, customer_name, phone, username, card_number = customer
        total = sum(max(0.0, parse_amount(r[6]) - get_order_spent(r[0])) for r in get_user_orders(customer_id) if r[3] == '🚗 Выдан')
        level_name, rate = get_level(total)
        balance = get_balance(customer_id)
        await update.message.reply_text(
            '💳 КАРТА КЛИЕНТА\n\n'
            f'🔢 Карта: {card_number or "не указана"}\n'
            f'👤 {customer_name or "Имя не указано"}\n'
            f'📱 {phone or "Телефон не указан"}\n'
            f'💬 {("@" + username) if username else "Telegram не указан"}\n\n'
            f'🏆 Уровень: {level_name}\n'
            f'💳 Ставка: {rate}%\n'
            f'⭐ Доступно кешбэка: {balance:,.2f} ₽'.replace(',', ' '),
            reply_markup=admin_menu(),
        )
        return ADMIN_MENU

    if not has_consent(user.id):
        return await show_consent(update, context)

    name = get_name(user.id)
    if not name:
        await update.message.reply_text(
            'Как я могу к вам обращаться?\n\n'
            'Напишите ваше имя:'
        )
        return NAME

    await update.message.reply_text(
        f'Здравствуйте, {name}! 👋\n\n'
        'Чем могу помочь?',
        reply_markup=main_menu(),
    )
    return MENU


async def consent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return CONSENT

    await query.answer()

    if query.data == 'consent_no':
        await query.edit_message_text(
            'Без согласия я не смогу сохранять ваши данные '
            'и принимать заявки.\n\n'
            'Вы можете вернуться и дать согласие позже '
            'командой /start.'
        )
        return CONSENT

    if query.data != 'consent_yes':
        return CONSENT

    user = update.effective_user
    save_consent(user.id)
    name = get_name(user.id)

    if not name:
        await query.edit_message_text(
            'Спасибо! ✅\n\n'
            'Как я могу к вам обращаться?\n\n'
            'Напишите ваше имя:'
        )
        return NAME

    await query.edit_message_text(
        f'Спасибо! Согласие сохранено.\n\n'
        f'Здравствуйте, {name}! 👋'
    )
    await update.effective_chat.send_message(
        'Чем могу помочь?',
        reply_markup=main_menu(),
    )
    return MENU


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text('Пожалуйста, введите корректное имя.')
        return NAME

    save_name(update.effective_user.id, name)
    await update.message.reply_text(
        f'Очень приятно, {name}! 👋\n\n'
        'Теперь выберите нужное действие:',
        reply_markup=main_menu(),
    )
    return MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    name = get_name(update.effective_user.id)
    await update.message.reply_text(
        f'Здравствуйте, {name or "клиент"}! 👋\n\n'
        'Чем могу помочь?',
        reply_markup=main_menu(),
    )
    return MENU
