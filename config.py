import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 440464150
DB_NAME = os.getenv('DB_NAME', 'zapchasti_plus.db')

# Заполни эти переменные в Railway перед запуском продакшн-версии.
OPERATOR_NAME = os.getenv('OPERATOR_NAME', 'ИП — укажите ФИО')
OPERATOR_CONTACT = os.getenv('OPERATOR_CONTACT', 'укажите контакт оператора')
POLICY_URL = os.getenv('POLICY_URL', '')
