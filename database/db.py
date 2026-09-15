import sqlite3
from config import DB_NAME


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('PRAGMA foreign_keys = ON')
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
        consent_at TEXT
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
        updated_at TEXT NOT NULL
    )''')

    # Миграции существующей БД.
    _add_column(cur, 'users', 'telegram_name', 'TEXT')
    _add_column(cur, 'users', 'name', 'TEXT')
    _add_column(cur, 'users', 'consent_given', 'INTEGER NOT NULL DEFAULT 0')
    _add_column(cur, 'users', 'consent_at', 'TEXT')
    _add_column(cur, 'requests', 'updated_at', "TEXT NOT NULL DEFAULT ''")
    _add_column(cur, 'requests', 'offer_text', 'TEXT')
    _add_column(cur, 'orders', 'offer_text', 'TEXT')

    conn.commit()
    conn.close()
