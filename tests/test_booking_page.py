"""The customer booking page at /book."""
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import book, create_service, create_slot

client = TestClient(app)


def test_booking_page_is_served_as_html():
    response = client.get("/book")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<form" in response.text


def test_booking_page_uses_only_the_public_endpoints():
    page = client.get("/book").text
    for path in ('"/services"', '"/slots"', '"/bookings"'):
        assert path in page
    # The page must never need the admin key.
    assert "X-Admin-Key" not in page
    assert "/admin" not in page


def test_booking_page_writes_text_safely():
    # Names come from users, so the page must never insert them as HTML.
    page = client.get("/book").text
    assert "innerHTML" not in page


def test_home_points_to_the_booking_page():
    assert client.get("/").json()["booking_page"] == "/book"


def test_the_flow_the_page_runs():
    service = create_service(client, name="Page test cut")
    slot = create_slot(client)
    assert slot["id"] in [s["id"] for s in client.get("/slots").json()]
    assert book(client, service["id"], slot["id"]).status_code == 201
    # A booked time disappears from the list the page shows.
    assert slot["id"] not in [s["id"] for s in client.get("/slots").json()]
    # A second booking for it gets the 409 the page explains.
    assert book(client, service["id"], slot["id"], customer_name="Bea").status_code == 409
