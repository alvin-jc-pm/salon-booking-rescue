from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Booking, Service, Slot

app = FastAPI(title="Salon Booking API")

ADMIN_KEY = "admin123"


class ServiceIn(BaseModel):
    name: str
    price: float
    duration: int


class SlotIn(BaseModel):
    start_time: str


class BookingIn(BaseModel):
    customer_name: str
    phone: str
    service_id: int
    slot_id: int


def as_dict(row):
    return {c.name: getattr(row, c.key) for c in row.__table__.columns}


@app.get("/")
def home():
    return {"message": "Welcome to the Salon Booking API"}


@app.get("/health")
def health(db: Session = Depends(get_session)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "database unavailable"})
    return {"status": "ok"}


@app.get("/services")
def list_services(db: Session = Depends(get_session)):
    return [as_dict(s) for s in db.scalars(select(Service).order_by(Service.id))]


@app.post("/services")
def add_service(service: ServiceIn, db: Session = Depends(get_session)):
    db.add(Service(name=service.name, price=service.price, duration=service.duration))
    db.commit()
    return {"status": "service added"}


@app.get("/slots")
def list_slots(db: Session = Depends(get_session)):
    rows = db.scalars(select(Slot).where(Slot.available.is_(True)).order_by(Slot.id))
    return [as_dict(s) for s in rows]


@app.post("/slots")
def add_slot(slot: SlotIn, db: Session = Depends(get_session)):
    db.add(Slot(start_time=slot.start_time))
    db.commit()
    return {"status": "slot added"}


@app.post("/bookings")
def create_booking(booking: BookingIn, db: Session = Depends(get_session)):
    slot = db.get(Slot, booking.slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.add(Booking(**booking.model_dump()))
    slot.available = False
    db.commit()
    return {"status": "booked"}


@app.get("/admin/bookings")
def admin_bookings(key: str, db: Session = Depends(get_session)):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return [as_dict(b) for b in db.scalars(select(Booking).order_by(Booking.id))]


@app.delete("/admin/bookings/{booking_id}")
def admin_delete_booking(booking_id: int, db: Session = Depends(get_session)):
    db.execute(delete(Booking).where(Booking.id == booking_id))
    db.commit()
    return {"status": "deleted"}
