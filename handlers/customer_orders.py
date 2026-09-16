from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from database.orders import get_user_orders, get_order, cancel_order
from database.cashback import get_order_spent, get_order_earned
from database.requests import create_request
from keyboards.keyboards import main_menu
from states import MENU, ORDER_LIST, ORDER_DETAILS
from config import OWNER_ID
from database.users import get_name, get_phone


def car_title(row):
    make, model, year, plate = row[7], row[8], row[9], row[11]
    label = f'{make} {model}'.strip() if (make or model) else 'Автомобиль'
    if plate:
        return f'{label} — {plate}'
    return f'{label} — номер не указан'


def short_price(offer):
    if not offer:
        return 'цена не указана'
    lines = [x.strip() for x in offer.splitlines() if x.strip()]
    for line in reversed(lines):
        low = line.lower()
        if 'итого' in low or 'всего' in low:
            return line[:80]
    return lines[-1][:80] if lines else 'цена не указана'


async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_user_orders(update.effective_user.id)
    if not rows:
        await update.message.reply_text('🛒 У вас пока нет оформленных заказов.', reply_markup=main_menu())
        return MENU
    context.user_data['customer_order_ids'] = [r[0] for r in rows]
    keyboard = []
    for row in rows:
        order_id, _, _, status, created = row[:5]
        keyboard.append([f'🛒 №{order_id} — {status}'])
    keyboard.append(['⬅️ Назад'])
    await update.message.reply_text(
        '🛒 Мои заказы\n\nВыберите заказ:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return ORDER_LIST


async def order_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '⬅️ Назад':
        await update.message.reply_text('Главное меню:', reply_markup=main_menu())
        return MENU
    try:
        order_id = int(text.split('№', 1)[1].split(' ', 1)[0])
    except (ValueError, IndexError):
        return ORDER_LIST
    if order_id not in context.user_data.get('customer_order_ids', []):
        return ORDER_LIST
    row = get_order(order_id)
    if not row or row[2] != update.effective_user.id:
        await update.message.reply_text('Заказ не найден.')
        return ORDER_LIST
    context.user_data['customer_order_id'] = order_id
    await send_order_details(update, row)
    return ORDER_DETAILS


async def send_order_details(update: Update, row):
    order_id, request_id, _, status, created, updated, offer_text, make, model, year, vin, plate, request_text, phone = row
    vehicle_lines = []
    for label, value in [('Марка', make), ('Модель', model), ('Год', year), ('VIN / номер кузова', vin), ('Госномер', plate)]:
        if value:
            vehicle_lines.append(f'{label}: {value}')
    vehicle = '\n'.join(vehicle_lines) if vehicle_lines else 'не указан'
    text = (
        f'🛒 Заказ №{order_id}\n\n'
        f'📅 Оформлен: {created}\n'
        f'📌 Статус: {status}\n'
        f'🕒 Последнее изменение: {updated}\n\n'
        f'🚗 Автомобиль:\n{vehicle}\n\n'
        f'🔧 Что заказано:\n{request_text}'
    )
    if offer_text:
        text += f'\n\n💰 Цена / предложение:\n{offer_text}'
    spent = get_order_spent(order_id)
    earned = get_order_earned(order_id)
    if spent:
        text += f'\n\n💳 Кешбэк списан: {spent:,.2f} ₽'.replace(',', ' ')
    if earned:
        text += f'\n⭐ Кешбэк начислен: {earned:,.2f} ₽'.replace(',', ' ')
    keyboard = []
    if status not in ('❌ Отменён', '🚗 Выдан'):
        keyboard.append(['❌ Отменить заказ'])
    if status != '❌ Отменён':
        keyboard.append(['🔄 Повторить заказ'])
    keyboard.append(['⬅️ К заказам'])
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


async def order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    order_id = context.user_data.get('customer_order_id')
    if text == '⬅️ К заказам':
        return await show_orders(update, context)
    if text == '❌ Отменить заказ':
        if not order_id:
            return ORDER_DETAILS
        row = get_order(order_id)
        if not row or row[2] != update.effective_user.id:
            await update.message.reply_text('Заказ не найден.', reply_markup=main_menu())
            return MENU
        if row[3] in ('❌ Отменён', '🚗 Выдан'):
            await update.message.reply_text(
                'Этот заказ уже нельзя отменить.',
                reply_markup=ReplyKeyboardMarkup([['⬅️ К заказам']], resize_keyboard=True),
            )
            return ORDER_DETAILS
        context.user_data['confirm_cancel_order'] = True
        await update.message.reply_text(
            f'⚠️ Вы действительно хотите отменить заказ №{order_id}?',
            reply_markup=ReplyKeyboardMarkup(
                [['✅ Да, отменить'], ['↩️ Не отменять']],
                resize_keyboard=True,
            ),
        )
        return ORDER_DETAILS

    if context.user_data.get('confirm_cancel_order'):
        if text == '↩️ Не отменять':
            context.user_data.pop('confirm_cancel_order', None)
            row = get_order(order_id) if order_id else None
            if row:
                await send_order_details(update, row)
            return ORDER_DETAILS
        if text == '✅ Да, отменить':
            context.user_data.pop('confirm_cancel_order', None)
            ok, reason = cancel_order(order_id, update.effective_user.id)
            if not ok:
                await update.message.reply_text(
                    'Заказ уже отменён или его больше нельзя отменить.',
                    reply_markup=main_menu(),
                )
                return MENU

            row = get_order(order_id)
            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=(
                        '❌ КЛИЕНТ ОТМЕНИЛ ЗАКАЗ\n\n'
                        f'🛒 Заказ №{order_id}\n'
                        f'👤 Клиент: {get_name(update.effective_user.id) or update.effective_user.full_name}\n'
                        f'📱 Телефон: {row[13] or get_phone(update.effective_user.id) or "не указан"}\n'
                        f'🚗 Автомобиль: {row[7]} {row[8]}'.strip()
                    ),
                )
            except Exception:
                pass
            await update.message.reply_text(
                f'❌ Заказ №{order_id} отменён.\n\nЕсли захотите оформить его снова, вы сможете повторить заказ.',
                reply_markup=main_menu(),
            )
            context.user_data.clear()
            return MENU
        return ORDER_DETAILS

    if text == '🔄 Повторить заказ':
        row = get_order(order_id) if order_id else None
        if not row or row[2] != update.effective_user.id:
            await update.message.reply_text('Заказ не найден.', reply_markup=main_menu())
            return MENU
        _, _, uid, _, _, _, _, make, model, year, vin, plate, request_text, phone = row
        rid = create_request(uid, None, make, model, year, vin, plate, request_text, phone or get_phone(uid) or 'не указан')
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    '🔄 ПОВТОРНЫЙ ЗАПРОС\n\n'
                    f'📋 Новая заявка №{rid}\n'
                    f'👤 Клиент: {get_name(uid) or "не указано"}\n'
                    f'📱 Телефон: {phone or get_phone(uid) or "не указан"}\n'
                    f'🚗 Автомобиль: {make} {model} {year}'.strip() +
                    f'\n\n🔧 Что требуется:\n{request_text}'
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
    return ORDER_DETAILS
