import os


def database_url(env=os.environ):
    """The database to use, from DATABASE_URL.

    There is deliberately no default. A file next to the code is wiped
    whenever a container host redeploys, so the app must be pointed at a
    real database server.
    """
    url = env.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Point it at a PostgreSQL database.")
    # Hosts usually hand out postgres:// or postgresql:// URLs.
    # SQLAlchemy needs to be told which driver to use.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
