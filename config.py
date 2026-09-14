import os


BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 440464150

DB_NAME = os.getenv(
    "DB_NAME",
    "zapchasti_plus.db"
)

# Данные оператора
OPERATOR_NAME = os.getenv(
    "OPERATOR_NAME",
    "ИП — укажите ФИО"
)

OPERATOR_INN = os.getenv(
    "OPERATOR_INN",
    "укажите ИНН"
)

OPERATOR_OGRNIP = os.getenv(
    "OPERATOR_OGRNIP",
    "укажите ОГРНИП"
)

OPERATOR_ADDRESS = os.getenv(
    "OPERATOR_ADDRESS",
    "укажите адрес регистрации"
)

OPERATOR_CONTACT = os.getenv(
    "OPERATOR_CONTACT",
    "укажите телефон и e-mail"
)

# Публичная ссылка на политику
POLICY_URL = os.getenv(
    "POLICY_URL",
    ""
)
