from datetime import datetime
from .db import db
from .loyalty import parse_amount, calculate_cashback
from .cashback import add_transaction, get_balance, get_order_spent, has_transaction


def _now():
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')


def create_order(request_id, telegram_id, cashback_used=0, promo=None):
    now = _now()
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT id FROM orders WHERE request_id=? AND status!=?', (request_id, '❌ Отменён'))
    existing = cur.fetchone()
    if existing:
        conn.close(); return existing[0], False

    cur.execute('SELECT offer_text FROM requests WHERE id=? AND telegram_id=?', (request_id, telegram_id))
    offer_row = cur.fetchone()
    offer_text = offer_row[0] if offer_row else None
    offer_amount = parse_amount(offer_text)
    promo_discount = float((promo or {}).get('discount', 0) or 0)
    promo_discount = round(max(0.0, min(promo_discount, offer_amount)), 2)
    cashback_base = max(0.0, offer_amount - promo_discount)
    cashback_used = round(max(0.0, min(float(cashback_used or 0), cashback_base * 0.5)), 2)

    # Списываем кешбэк только в момент подтверждения заказа.
    balance = get_balance(telegram_id)
    cashback_used = min(cashback_used, balance)

    cur.execute('''INSERT INTO orders
        (request_id,telegram_id,status,created_at,updated_at,offer_text)
        VALUES(?,?,?,?,?,?)''',
        (request_id, telegram_id, '🆕 Новый', now, now, offer_text))
    order_id = cur.lastrowid

    if promo and promo_discount > 0:
        from database.promos import redeem_promo
        redeem_promo(promo.get('id'), telegram_id, order_id, promo_discount)
    if cashback_used > 0:
        cur.execute('''INSERT INTO cashback_transactions
            (telegram_id, order_id, amount, kind, note, created_at)
            VALUES (?, ?, ?, 'spent', ?, ?)''',
            (telegram_id, order_id, -cashback_used, 'Списание при оформлении заказа', now))

    conn.commit(); conn.close()
    return order_id, True


def get_order(order_id):
    conn = db(); cur = conn.cursor()
    cur.execute('''SELECT
        o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
        r.make,r.model,r.year,r.vin,r.plate,r.request_text,r.phone
        FROM orders o JOIN requests r ON r.id=o.request_id WHERE o.id=?''', (order_id,))
    row = cur.fetchone(); conn.close(); return row


def get_order_by_request(request_id, user_id=None):
    conn = db(); cur = conn.cursor()
    base = '''SELECT o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
        r.make,r.model,r.year,r.vin,r.plate,r.request_text,r.phone
        FROM orders o JOIN requests r ON r.id=o.request_id WHERE o.request_id=?'''
    if user_id is None:
        cur.execute(base + ' ORDER BY o.id DESC LIMIT 1', (request_id,))
    else:
        cur.execute(base + ' AND o.telegram_id=? ORDER BY o.id DESC LIMIT 1', (request_id, user_id))
    row = cur.fetchone(); conn.close(); return row


def get_user_orders(user_id):
    conn = db(); cur = conn.cursor()
    cur.execute('''SELECT o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
        r.make,r.model,r.year,r.vin,r.plate,r.request_text,r.phone
        FROM orders o JOIN requests r ON r.id=o.request_id WHERE o.telegram_id=? ORDER BY o.id DESC''', (user_id,))
    rows = cur.fetchall(); conn.close(); return rows


def get_all_orders(status=None):
    conn = db(); cur = conn.cursor()
    base = '''SELECT o.id,o.request_id,o.telegram_id,o.status,o.created_at,o.updated_at,o.offer_text,
        r.make,r.model,r.year,r.request_text,r.phone FROM orders o JOIN requests r ON r.id=o.request_id '''
    if status:
        cur.execute(base + 'WHERE o.status=? ORDER BY o.id DESC', (status,))
    else:
        cur.execute(base + 'ORDER BY o.id DESC')
    rows = cur.fetchall(); conn.close(); return rows


def _completed_paid_total(cur, user_id, exclude_order_id=None):
    sql = "SELECT id, offer_text FROM orders WHERE telegram_id=? AND status='🚗 Выдан'"
    args = [user_id]
    if exclude_order_id is not None:
        sql += ' AND id!=?'; args.append(exclude_order_id)
    cur.execute(sql + ' ORDER BY id', args)
    total = 0.0
    for oid, offer_text in cur.fetchall():
        total += max(0.0, parse_amount(offer_text) - get_order_spent(oid))
    return total


def update_order_status(order_id, status):
    now = _now()
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT telegram_id, offer_text, status FROM orders WHERE id=?', (order_id,))
    row = cur.fetchone()
    if not row:
        conn.close(); return
    user_id, offer_text, old_status = row

    cashback_amount = 0.0
    if status == '🚗 Выдан' and old_status != '🚗 Выдан':
        gross = parse_amount(offer_text)
        spent = get_order_spent(order_id)
        cur.execute('SELECT promo_discount FROM orders WHERE id=?', (order_id,))
        promo_discount = float(cur.fetchone()[0] or 0)
        paid = max(0.0, gross - promo_discount - spent)
        previous_paid = _completed_paid_total(cur, user_id, order_id)
        cashback_amount = calculate_cashback(previous_paid + paid, paid)
        if cashback_amount > 0 and not has_transaction(order_id, 'earned'):
            cur.execute('''INSERT INTO cashback_transactions
                (telegram_id, order_id, amount, kind, note, created_at)
                VALUES (?, ?, ?, 'earned', ?, ?)''',
                (user_id, order_id, cashback_amount,
                 f'Начисление за покупку на {paid:,.2f} ₽'.replace(',', ' '), now))
    elif status == '❌ Отменён':
        # Если заказ отменён, возвращаем использованный кешбэк и освобождаем промокод.
        cur.execute('SELECT promo_code, promo_discount FROM orders WHERE id=?', (order_id,))
        promo_row = cur.fetchone()
        if promo_row and promo_row[0]:
            from database.promos import release_promo
            release_promo(promo_row[0], user_id, order_id)
        # Если при оформлении использовали кешбэк, возвращаем его один раз.
        spent = get_order_spent(order_id)
        if spent > 0 and not has_transaction(order_id, 'refunded'):
            cur.execute('''INSERT INTO cashback_transactions
                (telegram_id, order_id, amount, kind, note, created_at)
                VALUES (?, ?, ?, 'refunded', ?, ?)''',
                (user_id, order_id, spent, 'Возврат кешбэка за отменённый заказ', now))
    
    cur.execute('UPDATE orders SET status=?,updated_at=?,cashback_amount=? WHERE id=?',
                (status, now, cashback_amount, order_id))
    if status == '🚗 Выдан':
        try:
            from database.referrals import reward_referral_if_needed
            reward_referral_if_needed(user_id, order_id)
        except Exception:
            pass

    if status in ('🚗 Выдан', '❌ Отменён'):
        cur.execute("UPDATE requests SET status='🗄 Архив',updated_at=? WHERE id=(SELECT request_id FROM orders WHERE id=?)", (now, order_id))

    conn.commit(); conn.close()


def get_order_stats():
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM orders'); total=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='🆕 Новый'"); new=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='🔧 В работе'"); work=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='📦 Готов к выдаче'"); ready=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='🚗 Выдан'"); done=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='❌ Отменён'"); cancelled=cur.fetchone()[0]
    conn.close(); return total,new,work,ready,done,cancelled


def cancel_order(order_id, user_id):
    now = _now()
    conn = db(); cur = conn.cursor()
    cur.execute('SELECT status FROM orders WHERE id=? AND telegram_id=?', (order_id, user_id))
    row=cur.fetchone()
    if not row:
        conn.close(); return False,'not_found'
    status=row[0]
    if status=='❌ Отменён': conn.close(); return False,'already_cancelled'
    if status=='🚗 Выдан': conn.close(); return False,'already_issued'

    spent = get_order_spent(order_id)
    cur.execute('UPDATE orders SET status=?,updated_at=? WHERE id=? AND telegram_id=?', ('❌ Отменён',now,order_id,user_id))
    cur.execute("UPDATE requests SET status='🗄 Архив',updated_at=? WHERE id=(SELECT request_id FROM orders WHERE id=?)", (now,order_id))
    if spent > 0 and not has_transaction(order_id, 'refunded'):
        cur.execute('''INSERT INTO cashback_transactions
            (telegram_id, order_id, amount, kind, note, created_at)
            VALUES (?, ?, ?, 'refunded', ?, ?)''',
            (user_id, order_id, spent, 'Возврат кешбэка за отменённый заказ', now))
    conn.commit(); conn.close(); return True,'cancelled'
