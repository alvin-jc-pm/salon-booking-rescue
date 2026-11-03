"""BEFORE.md rows 5 and 13: user text was pasted straight into SQL."""
import ast
import os

from fastapi.testclient import TestClient

import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client = TestClient(main.app)


def service_names():
    return [s["name"] for s in client.get("/services").json()]


def test_service_name_with_apostrophe_is_saved():
    response = client.post("/services", json={"name": "Men's cut", "price": 20, "duration": 30})
    assert response.status_code == 200
    assert "Men's cut" in service_names()


def test_customer_name_with_apostrophe_is_saved():
    client.post("/slots", json={"start_time": "2026-11-08T11:00"})
    slot_id = client.get("/slots").json()[-1]["id"]
    response = client.post(
        "/bookings",
        json={"customer_name": "Siobhan O'Neil", "phone": "0800", "service_id": 1, "slot_id": slot_id},
    )
    assert response.status_code == 200


def test_sql_in_service_name_is_stored_as_plain_text():
    payload = "x', 0, 0); DELETE FROM bookings; --"
    response = client.post("/services", json={"name": payload, "price": 1, "duration": 1})
    assert response.status_code == 200
    assert payload in service_names()


def test_single_statement_injection_does_not_change_other_rows():
    # A payload that SQLite's one-statement rule would not have stopped.
    client.post("/services", json={"name": "Colour", "price": 40, "duration": 60})
    payload = "y', 0, 0), ('injected', 0, 0) --"
    client.post("/services", json={"name": payload, "price": 1, "duration": 1})
    names = service_names()
    assert payload in names
    assert "injected" not in names


def test_no_query_is_built_with_an_f_string():
    tree = ast.parse(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "execute":
            assert not isinstance(node.args[0], ast.JoinedStr), f"f-string SQL on line {node.lineno}"
