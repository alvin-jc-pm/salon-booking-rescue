"""Entry point. Run with `python main.py`, or `uvicorn main:app`."""
import os

from app.main import app  # noqa: F401


def server_options(env=os.environ):
    """Where to listen. Hosts tell the app which port to use through PORT."""
    return env.get("HOST", "0.0.0.0"), int(env.get("PORT", "8000"))


if __name__ == "__main__":
    import uvicorn

    host, port = server_options()
    uvicorn.run(app, host=host, port=port)
