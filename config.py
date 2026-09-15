import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 440464150

# На Railway с подключённым Volume база будет храниться в /data.
# Если /data недоступна (например, локальный запуск на Mac), используется
# обычный файл в папке проекта.
_default_db = '/data/zapchasti_plus.db' if os.path.isdir('/data') else 'zapchasti_plus.db'
DB_NAME = os.getenv('DB_NAME', _default_db)

# Заполни эти переменные в Railway перед запуском продакшн-версии.
OPERATOR_NAME = os.getenv('OPERATOR_NAME', 'ИП — укажите ФИО')
OPERATOR_CONTACT = os.getenv('OPERATOR_CONTACT', 'укажите контакт оператора')
POLICY_URL = os.getenv('POLICY_URL', '')
