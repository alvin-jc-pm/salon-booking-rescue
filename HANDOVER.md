# Handover

This note is for whoever runs or changes the Salon Booking API next. It covers where the app runs, how it gets deployed, where the secrets and data live, and what is still left to do.

## Where it runs

- **Live URL:** https://salon-booking-rescue-production.up.railway.app
- **Health check:** https://salon-booking-rescue-production.up.railway.app/health
- **API docs:** https://salon-booking-rescue-production.up.railway.app/docs
- **Host:** Railway, project `artistic-vitality`, environment `production`. It has two services:
  - `salon-booking-rescue`: the app, built from the [Dockerfile](Dockerfile) in this repository.
  - `Postgres`: Railway's managed PostgreSQL. The app reaches it over Railway's private network, so the database is not exposed to the internet.

The data lives in the Postgres service, not in the app container. Redeploying or restarting the app does not lose any bookings.

## How a deploy works

1. A push to `main` on GitHub starts a Railway build from the Dockerfile.
2. The new container runs `alembic upgrade head`. If a migration fails, the container stops and the old version keeps serving.
3. The app starts on the port Railway gives it in `PORT`.
4. Railway waits for `/health` to return 200 before it sends traffic to the new version ([railway.json](railway.json)). `/health` also checks the database.

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the tests on PostgreSQL and SQLite, builds the Docker image, and replays every request from [BEFORE.md](BEFORE.md) against it.

## Secrets and settings

These are set on the `salon-booking-rescue` service in Railway, under **Variables**. None of them are in the repository.

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}`. This is a reference, so Railway fills in the current database address. Do not paste a fixed URL here. |
| `ADMIN_API_KEY` | A random 43-character key. Staff send it in the `X-Admin-Key` header. |
| `PORT` | Set by Railway. Do not set it yourself. |

**To read the admin key:** Railway dashboard, `salon-booking-rescue`, then **Variables**. Or run `railway variables --service salon-booking-rescue` after `railway link`.

**To change the admin key**, for example when someone leaves:

```sh
railway variables --service salon-booking-rescue --set "ADMIN_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Railway redeploys with the new key. The old key stops working as soon as the new version is live.

## Backups

**Action needed: backups are not switched on yet.** Railway's command line tool cannot schedule them, so this has to be done in the dashboard:

1. Open the `Postgres` service and go to the **Backups** tab.
2. Turn on a **daily** schedule. Add weekly as well if your plan offers it.
3. Click **Backup now** once, so there is a first copy straight away.

Which schedules you can choose, and how long backups are kept, depends on the Railway plan.

**To restore**, open the **Backups** tab, pick a backup, and click **Restore**. Railway restores it into the same service. Do a test restore at least once, so you know it works before you need it.

**A one-off copy on your own machine** is worth taking before any risky change. It needs `pg_dump` installed, and you need the public database URL from the `Postgres` service's **Variables** tab (`DATABASE_PUBLIC_URL`):

```sh
pg_dump --format=custom --file=salon-$(date +%F).dump "<DATABASE_PUBLIC_URL>"
```

The dump holds customers' names and phone numbers. Store it like any other personal data and delete it when you no longer need it.

## Checking that it works

```sh
ADMIN_API_KEY=<key> python evidence/after_check.py https://salon-booking-rescue-production.up.railway.app
```

This sends the same requests that broke the prototype and checks every answer. The run recorded at handover is in [evidence/after_results.txt](evidence/after_results.txt), with 16 of 16 checks passing. Each run adds a few demo services, slots and bookings (customer "Ada"), so do not run it once real customers are using the system. Use a separate Railway environment instead.

## Changing the code

See [README.md](README.md) for running it locally, the tests, and adding a migration. In short:

1. Make the change and add a test.
2. If the database changes, edit [app/models.py](app/models.py) and add an Alembic migration. `tests/test_database.py` fails if they disagree.
3. Run `pytest`, push, and wait for CI to pass.

## Still to do

These were outside the rescue plan, but a real salon would need them:

- **Turn on backups** (see above).
- **Make Railway wait for CI.** Right now Railway deploys a push even if the tests fail. In the `salon-booking-rescue` service settings, turn on **Wait for CI**.
- **Remove the demo data** created by the after-check before real customers use the system.
- **One shared admin key.** Every staff member uses the same key. Separate staff logins would let you remove one person's access without changing everyone's key.
- **No rate limiting.** Anyone can send many booking requests. Add limits at the app or a proxy before going public.
- **One booking per slot, nothing more.** Slots do not belong to a stylist and do not account for how long a service takes. A salon with several chairs needs slots per stylist, and long services need to block the slots that follow.
- **Customers cannot cancel their own bookings.** Only staff can, through the admin route.
- **Migrations run when the app starts.** That is fine with one replica, which is the current setup. With more than one, move `alembic upgrade head` to a pre-deploy command so it runs once.
