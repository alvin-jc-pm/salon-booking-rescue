import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="Salon Booking API")

DB = "salon.db"
ADMIN_KEY = "admin123"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY, name TEXT, price REAL, duration INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY, start_time TEXT, available INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, customer_name TEXT, phone TEXT, service_id INTEGER, slot_id INTEGER)")
    conn.commit()
    conn.close()


init_db()


class Service(BaseModel):
    name: str
    price: float
    duration: int


class Slot(BaseModel):
    start_time: str


class Booking(BaseModel):
    customer_name: str
    phone: str
    service_id: int
    slot_id: int


@app.get("/")
def home():
    return {"message": "Welcome to the Salon Booking API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/services")
def list_services():
    conn = get_db()
    rows = conn.execute("SELECT * FROM services").fetchall()
    return [dict(r) for r in rows]


@app.post("/services")
def add_service(service: Service):
    conn = get_db()
    conn.execute(f"INSERT INTO services (name, price, duration) VALUES ('{service.name}', {service.price}, {service.duration})")
    conn.commit()
    return {"status": "service added"}


@app.get("/slots")
def list_slots():
    conn = get_db()
    rows = conn.execute("SELECT * FROM slots WHERE available = 1").fetchall()
    return [dict(r) for r in rows]


@app.post("/slots")
def add_slot(slot: Slot):
    conn = get_db()
    conn.execute(f"INSERT INTO slots (start_time) VALUES ('{slot.start_time}')")
    conn.commit()
    return {"status": "slot added"}


@app.post("/bookings")
def create_booking(booking: Booking):
    conn = get_db()
    slot = conn.execute(f"SELECT * FROM slots WHERE id = {booking.slot_id}").fetchone()
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    conn.execute(
        f"INSERT INTO bookings (customer_name, phone, service_id, slot_id) VALUES ('{booking.customer_name}', '{booking.phone}', {booking.service_id}, {booking.slot_id})"
    )
    conn.execute(f"UPDATE slots SET available = 0 WHERE id = {booking.slot_id}")
    conn.commit()
    return {"status": "booked"}


@app.get("/admin/bookings")
def admin_bookings(key: str):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_db()
    rows = conn.execute("SELECT * FROM bookings").fetchall()
    return [dict(r) for r in rows]


@app.delete("/admin/bookings/{booking_id}")
def admin_delete_booking(booking_id: int):
    conn = get_db()
    conn.execute(f"DELETE FROM bookings WHERE id = {booking_id}")
    conn.commit()
    return {"status": "deleted"}


def server_options(env=os.environ):
    """Where to listen. Hosts tell the app which port to use through PORT."""
    return env.get("HOST", "0.0.0.0"), int(env.get("PORT", "8000"))


if __name__ == "__main__":
    import uvicorn

    host, port = server_options()
    uvicorn.run(app, host=host, port=port)
