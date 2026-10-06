import logging

from datetime import datetime, time, timezone

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN
from database.db import init_db
from handlers.start import start, receive_name, consent_handler, cancel
from handlers.menu import menu_handler
from handlers.profile import edit_name, edit_phone, start_edit_data, show_referral, start_promo_from_profile, start_birthday, save_birthday_handler
from handlers.cars import (
    show_cars, add_car_start, car_make, car_model, car_year, car_photo_from_make,
    car_vin, car_vin_photo, car_plate, delete_car_start, delete_car_handler, car_back, car_photo_confirm,
)
from handlers.requests import (
    start_request, request_car, request_vin, request_text,
    request_phone, back_to_menu,
)
from handlers.customer_cases import show_cases, case_list, case_details
from handlers.orders import order_create_handler, order_decline_handler, cashback_use_handler, promo_enter_handler, promo_apply_handler
from handlers.customer_orders import order_list, order_details
from handlers.customer_chat import start_customer_reply, start_customer_message, show_chat_history, receive_customer_message
from handlers.customer_stats import show_customer_stats, show_bonus_history
from handlers.customer_card import show_customer_card
from handlers.customer_review import review_handler
async def promo_add_command(update, context):
    from config import OWNER_ID
    if update.effective_user.id != OWNER_ID:
        return
    from database.promos import create_promo
    args = context.args
    if len(args) < 3:
        await update.message.reply_text('Формат: /promoadd КОД percent 10 [лимит]\nили /promoadd КОД fixed 500 [лимит]')
        return
    code, kind, value = args[0], args[1].lower(), args[2]
    try:
        value = float(value)
        limit = int(args[3]) if len(args) > 3 else None
    except ValueError:
        await update.message.reply_text('❌ Проверьте значение скидки и лимит.')
        return
    if kind not in ('percent', 'fixed'):
        await update.message.reply_text('❌ Тип: percent или fixed.')
        return
    ok = create_promo(code, kind, value, limit)
    await update.message.reply_text('✅ Промокод создан.' if ok else '❌ Не удалось создать промокод. Возможно, такой код уже есть.')

from handlers.admin import (
    admin_entry, admin_menu_handler, admin_request_or_order_list,
    admin_request_or_order_details, admin_message,
)
from states import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)



async def birthday_bonus_job(context):
    from database.birthday import users_with_birthday_today, award_birthday_bonus, BIRTHDAY_BONUS, BIRTHDAY_BONUS_DAYS
    today = datetime.now(timezone.utc).date()
    for user_id, name, birthday in users_with_birthday_today(today):
        try:
            awarded, expires = award_birthday_bonus(user_id, today.year)
            if awarded:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        '🎂 С днём рождения! 🎉\n\n'
                        f"Мы начислили вам {BIRTHDAY_BONUS:,.0f} ₽ бонусами в подарок.\n".replace(',', ' ') +
                        f'Бонусы действуют {BIRTHDAY_BONUS_DAYS} дней — до {expires.strftime("%d.%m.%Y")}.\n\n'
                        'Использовать их можно при оформлении заказа.'
                    ),
                )
        except Exception:
            logging.exception('Birthday bonus failed for user %s', user_id)

def main():
    init_db()
    if not BOT_TOKEN:
        raise ValueError('Не найдена переменная BOT_TOKEN в Railway.')

    app = Application.builder().token(BOT_TOKEN).build()
    # Railway runs in UTC; 05:00 UTC = 09:00 in Tolyatti/Samara.
    if app.job_queue:
        app.job_queue.run_daily(birthday_bonus_job, time=time(hour=5, minute=0, tzinfo=timezone.utc), name='birthday_bonus')

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('admin', admin_entry),
            CommandHandler('promoadd', promo_add_command),
        ],
        allow_reentry=True,
        states={
            CONSENT: [
                CallbackQueryHandler(consent_handler, pattern=r'^consent_(yes|no)$'),
            ],
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
            ],
            MENU: [
                CallbackQueryHandler(order_create_handler, pattern=r'^order_create:\d+(?::[0-9.]+)?$'),
                CallbackQueryHandler(cashback_use_handler, pattern=r'^cashback_use:\d+$'),
                CallbackQueryHandler(promo_enter_handler, pattern=r'^promo_enter:\d+$'),
                CallbackQueryHandler(show_bonus_history, pattern=r'^bonus_history$'),
                CallbackQueryHandler(order_decline_handler, pattern=r'^order_decline:\d+$'),
                CallbackQueryHandler(review_handler, pattern=r'^review:\d+:[1-5]$'),
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^💬 Написать сообщение$'), start_customer_message),
                MessageHandler(filters.Regex(r'^📖 История переписки$'), show_chat_history),
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler),
            ],
            REQUEST_CAR: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), back_to_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_car),
            ],
            REQUEST_VIN: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), back_to_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_vin),
            ],
            REQUEST_TEXT: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), back_to_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_text),
            ],
            REQUEST_PHONE: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), back_to_menu),
                MessageHandler(filters.CONTACT, request_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_phone),
            ],
            REQUEST_LIST: [
                CallbackQueryHandler(order_create_handler, pattern=r'^order_create:\d+(?::[0-9.]+)?$'),
                CallbackQueryHandler(cashback_use_handler, pattern=r'^cashback_use:\d+$'),
                CallbackQueryHandler(order_decline_handler, pattern=r'^order_decline:\d+$'),
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, case_list),
            ],
            ORDER_LIST: [
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), order_list),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_list),
            ],
            ORDER_DETAILS: [
                CallbackQueryHandler(order_create_handler, pattern=r'^order_create:\d+(?::[0-9.]+)?$'),
                CallbackQueryHandler(cashback_use_handler, pattern=r'^cashback_use:\d+$'),
                CallbackQueryHandler(order_decline_handler, pattern=r'^order_decline:\d+$'),
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^⬅️ К заказам$'), order_details),
                MessageHandler(filters.Regex(r'^🔄 Повторить заказ$'), order_details),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_details),
            ],
            REQUEST_DETAILS: [
                CallbackQueryHandler(order_create_handler, pattern=r'^order_create:\d+(?::[0-9.]+)?$'),
                CallbackQueryHandler(cashback_use_handler, pattern=r'^cashback_use:\d+$'),
                CallbackQueryHandler(order_decline_handler, pattern=r'^order_decline:\d+$'),
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, case_details),
            ],
            CAR_MAKE: [
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.Regex(r'^📷 Сфотографировать СТС / VIN$'), car_photo_from_make),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_make),
            ],
            CAR_MODEL: [
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_model),
            ],
            CAR_YEAR: [
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_year),
            ],
            CAR_VIN: [
                CallbackQueryHandler(order_create_handler, pattern=r'^order_create:\d+(?::[0-9.]+)?$'),
                CallbackQueryHandler(cashback_use_handler, pattern=r'^cashback_use:\d+$'),
                CallbackQueryHandler(order_decline_handler, pattern=r'^order_decline:\d+$'),
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                CallbackQueryHandler(car_photo_confirm, pattern=r'^car_photo_confirm:(yes|no)$'),
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.PHOTO & ~filters.COMMAND, car_vin_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_vin),
            ],
            CAR_PLATE: [
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_plate),
            ],
            DELETE_CAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_car_handler)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            PROFILE_MENU: [
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
                CallbackQueryHandler(show_bonus_history, pattern=r'^bonus_history$'),
                MessageHandler(filters.Regex(r'^📊 Моя статистика$'), show_customer_stats),
                MessageHandler(filters.Regex(r'^💳 Моя карта$'), show_customer_card),
                MessageHandler(filters.Regex(r'^👥 Пригласить друга$'), show_referral),
                MessageHandler(filters.Regex(r'^🎟 Промокод$'), start_promo_from_profile),
                MessageHandler(filters.Regex(r'^✏️ Изменить данные$'), start_edit_data),
                MessageHandler(filters.Regex(r'^🎂 День рождения$'), start_birthday),
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), back_to_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler),
            ],
            BIRTHDAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_birthday_handler),
            ],
            PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, promo_apply_handler),
            ],
            EDIT_PHONE: [
                MessageHandler(filters.CONTACT, edit_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_phone),
            ],
            CUSTOMER_MESSAGE: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), cancel),
                MessageHandler(filters.PHOTO & ~filters.COMMAND, receive_customer_message),
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, receive_customer_message),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_customer_message),
            ],
            ADMIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_handler),
            ],
            ADMIN_REQUEST_LIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_request_or_order_list),
            ],
            ADMIN_REQUEST_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_request_or_order_details),
            ],
            ADMIN_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('promoadd', promo_add_command)],
    )

    # Эти callback-и должны работать независимо от текущего состояния клиента.
    # Например, отзыв может прийти сразу после выдачи заказа, когда клиент находится
    # не в MENU, а история бонусов открывается из карточки.
    app.add_handler(CallbackQueryHandler(review_handler, pattern=r'^review:\d+:[1-5]$'))
    app.add_handler(CallbackQueryHandler(show_bonus_history, pattern=r'^bonus_history$'))
    app.add_handler(conv)
    print('Бот запущен...')
    app.run_polling()


if __name__ == '__main__':
    main()
