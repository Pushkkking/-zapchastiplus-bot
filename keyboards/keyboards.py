from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import POLICY_URL


def main_menu():
    return ReplyKeyboardMarkup(
        [
            ['🔧 Подобрать запчасть'],
            ['📋 Мои обращения'],
            ['💬 Связаться с Запчасти+'],
            ['🚗 Мои автомобили'],
            ['👤 Мои данные'],
        ],
        resize_keyboard=True,
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [['⬅️ Назад']],
        resize_keyboard=True,
    )


def phone_menu():
    return ReplyKeyboardMarkup(
        [
            ['📱 Изменить телефон'],
            ['⬅️ Назад'],
        ],
        resize_keyboard=True,
    )


def profile_menu():
    return ReplyKeyboardMarkup(
        [
            ['✏️ Изменить имя'],
            ['📱 Изменить телефон'],
            ['📊 Моя статистика'],
            ['⬅️ Назад'],
        ],
        resize_keyboard=True,
    )


def request_phone_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton('📱 Отправить мой номер', request_contact=True)],
            ['Пропустить'],
            ['⬅️ Назад'],
        ],
        resize_keyboard=True,
    )


def consent_keyboard():
    buttons = []
    if POLICY_URL:
        buttons.append([
            InlineKeyboardButton(
                '📄 Ознакомиться с политикой',
                url=POLICY_URL,
            )
        ])
    buttons.extend([
        [InlineKeyboardButton('✅ Даю согласие', callback_data='consent_yes')],
        [InlineKeyboardButton('❌ Не согласен', callback_data='consent_no')],
    ])
    return InlineKeyboardMarkup(buttons)


def order_confirm_keyboard(request_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            '✅ Оформить заказ',
            callback_data=f'order_create:{request_id}',
        )],
        [InlineKeyboardButton(
            '💬 Задать вопрос',
            callback_data=f'customer_reply:request:{request_id}',
        )],
        [InlineKeyboardButton(
            '❌ Отказаться',
            callback_data=f'order_decline:{request_id}',
        )],
    ])


def customer_reply_keyboard(request_id=None, order_id=None):
    target_type = 'order' if order_id else 'request'
    target_id = order_id or request_id
    if not target_id:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton('💬 Ответить', callback_data='customer_reply:general:0')]
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            '💬 Ответить',
            callback_data=f'customer_reply:{target_type}:{target_id}',
        )]
    ])


def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ['📋 Новые заявки'],
            ['🔎 Все заявки'],
            ['🛒 Заказы'],
            ['💬 Сообщения'],
            ['👥 Клиенты'],
            ['📊 Статистика'],
            ['🏠 Клиентское меню'],
        ],
        resize_keyboard=True,
    )


def admin_request_actions():
    return ReplyKeyboardMarkup(
        [
            ['🔎 Взять в работу'],
            ['💰 Предложение готово'],
            ['💬 Написать клиенту'],
            ['✅ Выполнена', '❌ Отменена'],
            ['⬅️ К заявкам'],
        ],
        resize_keyboard=True,
    )



def admin_message_thread_actions():
    return ReplyKeyboardMarkup(
        [['💬 Ответить'], ['⬅️ К сообщениям']],
        resize_keyboard=True,
    )

def admin_order_actions():
    return ReplyKeyboardMarkup(
        [
            ['🔧 В работу'],
            ['📦 Готов к выдаче'],
            ['💬 Написать клиенту'],
            ['🚗 Выдан', '❌ Отменить'],
            ['⬅️ К заказам'],
        ],
        resize_keyboard=True,
    )
