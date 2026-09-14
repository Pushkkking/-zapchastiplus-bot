from .db import db


def get_cars(user_id):
    conn=db(); cur=conn.cursor(); cur.execute('''SELECT id,make,model,year,vin,plate FROM cars WHERE telegram_id=? ORDER BY id DESC''',(user_id,)); rows=cur.fetchall(); conn.close(); return rows


def save_car(user_id, make, model, year, vin, plate):
    conn=db(); conn.execute('''INSERT INTO cars(telegram_id,make,model,year,vin,plate) VALUES(?,?,?,?,?,?)''',(user_id,make,model,year,vin,plate)); conn.commit(); conn.close()


def delete_car(car_id,user_id):
    conn=db(); conn.execute('DELETE FROM cars WHERE id=? AND telegram_id=?',(car_id,user_id)); conn.commit(); conn.close()
