from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from config import OWNER_ID
from database.requests import get_requests, get_request, create_request
from database.orders import get_order_by_request, get_order, cancel_order
from database.users import get_name, get_phone
from keyboards.keyboards import main_menu, order_confirm_keyboard
from states import MENU, REQUEST_LIST, REQUEST_DETAILS


def _car_name(make, model):
    return f'{make} {model}'.strip() or 'Автомобиль по VIN'


def _case_title(request_row, order_row=None):
    rid, make, model, year, text, req_status, created = request_row
    car = _car_name(make, model)
    if order_row:
        return f'🛒 №{order_row[0]} — {order_row[3]}'
    return f'📋 №{rid} — {car}'


async def show_cases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_requests(update.effective_user.id)
    if not rows:
        await update.message.reply_text('📋 У вас пока нет обращений.', reply_markup=main_menu())
        return MENU

    items = []
    for row in rows:
        order = get_order_by_request(row[0], update.effective_user.id)
        items.append((row, order))

    # Не пытаемся разбирать кнопку по «№1»: номера заявок и заказов ведутся
    # раздельно и могут совпадать. Храним точное соответствие текста кнопки объекту.
    button_map = {}
    keyboard = []
    for request_row, order_row in items:
        title = _case_title(request_row, order_row)
        # Telegram-клавиатура допускает одинаковый текст, но для пользователя
        # лучше всё равно сделать уникальный ключ в памяти.
        button_map[title] = (request_row[0], order_row[0] if order_row else None)
        keyboard.append([title])

    context.user_data['case_button_map'] = button_map
    context.user_data['case_request_ids'] = [r[0] for r, _ in items]
    context.user_data['case_order_ids'] = [o[0] for _, o in items if o]

    keyboard.append(['⬅️ Назад'])
    await update.message.reply_text(
        '📋 Мои обращения\n\n'
        'Здесь отображаются ваши заявки и заказы в одной истории.\n\n'
        'Выберите обращение:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return REQUEST_LIST


async def case_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '⬅️ Назад':
        await update.message.reply_text('Главное меню:', reply_markup=main_menu())
        return MENU

    mapped = context.user_data.get('case_button_map', {}).get(text)
    if not mapped:
        return REQUEST_LIST

    request_id, order_id = mapped
    row = get_request(request_id, update.effective_user.id)
    if not row:
        await update.message.reply_text('Обращение не найдено.')
        return REQUEST_LIST

    order = None
    if order_id:
        order = get_order(order_id)
        if not order or order[2] != update.effective_user.id:
            order = None

    context.user_data['case_request_id'] = request_id
    context.user_data['case_order_id'] = order[0] if order else None
    await send_case_details(update, row, order)
    return REQUEST_DETAILS


async def send_case_details(update: Update, request_row, order_row=None):
    rid, uid, make, model, year, vin, plate, request_text, phone, req_status, created, updated = request_row
    lines = []
    for label, value in [
        ('Марка', make),
        ('Модель', model),
        ('Год', year),
        ('VIN / номер кузова', vin),
        ('Госномер', plate),
    ]:
        if value:
            lines.append(f'{label}: {value}')
    vehicle = '\n'.join(lines) or 'не указан'

    text = f'📋 Обращение №{rid}\n\n'
    text += f'📅 Создано: {created}\n'
    text += f'📌 Статус заявки: {req_status}\n\n'
    text += f'🚗 Автомобиль:\n{vehicle}\n\n'
    text += f'🔧 Что требуется:\n{request_text}'

    inline_keyboard = None
    keyboard = []
    # Если предложение готово, но заказ ещё не создан, оформление должно быть
    # доступно прямо из «Мои обращения», а не только из сообщения с предложением.
    if not order_row and req_status == '💰 Предложение готово':
        offer_text = __import__('database.requests', fromlist=['get_offer']).get_offer(rid) or ''
        from database.cashback import get_balance
        from database.loyalty import parse_amount
        balance = get_balance(update.effective_user.id)
        max_cashback = round(min(balance, parse_amount(offer_text) * 0.5), 2)
        inline_keyboard = order_confirm_keyboard(rid, balance, max_cashback)
        if offer_text:
            text += f'\n\n💰 Цена / предложение:\n{offer_text}'
        text += '\n\nВы можете оформить заказ прямо сейчас.'
    if order_row:
        order_id, _, _, order_status, order_created, _, offer_text = order_row[:7]
        text += f'\n\n🛒 Заказ №{order_id}\n📌 Статус заказа: {order_status}\n📅 Оформлен: {order_created}'
        if offer_text:
            text += f'\n\n💰 Цена / предложение:\n{offer_text}'
        if order_status not in ('❌ Отменён', '🚗 Выдан'):
            keyboard.append(['❌ Отменить заказ'])
        if order_status != '❌ Отменён':
            keyboard.append(['🔄 Повторить заказ'])

    keyboard.append(['⬅️ К обращениям'])
    await update.message.reply_text(
        text,
        reply_markup=inline_keyboard or ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


async def case_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '⬅️ К обращениям':
        return await show_cases(update, context)

    request_id = context.user_data.get('case_request_id')
    order_id = context.user_data.get('case_order_id')
    if not request_id:
        return REQUEST_LIST

    order = get_order(order_id) if order_id else get_order_by_request(request_id, update.effective_user.id)
    if order and order[2] != update.effective_user.id:
        order = None

    if text == '❌ Отменить заказ':
        if not order:
            return REQUEST_DETAILS
        if order[3] in ('❌ Отменён', '🚗 Выдан'):
            await update.message.reply_text('Этот заказ уже нельзя отменить.')
            return REQUEST_DETAILS
        context.user_data['confirm_cancel_order'] = True
        await update.message.reply_text(
            f'⚠️ Вы действительно хотите отменить заказ №{order[0]}?',
            reply_markup=ReplyKeyboardMarkup(
                [['✅ Да, отменить'], ['↩️ Не отменять']], resize_keyboard=True
            ),
        )
        return REQUEST_DETAILS

    if context.user_data.get('confirm_cancel_order'):
        if text == '↩️ Не отменять':
            context.user_data.pop('confirm_cancel_order', None)
            row = get_request(request_id, update.effective_user.id)
            order = get_order(order_id) if order_id else None
            if row:
                await send_case_details(update, row, order)
            return REQUEST_DETAILS
        if text == '✅ Да, отменить':
            context.user_data.pop('confirm_cancel_order', None)
            if not order:
                await update.message.reply_text('Заказ не найден.', reply_markup=main_menu())
                context.user_data.clear()
                return MENU
            ok, _ = cancel_order(order[0], update.effective_user.id)
            if not ok:
                await update.message.reply_text('Заказ уже отменён или его больше нельзя отменить.', reply_markup=main_menu())
                context.user_data.clear()
                return MENU
            row = get_order(order[0])
            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=(
                        '❌ КЛИЕНТ ОТМЕНИЛ ЗАКАЗ\n\n'
                        f'🛒 Заказ №{order[0]}\n'
                        f'👤 Клиент: {get_name(update.effective_user.id) or update.effective_user.full_name}\n'
                        f'📱 Телефон: {row[13] or get_phone(update.effective_user.id) or "не указан"}\n'
                        f'🚗 Автомобиль: {row[7]} {row[8]}'.strip()
                    ),
                )
            except Exception:
                pass
            await update.message.reply_text(
                f'❌ Заказ №{order[0]} отменён.\n\nЕсли захотите, его можно будет заказать снова.',
                reply_markup=main_menu(),
            )
            context.user_data.clear()
            return MENU
        return REQUEST_DETAILS

    if text == '🔄 Повторить заказ':
        if not order:
            return REQUEST_DETAILS
        _, _, uid, _, _, _, _, make, model, year, vin, plate, request_text, phone = order
        rid = create_request(
            uid, None, make, model, year, vin, plate, request_text,
            phone or get_phone(uid) or 'не указан'
        )
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    '🔄 ПОВТОРНЫЙ ЗАПРОС\n\n'
                    f'📋 Новая заявка №{rid}\n'
                    f'👤 Клиент: {get_name(uid) or "не указано"}\n'
                    f'📱 Телефон: {phone or get_phone(uid) or "не указан"}\n'
                    f'🚗 Автомобиль: {make} {model} {year}'.strip()
                    + f'\n\n🔧 Что требуется:\n{request_text}'
                ),
            )
        except Exception:
            pass
        await update.message.reply_text(
            '🔄 Запрос на повторный заказ отправлен. Мы свяжемся с вами после проверки актуальности цены и наличия.',
            reply_markup=main_menu(),
        )
        context.user_data.clear()
        return MENU

    return REQUEST_DETAILS
