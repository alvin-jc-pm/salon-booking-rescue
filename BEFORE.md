# Before: how the one-prompt prototype fails

The code at tag `before` was run unchanged, the way a hosting platform would run it, and then sent 14 ordinary requests. The raw output is in `evidence/before_results.txt`, and the script that produced it is `evidence/before_check.py`.

## What a real host would see

| # | What was tried | What happened | Why it matters |
|---|---|---|---|
| 1 | Start it with `PORT=8080`, as hosts do, and send a request | Connection refused | The server ignores `PORT` and listens only on `127.0.0.1:8000`, so a host's router can never reach it. **The app cannot be deployed as written.** |
| 3 | `GET /health` | 404 | There is no health check, so the host cannot tell whether the app is up, and a deploy would be marked as failed. |
| 5 | Add a service called "Men's cut" | 500 Internal Server Error | Every query is built by pasting user text into SQL. One apostrophe breaks it. |
| 13 | Send SQL in the service name | 500, "You can only execute one statement at a time" | The injection was only stopped by a quirk of the SQLite driver. The same code on PostgreSQL, or a single-statement payload, would not be protected. |
| 8 | Book a slot that is already booked | 200, booked | Double bookings are allowed. Two customers get the same chair at the same time. |
| 9 | Book a service that does not exist (id 999) | 200, booked | There is no check on related records, so the bookings table fills with orphaned rows. |
| 10 | Create a slot at "whenever" | 200, added | Times are free text. Nothing can be sorted, filtered or checked for clashes. |
| 11 | Read every booking using the key `admin123` | 200, full list with names and phone numbers | The admin key is written into the source code, so anyone who sees the repository can read customers' personal data. It also travels in the URL, where it ends up in logs. |
| 12 | Delete a booking with no key at all | 200, deleted | The delete endpoint has no protection. Anyone can wipe bookings. |

## Problems you only see in the code

- **Data lives in `salon.db` next to the code.** On a container host, that file is deleted on every redeploy or restart, so all bookings vanish.
- **Database connections are never closed.** Each request opens a new SQLite connection and leaves it open.
- **The tables are created by `CREATE TABLE IF NOT EXISTS` at import time.** There are no migrations, so the schema cannot evolve safely.
- **`requirements.txt` lists `fastapi` and `uvicorn` with no versions.** A future install can pull breaking releases.
- **There are no tests, no Dockerfile, no `.env.example` and no README.**
- **Prices are floats,** which gives rounding errors on money.

## The rescue plan, one commit each

1. Read `HOST` and `PORT` from the environment, and add `/health`
2. Use parameterised queries everywhere, which removes the SQL injection risk
3. Move to PostgreSQL with SQLAlchemy and Alembic migrations
4. Move secrets to environment variables, add `.env.example`, and protect every admin route with a header key
5. Validate input: real datetimes, positive prices stored as cents, and existing service and slot ids
6. Prevent double booking, with a uniqueness rule in the database, not only in code
7. Pin dependencies, add a Dockerfile, and add tests for each failure above
8. Deploy with a managed database and backups, then write `HANDOVER.md`
