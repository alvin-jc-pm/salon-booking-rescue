"""BEFORE.md row 8: the same slot could be booked twice."""
import threading

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models import Booking
from tests.helpers import admin_headers, alembic_config, book, create_service, create_slot, sqlite_url

client = TestClient(app)


@pytest.fixture
def service_id():
    return create_service(client)["id"]


def bookings_for(slot_id):
    return [b for b in client.get("/admin/bookings", headers=admin_headers()).json() if b["slot_id"] == slot_id]


def test_booking_a_taken_slot_is_refused(service_id):
    slot = create_slot(client)
    assert book(client, service_id, slot["id"], customer_name="Ada").status_code == 201
    second = book(client, service_id, slot["id"], customer_name="Ben")
    assert second.status_code == 409
    assert second.json()["detail"] == "Slot already booked"
    assert [b["customer_name"] for b in bookings_for(slot["id"])] == ["Ada"]


def test_database_itself_refuses_a_second_booking(service_id):
    # Code that skips the API cannot double book either.
    slot = create_slot(client)
    with Session(engine) as db:
        db.add(Booking(customer_name="Ada", phone="0800 000 001", service_id=service_id, slot_id=slot["id"]))
        db.commit()
        db.add(Booking(customer_name="Ben", phone="0800 000 002", service_id=service_id, slot_id=slot["id"]))
        with pytest.raises(IntegrityError):
            db.commit()


def test_only_one_of_many_simultaneous_requests_wins(service_id):
    slot = create_slot(client)
    start = threading.Barrier(8)
    codes = []

    def attempt(n):
        own_client = TestClient(app)
        start.wait()
        codes.append(book(own_client, service_id, slot["id"], customer_name=f"Racer {n}").status_code)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [201] + [409] * 7
    assert len(bookings_for(slot["id"])) == 1


def test_booked_slot_is_no_longer_listed(service_id):
    slot = create_slot(client)
    assert slot["id"] in [s["id"] for s in client.get("/slots").json()]
    book(client, service_id, slot["id"])
    assert slot["id"] not in [s["id"] for s in client.get("/slots").json()]


def test_cancelling_a_booking_frees_the_slot(service_id):
    slot = create_slot(client)
    booking = book(client, service_id, slot["id"]).json()
    client.delete(f"/admin/bookings/{booking['id']}", headers=admin_headers())
    assert slot["id"] in [s["id"] for s in client.get("/slots").json()]
    assert book(client, service_id, slot["id"], customer_name="Ben").status_code == 201


def test_migration_stops_if_double_bookings_already_exist(tmp_path):
    url = sqlite_url(tmp_path, "doubled.db")
    command.upgrade(alembic_config(url), "0002")
    old = create_engine(url)
    with old.begin() as db:
        db.execute(text("INSERT INTO services (id, name, price_cents, duration) VALUES (1, 'Cut', 2500, 30)"))
        db.execute(text("INSERT INTO slots (id, start_time) VALUES (1, '2030-01-01 10:00:00')"))
        db.execute(text(
            "INSERT INTO bookings (customer_name, phone, service_id, slot_id) "
            "VALUES ('Ada', '0800 000 001', 1, 1), ('Ben', '0800 000 002', 1, 1)"
        ))
    with pytest.raises(IntegrityError):
        command.upgrade(alembic_config(url), "0003")
    old.dispose()
