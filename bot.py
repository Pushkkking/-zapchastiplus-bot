import logging

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
from handlers.profile import edit_name, edit_phone
from handlers.cars import (
    show_cars, add_car_start, car_make, car_model, car_year,
    car_vin, car_plate, delete_car_start, delete_car_handler, car_back,
)
from handlers.requests import (
    start_request, request_car, request_vin, request_text,
    request_phone, back_to_menu,
)
from handlers.customer_cases import show_cases, case_list, case_details
from handlers.orders import order_create_handler, order_decline_handler
from handlers.customer_orders import order_list, order_details
from handlers.customer_chat import start_customer_reply, receive_customer_message
from handlers.admin import (
    admin_entry, admin_menu_handler, admin_request_or_order_list,
    admin_request_or_order_details, admin_message,
)
from states import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


def main():
    init_db()
    if not BOT_TOKEN:
        raise ValueError('Не найдена переменная BOT_TOKEN в Railway.')

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('admin', admin_entry),
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
                CallbackQueryHandler(order_create_handler, pattern=r'^order_create:\d+$'),
                CallbackQueryHandler(order_decline_handler, pattern=r'^order_decline:\d+$'),
                CallbackQueryHandler(start_customer_reply, pattern=r'^customer_reply:(request|order|general):\d+$'),
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, case_list),
            ],
            ORDER_LIST: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), order_list),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_list),
            ],
            ORDER_DETAILS: [
                MessageHandler(filters.Regex(r'^⬅️ К заказам$'), order_details),
                MessageHandler(filters.Regex(r'^🔄 Повторить заказ$'), order_details),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_details),
            ],
            REQUEST_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, case_details),
            ],
            CAR_MAKE: [
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_make),
            ],
            CAR_MODEL: [
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_model),
            ],
            CAR_YEAR: [
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_year),
            ],
            CAR_VIN: [
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_vin),
            ],
            CAR_PLATE: [
                MessageHandler(filters.Regex(r'^(?:⬅️\s*)?Назад$'), car_back),
                MessageHandler(filters.TEXT & ~filters.COMMAND, car_plate),
            ],
            DELETE_CAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_car_handler)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_PHONE: [
                MessageHandler(filters.CONTACT, edit_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_phone),
            ],
            CUSTOMER_MESSAGE: [
                MessageHandler(filters.Regex(r'^⬅️ Назад$'), cancel),
                MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, receive_customer_message),
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
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv)
    print('Бот запущен...')
    app.run_polling()


if __name__ == '__main__':
    main()
