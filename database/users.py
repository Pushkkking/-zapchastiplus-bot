import secrets
from datetime import datetime
from .db import db


def _new_card_token():
    return secrets.token_urlsafe(9)


def _new_card_number(cur):
    """Stable customer card number for future 1C/cash-desk integration."""
    while True:
        number = f"ZP-{secrets.randbelow(100_000_000):08d}"
        cur.execute('SELECT 1 FROM users WHERE card_number=? LIMIT 1', (number,))
        if not cur.fetchone():
            return number


def save_user(user):
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT telegram_id, card_token, card_number FROM users WHERE telegram_id = ?', (user.id,))
    row = cur.fetchone()
    if row:
        cur.execute('''UPDATE users SET telegram_name=?, username=? WHERE telegram_id=?''',
                    (user.full_name, user.username, user.id))
        if not row[1] or not row[2]:
            token = row[1] or _new_card_token()
            number = row[2] or _new_card_number(cur)
            cur.execute('UPDATE users SET card_token=?, card_number=? WHERE telegram_id=?', (token, number, user.id))
    else:
        token = _new_card_token()
        cur.execute('''INSERT INTO users
            (telegram_id, telegram_name, username, name, phone, consent_given, consent_at, card_token, card_number)
            VALUES (?, ?, ?, ?, ?, 0, NULL, ?, ?)''',
                    (user.id, user.full_name, user.username, None, None, token, _new_card_number(cur)))
    conn.commit(); conn.close()


def get_name(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT name FROM users WHERE telegram_id=?',(user_id,)); row=cur.fetchone(); conn.close()
    return row[0] if row and row[0] else None


def save_name(user_id, name):
    conn=db(); conn.execute('UPDATE users SET name=? WHERE telegram_id=?',(name,user_id)); conn.commit(); conn.close()


def get_phone(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT phone FROM users WHERE telegram_id=?',(user_id,)); row=cur.fetchone(); conn.close()
    return row[0] if row and row[0] else None


def save_phone(user_id, phone):
    conn=db(); conn.execute('UPDATE users SET phone=? WHERE telegram_id=?',(phone,user_id)); conn.commit(); conn.close()


def get_username(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT username FROM users WHERE telegram_id=?',(user_id,)); row=cur.fetchone(); conn.close()
    return row[0] if row and row[0] else None


def get_card_number(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT card_number FROM users WHERE telegram_id=?',(user_id,)); row=cur.fetchone(); conn.close()
    return row[0] if row and row[0] else None


def get_card_token(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT card_token FROM users WHERE telegram_id=?',(user_id,)); row=cur.fetchone(); conn.close()
    return row[0] if row and row[0] else None


def get_user_by_card_token(token):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT telegram_id,name,phone,username,card_number FROM users WHERE card_token=?',(token,)); row=cur.fetchone(); conn.close()
    return row


def has_consent(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('SELECT consent_given FROM users WHERE telegram_id=?',(user_id,)); row=cur.fetchone(); conn.close()
    return bool(row and row[0])


def save_consent(user_id):
    conn=db(); conn.execute('UPDATE users SET consent_given=1, consent_at=? WHERE telegram_id=?',
                            (datetime.now().isoformat(timespec='seconds'), user_id)); conn.commit(); conn.close()


def get_all_users(limit=100):
    conn=db(); cur=conn.cursor()
    cur.execute('''SELECT telegram_id,name,phone,username,consent_given FROM users ORDER BY telegram_id DESC LIMIT ?''', (limit,))
    rows=cur.fetchall(); conn.close(); return rows


def get_user_summary(user_id):
    conn=db(); cur=conn.cursor()
    cur.execute('SELECT telegram_id,name,phone,username,consent_given FROM users WHERE telegram_id=?', (user_id,)); user=cur.fetchone()
    cur.execute('SELECT COUNT(*) FROM cars WHERE telegram_id=?', (user_id,)); cars=cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM requests WHERE telegram_id=?', (user_id,)); requests=cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM orders WHERE telegram_id=?', (user_id,)); orders=cur.fetchone()[0]
    conn.close(); return user,cars,requests,orders
