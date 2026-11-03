"""BEFORE.md, problems in the code: data in a local file, connections never
closed, and tables created at import time with no migrations."""
import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app.config import database_url
from app.db import engine
from app.main import app
from app.models import Base
from tests.helpers import ROOT, alembic_config, sqlite_url


def test_database_url_is_required():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database_url({})


@pytest.mark.parametrize("given", ["postgres://u:p@db:5432/salon", "postgresql://u:p@db:5432/salon"])
def test_host_style_postgres_urls_use_the_psycopg_driver(given):
    assert database_url({"DATABASE_URL": given}) == "postgresql+psycopg://u:p@db:5432/salon"


def test_connections_go_back_to_the_pool_after_requests():
    client = TestClient(app)
    for _ in range(25):
        client.get("/services")
        client.get("/slots")
        client.get("/health")
    assert engine.pool.checkedout() == 0


def test_health_reports_database_is_reachable():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_migrations_build_and_remove_the_schema(tmp_path):
    url = sqlite_url(tmp_path, "fresh.db")
    command.upgrade(alembic_config(url), "head")
    fresh = create_engine(url)
    assert {"services", "slots", "bookings"} <= set(inspect(fresh).get_table_names())
    command.downgrade(alembic_config(url), "base")
    assert set(inspect(fresh).get_table_names()) == {"alembic_version"}
    fresh.dispose()


def test_models_match_the_migrations():
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == []


def test_app_never_creates_tables_itself():
    for folder, _, files in os.walk(os.path.join(ROOT, "app")):
        for name in files:
            if name.endswith(".py"):
                source = open(os.path.join(folder, name), encoding="utf-8").read()
                assert "create_all" not in source
                assert "CREATE TABLE" not in source.upper()
