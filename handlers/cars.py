import logging

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.cars import get_cars,save_car,delete_car
from keyboards.keyboards import main_menu,back_keyboard
from states import MENU,CAR_MAKE,CAR_MODEL,CAR_YEAR,CAR_VIN,CAR_PLATE,DELETE_CAR
from ocr import recognise_vehicle_data

logger = logging.getLogger(__name__)


def title(car):
    _, make, model, year, _, plate = car
    label = f'🚗 {make} {model}'.strip()
    if plate:
        return f'{label} — {plate}'
    return f'{label} — номер не указан'


def photo_keyboard():
    return ReplyKeyboardMarkup(
        [['📷 Сфотографировать СТС / VIN'], ['⬅️ Назад']],
        resize_keyboard=True,
    )


def vin_keyboard():
    return ReplyKeyboardMarkup(
        [['📷 Сфотографировать СТС / VIN'], ['Пропустить'], ['⬅️ Назад']],
        resize_keyboard=True,
    )


def photo_result_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Всё верно, сохранить', callback_data='car_photo_confirm:yes')],
        [InlineKeyboardButton('✏️ Ввести вручную', callback_data='car_photo_confirm:no')],
    ])


async def car_back(update,context):
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
    context.user_data['new_car']={}
    await update.message.reply_text(
        'Добавление автомобиля.\n\n'
        'Можно ввести данные вручную или сразу отправить фотографию СТС / VIN.\n'
        'По фотографии бот попробует определить марку, модель, год, VIN и госномер.',
        reply_markup=photo_keyboard(),
    )
    return CAR_MAKE
async def car_photo_from_make(update, context):
    if update.message.text.strip() == '📷 Сфотографировать СТС / VIN':
        await update.message.reply_text(
            '📷 Отправьте фотографию СТС или VIN-таблички.\n\n'
            'Лучше сфотографировать документ целиком и без бликов. На фото должны быть хорошо видны поля с маркой, моделью, годом, VIN и госномером (если они есть).',
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True),
        )
        return CAR_VIN
    return await car_make(update, context)


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
    context.user_data['new_car']['year']='' if t=='Пропустить' else t; await update.message.reply_text('Введите VIN или номер кузова автомобиля.\n\nМожно нажать «📷 Сфотографировать VIN», чтобы бот попытался распознать VIN и госномер с фотографии.',reply_markup=vin_keyboard()); return CAR_VIN

async def car_vin_photo(update, context):
    if not update.message.photo:
        return CAR_VIN
    await update.message.reply_text('📷 Фото получено. Распознаю VIN и госномер…')
    try:
        photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await tg_file.download_as_bytearray())
        result = recognise_vehicle_data(image_bytes, 'image/jpeg')
    except Exception as exc:
        logger.exception('Vehicle OCR failed')
        await update.message.reply_text(
            '❌ Не удалось распознать данные на фотографии.\n\n'
            'Попробуйте сделать более чёткое фото VIN или введите данные вручную.',
            reply_markup=vin_keyboard(),
        )
        return CAR_VIN

    context.user_data['car_photo_result'] = result
    lines = ['🔎 Результат распознавания:\n']
    lines.append(f"VIN: {result['vin'] or 'не распознан'}")
    lines.append(f"Госномер: {result['plate'] or 'не распознан'}")
    lines.append(f"Год: {result.get('year') or 'не распознан'}")
    if result.get('make'):
        lines.append(f"Марка: {result['make']}")
    if result.get('model'):
        lines.append(f"Модель: {result['model']}")
    lines.append(f"\nУверенность: {result.get('confidence', 0)}%")
    lines.append('\nПроверьте данные перед сохранением.')
    await update.message.reply_text('\n'.join(lines), reply_markup=photo_result_keyboard())
    return CAR_VIN

async def car_photo_confirm(update, context):
    query = update.callback_query
    await query.answer()
    result = context.user_data.get('car_photo_result') or {}
    if query.data.endswith(':no'):
        context.user_data.pop('car_photo_result', None)
        await query.edit_message_text('Хорошо. Введите VIN или номер кузова вручную.')
        await query.message.reply_text('Введите VIN или номер кузова автомобиля:', reply_markup=ReplyKeyboardMarkup([['Пропустить'],['⬅️ Назад']],resize_keyboard=True))
        return CAR_VIN

    car = context.user_data.get('new_car', {})
    if result.get('make') and not car.get('make'):
        car['make'] = result['make']
    if result.get('model') and not car.get('model'):
        car['model'] = result['model']
    if result.get('year') and not car.get('year'):
        car['year'] = result['year']
    car['vin'] = result.get('vin', '')
    car['plate'] = result.get('plate', '')
    if not car.get('vin') and not car.get('plate'):
        await query.edit_message_text('Не удалось уверенно распознать VIN или госномер. Попробуйте другое фото или введите данные вручную.')
        return CAR_VIN

    # Если VIN и госномер уже распознаны, сохраняем автомобиль сразу.
    save_car(update.effective_user.id, car.get('make',''), car.get('model',''), car.get('year',''), car.get('vin',''), car.get('plate',''))
    context.user_data.clear()
    await query.edit_message_text('Автомобиль сохранён по фотографии ✅')
    await query.message.reply_text('Теперь автомобиль доступен в разделе «🚗 Мои автомобили».', reply_markup=main_menu())
    return MENU

async def car_vin(update,context):
    t=update.message.text.strip().upper()
    if t=='⬅️ Назад': return await show_cars(update,context)
    if t=='📷 СФОТОГРАФИРОВАТЬ СТС / VIN'.upper():
        await update.message.reply_text('📷 Отправьте фотографию VIN-таблички, VIN под лобовым стеклом или документа, где хорошо виден VIN и госномер.')
        return CAR_VIN
    if t=='Пропустить': t=''
    elif len(t)<3 or len(t)>30 or not all(ch.isalnum() or ch in '-_ ' for ch in t):
        await update.message.reply_text('Введите корректный VIN или номер кузова (от 3 до 30 символов), либо используйте фотографию.')
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
