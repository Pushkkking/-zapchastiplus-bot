from datetime import datetime
from .db import db


def create_request(telegram_id, car_id, make, model, year, vin, plate, request_text, phone):
    now=datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    conn=db(); cur=conn.cursor()
    cur.execute('''INSERT INTO requests
        (telegram_id,car_id,make,model,year,vin,plate,request_text,phone,status,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
        (telegram_id,car_id,make,model,year,vin,plate,request_text,phone,'🆕 Новая',now,now))
    rid=cur.lastrowid; conn.commit(); conn.close(); return rid


def get_requests(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('''SELECT id,make,model,year,request_text,status,created_at FROM requests WHERE telegram_id=? ORDER BY id DESC''',(user_id,)); rows=cur.fetchall(); conn.close(); return rows


def get_request(request_id, user_id=None):
    conn=db(); cur=conn.cursor()
    if user_id is None:
        cur.execute('''SELECT id,telegram_id,make,model,year,vin,plate,request_text,phone,status,created_at,updated_at FROM requests WHERE id=?''',(request_id,))
    else:
        cur.execute('''SELECT id,telegram_id,make,model,year,vin,plate,request_text,phone,status,created_at,updated_at FROM requests WHERE id=? AND telegram_id=?''',(request_id,user_id))
    row=cur.fetchone(); conn.close(); return row


def get_all_requests(status=None):
    # Заявки, по которым заказ уже выдан или отменён, считаем архивными.
    # Они остаются в базе и истории клиента, но не отображаются в админском
    # разделе «Все заявки».
    conn=db(); cur=conn.cursor()
    base='''SELECT r.id,r.telegram_id,r.make,r.model,r.year,r.request_text,r.status,r.created_at
            FROM requests r
            WHERE NOT EXISTS (
                SELECT 1 FROM orders o
                WHERE o.request_id=r.id
                  AND o.status IN ('🚗 Выдан','❌ Отменён')
            )'''
    if status:
        cur.execute(base + ' AND r.status=? ORDER BY r.id DESC',(status,))
    else:
        cur.execute(base + ' ORDER BY r.id DESC')
    rows=cur.fetchall(); conn.close(); return rows


def update_status(request_id,status):
    now=datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    conn=db(); cur=conn.cursor(); cur.execute('UPDATE requests SET status=?,updated_at=? WHERE id=?',(status,now,request_id)); conn.commit(); conn.close()


def get_stats():
    conn=db(); cur=conn.cursor()
    cur.execute('SELECT COUNT(*) FROM requests'); total=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM requests WHERE status='🆕 Новая'"); new=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM requests WHERE status='🔎 Подбираем'"); selecting=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM requests WHERE status='💰 Предложение готово'"); offer=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM requests WHERE status='✅ Выполнена'"); done=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM requests WHERE status='❌ Отменена'"); cancelled=cur.fetchone()[0]
    conn.close(); return total,new,selecting,offer,done,cancelled


def set_offer(request_id, offer_text):
    now=datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    conn=db(); cur=conn.cursor()
    cur.execute('UPDATE requests SET offer_text=?,status=?,updated_at=? WHERE id=?',
                (offer_text, '💰 Предложение готово', now, request_id))
    conn.commit(); conn.close()


def get_offer(request_id):
    conn=db(); cur=conn.cursor()
    cur.execute('SELECT offer_text FROM requests WHERE id=?', (request_id,))
    row=cur.fetchone(); conn.close()
    return row[0] if row else None
