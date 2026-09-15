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
    conn=db(); cur=conn.cursor()
    if status:
        cur.execute('''SELECT id,telegram_id,make,model,year,request_text,status,created_at FROM requests WHERE status=? ORDER BY id DESC''',(status,))
    else:
        cur.execute('''SELECT id,telegram_id,make,model,year,request_text,status,created_at FROM requests ORDER BY id DESC''')
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
