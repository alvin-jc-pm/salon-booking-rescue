import os
import secrets
import tempfile

from alembic import command

from tests.helpers import alembic_config, sqlite_url

# Run from a throwaway folder so nothing is written next to the code.
TMP = tempfile.mkdtemp(prefix="salon-tests-")
os.chdir(TMP)

# CI sets TEST_DATABASE_URL to a real PostgreSQL server.
# Locally the tests fall back to a SQLite file in the throwaway folder.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or sqlite_url(TMP, "test.db")

# A fresh random admin key for every run, so no key is ever written in the repo.
os.environ["ADMIN_API_KEY"] = secrets.token_urlsafe(32)

# Build the schema the same way production does: with the migrations.
# Going down to base first gives a clean database on every run.
command.downgrade(alembic_config(), "base")
command.upgrade(alembic_config(), "head")
