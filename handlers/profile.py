from telegram import Update
from telegram.ext import ContextTypes
from database.users import get_name,get_phone,save_name,save_phone
from keyboards.keyboards import main_menu,back_keyboard,profile_menu
from states import MENU,EDIT_NAME,EDIT_PHONE,PROFILE_MENU,PROMO_CODE

async def show_my_data(update,context):
    uid=update.effective_user.id; name=get_name(uid); phone=get_phone(uid)
    await update.message.reply_text(
        f'👤 Мои данные\n\nИмя: {name or "не указано"}\nТелефон: {phone or "не указан"}',
        reply_markup=profile_menu())
    return PROFILE_MENU

async def start_edit_data(update,context):
    uid=update.effective_user.id
    name=get_name(uid) or 'не указано'; phone=get_phone(uid) or 'не указан'
    context.user_data['editing_data']=True
    await update.message.reply_text(
        f'✏️ Изменить данные\n\nТекущее имя: {name}\nТекущий телефон: {phone}\n\nВведите новое имя.',
        reply_markup=back_keyboard())
    return EDIT_NAME

async def edit_name(update,context):
    text=update.message.text.strip()
    if text=='⬅️ Назад':
        context.user_data.pop('editing_data',None)
        return await show_my_data(update,context)
    if len(text)<2 or len(text)>50:
        await update.message.reply_text('Пожалуйста, введите корректное имя.')
        return EDIT_NAME
    save_name(update.effective_user.id,text)
    if context.user_data.get('editing_data'):
        await update.message.reply_text('Имя сохранено ✅\n\nВведите новый номер телефона или отправьте контакт.',
                                        reply_markup=back_keyboard())
        return EDIT_PHONE
    await update.message.reply_text('Имя успешно изменено ✅',reply_markup=main_menu())
    return MENU

async def edit_phone(update,context):
    phone=update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    if phone=='⬅️ Назад':
        context.user_data.pop('editing_data',None)
        return await show_my_data(update,context)
    if len(phone)<5 or len(phone)>30:
        await update.message.reply_text('Пожалуйста, введите корректный номер телефона.')
        return EDIT_PHONE
    save_phone(update.effective_user.id,phone)
    context.user_data.pop('editing_data',None)
    await update.message.reply_text('Данные успешно сохранены ✅',reply_markup=main_menu())
    return MENU



async def show_referral(update, context):
    from database.users import get_referral_code, get_referral_info
    from config import BOT_USERNAME
    code = get_referral_code(update.effective_user.id)
    invited, rewarded = get_referral_info(update.effective_user.id)
    username = BOT_USERNAME or (await context.bot.get_me()).username
    link = f'https://t.me/{username}?start=ref_{code}'
    text = (
        '👥 Пригласить друга\n\n'
        'Поделитесь ссылкой с другом. После его первой полученной покупки вы оба получите по 300 ₽ бонусами.\n\n'
        f'🔗 Ваша ссылка:\n{link}\n\n'
        f'👤 Приглашено: {invited}\n'
        f'⭐ Бонус получен: {rewarded}'
    )
    await update.message.reply_text(text, reply_markup=profile_menu())
    return PROFILE_MENU


async def start_promo_from_profile(update, context):
    await update.message.reply_text(
        '🎟 Промокод\n\n'
        'Промокод вводится при получении предложения по новой заявке.\n\n'
        'Откройте предложение и нажмите «🎟 Ввести промокод».',
        reply_markup=profile_menu())
    return PROFILE_MENU
