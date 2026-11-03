from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import database_url

engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session():
    """One session per request, always closed, so connections go back to the pool."""
    with SessionLocal() as session:
        yield session
