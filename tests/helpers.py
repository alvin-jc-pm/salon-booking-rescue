import itertools
import os
from datetime import datetime, timedelta, timezone

from alembic.config import Config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def alembic_config(url=None):
    cfg = Config(os.path.join(ROOT, "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    if url:
        cfg.attributes["database_url"] = url
    return cfg


def sqlite_url(folder, name):
    return "sqlite:///" + os.path.join(str(folder), name).replace("\\", "/")


def admin_headers():
    return {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}


_minutes = itertools.count(1)


def future_time(days=7):
    """A distinct time in the future, with a UTC offset."""
    start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    return (start + timedelta(days=days, minutes=next(_minutes))).isoformat()


def create_service(client, name="Haircut", price="25.00", duration=30):
    response = client.post(
        "/services", json={"name": name, "price": price, "duration": duration}, headers=admin_headers()
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_slot(client, start_time=None):
    response = client.post("/slots", json={"start_time": start_time or future_time()}, headers=admin_headers())
    assert response.status_code == 201, response.text
    return response.json()


def book(client, service_id, slot_id, customer_name="Ada", phone="0800 000 001"):
    return client.post(
        "/bookings",
        json={"customer_name": customer_name, "phone": phone, "service_id": service_id, "slot_id": slot_id},
    )
