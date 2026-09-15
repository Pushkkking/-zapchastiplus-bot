from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from config import OWNER_ID
from database.requests import get_all_requests, get_request, update_status, get_stats
from database.orders import get_all_orders, get_order, update_order_status, get_order_stats
from database.users import get_name, get_phone, get_username
from keyboards.keyboards import admin_menu, main_menu, admin_order_actions
from states import ADMIN_MENU, ADMIN_REQUEST_LIST, ADMIN_REQUEST_DETAILS, ADMIN_MESSAGE, MENU


REQUEST_STATUSES = {
    '🔎 Взять в работу': '🔎 Подбираем',
    '💰 Предложение готово': '💰 Предложение готово',
    '✅ Выполнена': '✅ Выполнена',
    '❌ Отменена': '❌ Отменена',
}

ORDER_STATUSES = {
    '🔧 В работу': '🔧 В работе',
    '📦 Готов к выдаче': '📦 Готов к выдаче',
    '🚗 Выдан': '🚗 Выдан',
    '❌ Отменить': '❌ Отменён',
}


def require_owner(update):
    return update.effective_user.id == OWNER_ID


def admin_row_title(row):
    request_id, user_id, make, model, year, text, status, created = row
    car = f'{make} {model}'.strip() or 'Автомобиль'
    return f'📋 №{request_id} — {car} — {status}'


def admin_order_title(row):
    order_id, request_id, user_id, status, created, updated, make, model, year, text, phone = row
    car = f'{make} {model}'.strip() or 'Автомобиль'
    return f'🛒 №{order_id} — {car} — {status}'


async def admin_entry(update, context):
    if not require_owner(update):
        return MENU
    context.user_data.clear()
    await update.message.reply_text(
        '🛠 АДМИН-ПАНЕЛЬ\n\nВыберите действие:',
        reply_markup=admin_menu(),
    )
    return ADMIN_MENU


async def admin_menu_handler(update, context):
    if not require_owner(update):
        return MENU

    text = update.message.text.strip()
    if text == '📋 Новые заявки':
        return await admin_list(update, context, '🆕 Новая')
    if text == '🔎 Все заявки':
        return await admin_list(update, context, None)
    if text == '🛒 Заказы':
        return await admin_order_list(update, context)
    if text == '📊 Статистика':
        total, new, selecting, offer, done, cancelled = get_stats()
        ototal, onew, owork, oready, odone, ocancelled = get_order_stats()
        await update.message.reply_text(
            '📊 Статистика\n\n'
            'ЗАЯВКИ\n'
            f'Всего: {total}\n'
            f'🆕 Новая: {new}\n'
            f'🔎 Подбираем: {selecting}\n'
            f'💰 Предложение готово: {offer}\n'
            f'✅ Выполнена: {done}\n'
            f'❌ Отменена: {cancelled}\n\n'
            'ЗАКАЗЫ\n'
            f'Всего: {ototal}\n'
            f'🆕 Новый: {onew}\n'
            f'🔧 В работе: {owork}\n'
            f'📦 Готов к выдаче: {oready}\n'
            f'🚗 Выдан: {odone}\n'
            f'❌ Отменён: {ocancelled}',
            reply_markup=admin_menu(),
        )
        return ADMIN_MENU
    if text == '🏠 Клиентское меню':
        await update.message.reply_text('Клиентское меню:', reply_markup=main_menu())
        return MENU
    return ADMIN_MENU


async def admin_list(update, context, status):
    rows = get_all_requests(status)
    context.user_data['admin_request_ids'] = [row[0] for row in rows]
    context.user_data['admin_list_mode'] = status
    context.user_data.pop('admin_order_ids', None)

    if not rows:
        await update.message.reply_text('Заявок нет.', reply_markup=admin_menu())
        return ADMIN_MENU

    keyboard = [[admin_row_title(row)] for row in rows]
    keyboard.append(['⬅️ В админ-панель'])
    await update.message.reply_text(
        '📋 Заявки:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return ADMIN_REQUEST_LIST


async def admin_request_list(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    if text == '⬅️ В админ-панель':
        return await admin_entry(update, context)
    try:
        request_id = int(text.split('№', 1)[1].split(' ', 1)[0])
    except (ValueError, IndexError):
        return ADMIN_REQUEST_LIST
    if request_id not in context.user_data.get('admin_request_ids', []):
        return ADMIN_REQUEST_LIST
    row = get_request(request_id)
    if not row:
        await update.message.reply_text('Заявка не найдена.')
        return ADMIN_REQUEST_LIST
    context.user_data['admin_request_id'] = request_id
    context.user_data['admin_message_target'] = 'request'
    await send_admin_details(update, row)
    return ADMIN_REQUEST_DETAILS


def admin_request_keyboard():
    return ReplyKeyboardMarkup(
        [
            ['🔎 Взять в работу'],
            ['💰 Предложение готово'],
            ['💬 Написать клиенту'],
            ['✅ Выполнена', '❌ Отменена'],
            ['⬅️ К заявкам'],
        ],
        resize_keyboard=True,
    )


async def send_admin_details(update, row):
    request_id, user_id, make, model, year, vin, plate, request_text, phone, status, created, updated = row
    vehicle_lines = []
    for label, value in [('Марка', make), ('Модель', model), ('Год', year), ('VIN', vin), ('Госномер', plate)]:
        if value:
            vehicle_lines.append(f'{label}: {value}')
    vehicle = '\n'.join(vehicle_lines) if vehicle_lines else 'не указан'
    username = get_username(user_id)
    customer_name = get_name(user_id) or 'не указано'
    telegram_name = f'@{username}' if username else 'не указан'
    message = (
        f'📋 Заявка №{request_id}\n\n'
        f'📅 Создана: {created}\n'
        f'🔄 Изменена: {updated}\n'
        f'📌 Статус: {status}\n\n'
        f'👤 Клиент: {customer_name}\n'
        f'📱 Телефон: {phone or "не указан"}\n'
        f'💬 Telegram: {telegram_name}\n\n'
        f'🚗 АВТОМОБИЛЬ\n{vehicle}\n\n'
        f'🔧 ЧТО НУЖНО:\n{request_text}'
    )
    await update.message.reply_text(message, reply_markup=admin_request_keyboard())


async def admin_details(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    request_id = context.user_data.get('admin_request_id')
    if not request_id:
        return await admin_entry(update, context)

    if text == '⬅️ К заявкам':
        return await admin_list(update, context, context.user_data.get('admin_list_mode'))

    if text in REQUEST_STATUSES:
        new_status = REQUEST_STATUSES[text]
        update_status(request_id, new_status)
        row = get_request(request_id)
        if not row:
            await update.message.reply_text('Заявка не найдена.')
            return ADMIN_REQUEST_LIST

        await send_admin_details(update, row)

        try:
            if new_status == '💰 Предложение готово':
                from keyboards.keyboards import order_confirm_keyboard
                await context.bot.send_message(
                    chat_id=row[1],
                    text=(
                        f'💰 По заявке №{request_id} подготовлено предложение.\n\n'
                        'Если всё устраивает, вы можете оформить заказ прямо в боте.'
                    ),
                    reply_markup=order_confirm_keyboard(request_id),
                )
            else:
                await context.bot.send_message(
                    chat_id=row[1],
                    text=(
                        f'📋 По вашей заявке №{request_id} изменился статус:\n\n'
                        f'{new_status}'
                    ),
                )
        except Exception:
            await update.message.reply_text(
                '⚠️ Статус изменён, но уведомление клиенту отправить не удалось.'
            )
        return ADMIN_REQUEST_DETAILS

    if text == '💬 Написать клиенту':
        context.user_data['admin_message_target'] = 'request'
        await update.message.reply_text(
            '💬 Введите сообщение клиенту:\n\nДля отмены нажмите /cancel'
        )
        return ADMIN_MESSAGE

    return ADMIN_REQUEST_DETAILS


# ========================= ЗАКАЗЫ =========================

async def admin_order_list(update, context):
    if not require_owner(update):
        return MENU
    rows = get_all_orders()
    context.user_data['admin_order_ids'] = [row[0] for row in rows]
    context.user_data.pop('admin_request_ids', None)

    if not rows:
        await update.message.reply_text(
            '🛒 Заказов пока нет.',
            reply_markup=admin_menu(),
        )
        return ADMIN_MENU

    keyboard = [[admin_order_title(row)] for row in rows]
    keyboard.append(['⬅️ В админ-панель'])
    await update.message.reply_text(
        '🛒 ЗАКАЗЫ:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return ADMIN_REQUEST_LIST


async def admin_request_or_order_list(update, context):
    if context.user_data.get('admin_order_ids') is not None:
        return await admin_order_select(update, context)
    return await admin_request_list(update, context)


async def admin_order_select(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    if text == '⬅️ В админ-панель':
        return await admin_entry(update, context)
    try:
        order_id = int(text.split('№', 1)[1].split(' ', 1)[0])
    except (ValueError, IndexError):
        return ADMIN_REQUEST_LIST
    if order_id not in context.user_data.get('admin_order_ids', []):
        return ADMIN_REQUEST_LIST
    row = get_order(order_id)
    if not row:
        await update.message.reply_text('Заказ не найден.')
        return ADMIN_REQUEST_LIST
    context.user_data['admin_order_id'] = order_id
    context.user_data['admin_message_target'] = 'order'
    await send_admin_order_details(update, row)
    return ADMIN_REQUEST_DETAILS


async def send_admin_order_details(update, row):
    order_id, request_id, user_id, status, created, updated, make, model, year, vin, plate, request_text, phone = row
    vehicle_lines = []
    for label, value in [('Марка', make), ('Модель', model), ('Год', year), ('VIN', vin), ('Госномер', plate)]:
        if value:
            vehicle_lines.append(f'{label}: {value}')
    vehicle = '\n'.join(vehicle_lines) if vehicle_lines else 'не указан'
    username = get_username(user_id)
    customer_name = get_name(user_id) or 'не указано'
    telegram_name = f'@{username}' if username else 'не указан'
    message = (
        f'🛒 ЗАКАЗ №{order_id}\n\n'
        f'📋 Заявка: №{request_id}\n'
        f'📅 Создан: {created}\n'
        f'🔄 Изменён: {updated}\n'
        f'📌 Статус: {status}\n\n'
        f'👤 Клиент: {customer_name}\n'
        f'📱 Телефон: {phone or "не указан"}\n'
        f'💬 Telegram: {telegram_name}\n\n'
        f'🚗 АВТОМОБИЛЬ\n{vehicle}\n\n'
        f'🔧 ЧТО ЗАКАЗАНО:\n{request_text}'
    )
    await update.message.reply_text(message, reply_markup=admin_order_actions())


async def admin_order_details(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    order_id = context.user_data.get('admin_order_id')
    if not order_id:
        return await admin_entry(update, context)

    if text == '⬅️ К заказам':
        return await admin_order_list(update, context)

    if text in ORDER_STATUSES:
        new_status = ORDER_STATUSES[text]
        update_order_status(order_id, new_status)
        row = get_order(order_id)
        if not row:
            await update.message.reply_text('Заказ не найден.')
            return ADMIN_REQUEST_LIST
        await send_admin_order_details(update, row)
        try:
            await context.bot.send_message(
                chat_id=row[2],
                text=(
                    f'🛒 По вашему заказу №{order_id} изменился статус:\n\n'
                    f'{new_status}'
                ),
            )
        except Exception:
            await update.message.reply_text(
                '⚠️ Статус изменён, но уведомление клиенту отправить не удалось.'
            )
        return ADMIN_REQUEST_DETAILS

    if text == '💬 Написать клиенту':
        context.user_data['admin_message_target'] = 'order'
        await update.message.reply_text(
            '💬 Введите сообщение клиенту:\n\nДля отмены нажмите /cancel'
        )
        return ADMIN_MESSAGE

    return ADMIN_REQUEST_DETAILS


async def admin_request_or_order_details(update, context):
    target = context.user_data.get('admin_message_target')
    if target == 'order':
        return await admin_order_details(update, context)
    return await admin_details(update, context)


async def admin_message(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text('Сообщение не может быть пустым.')
        return ADMIN_MESSAGE

    target = context.user_data.get('admin_message_target', 'request')

    if target == 'order':
        order_id = context.user_data.get('admin_order_id')
        row = get_order(order_id) if order_id else None
        if not row:
            return await admin_entry(update, context)
        chat_id = row[2]
    else:
        request_id = context.user_data.get('admin_request_id')
        row = get_request(request_id) if request_id else None
        if not row:
            return await admin_entry(update, context)
        chat_id = row[1]

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f'💬 Сообщение от «Запчасти+»:\n\n{text}',
        )
    except Exception:
        await update.message.reply_text('❌ Не удалось отправить сообщение клиенту.')
        return ADMIN_REQUEST_DETAILS

    await update.message.reply_text('Сообщение отправлено клиенту ✅')

    if target == 'order':
        row = get_order(context.user_data['admin_order_id'])
        await send_admin_order_details(update, row)
    else:
        row = get_request(context.user_data['admin_request_id'])
        await send_admin_details(update, row)
    return ADMIN_REQUEST_DETAILS
