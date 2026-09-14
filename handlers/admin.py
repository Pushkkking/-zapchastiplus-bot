from telegram import Update,ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config import OWNER_ID
from database.requests import get_all_requests,get_request,update_status,get_stats
from database.users import get_name,get_phone,get_username
from keyboards.keyboards import admin_menu,main_menu
from states import ADMIN_MENU,ADMIN_REQUEST_LIST,ADMIN_REQUEST_DETAILS,ADMIN_MESSAGE,MENU

STATUSES={'🔎 Взять в работу':'🔎 Подбираем','💰 Предложение готово':'💰 Предложение готово','✅ Выполнена':'✅ Выполнена','❌ Отменена':'❌ Отменена'}

def require_owner(update): return update.effective_user.id==OWNER_ID

def admin_row_title(r):
    rid,uid,make,model,year,text,status,created=r; car=f'{make} {model}'.strip() or 'VIN'; return f'📋 №{rid} — {car} — {status}'

async def admin_entry(update,context):
    if not require_owner(update): return MENU
    context.user_data.clear(); await update.message.reply_text('🛠 АДМИН-ПАНЕЛЬ\n\nВыберите действие:',reply_markup=admin_menu()); return ADMIN_MENU

async def admin_menu_handler(update,context):
    if not require_owner(update): return MENU
    t=update.message.text.strip()
    if t=='📋 Новые заявки': return await admin_list(update,context,'🆕 Новая')
    if t=='🔎 Все заявки': return await admin_list(update,context,None)
    if t=='📊 Статистика':
        total,new,sel,offer,done,cancel=get_stats(); await update.message.reply_text(f'📊 Статистика\n\nВсего заявок: {total}\n🆕 Новая: {new}\n🔎 Подбираем: {sel}\n💰 Предложение готово: {offer}\n✅ Выполнена: {done}\n❌ Отменена: {cancel}',reply_markup=admin_menu()); return ADMIN_MENU
    if t=='🏠 Клиентское меню': await update.message.reply_text('Клиентское меню:',reply_markup=main_menu()); return MENU
    return ADMIN_MENU

async def admin_list(update,context,status):
    rows=get_all_requests(status); context.user_data['admin_request_ids']=[r[0] for r in rows]
    if not rows: await update.message.reply_text('Заявок нет.',reply_markup=admin_menu()); return ADMIN_MENU
    context.user_data['admin_list_mode']=status
    await update.message.reply_text('📋 Заявки:',reply_markup=ReplyKeyboardMarkup([[admin_row_title(r)] for r in rows]+[['⬅️ В админ-панель']],resize_keyboard=True)); return ADMIN_REQUEST_LIST

async def admin_request_list(update,context):
    if not require_owner(update): return MENU
    t=update.message.text.strip()
    if t=='⬅️ В админ-панель': return await admin_entry(update,context)
    try: rid=int(t.split('№',1)[1].split(' ',1)[0])
    except (ValueError,IndexError): return ADMIN_REQUEST_LIST
    if rid not in context.user_data.get('admin_request_ids',[]): return ADMIN_REQUEST_LIST
    row=get_request(rid)
    if not row: return ADMIN_REQUEST_LIST
    context.user_data['admin_request_id']=rid
    await send_admin_details(update,row)
    return ADMIN_REQUEST_DETAILS

async def send_admin_details(update,row):
    rid,uid,make,model,year,vin,plate,text,phone,status,created,updated=row
    lines=[]
    for label,val in [('Марка',make),('Модель',model),('Год',year),('VIN',vin),('Госномер',plate)]:
        if val: lines.append(f'{label}: {val}')
    tg=get_username(uid); customer=get_name(uid) or 'не указано'; vehicle='\n'.join(lines) or 'не указан'
    msg=(f'📋 Заявка №{rid}\n\n📅 Создана: {created}\n🔄 Изменена: {updated}\n📌 Статус: {status}\n\n👤 Клиент: {customer}\n📱 Телефон: {phone or "не указан"}\n💬 Telegram: {("@"+tg) if tg else "не указан"}\n\n🚗 АВТОМОБИЛЬ\n{vehicle}\n\n🔧 ЧТО НУЖНО:\n{text}')
    await update.message.reply_text(msg,reply_markup=ReplyKeyboardMarkup([['🔎 Взять в работу'],['💰 Предложение готово'],['💬 Написать клиенту'],['✅ Выполнена','❌ Отменена'],['⬅️ К заявкам']],resize_keyboard=True))

async def admin_details(update,context):
    if not require_owner(update): return MENU
    t=update.message.text.strip(); rid=context.user_data.get('admin_request_id')
    if t=='⬅️ К заявкам': return await admin_list(update,context,context.user_data.get('admin_list_mode'))
    if t in STATUSES:
        status=STATUSES[t]; update_status(rid,status); row=get_request(rid)
        await send_admin_details(update,row)
        await context.bot.send_message(chat_id=row[1],text=f'📋 По заявке №{rid} изменился статус:\n\n{status}')
        return ADMIN_REQUEST_DETAILS
    if t=='💬 Написать клиенту':
        await update.message.reply_text('Введите сообщение клиенту:'); return ADMIN_MESSAGE
    return ADMIN_REQUEST_DETAILS

async def admin_message(update,context):
    if not require_owner(update): return MENU
    text=update.message.text.strip(); rid=context.user_data.get('admin_request_id'); row=get_request(rid)
    if not row: return await admin_entry(update,context)
    await context.bot.send_message(chat_id=row[1],text=f'💬 Сообщение от «Запчасти+»:\n\n{text}')
    await update.message.reply_text('Сообщение отправлено клиенту ✅')
    await send_admin_details(update,row)
    return ADMIN_REQUEST_DETAILS
