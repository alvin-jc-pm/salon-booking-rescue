from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Booking, Service, Slot
from app.security import require_admin

app = FastAPI(title="Salon Booking API")

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9 ()-]{6,20}$")]


class StrictModel(BaseModel):
    # Unknown fields are an error, not silently dropped.
    model_config = ConfigDict(extra="forbid")


class ServiceIn(StrictModel):
    name: Name
    price: Decimal = Field(gt=0, max_digits=8, decimal_places=2, description="For example 25.00")
    duration: int = Field(ge=5, le=480, description="Minutes")


class SlotIn(StrictModel):
    start_time: AwareDatetime = Field(description="ISO 8601 with a UTC offset, for example 2026-11-08T10:00:00+00:00")

    @field_validator("start_time")
    @classmethod
    def in_the_future(cls, value):
        if value <= datetime.now(timezone.utc):
            raise ValueError("must be in the future")
        return value


class BookingIn(StrictModel):
    customer_name: Name
    phone: Phone
    service_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)


def utc(value):
    # SQLite gives back times without a zone. Everything is stored as UTC.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def service_out(s):
    return {
        "id": s.id,
        "name": s.name,
        "price": f"{Decimal(s.price_cents) / 100:.2f}",
        "price_cents": s.price_cents,
        "duration": s.duration,
    }


def slot_out(s):
    return {"id": s.id, "start_time": utc(s.start_time).isoformat(), "available": s.available}


def booking_out(b):
    return {
        "id": b.id,
        "customer_name": b.customer_name,
        "phone": b.phone,
        "service_id": b.service_id,
        "slot_id": b.slot_id,
    }


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
    return [service_out(s) for s in db.scalars(select(Service).order_by(Service.id))]


@app.post("/services", status_code=201, dependencies=[Depends(require_admin)])
def add_service(service: ServiceIn, db: Session = Depends(get_session)):
    row = Service(name=service.name, price_cents=int(service.price * 100), duration=service.duration)
    db.add(row)
    db.commit()
    return service_out(row)


@app.get("/slots")
def list_slots(db: Session = Depends(get_session)):
    rows = db.scalars(select(Slot).where(Slot.available.is_(True)).order_by(Slot.start_time, Slot.id))
    return [slot_out(s) for s in rows]


@app.post("/slots", status_code=201, dependencies=[Depends(require_admin)])
def add_slot(slot: SlotIn, db: Session = Depends(get_session)):
    row = Slot(start_time=slot.start_time.astimezone(timezone.utc))
    db.add(row)
    db.commit()
    return slot_out(row)


@app.post("/bookings", status_code=201)
def create_booking(booking: BookingIn, db: Session = Depends(get_session)):
    if db.get(Service, booking.service_id) is None:
        raise HTTPException(status_code=404, detail="Service not found")
    slot = db.get(Slot, booking.slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    row = Booking(**booking.model_dump())
    db.add(row)
    slot.available = False
    db.commit()
    return booking_out(row)


@app.get("/admin/bookings", dependencies=[Depends(require_admin)])
def admin_bookings(db: Session = Depends(get_session)):
    return [booking_out(b) for b in db.scalars(select(Booking).order_by(Booking.id))]


@app.delete("/admin/bookings/{booking_id}", dependencies=[Depends(require_admin)])
def admin_delete_booking(booking_id: int, db: Session = Depends(get_session)):
    row = db.get(Booking, booking_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted"}
