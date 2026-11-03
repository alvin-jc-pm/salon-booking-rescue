FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes do not reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini main.py ./
COPY app ./app
COPY migrations ./migrations

# Do not run as root.
RUN useradd --create-home --uid 10001 salon
USER salon

# Hosts usually set PORT themselves. These are only defaults.
ENV HOST=0.0.0.0 \
    PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=4)"

# Bring the schema up to date, then start. If the migration fails, the app
# does not start, so it never runs against a schema it does not expect.
CMD ["sh", "-c", "alembic upgrade head && exec python main.py"]
