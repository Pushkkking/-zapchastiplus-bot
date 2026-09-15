from datetime import datetime
from .db import db

def _now(): return datetime.now().strftime('%d.%m.%Y %H:%M:%S')

def validate_promo(code, user_id, order_amount):
    code=str(code or '').strip().upper()
    if not code: return None, 'Введите промокод.'
    conn=db(); cur=conn.cursor(); cur.execute('SELECT id,code,kind,value,max_uses,used_count,active,expires_at FROM promo_codes WHERE code=?',(code,)); row=cur.fetchone()
    if not row: conn.close(); return None, '❌ Промокод не найден.'
    pid,code,kind,value,max_uses,used_count,active,expires=row
    if not active: conn.close(); return None, '❌ Этот промокод больше не действует.'
    if expires:
        try:
            if datetime.strptime(expires,'%Y-%m-%d %H:%M:%S') < datetime.now(): conn.close(); return None, '❌ Срок действия промокода истёк.'
        except ValueError: pass
    if max_uses is not None and used_count >= max_uses: conn.close(); return None, '❌ Лимит использований промокода исчерпан.'
    cur.execute('SELECT 1 FROM promo_redemptions WHERE promo_id=? AND telegram_id=?',(pid,user_id,));
    if cur.fetchone(): conn.close(); return None, '❌ Вы уже использовали этот промокод.'
    amount=float(order_amount or 0)
    discount=amount*float(value)/100 if kind=='percent' else float(value)
    discount=max(0.0,min(discount,amount))
    conn.close(); return {'id':pid,'code':code,'kind':kind,'value':float(value),'discount':round(discount,2)}, None

def list_promos():
    conn=db(); cur=conn.cursor(); cur.execute('SELECT code,kind,value,max_uses,used_count,active,expires_at FROM promo_codes ORDER BY id DESC'); rows=cur.fetchall(); conn.close(); return rows

def create_promo(code, kind, value, max_uses=None, expires_at=None):
    conn=db(); cur=conn.cursor();
    try:
        cur.execute('INSERT INTO promo_codes(code,kind,value,max_uses,expires_at) VALUES(?,?,?,?,?)',(str(code).strip().upper(),kind,float(value),max_uses,expires_at)); conn.commit(); ok=True
    except Exception: ok=False
    conn.close(); return ok

def redeem_promo(promo_id,user_id,order_id,discount):
    conn=db(); cur=conn.cursor();
    cur.execute('SELECT used_count,max_uses,active FROM promo_codes WHERE id=?',(promo_id,)); row=cur.fetchone()
    if not row or not row[2] or (row[1] is not None and row[0]>=row[1]): conn.close(); return False
    try:
        cur.execute('INSERT INTO promo_redemptions(promo_id,telegram_id,order_id,discount,created_at) VALUES(?,?,?,?,?)',(promo_id,user_id,order_id,float(discount),_now()))
        cur.execute('UPDATE promo_codes SET used_count=used_count+1 WHERE id=?',(promo_id,)); conn.commit(); ok=True
    except Exception: conn.rollback(); ok=False
    conn.close(); return ok


def release_promo(code, user_id, order_id):
    conn=db(); cur=conn.cursor()
    cur.execute('SELECT id FROM promo_codes WHERE code=?',(str(code).upper(),)); row=cur.fetchone()
    if not row:
        conn.close(); return False
    cur.execute('SELECT 1 FROM promo_redemptions WHERE promo_id=? AND telegram_id=? AND order_id=?',(row[0],user_id,order_id))
    if not cur.fetchone():
        conn.close(); return False
    cur.execute('DELETE FROM promo_redemptions WHERE promo_id=? AND telegram_id=? AND order_id=?',(row[0],user_id,order_id))
    cur.execute('UPDATE promo_codes SET used_count=CASE WHEN used_count>0 THEN used_count-1 ELSE 0 END WHERE id=?',(row[0],))
    conn.commit(); conn.close(); return True
