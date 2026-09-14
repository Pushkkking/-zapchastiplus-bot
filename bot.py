import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
VIN, REQUEST = range(2)
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = 440464150
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Здравствуйте!\n\n"
        "Вы обратились в «Запчасти+» — поможем подобрать "
        "запчасти для вашего автомобиля.\n\n"
        "🚗 Для начала отправьте VIN автомобиля."
    )
    return VIN
async def get_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["vin"] = update.message.text.strip()
    await update.message.reply_text(
        "Отлично 👍\n\n"
        "Теперь напишите, какие запчасти вам нужны.\n"
        "Можно указать несколько деталей в одном сообщении."
    )
    return REQUEST
async def get_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = context.user_data.get("vin", "не указан")
    request = update.message.text.strip()
    user = update.effective_user
    username = f"@{user.username}" if user.username else "нет username"
    message = (
        "🔔 НОВАЯ ЗАЯВКА «ЗАПЧАСТИ+»\n\n"
        f"👤 Клиент: {user.full_name}\n"
        f"📱 Username: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"🚗 VIN: {vin}\n"
        f"🔧 Требуется: {request}"
    )
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=message
    )
    await update.message.reply_text(
        "✅ Заявка получена!\n\n"
        "Мы проверим наличие и цены и свяжемся с вами.\n\n"
        "Спасибо, что обратились в «Запчасти+»!"
    )
    return ConversationHandler.END
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Заявка отменена. Чтобы начать заново, нажмите /start"
    )
    return ConversationHandler.END
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            VIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_vin)
            ],
            REQUEST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_request)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conversation)
    print("Бот запущен!")
    app.run_polling()
if __name__ == "__main__":
    main()