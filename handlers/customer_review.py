from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.orders import get_order
from database.reviews import save_review, get_review
from states import MENU


def review_keyboard(order_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⭐', callback_data=f'review:{order_id}:1'), InlineKeyboardButton('⭐⭐', callback_data=f'review:{order_id}:2'), InlineKeyboardButton('⭐⭐⭐', callback_data=f'review:{order_id}:3')],
        [InlineKeyboardButton('⭐⭐⭐⭐', callback_data=f'review:{order_id}:4'), InlineKeyboardButton('⭐⭐⭐⭐⭐', callback_data=f'review:{order_id}:5')],
    ])


async def review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, order_id_s, rating_s = query.data.split(':')
        order_id, rating = int(order_id_s), int(rating_s)
    except (ValueError, IndexError):
        return MENU
    row = get_order(order_id)
    if not row or row[2] != update.effective_user.id or row[3] != '🚗 Выдан':
        await query.edit_message_text('Оценка недоступна для этого заказа.')
        return MENU
    if get_review(order_id):
        await query.edit_message_text('⭐ Вы уже оценили этот заказ. Спасибо!')
        return MENU
    if save_review(update.effective_user.id, order_id, rating):
        await query.edit_message_text(
            f'Спасибо за оценку! {"⭐" * rating}\n\n'
            'Ваш отзыв помогает нам улучшать сервис «Запчасти+».'
        )
    else:
        await query.edit_message_text('Не удалось сохранить оценку. Попробуйте ещё раз.')
    return MENU
