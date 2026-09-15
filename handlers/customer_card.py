from io import BytesIO
import qrcode
import barcode
from barcode.writer import ImageWriter

from telegram import Update
from telegram.ext import ContextTypes

from config import BOT_USERNAME
from database.users import get_card_token, get_card_number
from database.cashback import get_balance, get_order_spent
from database.loyalty import get_level
from keyboards.keyboards import profile_menu
from states import PROFILE_MENU


async def show_customer_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = get_card_token(update.effective_user.id)
    card_number = get_card_number(update.effective_user.id)
    if not token:
        await update.message.reply_text('Не удалось сформировать карту. Попробуйте ещё раз.')
        return PROFILE_MENU

    username = BOT_USERNAME or (await context.bot.get_me()).username
    link = f'https://t.me/{username}?start=card_{token}'
    balance = get_balance(update.effective_user.id)
    # Уровень здесь показываем по фактически полученным покупкам — как в статистике.
    from database.orders import get_user_orders
    from database.loyalty import parse_amount
    orders = get_user_orders(update.effective_user.id)
    total = sum(max(0.0, parse_amount(r[6]) - get_order_spent(r[0]))
                 for r in orders if r[3] == '🚗 Выдан')
    level_name, rate = get_level(max(0, total))

    qr = qrcode.QRCode(version=None, box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    qr_image = qr.make_image().convert('RGB')

    # Code 128: пригодится в будущем для сканера/кассы/1С.
    code = barcode.get('code128', card_number, writer=ImageWriter())
    barcode_buf = BytesIO()
    code.write(barcode_buf, options={'write_text': True, 'module_width': 0.35, 'module_height': 15, 'font_size': 10, 'quiet_zone': 3})
    barcode_buf.seek(0)
    from PIL import Image, ImageDraw
    bar_image = Image.open(barcode_buf).convert('RGB')

    width = max(qr_image.width, bar_image.width, 700)
    height = qr_image.height + bar_image.height + 60
    card = Image.new('RGB', (width, height), 'white')
    card.paste(qr_image, ((width - qr_image.width)//2, 0))
    card.paste(bar_image, ((width - bar_image.width)//2, qr_image.height + 20))
    draw = ImageDraw.Draw(card)
    draw.text((20, height - 25), card_number, fill='black')

    bio = BytesIO()
    card.save(bio, format='PNG')
    bio.seek(0)
    bio.name = 'card.png'

    await update.message.reply_photo(
        photo=bio,
        caption=(
            '💳 КАРТА ПОСТОЯННОГО КЛИЕНТА\n\n'
            f'🔢 Номер карты: {card_number}\n'
            f'🏆 Уровень: {level_name}\n'
            f'💳 Кешбэк: {rate}%\n'
            f'⭐ Доступно: {balance:,.2f} ₽'.replace(',', ' ')
            + '\n\nПредъявите этот QR-код сотруднику «Запчасти+» при покупке.\n'
              'Код карты уникальный и не меняется при обновлении бота.'
        ),
    )
    await update.message.reply_text('Меню «Мои данные»:', reply_markup=profile_menu())
    return PROFILE_MENU
