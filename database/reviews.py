from datetime import datetime
from .db import db


def save_review(user_id, order_id, rating):
    rating = int(rating)
    if rating < 1 or rating > 5:
        return False
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO reviews (telegram_id, order_id, rating, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, order_id, rating, datetime.now().strftime('%d.%m.%Y %H:%M:%S')))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_review(order_id):
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT rating, created_at FROM reviews WHERE order_id=?', (order_id,))
    row = cur.fetchone(); conn.close(); return row


def get_review_stats():
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*), COALESCE(AVG(rating), 0) FROM reviews')
    count, avg = cur.fetchone(); conn.close()
    return int(count or 0), round(float(avg or 0), 2)
