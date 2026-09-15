from telegram import Update
from telegram.ext import ContextTypes
from database.users import get_name,get_phone,save_name,save_phone
from keyboards.keyboards import main_menu,back_keyboard,profile_menu
from states import MENU,EDIT_NAME,EDIT_PHONE,PROFILE_MENU

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
