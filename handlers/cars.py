from telegram import Update,ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database.cars import get_cars,save_car,delete_car
from keyboards.keyboards import main_menu,back_keyboard
from states import MENU,CAR_MAKE,CAR_MODEL,CAR_YEAR,CAR_VIN,CAR_PLATE,DELETE_CAR

def title(car):
    _, make, model, year, _, plate = car
    label = f'🚗 {make} {model}'.strip()
    if plate:
        return f'{label} — {plate}'
    return f'{label} — номер не указан'

async def car_back(update,context):
    # Явный выход из любого шага добавления автомобиля.
    # Очищаем незавершённые данные, чтобы старый сценарий больше не продолжался.
    context.user_data.pop('new_car', None)
    await update.message.reply_text('Добавление автомобиля отменено.', reply_markup=ReplyKeyboardMarkup([['➕ Добавить автомобиль'],['⬅️ Назад']], resize_keyboard=True))
    return await show_cars(update,context)

async def show_cars(update,context):
    cars=get_cars(update.effective_user.id)
    if not cars:
        await update.message.reply_text('У вас пока нет сохранённых автомобилей.',reply_markup=ReplyKeyboardMarkup([['➕ Добавить автомобиль'],['⬅️ Назад']],resize_keyboard=True)); return MENU
    kb=[[title(c)] for c in cars]+[['➕ Добавить автомобиль'],['🗑 Удалить автомобиль'],['⬅️ Назад']]
    await update.message.reply_text('Ваши автомобили:',reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True)); return MENU

async def add_car_start(update,context):
    context.user_data['new_car']={}; await update.message.reply_text('Введите марку автомобиля:',reply_markup=back_keyboard()); return CAR_MAKE
async def car_make(update,context):
    t=update.message.text.strip()
    if t=='⬅️ Назад': return await show_cars(update,context)
    if not t: await update.message.reply_text('Введите марку автомобиля.'); return CAR_MAKE
    context.user_data['new_car']['make']=t; await update.message.reply_text('Введите модель автомобиля:',reply_markup=back_keyboard()); return CAR_MODEL
async def car_model(update,context):
    t=update.message.text.strip()
    if t=='⬅️ Назад': return await show_cars(update,context)
    if not t: await update.message.reply_text('Введите модель автомобиля.'); return CAR_MODEL
    context.user_data['new_car']['model']=t; await update.message.reply_text('Введите год выпуска или нажмите «Пропустить»:',reply_markup=ReplyKeyboardMarkup([['Пропустить'],['⬅️ Назад']],resize_keyboard=True)); return CAR_YEAR
async def car_year(update,context):
    t=update.message.text.strip()
    if t=='⬅️ Назад': return await show_cars(update,context)
    context.user_data['new_car']['year']='' if t=='Пропустить' else t; await update.message.reply_text('Введите VIN или номер кузова автомобиля.\n\nЕсли VIN/номер кузова неизвестен — нажмите «Пропустить».',reply_markup=ReplyKeyboardMarkup([['Пропустить'],['⬅️ Назад']],resize_keyboard=True)); return CAR_VIN
async def car_vin(update,context):
    t=update.message.text.strip().upper()
    if t=='⬅️ Назад': return await show_cars(update,context)
    if t=='Пропустить': t=''
    elif len(t)<3 or len(t)>30 or not all(ch.isalnum() or ch in '-_ ' for ch in t):
        await update.message.reply_text('Введите корректный VIN или номер кузова (от 3 до 30 символов) либо нажмите «Пропустить».')
        return CAR_VIN
    context.user_data['new_car']['vin']=t; await update.message.reply_text('Введите госномер или нажмите «Пропустить»:',reply_markup=ReplyKeyboardMarkup([['Пропустить'],['⬅️ Назад']],resize_keyboard=True)); return CAR_PLATE
async def car_plate(update,context):
    t=update.message.text.strip()
    if t=='⬅️ Назад': return await show_cars(update,context)
    if t=='Пропустить': t=''
    c=context.user_data.get('new_car',{}); save_car(update.effective_user.id,c.get('make',''),c.get('model',''),c.get('year',''),c.get('vin',''),t); context.user_data.clear(); await update.message.reply_text('Автомобиль сохранён ✅',reply_markup=main_menu()); return MENU
async def delete_car_start(update,context):
    cars=get_cars(update.effective_user.id)
    if not cars: await update.message.reply_text('У вас нет сохранённых автомобилей.',reply_markup=main_menu()); return MENU
    context.user_data['delete_cars']=cars; await update.message.reply_text('Выберите автомобиль для удаления:',reply_markup=ReplyKeyboardMarkup([[title(c)] for c in cars]+[['⬅️ Назад']],resize_keyboard=True)); return DELETE_CAR
async def delete_car_handler(update,context):
    t=update.message.text.strip()
    if t=='⬅️ Назад': return await show_cars(update,context)
    for c in context.user_data.get('delete_cars',[]):
        if t==title(c): delete_car(c[0],update.effective_user.id); context.user_data.clear(); await update.message.reply_text('Автомобиль удалён ✅',reply_markup=main_menu()); return MENU
    return DELETE_CAR
