import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = os.environ["BOT_TOKEN"]
# Telegram ID владельца
OWNER_ID = 440464150
# Состояния диалога
VIN, REQUEST = range(2)
# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
# =========================
# КЛАВИАТУРА
# =========================
new_request_keyboard = ReplyKeyboardMarkup(
    [["🔄 Новая заявка"]],
    resize_keyboard=True,
)
# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало новой заявки."""
    # Полностью очищаем предыдущую заявку
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Здравствуйте!\n\n"
        "Вы обратились в «Запчасти+».\n"
        "Поможем подобрать запчасти для вашего автомобиля.\n\n"
        "🚗 Отправьте VIN автомобиля.\n\n"
        "Например:\n"
        "XTA12345678901234",
        reply_markup=ReplyKeyboardMarkup(
            [["❌ Отменить"]],
            resize_keyboard=True,
        ),
    )
    return VIN
# =========================
# ПОЛУЧАЕМ VIN
# =========================
async def get_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение VIN."""
    vin = update.message.text.strip()
    if len(vin) < 5:
        await update.message.reply_text(
            "⚠️ Похоже, VIN слишком короткий.\n\n"
            "Пожалуйста, проверьте VIN и отправьте его ещё раз."
        )
        return VIN
    context.user_data["vin"] = vin
    await update.message.reply_text(
        "✅ VIN получил.\n\n"
        "🔧 Теперь напишите, какие запчасти вам нужны.\n\n"
        "Можно указать несколько деталей одним сообщением.\n\n"
        "Например:\n"
        "Передние тормозные диски и колодки."
    )
    return REQUEST
# =========================
# ПОЛУЧАЕМ ЗАПРОС
# =========================
async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение списка необходимых запчастей."""
    request = update.message.text.strip()
    vin = context.user_data.get("vin", "не указан")
    user = update.effective_user
    if user.username:
        username = f"@{user.username}"
    else:
        username = "нет username"
    # Формируем заявку для владельца
    owner_message = (
        "🔔 НОВАЯ ЗАЯВКА «ЗАПЧАСТИ+»\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Клиент: {user.full_name}\n"
        f"📱 Username: {username}\n"
        f"🆔 Telegram ID: {user.id}\n\n"
        f"🚗 VIN:\n{vin}\n\n"
        f"🔧 Что требуется:\n{request}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    # Отправляем заявку владельцу
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=owner_message,
        )
        logger.info(
            "Заявка отправлена владельцу. Клиент ID: %s",
            user.id,
        )
    except Exception as error:
        logger.exception(
            "ОШИБКА отправки заявки владельцу: %s",
            error,
        )
    # Ответ клиенту
    await update.message.reply_text(
        "✅ Заявка получена!\n\n"
        "Мы проверим запчасти по вашему VIN и уточним "
        "наличие и цену.\n\n"
        "Спасибо, что обратились в «Запчасти+»! 🚗🔧\n\n"
        "Если хотите сделать ещё один запрос — "
        "нажмите кнопку ниже.",
        reply_markup=new_request_keyboard,
    )
    # Очищаем старую заявку
    context.user_data.clear()
    return ConversationHandler.END
# =========================
# НОВАЯ ЗАЯВКА
# =========================
async def new_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало новой заявки через кнопку."""
    context.user_data.clear()
    await update.message.reply_text(
        "🔄 Начинаем новую заявку.\n\n"
        "🚗 Отправьте VIN автомобиля."
    )
    return VIN
# =========================
# ОТМЕНА
# =========================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заявки."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Заявка отменена.\n\n"
        "Чтобы начать новую заявку, нажмите /start"
    )
    return ConversationHandler.END
# =========================
# ОБРАБОТКА ОШИБОК
# =========================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Записываем ошибки в Railway Logs."""
    logger.error(
        "Ошибка при обработке обновления:",
        exc_info=context.error,
    )
# =========================
# ЗАПУСК
# =========================
def main():
    logger.info("Запускаем бота «Запчасти+»...")
    application = Application.builder().token(BOT_TOKEN).build()
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
        ],
        states={
            VIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_vin,
                ),
            ],
            REQUEST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_request,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
            MessageHandler(
                filters.Regex("^❌ Отменить$"),
                cancel,
            ),
            MessageHandler(
                filters.Regex("^🔄 Новая заявка$"),
                new_request,
            ),
        ],
        allow_reentry=True,
    )
    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)
    logger.info("Бот запущен!")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )
if __name__ == "__main__":
    main()