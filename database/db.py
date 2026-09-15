import os
import shutil
import sqlite3
import secrets
from datetime import datetime

from config import DB_NAME


def _prepare_database_path():
    """Prepare the persistent Railway Volume database path.

    On the first launch after attaching /data, an existing SQLite database
    from the old ephemeral working directory is copied to the Volume if the
    Volume does not already contain a database.
    """
    target = os.path.abspath(DB_NAME)

    # Only perform the automatic migration when the application is configured
    # to use Railway's default /data path.
    if not target.startswith('/data/'):
        return target

    os.makedirs('/data', exist_ok=True)
    if os.path.exists(target):
        return target

    legacy = os.path.abspath('zapchasti_plus.db')
    if os.path.exists(legacy) and legacy != target:
        shutil.copy2(legacy, target)
        # Preserve SQLite WAL/SHM files too if they exist. Usually they won't,
        # but copying them avoids an incomplete database state on first boot.
        for suffix in ('-wal', '-shm'):
            legacy_sidecar = legacy + suffix
            if os.path.exists(legacy_sidecar):
                shutil.copy2(legacy_sidecar, target + suffix)

    return target


def db():
    path = _prepare_database_path()
    conn = sqlite3.connect(path, timeout=30)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn


def _add_column(cur, table, column, definition):
    try:
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
    except sqlite3.OperationalError:
        pass


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        telegram_name TEXT,
        username TEXT,
        name TEXT,
        phone TEXT,
        consent_given INTEGER NOT NULL DEFAULT 0,
        consent_at TEXT,
        card_token TEXT UNIQUE,
        card_number TEXT UNIQUE
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        year TEXT,
        vin TEXT,
        plate TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        car_id INTEGER,
        make TEXT,
        model TEXT,
        year TEXT,
        vin TEXT,
        plate TEXT,
        request_text TEXT NOT NULL,
        phone TEXT,
        status TEXT NOT NULL DEFAULT '🆕 Новая',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL UNIQUE,
        telegram_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT '🆕 Новый',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        offer_text TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS cashback_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        order_id INTEGER,
        amount REAL NOT NULL,
        kind TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        message_type TEXT NOT NULL DEFAULT 'text',
        file_id TEXT,
        request_id INTEGER,
        order_id INTEGER,
        created_at TEXT NOT NULL
    )''')

    # Миграции существующей БД.
    _add_column(cur, 'users', 'telegram_name', 'TEXT')
    _add_column(cur, 'users', 'name', 'TEXT')
    _add_column(cur, 'users', 'consent_given', 'INTEGER NOT NULL DEFAULT 0')
    _add_column(cur, 'users', 'consent_at', 'TEXT')
    _add_column(cur, 'users', 'card_token', 'TEXT')
    _add_column(cur, 'users', 'card_number', 'TEXT')
    _add_column(cur, 'requests', 'updated_at', "TEXT NOT NULL DEFAULT ''")
    _add_column(cur, 'requests', 'offer_text', 'TEXT')
    _add_column(cur, 'orders', 'offer_text', 'TEXT')
    _add_column(cur, 'orders', 'cashback_amount', 'REAL NOT NULL DEFAULT 0')
    _add_column(cur, 'messages', 'message_type', "TEXT NOT NULL DEFAULT 'text'")
    _add_column(cur, 'messages', 'file_id', 'TEXT')

    # Для уже выданных заказов один раз рассчитываем кешбэк задним числом.
    # Расчёт идёт в хронологическом порядке по каждому клиенту.
    from database.loyalty import parse_amount, calculate_cashback
    cur.execute('''SELECT id, telegram_id, offer_text, created_at
                   FROM orders
                   WHERE status='🚗 Выдан'
                   ORDER BY telegram_id, id''')
    completed_by_user = {}
    for order_id, user_id, offer_text, created_at in cur.fetchall():
        if cur.execute('SELECT cashback_amount FROM orders WHERE id=?', (order_id,)).fetchone()[0]:
            completed_by_user[user_id] = completed_by_user.get(user_id, 0) + parse_amount(offer_text)
            continue
        amount = parse_amount(offer_text)
        before = completed_by_user.get(user_id, 0)
        cashback = calculate_cashback(before + amount, amount)
        cur.execute('UPDATE orders SET cashback_amount=? WHERE id=?', (cashback, order_id))
        completed_by_user[user_id] = before + amount

    # Уникальные токены и стабильные номера карт для существующих клиентов.
    cur.execute("SELECT telegram_id, card_token, card_number FROM users")
    for user_id, existing_token, existing_number in cur.fetchall():
        token = existing_token or secrets.token_urlsafe(9)
        number = existing_number
        if not number:
            while True:
                number = f"ZP-{secrets.randbelow(100_000_000):08d}"
                try:
                    cur.execute('UPDATE users SET card_token=?, card_number=? WHERE telegram_id=?', (token, number, user_id))
                    break
                except sqlite3.IntegrityError:
                    number = None
                    continue
        else:
            cur.execute('UPDATE users SET card_token=? WHERE telegram_id=?', (token, user_id))

    # Переносим уже начисленный кешбэк из orders в журнал операций.
    cur.execute("SELECT id, telegram_id, cashback_amount FROM orders WHERE cashback_amount>0 AND status='🚗 Выдан' ORDER BY id")
    for order_id, user_id, amount in cur.fetchall():
        exists = cur.execute("SELECT 1 FROM cashback_transactions WHERE order_id=? AND kind='earned' LIMIT 1", (order_id,)).fetchone()
        if not exists:
            cur.execute('''INSERT INTO cashback_transactions
                (telegram_id, order_id, amount, kind, note, created_at)
                VALUES (?, ?, ?, 'earned', ?, ?)''',
                (user_id, order_id, float(amount), 'Перенос из истории заказов', datetime.now().strftime('%d.%m.%Y %H:%M:%S')))

    conn.commit()
    conn.close()
