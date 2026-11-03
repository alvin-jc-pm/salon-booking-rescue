"""BEFORE.md rows 11 and 12: the admin key was in the source code and in the
URL, and anyone could delete bookings with no key at all."""
import os
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.config import EXAMPLE_ADMIN_KEY, admin_api_key
from app.main import app
from tests.helpers import ROOT, admin_headers

client = TestClient(app)


@pytest.fixture
def booking_id():
    client.post("/services", json={"name": "Blow dry", "price": 30, "duration": 45}, headers=admin_headers())
    service_id = client.get("/services").json()[-1]["id"]
    client.post("/slots", json={"start_time": "2026-11-09T09:00"}, headers=admin_headers())
    slot_id = client.get("/slots").json()[-1]["id"]
    client.post(
        "/bookings",
        json={"customer_name": "Dana", "phone": "0803", "service_id": service_id, "slot_id": slot_id},
    )
    return client.get("/admin/bookings", headers=admin_headers()).json()[-1]["id"]


def booking_ids():
    return [b["id"] for b in client.get("/admin/bookings", headers=admin_headers()).json()]


def test_delete_without_a_key_is_refused_and_the_booking_stays(booking_id):
    assert client.delete(f"/admin/bookings/{booking_id}").status_code == 401
    assert booking_id in booking_ids()


def test_delete_with_the_right_key_works(booking_id):
    assert client.delete(f"/admin/bookings/{booking_id}", headers=admin_headers()).status_code == 200
    assert booking_id not in booking_ids()


def test_list_without_a_key_is_refused():
    assert client.get("/admin/bookings").status_code == 401


def test_list_with_a_wrong_key_is_refused():
    assert client.get("/admin/bookings", headers={"X-Admin-Key": "x" * 40}).status_code == 401


def test_old_key_from_the_source_code_no_longer_works():
    assert client.get("/admin/bookings?key=admin123").status_code == 401
    assert client.get("/admin/bookings", headers={"X-Admin-Key": "admin123"}).status_code == 401


def test_real_key_in_the_url_is_not_accepted():
    # Keys in URLs end up in logs. Only the header counts.
    key = os.environ["ADMIN_API_KEY"]
    assert client.get(f"/admin/bookings?key={key}").status_code == 401


def test_list_with_the_key_in_the_header_works():
    assert client.get("/admin/bookings", headers=admin_headers()).status_code == 200


@pytest.mark.parametrize("path, body", [
    ("/services", {"name": "Free haircut", "price": 0.01, "duration": 5}),
    ("/slots", {"start_time": "2026-11-09T10:00"}),
])
def test_creating_services_and_slots_needs_the_key(path, body):
    assert client.post(path, json=body).status_code == 401


@pytest.mark.parametrize("value", ["", "short", EXAMPLE_ADMIN_KEY])
def test_app_refuses_a_missing_short_or_example_key(value):
    with pytest.raises(RuntimeError, match="ADMIN_API_KEY"):
        admin_api_key({"ADMIN_API_KEY": value})


def source_files():
    yield os.path.join(ROOT, "main.py")
    for top in ("app", "migrations"):
        for folder, _, files in os.walk(os.path.join(ROOT, top)):
            yield from (os.path.join(folder, f) for f in files if f.endswith(".py"))


def test_no_admin_key_is_written_in_the_code():
    for path in source_files():
        assert "admin123" not in open(path, encoding="utf-8").read(), path


def test_env_file_is_ignored_and_an_example_is_provided():
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT)
    assert ignored.returncode == 0
    example = open(os.path.join(ROOT, ".env.example"), encoding="utf-8").read()
    for name in ("DATABASE_URL", "ADMIN_API_KEY", "HOST", "PORT"):
        assert f"{name}=" in example
