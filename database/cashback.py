from datetime import datetime
from .db import db


def _now():
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')


def get_balance(user_id):
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT COALESCE(SUM(amount), 0) FROM cashback_transactions WHERE telegram_id=?', (user_id,))
    value = float(cur.fetchone()[0] or 0)
    conn.close()
    return round(max(0.0, value), 2)


def add_transaction(user_id, amount, kind, order_id=None, note=None):
    if not amount:
        return
    conn = db(); cur = conn.cursor()
    cur.execute('''INSERT INTO cashback_transactions
        (telegram_id, order_id, amount, kind, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, order_id, round(float(amount), 2), kind, note, _now()))
    conn.commit(); conn.close()


def get_order_spent(order_id):
    conn = db(); cur = conn.cursor()
    cur.execute('''SELECT COALESCE(SUM(-amount), 0) FROM cashback_transactions
                   WHERE order_id=? AND kind='spent' ''', (order_id,))
    value = float(cur.fetchone()[0] or 0)
    conn.close()
    return round(max(0.0, value), 2)


def has_transaction(order_id, kind):
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT 1 FROM cashback_transactions WHERE order_id=? AND kind=? LIMIT 1', (order_id, kind))
    found = cur.fetchone() is not None
    conn.close()
    return found


def get_transactions(user_id, limit=20):
    conn = db(); cur = conn.cursor()
    cur.execute('''SELECT amount, kind, order_id, note, created_at
                   FROM cashback_transactions
                   WHERE telegram_id=?
                   ORDER BY id DESC LIMIT ?''', (user_id, limit))
    rows = cur.fetchall(); conn.close(); return rows


def get_order_earned(order_id):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM cashback_transactions WHERE order_id=? AND kind='earned'", (order_id,))
    value = float(cur.fetchone()[0] or 0)
    conn.close()
    return round(max(0.0, value), 2)
