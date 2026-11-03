from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import database_url
from app.models import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)


def run_migrations_online():
    url = config.attributes.get("database_url") or database_url()
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            # SQLite cannot alter columns in place. Batch mode copies the table instead.
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported. Set DATABASE_URL and run online.")
run_migrations_online()
