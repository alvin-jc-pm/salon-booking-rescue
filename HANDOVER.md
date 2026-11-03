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

1. A push to `main` on GitHub starts a Railway build from the Dockerfile, but only after CI has passed (**Wait for CI** is on).
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

**Backups are manual, by choice.** This deployment is a portfolio demo and holds only demo data. The Railway plan it runs on has no built-in backups, and automating them would add cost and moving parts to protect nothing real. So backups are a manual routine. The design for a real client is further down.

The database has no public address. It can only be reached over Railway's private network, and the routine below keeps it that way.

**Status: these commands are written out but have not been run yet.** Do the first backup and a test restore before relying on them.

### One-time setup

Run every command in this section in **Git Bash** (installed with Git for Windows), from the project folder. Do not use PowerShell: Windows PowerShell 5.1 rewrites redirected output as UTF-16, which corrupts a database dump.

1. Install the [Railway CLI](https://docs.railway.com/guides/cli), then run `railway login` and `railway link` (project `artistic-vitality`, environment `production`).
2. `railway ssh` needs an SSH key registered with your Railway account. Create one with `ssh-keygen -t ed25519`, then register it with `railway ssh keys add`. Remove it later with `railway ssh keys remove` if you stop doing backups from that computer.
3. Create a GPG key for backups, if you do not have one: `gpg --full-generate-key`. Keep the private key and its passphrase somewhere safe, such as a password manager. Without them the backups cannot be read.

### Taking a backup (weekly, and before any risky change)

```sh
DAY=$(date +%F)
railway ssh --service Postgres -- sh -c 'pg_dump --no-owner --no-privileges -h localhost -U "$PGUSER" -d "$PGDATABASE"' > salon-$DAY.sql
grep -q "PostgreSQL database dump complete" salon-$DAY.sql && echo "dump is complete"
gpg --encrypt --recipient "<your GPG key id>" salon-$DAY.sql
rm salon-$DAY.sql
```

`pg_dump` runs inside the Postgres service, so the database never needs a public address. The dump holds customers' names and phone numbers, so only the encrypted `.sql.gpg` file is kept. Store it somewhere other than this computer and never in this repository. Delete old copies when they are no longer needed.

### Restoring

Restores are rare, so this uses a temporary public address:

1. In the `Postgres` service, go to **Settings**, then **Networking**, and add a **TCP Proxy**. Copy `DATABASE_PUBLIC_URL` from its **Variables** tab.
2. Restore into an empty database: `gpg --decrypt salon-<date>.sql.gpg | psql "<DATABASE_PUBLIC_URL>"`
3. Remove the TCP proxy again, so the database is private once more.

### For a real client

With real customer data, backups must not depend on someone remembering to take them. The design would be:

- A small **scheduled Railway service** in the same project. Each night it runs `pg_dump` over the private network, encrypts the dump with the client's public GPG key, and uploads it to a storage bucket the client owns (for example Cloudflare R2 or Backblaze B2), with a retention rule such as 30 daily and 12 monthly copies.
- An alert if a night's backup is missing, and a test restore every quarter.
- Or, more simply, a Railway plan with built-in backups, if its retention is enough.

Running backups from GitHub Actions was considered and rejected. It needs the database on the internet, and the dumps would sit next to a public repository.

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

- **Run the first manual backup and a test restore** (see above), so the routine is proven.
- **Remove the demo data** before real customers use the system. The demo booking has been deleted. The three demo services and one slot are still there, because the API has no route to delete them. To clear them, run this in Git Bash after the one-time setup in the Backups section:

  ```sh
  railway ssh --service Postgres -- sh -c 'psql -h localhost -U "$PGUSER" -d "$PGDATABASE" -c "TRUNCATE bookings, slots, services RESTART IDENTITY;"'
  ```
- **One shared admin key.** Every staff member uses the same key. Separate staff logins would let you remove one person's access without changing everyone's key.
- **No rate limiting.** Anyone can send many booking requests. Add limits at the app or a proxy before going public.
- **One booking per slot, nothing more.** Slots do not belong to a stylist and do not account for how long a service takes. A salon with several chairs needs slots per stylist, and long services need to block the slots that follow.
- **Customers cannot cancel their own bookings.** Only staff can, through the admin route.
- **Migrations run when the app starts.** That is fine with one replica, which is the current setup. With more than one, move `alembic upgrade head` to a pre-deploy command so it runs once.
