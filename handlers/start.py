from telegram import Update
from telegram.ext import ContextTypes
from database.users import (
    save_user,
    get_name,
    has_consent,
    save_consent,
    save_name,
)
from keyboards.keyboards import (
    main_menu,
    consent_keyboard,
)
from config import OPERATOR_NAME, OPERATOR_CONTACT
from states import (
    CONSENT,
    NAME,
    MENU,
)
async def show_consent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        'Здравствуйте! 👋\n\n'
        'Для работы бота потребуется обработка персональных данных.\n\n'
        'Перед продолжением ознакомьтесь с политикой '
        'и подтвердите согласие отдельной кнопкой.',
        reply_markup=consent_keyboard(),
    )
    return CONSENT
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()
    user = update.effective_user
    save_user(user)
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
async def consent_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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
async def receive_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text(
            'Пожалуйста, введите корректное имя.'
        )
        return NAME
    save_name(
        update.effective_user.id,
        name,
    )
    await update.message.reply_text(
        f'Очень приятно, {name}! 👋\n\n'
        'Теперь выберите нужное действие:',
        reply_markup=main_menu(),
    )
    return MENU
async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()
    name = get_name(update.effective_user.id)
    await update.message.reply_text(
        f'Здравствуйте, {name or "клиент"}! 👋\n\n'
        'Чем могу помочь?',
        reply_markup=main_menu(),
    )
    return MENU
