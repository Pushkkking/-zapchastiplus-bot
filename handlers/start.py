from telegram import Update
from telegram.ext import ContextTypes
from database.users import save_user,get_name,has_consent,save_consent
from keyboards.keyboards import main_menu,consent_keyboard
from config import OPERATOR_NAME,OPERATOR_CONTACT,POLICY_URL
from states import CONSENT,NAME,MENU


def policy_text():
    return (f'📄 Политика обработки персональных данных\n\n'
            f'Оператор: {OPERATOR_NAME}\n'
            f'Контакт: {OPERATOR_CONTACT}\n\n'
            'В боте могут обрабатываться: имя, номер телефона, Telegram username, '
            'данные автомобиля (в том числе VIN и госномер), а также история заявок.\n\n'
            'Цель обработки: подбор и продажа автозапчастей, связь с клиентом по заявке, '
            'ведение истории обращений и исполнение обращений клиента.\n\n'
            'Данные не запрашиваются сверх необходимого для указанных целей и должны '
            'обрабатываться в соответствии с законодательством РФ.\n\n'
            + (f'Полная версия политики: {POLICY_URL}' if POLICY_URL else 'Полную версию политики необходимо разместить в доступном пользователю месте и указать ссылку в настройках бота.'))


async def show_consent(update, context):
    await update.message.reply_text(
        'Здравствуйте! 👋\n\nДля работы бота потребуется обработка персональных данных.\n\n'
        'Перед продолжением ознакомьтесь с политикой и подтвердите согласие отдельной кнопкой.',
        reply_markup=consent_keyboard())
    return CONSENT


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear(); user=update.effective_user; save_user(user)
    if not has_consent(user.id): return await show_consent(update,context)
    name=get_name(user.id)
    if not name:
        await update.message.reply_text('Как я могу к вам обращаться?\n\nНапишите ваше имя:'); return NAME
    await update.message.reply_text(f'Здравствуйте, {name}! 👋\n\nЧем могу помочь?', reply_markup=main_menu()); return MENU


async def consent_handler(update,context):
    text=update.message.text.strip()
    if text=='📄 Политика обработки ПД':
        await update.message.reply_text(policy_text(), reply_markup=consent_keyboard()); return CONSENT
    if text=='❌ Не согласен':
        await update.message.reply_text('Без согласия я не смогу сохранять ваши данные и принимать заявки. Вы можете вернуться и дать согласие позже командой /start.'); return CONSENT
    if text!='✅ Согласен': return CONSENT
    save_consent(update.effective_user.id)
    name=get_name(update.effective_user.id)
    if not name:
        await update.message.reply_text('Спасибо! ✅\n\nКак я могу к вам обращаться?\n\nНапишите ваше имя:'); return NAME
    await update.message.reply_text(f'Спасибо! Согласие сохранено.\n\nЗдравствуйте, {name}! 👋', reply_markup=main_menu()); return MENU


async def receive_name(update,context):
    name=update.message.text.strip()
    if len(name)<2 or len(name)>50:
        await update.message.reply_text('Пожалуйста, введите корректное имя.'); return NAME
    from database.users import save_name
    save_name(update.effective_user.id,name)
    await update.message.reply_text(f'Очень приятно, {name}! 👋\n\nТеперь выберите нужное действие:',reply_markup=main_menu()); return MENU


async def cancel(update,context):
    context.user_data.clear(); name=get_name(update.effective_user.id)
    await update.message.reply_text(f'Здравствуйте, {name or "клиент"}! 👋\n\nЧем могу помочь?',reply_markup=main_menu()); return MENU
