import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = 440464150
VIN, REQUEST = range(2)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
# =========================
# КЛАВИАТУРЫ
# =========================
cancel_keyboard = ReplyKeyboardMarkup(
    [["❌ Отменить"]],
    resize_keyboard=True,
)
new_request_keyboard = ReplyKeyboardMarkup(
    [["🔄 Новая заявка"]],
    resize_keyboard=True,
)
# =========================
# /START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Здравствуйте!\n\n"
        "Вы обратились в «Запчасти+».\n"
        "Поможем подобрать запчасти для вашего автомобиля.\n\n"
        "🚗 Отправьте VIN автомобиля.\n\n"
        "Например:\n"
        "XTA12345678901234",
        reply_markup=cancel_keyboard,
    )
    return VIN
# =========================
# VIN
# =========================
async def get_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip()
    if len(vin) < 5:
        await update.message.reply_text(
            "⚠️ Похоже, VIN слишком короткий.\n\n"
            "Проверьте VIN и отправьте его ещё раз."
        )
        return VIN
    context.user_data["vin"] = vin
    await update.message.reply_text(
        "✅ VIN получил.\n\n"
        "🔧 Теперь напишите, какие запчасти вам нужны.\n\n"
        "Можно указать несколько деталей одним сообщением.\n\n"
        "Например:\n"
        "Передние тормозные диски и колодки.",
        reply_markup=cancel_keyboard,
    )
    return REQUEST
# =========================
# ЗАПРОС ЗАПЧАСТЕЙ
# =========================
async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.message.text.strip()
    vin = context.user_data.get("vin", "не указан")
    user = update.effective_user
    username = (
        f"@{user.username}"
        if user.username
        else "нет username"
    )
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
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=owner_message,
        )
        logger.info(
            "Заявка успешно отправлена владельцу. Клиент ID: %s",
            user.id,
        )
        await update.message.reply_text(
            "✅ Заявка получена!\n\n"
            "Мы проверим запчасти по вашему VIN, "
            "уточним наличие и цену.\n\n"
            "Спасибо, что обратились в «Запчасти+»! 🚗🔧\n\n"
            "Если хотите сделать ещё один запрос — "
            "нажмите кнопку ниже.",
            reply_markup=new_request_keyboard,
        )
    except Exception as error:
        logger.exception(
            "❌ НЕ УДАЛОСЬ ОТПРАВИТЬ ЗАЯВКУ ВЛАДЕЛЬЦУ: %s",
            error,
        )
        await update.message.reply_text(
            "⚠️ Заявка принята, но произошла ошибка "
            "при передаче менеджеру.\n\n"
            "Пожалуйста, попробуйте ещё раз немного позже.",
            reply_markup=new_request_keyboard,
        )
    context.user_data.clear()
    return ConversationHandler.END
# =========================
# ОТМЕНА
# =========================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Заявка отменена.\n\n"
        "Чтобы начать новую заявку, отправьте /start",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END
# =========================
# НОВАЯ ЗАЯВКА
# =========================
async def new_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🔄 Начинаем новую заявку!\n\n"
        "🚗 Отправьте VIN автомобиля.",
        reply_markup=cancel_keyboard,
    )
    return VIN
# =========================
# ГЛОБАЛЬНЫЕ КНОПКИ
# =========================
async def global_new_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    return await new_request(update, context)
# =========================
# ОШИБКИ
# =========================
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
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
            MessageHandler(
                filters.Regex("^🔄 Новая заявка$"),
                new_request,
            ),
        ],
        states={
            VIN: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_vin,
                ),
            ],
            REQUEST: [
                MessageHandler(
                    filters.Regex("^❌ Отменить$"),
                    cancel,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_request,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )
    application.add_handler(conversation_handler)
    # Обработка кнопки «Новая заявка»
    # даже после завершения предыдущего диалога
    application.add_handler(
        MessageHandler(
            filters.Regex("^🔄 Новая заявка$"),
            global_new_request,
        )
    )
    application.add_error_handler(error_handler)
    logger.info("Бот запущен!")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )
if __name__ == "__main__":
    main()