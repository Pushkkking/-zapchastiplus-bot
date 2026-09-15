from telegram import Update
from telegram.ext import ContextTypes

from database.orders import get_user_orders
from database.loyalty import get_level, get_next_level, parse_amount
from keyboards.keyboards import profile_menu
from states import PROFILE_MENU


def get_customer_statistics(user_id):
    from database.cashback import get_balance, get_order_spent
    rows = get_user_orders(user_id)
    active = [r for r in rows if r[3] != '❌ Отменён']
    completed = [r for r in rows if r[3] == '🚗 Выдан']
    completed_amount = sum(max(0.0, parse_amount(r[6]) - get_order_spent(r[0])) for r in completed)
    cashback_balance = get_balance(user_id)
    level_name, cashback_rate = get_level(completed_amount)
    next_level = get_next_level(completed_amount)
    return (len(active), completed_amount, len(completed), cashback_balance, level_name, cashback_rate, next_level)


async def show_customer_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    (
        total_orders,
        completed_amount,
        completed_orders,
        cashback_balance,
        level_name,
        cashback_rate,
        next_level,
    ) = get_customer_statistics(update.effective_user.id)

    amount_text = f'{completed_amount:,.0f} ₽'.replace(',', ' ')
    cashback_text = f'{cashback_balance:,.2f} ₽'.replace(',', ' ')

    text = (
        '📊 Моя статистика\n\n'
        f'🛒 Заказов: {total_orders}\n'
        f'✅ Получено: {completed_orders}\n'
        f'💰 Сумма покупок: {amount_text}\n\n'
        f'🏆 Уровень: {level_name}\n'
        f'💳 Кешбэк: {cashback_rate}%\n'
        f'⭐ Доступно кешбэка: {cashback_text}'
    )

    if next_level:
        threshold, rate, name = next_level
        left = max(0, threshold - completed_amount)
        left_text = f'{left:,.0f} ₽'.replace(',', ' ')
        text += f'\n\nДо уровня {name}: ещё {left_text}'
    else:
        text += '\n\n🎉 У вас максимальный уровень кешбэка!'

    await update.message.reply_text(text, reply_markup=profile_menu())
    return PROFILE_MENU

