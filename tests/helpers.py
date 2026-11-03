import os

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
