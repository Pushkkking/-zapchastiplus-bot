import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from config import BOT_TOKEN
from database.db import init_db
from handlers.start import (
    start,
    receive_name,
    consent_handler,
    cancel,
)
from handlers.menu import menu_handler
from handlers.profile import (
    edit_name,
    edit_phone,
)
from handlers.cars import (
    show_cars,
    add_car_start,
    car_make,
    car_model,
    car_year,
    car_vin,
    car_plate,
    delete_car_start,
    delete_car_handler,
)
from handlers.requests import (
    start_request,
    request_car,
    request_vin,
    request_text,
    request_phone,
    show_requests,
    request_list,
    request_details,
    back_to_menu,
)
from handlers.admin import (
    admin_entry,
    admin_menu_handler,
    admin_request_list,
    admin_details,
    admin_message,
)
from states import *
logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)
def main():
    init_db()
    if not BOT_TOKEN:
        raise ValueError(
            "Не найдена переменная BOT_TOKEN в Railway."
        )
    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_entry),
        ],
        states={
            # -------------------------
            # СОГЛАСИЕ
            # -------------------------
            CONSENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    consent_handler,
                ),
            ],
            # -------------------------
            # ИМЯ
            # -------------------------
            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_name,
                ),
            ],
            # -------------------------
            # ГЛАВНОЕ МЕНЮ
            # -------------------------
            MENU: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    menu_handler,
                ),
            ],
            # -------------------------
            # ПОДБОР ЗАПЧАСТИ
            # -------------------------
            REQUEST_CAR: [
                # "Назад" обрабатываем ПЕРВЫМ.
                MessageHandler(
                    filters.Regex(r"^⬅️ Назад$"),
                    back_to_menu,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_car,
                ),
            ],
            REQUEST_VIN: [
                # Глобальный выход из подбора.
                MessageHandler(
                    filters.Regex(r"^⬅️ Назад$"),
                    back_to_menu,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_vin,
                ),
            ],
            REQUEST_TEXT: [
                # Глобальный выход из подбора.
                MessageHandler(
                    filters.Regex(r"^⬅️ Назад$"),
                    back_to_menu,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_text,
                ),
            ],
            REQUEST_PHONE: [
                # Сначала "Назад".
                MessageHandler(
                    filters.Regex(r"^⬅️ Назад$"),
                    back_to_menu,
                ),
                MessageHandler(
                    filters.CONTACT,
                    request_phone,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_phone,
                ),
            ],
            # -------------------------
            # МОИ ЗАЯВКИ
            # -------------------------
            REQUEST_LIST: [
                MessageHandler(
                    filters.Regex(r"^⬅️ Назад$"),
                    back_to_menu,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_list,
                ),
            ],
            REQUEST_DETAILS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    request_details,
                ),
            ],
            # -------------------------
            # АВТОМОБИЛИ
            # -------------------------
            CAR_MAKE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_make,
                ),
            ],
            CAR_MODEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_model,
                ),
            ],
            CAR_YEAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_year,
                ),
            ],
            CAR_VIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_vin,
                ),
            ],
            CAR_PLATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    car_plate,
                ),
            ],
            DELETE_CAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    delete_car_handler,
                ),
            ],
            # -------------------------
            # ПРОФИЛЬ
            # -------------------------
            EDIT_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    edit_name,
                ),
            ],
            EDIT_PHONE: [
                MessageHandler(
                    filters.CONTACT,
                    edit_phone,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    edit_phone,
                ),
            ],
            # -------------------------
            # АДМИНКА
            # -------------------------
            ADMIN_MENU: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_menu_handler,
                ),
            ],
            ADMIN_REQUEST_LIST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_request_list,
                ),
            ],
            ADMIN_REQUEST_DETAILS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_details,
                ),
            ],
            ADMIN_MESSAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    admin_message,
                ),
            ],
        },
        # ВАЖНО:
        # /start больше не находится в fallbacks.
        # Это исключает лишний обработчик /start
        # внутри активного ConversationHandler.
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
    )
    app.add_handler(conv)
    print("Бот запущен...")
    app.run_polling()
if __name__ == "__main__":
    main()
