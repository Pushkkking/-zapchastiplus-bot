from datetime import datetime
from .db import db


def _now():
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')


def create_order(request_id, telegram_id):
    now = _now()
    conn = db()
    cur = conn.cursor()
    cur.execute(
        'SELECT id FROM orders WHERE request_id=? AND status!=?',
        (request_id, '❌ Отменён'),
    )
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing[0], False

    cur.execute('SELECT offer_text FROM requests WHERE id=?', (request_id,))
    offer_row = cur.fetchone()
    offer_text = offer_row[0] if offer_row else None

    cur.execute(
        '''INSERT INTO orders
        (request_id,telegram_id,status,created_at,updated_at,offer_text)
        VALUES(?,?,?,?,?,?)''',
        (request_id, telegram_id, '🆕 Новый', now, now, offer_text),
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id, True


def get_order(order_id):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        '''SELECT
            o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
            r.make,r.model,r.year,r.vin,r.plate,r.request_text,r.phone
        FROM orders o
        JOIN requests r ON r.id=o.request_id
        WHERE o.id=?''',
        (order_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_order_by_request(request_id, user_id=None):
    conn = db()
    cur = conn.cursor()
    base = '''SELECT
        o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
        r.make,r.model,r.year,r.vin,r.plate,r.request_text,r.phone
    FROM orders o
    JOIN requests r ON r.id=o.request_id
    WHERE o.request_id=?'''
    if user_id is None:
        cur.execute(base + ' ORDER BY o.id DESC LIMIT 1', (request_id,))
    else:
        cur.execute(
            base + ' AND o.telegram_id=? ORDER BY o.id DESC LIMIT 1',
            (request_id, user_id),
        )
    row = cur.fetchone()
    conn.close()
    return row


def get_user_orders(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        '''SELECT
            o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
            r.make,r.model,r.year,r.vin,r.plate,r.request_text,r.phone
        FROM orders o
        JOIN requests r ON r.id=o.request_id
        WHERE o.telegram_id=?
        ORDER BY o.id DESC''',
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def update_order_status(order_id, status):
    now = _now()
    conn = db()
    conn.execute(
        'UPDATE orders SET status=?,updated_at=? WHERE id=?',
        (status, now, order_id),
    )
    conn.commit()
    conn.close()


def get_order_stats():
    conn = db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM orders')
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='🆕 Новый'")
    new = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='🔧 В работе'")
    work = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='📦 Готов к выдаче'")
    ready = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='🚗 Выдан'")
    done = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='❌ Отменён'")
    cancelled = cur.fetchone()[0]
    conn.close()
    return total, new, work, ready, done, cancelled
