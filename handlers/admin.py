from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config import OWNER_ID
from database.requests import (
    get_all_requests,
    get_request,
    update_status,
    get_stats,
)
from database.users import (
    get_name,
    get_phone,
    get_username,
)
from keyboards.keyboards import (
    admin_menu,
    main_menu,
)
from states import (
    ADMIN_MENU,
    ADMIN_REQUEST_LIST,
    ADMIN_REQUEST_DETAILS,
    ADMIN_MESSAGE,
    MENU,
)
# =========================================================
# СТАТУСЫ ЗАЯВОК
# =========================================================
STATUSES = {
    '🔎 Взять в работу': '🔎 Подбираем',
    '💰 Предложение готово': '💰 Предложение готово',
    '✅ Выполнена': '✅ Выполнена',
    '❌ Отменена': '❌ Отменена',
}
# =========================================================
# ПРОВЕРКА АДМИНИСТРАТОРА
# =========================================================
def require_owner(update):
    return update.effective_user.id == OWNER_ID
# =========================================================
# ЗАГОЛОВОК ЗАЯВКИ В СПИСКЕ
# =========================================================
def admin_row_title(row):
    (
        request_id,
        user_id,
        make,
        model,
        year,
        text,
        status,
        created,
    ) = row
    car = f'{make} {model}'.strip() or 'Автомобиль'
    return f'📋 №{request_id} — {car} — {status}'
# =========================================================
# ВХОД В АДМИН-ПАНЕЛЬ
# =========================================================
async def admin_entry(update, context):
    if not require_owner(update):
        return MENU
    context.user_data.clear()
    await update.message.reply_text(
        '🛠 АДМИН-ПАНЕЛЬ\n\n'
        'Выберите действие:',
        reply_markup=admin_menu(),
    )
    return ADMIN_MENU
# =========================================================
# ГЛАВНОЕ МЕНЮ АДМИНА
# =========================================================
async def admin_menu_handler(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    if text == '📋 Новые заявки':
        return await admin_list(
            update,
            context,
            '🆕 Новая',
        )
    if text == '🔎 Все заявки':
        return await admin_list(
            update,
            context,
            None,
        )
    if text == '📊 Статистика':
        (
            total,
            new,
            selecting,
            offer,
            done,
            cancelled,
        ) = get_stats()
        await update.message.reply_text(
            '📊 Статистика\n\n'
            f'Всего заявок: {total}\n'
            f'🆕 Новая: {new}\n'
            f'🔎 Подбираем: {selecting}\n'
            f'💰 Предложение готово: {offer}\n'
            f'✅ Выполнена: {done}\n'
            f'❌ Отменена: {cancelled}',
            reply_markup=admin_menu(),
        )
        return ADMIN_MENU
    if text == '🏠 Клиентское меню':
        await update.message.reply_text(
            'Клиентское меню:',
            reply_markup=main_menu(),
        )
        return MENU
    return ADMIN_MENU
# =========================================================
# СПИСОК ЗАЯВОК
# =========================================================
async def admin_list(update, context, status):
    rows = get_all_requests(status)
    context.user_data['admin_request_ids'] = [
        row[0]
        for row in rows
    ]
    context.user_data['admin_list_mode'] = status
    if not rows:
        await update.message.reply_text(
            'Заявок нет.',
            reply_markup=admin_menu(),
        )
        return ADMIN_MENU
    keyboard = [
        [admin_row_title(row)]
        for row in rows
    ]
    keyboard.append(
        ['⬅️ В админ-панель']
    )
    await update.message.reply_text(
        '📋 Заявки:',
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
    return ADMIN_REQUEST_LIST
# =========================================================
# ВЫБОР ЗАЯВКИ
# =========================================================
async def admin_request_list(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    if text == '⬅️ В админ-панель':
        return await admin_entry(
            update,
            context,
        )
    try:
        request_id = int(
            text
            .split('№', 1)[1]
            .split(' ', 1)[0]
        )
    except (ValueError, IndexError):
        return ADMIN_REQUEST_LIST
    allowed_ids = context.user_data.get(
        'admin_request_ids',
        [],
    )
    if request_id not in allowed_ids:
        return ADMIN_REQUEST_LIST
    row = get_request(request_id)
    if not row:
        await update.message.reply_text(
            'Заявка не найдена.'
        )
        return ADMIN_REQUEST_LIST
    context.user_data['admin_request_id'] = request_id
    await send_admin_details(
        update,
        row,
    )
    return ADMIN_REQUEST_DETAILS
# =========================================================
# КНОПКИ УПРАВЛЕНИЯ ЗАЯВКОЙ
# =========================================================
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
# =========================================================
# ДЕТАЛИ ЗАЯВКИ
# =========================================================
async def send_admin_details(update, row):
    (
        request_id,
        user_id,
        make,
        model,
        year,
        vin,
        plate,
        request_text,
        phone,
        status,
        created,
        updated,
    ) = row
    vehicle_lines = []
    if make:
        vehicle_lines.append(
            f'Марка: {make}'
        )
    if model:
        vehicle_lines.append(
            f'Модель: {model}'
        )
    if year:
        vehicle_lines.append(
            f'Год: {year}'
        )
    if vin:
        vehicle_lines.append(
            f'VIN: {vin}'
        )
    if plate:
        vehicle_lines.append(
            f'Госномер: {plate}'
        )
    vehicle = (
        '\n'.join(vehicle_lines)
        if vehicle_lines
        else 'не указан'
    )
    username = get_username(user_id)
    customer_name = (
        get_name(user_id)
        or 'не указано'
    )
    telegram_name = (
        f'@{username}'
        if username
        else 'не указан'
    )
    message = (
        f'📋 Заявка №{request_id}\n\n'
        f'📅 Создана: {created}\n'
        f'🔄 Изменена: {updated}\n'
        f'📌 Статус: {status}\n\n'
        f'👤 Клиент: {customer_name}\n'
        f'📱 Телефон: {phone or "не указан"}\n'
        f'💬 Telegram: {telegram_name}\n\n'
        f'🚗 АВТОМОБИЛЬ\n'
        f'{vehicle}\n\n'
        f'🔧 ЧТО НУЖНО:\n'
        f'{request_text}'
    )
    await update.message.reply_text(
        message,
        reply_markup=admin_request_keyboard(),
    )
# =========================================================
# ОБРАБОТКА ЗАЯВКИ
# =========================================================
async def admin_details(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    request_id = context.user_data.get(
        'admin_request_id'
    )
    if not request_id:
        return await admin_entry(
            update,
            context,
        )
    # -----------------------------------------------------
    # НАЗАД К СПИСКУ
    # -----------------------------------------------------
    if text == '⬅️ К заявкам':
        return await admin_list(
            update,
            context,
            context.user_data.get(
                'admin_list_mode'
            ),
        )
    # -----------------------------------------------------
    # СМЕНА СТАТУСА
    # -----------------------------------------------------
    if text in STATUSES:
        new_status = STATUSES[text]
        update_status(
            request_id,
            new_status,
        )
        row = get_request(request_id)
        if not row:
            await update.message.reply_text(
                'Заявка не найдена.'
            )
            return ADMIN_REQUEST_LIST
        # Показываем обновлённую заявку админу
        await send_admin_details(
            update,
            row,
        )
        # Уведомляем клиента
        try:
            await context.bot.send_message(
                chat_id=row[1],
                text=(
                    f'📋 По вашей заявке №{request_id} '
                    f'изменился статус:\n\n'
                    f'{new_status}'
                ),
            )
        except Exception:
            await update.message.reply_text(
                '⚠️ Статус изменён, '
                'но уведомление клиенту отправить '
                'не удалось.'
            )
        return ADMIN_REQUEST_DETAILS
    # -----------------------------------------------------
    # НАПИСАТЬ КЛИЕНТУ
    # -----------------------------------------------------
    if text == '💬 Написать клиенту':
        await update.message.reply_text(
            '💬 Введите сообщение клиенту:\n\n'
            'Для отмены нажмите /cancel'
        )
        return ADMIN_MESSAGE
    return ADMIN_REQUEST_DETAILS
# =========================================================
# ОТПРАВКА СООБЩЕНИЯ КЛИЕНТУ
# =========================================================
async def admin_message(update, context):
    if not require_owner(update):
        return MENU
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text(
            'Сообщение не может быть пустым.'
        )
        return ADMIN_MESSAGE
    request_id = context.user_data.get(
        'admin_request_id'
    )
    if not request_id:
        return await admin_entry(
            update,
            context,
        )
    row = get_request(request_id)
    if not row:
        await update.message.reply_text(
            'Заявка не найдена.'
        )
        return ADMIN_REQUEST_LIST
    try:
        await context.bot.send_message(
            chat_id=row[1],
            text=(
                '💬 Сообщение от «Запчасти+»:\n\n'
                f'{text}'
            ),
        )
    except Exception:
        await update.message.reply_text(
            '❌ Не удалось отправить сообщение клиенту.'
        )
        return ADMIN_REQUEST_DETAILS
    await update.message.reply_text(
        'Сообщение отправлено клиенту ✅'
    )
    # Получаем заявку заново,
    # чтобы показать актуальные данные
    row = get_request(request_id)
    await send_admin_details(
        update,
        row,
    )
    return ADMIN_REQUEST_DETAILS
