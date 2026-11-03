"""BEFORE.md rows 9 and 10, and float prices: nothing checked what was sent."""
from datetime import datetime, timedelta, timezone

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models import Booking, Service
from tests.helpers import admin_headers, alembic_config, book, create_service, create_slot, sqlite_url

client = TestClient(app)


# Row 9: a booking for a service that does not exist was accepted.

def test_booking_an_unknown_service_is_refused():
    slot = create_slot(client)
    response = book(client, 999999, slot["id"])
    assert response.status_code == 404
    assert response.json()["detail"] == "Service not found"


def test_booking_an_unknown_slot_is_refused():
    service = create_service(client)
    assert book(client, service["id"], 999999).status_code == 404


def test_database_itself_rejects_orphan_bookings():
    # Even code that skips the API checks cannot save an orphan row.
    with Session(engine) as db:
        db.add(Booking(customer_name="Orphan", phone="0800 000 009", service_id=999999, slot_id=999999))
        with pytest.raises(IntegrityError):
            db.commit()


def test_deleting_an_unknown_booking_says_so():
    assert client.delete("/admin/bookings/999999", headers=admin_headers()).status_code == 404


# Row 10: a slot at "whenever" was accepted.

@pytest.mark.parametrize("start_time", [
    "whenever",
    "",
    "2026-13-40T10:00:00+00:00",
    "2030-11-08T10:00",  # no UTC offset, so the time is ambiguous
])
def test_slot_time_must_be_a_real_time_with_an_offset(start_time):
    response = client.post("/slots", json={"start_time": start_time}, headers=admin_headers())
    assert response.status_code == 422


def test_slot_in_the_past_is_refused():
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert client.post("/slots", json={"start_time": past}, headers=admin_headers()).status_code == 422


def test_slot_times_are_stored_in_utc_and_sorted():
    later = create_slot(client, "2031-01-02T12:00:00+02:00")
    earlier = create_slot(client, "2031-01-02T09:00:00+00:00")
    assert later["start_time"] == "2031-01-02T10:00:00+00:00"
    ids = [s["id"] for s in client.get("/slots").json()]
    assert ids.index(earlier["id"]) < ids.index(later["id"])


# Prices were floats.

def test_price_is_stored_as_exact_cents():
    service = create_service(client, name="Fringe", price="0.10")
    assert service["price_cents"] == 10
    assert service["price"] == "0.10"
    service = create_service(client, name="Colour", price="19.99")
    assert service["price_cents"] == 1999


@pytest.mark.parametrize("price", ["0", "-5", "12.345", "abc"])
def test_price_must_be_positive_with_at_most_two_decimals(price):
    response = client.post(
        "/services", json={"name": "Bad", "price": price, "duration": 30}, headers=admin_headers()
    )
    assert response.status_code == 422


def test_database_itself_rejects_a_zero_price():
    with Session(engine) as db:
        db.add(Service(name="Free", price_cents=0, duration=30))
        with pytest.raises(IntegrityError):
            db.commit()


# Other input that used to be accepted blindly.

@pytest.mark.parametrize("body", [
    {"name": "", "price": "10", "duration": 30},
    {"name": "x" * 101, "price": "10", "duration": 30},
    {"name": "Cut", "price": "10", "duration": 0},
    {"name": "Cut", "price": "10", "duration": 30, "price_cents": 1},
])
def test_bad_service_input_is_refused(body):
    assert client.post("/services", json=body, headers=admin_headers()).status_code == 422


@pytest.mark.parametrize("name, phone", [("", "0800 000 001"), ("Ada", "call me"), ("Ada", "12")])
def test_bad_booking_input_is_refused(name, phone):
    service = create_service(client)
    slot = create_slot(client)
    assert book(client, service["id"], slot["id"], customer_name=name, phone=phone).status_code == 422


# Data that was saved by the prototype is converted, not lost.

def test_migration_converts_prototype_data(tmp_path):
    url = sqlite_url(tmp_path, "legacy.db")
    command.upgrade(alembic_config(url), "0001")
    legacy = create_engine(url)
    with legacy.begin() as db:
        db.execute(text("INSERT INTO services (id, name, price, duration) VALUES (1, 'Cut', 19.99, 30)"))
        db.execute(text("INSERT INTO slots (id, start_time) VALUES (1, '2026-11-08 10:00:00')"))
        db.execute(text(
            "INSERT INTO bookings (customer_name, phone, service_id, slot_id) VALUES ('Ada', '0800', 1, 1)"
        ))
    command.upgrade(alembic_config(url), "0002")
    with legacy.connect() as db:
        assert db.execute(text("SELECT price_cents FROM services")).scalar() == 1999
        assert db.execute(text("SELECT count(*) FROM bookings")).scalar() == 1
    legacy.dispose()
