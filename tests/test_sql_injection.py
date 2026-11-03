"""BEFORE.md rows 5 and 13: user text was pasted straight into SQL."""
import ast
import os

from fastapi.testclient import TestClient

import main
from tests.helpers import ROOT, book, create_service, create_slot

client = TestClient(main.app)


def service_names():
    return [s["name"] for s in client.get("/services").json()]


def test_service_name_with_apostrophe_is_saved():
    assert create_service(client, name="Men's cut")["name"] == "Men's cut"
    assert "Men's cut" in service_names()


def test_customer_name_with_apostrophe_is_saved():
    service = create_service(client, name="Trim")
    slot = create_slot(client)
    response = book(client, service["id"], slot["id"], customer_name="Siobhan O'Neil")
    assert response.status_code == 201
    assert response.json()["customer_name"] == "Siobhan O'Neil"


def test_sql_in_service_name_is_stored_as_plain_text():
    payload = "x', 0, 0); DELETE FROM bookings; --"
    create_service(client, name=payload)
    assert payload in service_names()


def test_single_statement_injection_does_not_change_other_rows():
    # A payload that SQLite's one-statement rule would not have stopped.
    payload = "y', 0, 0), ('injected', 0, 0) --"
    create_service(client, name=payload)
    names = service_names()
    assert payload in names
    assert "injected" not in names


def python_files():
    yield os.path.join(ROOT, "main.py")
    for folder, _, files in os.walk(os.path.join(ROOT, "app")):
        yield from (os.path.join(folder, f) for f in files if f.endswith(".py"))


def test_no_query_is_built_from_formatted_strings():
    for path in python_files():
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in ("execute", "text"):
                first = node.args[0] if node.args else None
                assert not isinstance(first, (ast.JoinedStr, ast.BinOp)), f"formatted SQL in {path} line {node.lineno}"
