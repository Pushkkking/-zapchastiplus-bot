import re

from telegram import Update
from telegram.ext import ContextTypes

from database.orders import get_user_orders
from keyboards.keyboards import main_menu
from states import MENU


def _money_from_text(text):
    if not text:
        return None
    # Сначала ищем строки с явным итогом.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = []
    for line in lines:
        low = line.lower()
        if 'итого' in low or 'всего' in low or 'к оплате' in low:
            candidates.extend(re.findall(r'(\d[\d\s]*[.,]?\d*)\s*(?:₽|руб\.?|р\.)', line, flags=re.I))
    if not candidates:
        candidates = re.findall(r'(\d[\d\s]*[.,]?\d*)\s*(?:₽|руб\.?|р\.)', text, flags=re.I)
    if not candidates:
        return None
    raw = candidates[-1].replace(' ', '').replace(',', '.')
    try:
        return float(raw)
    except ValueError:
        return None


def get_customer_statistics(user_id):
    rows = get_user_orders(user_id)
    active = [r for r in rows if r[3] != '❌ Отменён']
    completed = [r for r in rows if r[3] == '🚗 Выдан']

    # Для будущей программы лояльности считаем сумму выданных заказов.
    completed_amount = sum((_money_from_text(r[6]) or 0) for r in completed)
    active_amount = sum((_money_from_text(r[6]) or 0) for r in active)
    return len(active), active_amount, len(completed), completed_amount


async def show_customer_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_orders, total_amount, completed_orders, completed_amount = get_customer_statistics(
        update.effective_user.id
    )
    amount_text = f'{total_amount:,.0f} ₽'.replace(',', ' ')
    completed_amount_text = f'{completed_amount:,.0f} ₽'.replace(',', ' ')

    text = (
        '📊 Моя статистика\n\n'
        f'🛒 Заказов: {total_orders}\n'
        f'💰 Сумма заказов: {amount_text}\n\n'
        f'✅ Получено заказов: {completed_orders}\n'
        f'💳 Сумма полученных заказов: {completed_amount_text}'
    )
    await update.message.reply_text(text, reply_markup=main_menu())
    return MENU
