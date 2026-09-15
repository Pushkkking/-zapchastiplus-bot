import os
import shutil
import sqlite3

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
        updated_at TEXT NOT NULL,
        offer_text TEXT
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
    _add_column(cur, 'requests', 'updated_at', "TEXT NOT NULL DEFAULT ''")
    _add_column(cur, 'requests', 'offer_text', 'TEXT')
    _add_column(cur, 'orders', 'offer_text', 'TEXT')
    _add_column(cur, 'messages', 'message_type', "TEXT NOT NULL DEFAULT 'text'")
    _add_column(cur, 'messages', 'file_id', 'TEXT')

    conn.commit()
    conn.close()
