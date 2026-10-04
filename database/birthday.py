from datetime import date, datetime, timedelta
from .db import db
from .cashback import add_transaction

BIRTHDAY_BONUS = 1000.0
BIRTHDAY_BONUS_DAYS = 14


def get_birthday(user_id):
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT birthday FROM users WHERE telegram_id=?', (user_id,))
    row = cur.fetchone(); conn.close()
    return row[0] if row and row[0] else None


def save_birthday(user_id, value):
    conn = db()
    conn.execute('UPDATE users SET birthday=? WHERE telegram_id=?', (value, user_id))
    conn.commit(); conn.close()


def _next_birthday_date(birthday_iso, today=None):
    today = today or date.today()
    try:
        month, day = int(birthday_iso[5:7]), int(birthday_iso[8:10])
    except Exception:
        return None
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= today:
            return candidate
    return None


def birthday_info(birthday_iso):
    if not birthday_iso:
        return None
    try:
        return datetime.strptime(birthday_iso, '%Y-%m-%d').date()
    except ValueError:
        return None


def users_with_birthday_today(today=None):
    today = today or date.today()
    conn = db(); cur = conn.cursor()
    cur.execute('''SELECT telegram_id, name, birthday, birthday_bonus_year
                   FROM users
                   WHERE birthday IS NOT NULL AND birthday!='' ''')
    rows = cur.fetchall(); conn.close()
    result = []
    for user_id, name, birthday, bonus_year in rows:
        try:
            b = birthday_info(birthday)
            if b and b.month == today.month and b.day == today.day and bonus_year != today.year:
                result.append((user_id, name, birthday))
        except Exception:
            pass
    return result


def award_birthday_bonus(user_id, year):
    now = datetime.now()
    expires = now + timedelta(days=BIRTHDAY_BONUS_DAYS)
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT birthday_bonus_year FROM users WHERE telegram_id=?', (user_id,))
    row = cur.fetchone()
    if not row or row[0] == year:
        conn.close(); return False, None
    cur.execute('''INSERT INTO cashback_transactions
        (telegram_id, order_id, amount, kind, note, created_at, expires_at)
        VALUES (?, NULL, ?, 'birthday', ?, ?, ?)''',
        (user_id, BIRTHDAY_BONUS,
         f'🎂 Подарок ко дню рождения — {BIRTHDAY_BONUS:.0f} ₽',
         now.strftime('%d.%m.%Y %H:%M:%S'), expires.isoformat(timespec='seconds')))
    cur.execute('UPDATE users SET birthday_bonus_year=? WHERE telegram_id=?', (year, user_id))
    conn.commit(); conn.close()
    return True, expires
