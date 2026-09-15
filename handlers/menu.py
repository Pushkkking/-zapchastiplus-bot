from database.users import get_name,get_phone
from keyboards.keyboards import main_menu,back_keyboard
from states import MENU,EDIT_NAME,EDIT_PHONE,PROFILE_MENU

async def menu_handler(update,context):
    text=update.message.text
    if text=='🔧 Подобрать запчасть':
        from handlers.requests import start_request; return await start_request(update,context)
    if text=='📋 Мои обращения':
        from handlers.customer_cases import show_cases; return await show_cases(update,context)
    if text=='💬 Связаться с Запчасти+':
        from handlers.customer_chat import show_chat; return await show_chat(update,context)
    if text=='🚗 Мои автомобили':
        from handlers.cars import show_cars; return await show_cars(update,context)
    if text=='💬 Написать сообщение':
        from handlers.customer_chat import start_customer_message; return await start_customer_message(update,context)
    if text=='📖 История переписки':
        from handlers.customer_chat import show_chat_history; return await show_chat_history(update,context)
    if text=='👤 Мои данные':
        from handlers.profile import show_my_data; return await show_my_data(update,context)
    if text=='✏️ Изменить имя':
        await update.message.reply_text('Введите новое имя:',reply_markup=back_keyboard()); return EDIT_NAME
    if text=='📱 Изменить телефон':
        await update.message.reply_text('Введите новый номер телефона:',reply_markup=back_keyboard()); return EDIT_PHONE
    if text=='➕ Добавить автомобиль':
        from handlers.cars import add_car_start; return await add_car_start(update,context)
    if text=='🗑 Удалить автомобиль':
        from handlers.cars import delete_car_start; return await delete_car_start(update,context)
    if text=='⬅️ Назад':
        name=get_name(update.effective_user.id); await update.message.reply_text(f'Здравствуйте, {name or "клиент"}! 👋',reply_markup=main_menu()); return MENU
    return MENU
