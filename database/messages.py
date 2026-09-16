from datetime import datetime
from .db import db


def _now():
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')


def create_message(telegram_id, sender, text, request_id=None, order_id=None, message_type='text', file_id=None):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        '''INSERT INTO messages
        (telegram_id,sender,text,message_type,file_id,request_id,order_id,created_at)
        VALUES(?,?,?,?,?,?,?,?)''',
        (telegram_id, sender, text, message_type, file_id, request_id, order_id, _now()),
    )
    message_id = cur.lastrowid
    conn.commit()
    conn.close()
    return message_id


def get_user_messages(telegram_id, limit=100):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        '''SELECT id,sender,text,message_type,file_id,request_id,order_id,created_at
        FROM messages
        WHERE telegram_id=?
        ORDER BY id DESC LIMIT ?''',
        (telegram_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))


def get_message_threads(limit=50):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        '''SELECT m.telegram_id, m.text, m.sender, m.created_at, m.request_id, m.order_id
        FROM messages m
        INNER JOIN (
            SELECT telegram_id, MAX(id) AS max_id
            FROM messages
            GROUP BY telegram_id
        ) x ON x.telegram_id=m.telegram_id AND x.max_id=m.id
        ORDER BY m.id DESC LIMIT ?''',
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
