from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import database_url

engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

if engine.dialect.name == "sqlite":
    # SQLite (used only for local tests) ignores foreign keys unless asked.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys = ON")


def get_session():
    """One session per request, always closed, so connections go back to the pool."""
    with SessionLocal() as session:
        yield session
