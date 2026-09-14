from telegram import ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    return ReplyKeyboardMarkup([
        ['🔧 Подобрать запчасть'],
        ['📋 Мои заявки'],
        ['🚗 Мои автомобили'],
        ['📱 Мой телефон'],
        ['👤 Мои данные'],
    ], resize_keyboard=True)


def back_keyboard(): return ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)

def phone_menu(): return ReplyKeyboardMarkup([['📱 Изменить телефон'],['⬅️ Назад']], resize_keyboard=True)

def profile_menu(): return ReplyKeyboardMarkup([['✏️ Изменить имя'],['📱 Изменить телефон'],['⬅️ Назад']], resize_keyboard=True)

def request_phone_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton('📱 Отправить мой номер', request_contact=True)],['Пропустить'],['⬅️ Назад']], resize_keyboard=True)


def consent_keyboard():
    return ReplyKeyboardMarkup([['📄 Политика обработки ПД'],['✅ Согласен'],['❌ Не согласен']], resize_keyboard=True)


def admin_menu():
    return ReplyKeyboardMarkup([['📋 Новые заявки'],['🔎 Все заявки'],['📊 Статистика'],['🏠 Клиентское меню']], resize_keyboard=True)


def admin_request_actions():
    return ReplyKeyboardMarkup([
        ['🔎 Взять в работу'],
        ['💰 Предложение готово'],
        ['💬 Написать клиенту'],
        ['✅ Выполнена','❌ Отменена'],
        ['⬅️ К заявкам'],
    ], resize_keyboard=True)
