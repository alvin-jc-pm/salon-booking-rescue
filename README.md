# Salon Booking API: rescuing a one-prompt prototype

This is a self-initiated portfolio project.

An AI coding assistant wrote a small FastAPI booking API for a salon from a single prompt ([PROMPT.md](PROMPT.md)). It looked finished, but it could not be deployed and it was not safe to use. [BEFORE.md](BEFORE.md) shows exactly how it failed when run the way a hosting platform runs it.

This repository fixes it one problem at a time, with one commit per fix and a test proving each failure is gone. The untouched prototype is the commit tagged `before`.

The rescued version runs on Railway with a managed PostgreSQL database: https://salon-booking-rescue-production.up.railway.app (try `/health` or `/docs`). [HANDOVER.md](HANDOVER.md) explains how it is deployed, backed up and maintained.

## Before and after

| # | What was tried | Before | After |
|---|---|---|---|
| 1 | Start with `PORT=8080` and send a request | Connection refused | Answers on 8080 |
| 3 | `GET /health` | 404 | 200, and 503 if the database is down |
| 5 | Add a service called "Men's cut" | 500 | 201, saved as typed |
| 13 | Send SQL in the service name | 500, stopped only by a driver quirk | 201, saved as plain text |
| 8 | Book a slot that is already booked | 200, double booked | 409, refused by the database |
| 9 | Book a service that does not exist | 200, orphan row saved | 404 |
| 10 | Create a slot at "whenever" | 200, saved | 422 |
| 11 | Read all bookings with the key from the source code | 200, names and phone numbers | 401. The key is now an environment variable sent in a header |
| 12 | Delete a booking with no key | 200, deleted | 401 |

The problems that only show in the code are fixed too:

| Problem | Fix |
|---|---|
| Data kept in a file that a container host wipes on redeploy | PostgreSQL through `DATABASE_URL` |
| Database connections never closed | One session per request, returned to a pool |
| Tables created at import, no migrations | Alembic migrations in [migrations/](migrations/) |
| Unpinned dependencies | Exact versions in [requirements.txt](requirements.txt) |
| No tests, Dockerfile, `.env.example` or README | All added. CI runs the tests on PostgreSQL and SQLite |
| Prices stored as floats | Whole cents in an integer column |

[evidence/after_check.py](evidence/after_check.py) sends the same requests as [evidence/before_check.py](evidence/before_check.py) to any running copy and checks every answer. CI runs it against the Docker image on every push.

## Run it locally

You need Python 3.11 and a PostgreSQL database.

```sh
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env             # then edit the values
set -a; . ./.env; set +a         # load them into this shell

alembic upgrade head             # create or update the tables
python main.py                   # serves on http://localhost:8000
```

Interactive API docs are at `http://localhost:8000/docs`.

## Run it with Docker

```sh
docker build -t salon-booking .
docker run -p 8000:8000 --env-file .env salon-booking
```

The container applies any new migrations, then starts. If a migration fails, the app does not start.

## Settings

All settings come from environment variables. See [.env.example](.env.example).

| Variable | Required | Meaning |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL URL. `postgres://` and `postgresql://` URLs from hosts work as given. |
| `ADMIN_API_KEY` | Yes | Key staff send in the `X-Admin-Key` header. At least 24 characters. The app will not start without it. |
| `PORT` | No | Port to listen on. Default 8000. Most hosts set this. |
| `HOST` | No | Address to listen on. Default `0.0.0.0`. |

## API

| Method and path | Who | What it does |
|---|---|---|
| `GET /health` | Anyone | 200 if the app and database are up |
| `GET /services` | Anyone | List services |
| `POST /services` | Staff | Add a service: `{"name": "Haircut", "price": "25.00", "duration": 30}` |
| `GET /slots` | Anyone | List free slots, earliest first |
| `POST /slots` | Staff | Add a slot: `{"start_time": "2026-12-01T10:00:00+00:00"}` |
| `POST /bookings` | Anyone | Book: `{"customer_name": "Ada", "phone": "0800 000 001", "service_id": 1, "slot_id": 1}` |
| `GET /admin/bookings` | Staff | List bookings, with customer details |
| `DELETE /admin/bookings/{id}` | Staff | Cancel a booking. The slot becomes free again. |

Staff routes need the `X-Admin-Key` header:

```sh
curl -H "X-Admin-Key: $ADMIN_API_KEY" http://localhost:8000/admin/bookings
```

Rules the API enforces:

- Times need a UTC offset, must be in the future, and are returned in UTC.
- Prices are above zero with at most two decimals. They are stored as cents and returned as both `"price": "25.00"` and `"price_cents": 2500`.
- A booking must name a service and a slot that exist (404 if not).
- One booking per slot. A second booking gets 409. The database enforces this, so two requests at the same moment cannot both succeed.
- Unknown fields are refused with 422.

## Tests

```sh
pytest
```

Without any setup, the tests use a throwaway SQLite file. To run them against PostgreSQL, as CI does, set `TEST_DATABASE_URL` to an empty test database. The tests build the schema with the real migrations, so they also check that the migrations work.

## Changing the database

Edit [app/models.py](app/models.py), then:

```sh
alembic revision --autogenerate -m "describe the change"
```

Read the generated file before committing it. `tests/test_database.py` fails if the models and migrations ever disagree.
