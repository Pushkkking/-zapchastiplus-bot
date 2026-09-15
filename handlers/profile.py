from telegram import Update
from telegram.ext import ContextTypes
from database.users import get_name,get_phone,save_name,save_phone
from keyboards.keyboards import main_menu,back_keyboard,profile_menu
from states import MENU,EDIT_NAME,EDIT_PHONE

async def show_my_data(update,context):
    uid=update.effective_user.id; name=get_name(uid); phone=get_phone(uid)
    await update.message.reply_text(f'👤 Мои данные\n\nИмя: {name or "не указано"}\nТелефон: {phone or "не указан"}',reply_markup=profile_menu()); return MENU

async def edit_name(update,context):
    text=update.message.text.strip()
    if text=='⬅️ Назад': return await show_my_data(update,context)
    if len(text)<2 or len(text)>50:
        await update.message.reply_text('Пожалуйста, введите корректное имя.'); return EDIT_NAME
    save_name(update.effective_user.id,text); await update.message.reply_text('Имя успешно изменено ✅',reply_markup=main_menu()); return MENU

async def edit_phone(update,context):
    phone=update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    if phone=='⬅️ Назад': return await show_my_data(update,context)
    save_phone(update.effective_user.id,phone); await update.message.reply_text('Номер телефона сохранён ✅',reply_markup=main_menu()); return MENU
