"""Fill a running copy of the app with demo services and free times.

Usage, with the admin key in the environment, never on the command line:

    ADMIN_API_KEY=... python scripts/seed_demo.py https://your-app.example.com

It adds the demo services only if there are none yet, and adds hourly slots
(10:00 to 16:00 salon time, Monday to Saturday) for each of the next 7 days
that has no free times yet. Run it again whenever the free times run low. It only uses the
public API, so it works against any deployment.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

SALON_TIMEZONE = ZoneInfo("America/New_York")
SERVICES = [
    {"name": "Women's cut and style", "price": "55.00", "duration": 60},
    {"name": "Men's cut", "price": "30.00", "duration": 30},
    {"name": "Colour, full head", "price": "95.00", "duration": 120},
    {"name": "Blow-dry", "price": "35.00", "duration": 45},
]
DAYS_AHEAD = 7
OPEN_HOURS = range(10, 17)  # last slot starts at 16:00


def call(base, method, path, body=None, key=None):
    request = urllib.request.Request(base + path, method=method)
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(body).encode()
    if key:
        request.add_header("X-Admin-Key", key)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read() or "null")


def wanted_times(now):
    local_today = now.astimezone(SALON_TIMEZONE).date()
    for offset in range(DAYS_AHEAD + 1):
        day = local_today + timedelta(days=offset)
        if day.weekday() == 6:  # closed on Sundays
            continue
        for hour in OPEN_HOURS:
            start = datetime.combine(day, time(hour), SALON_TIMEZONE)
            if start > now + timedelta(hours=1):
                yield start.astimezone(timezone.utc)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/seed_demo.py <base url>")
    base = sys.argv[1].rstrip("/")
    key = os.environ.get("ADMIN_API_KEY")
    if not key:
        sys.exit("Set ADMIN_API_KEY in the environment first.")

    try:
        if not call(base, "GET", "/services"):
            for service in SERVICES:
                call(base, "POST", "/services", service, key)
            print(f"Added {len(SERVICES)} services.")
        else:
            print("Services already exist. Left them alone.")

        # /slots lists only free times, so a booked time cannot be seen here.
        # To avoid adding a booked time back as free, only days with no free
        # times at all are filled. A re-run therefore just adds the new days.
        free = call(base, "GET", "/slots")
        filled_days = {datetime.fromisoformat(s["start_time"]).astimezone(SALON_TIMEZONE).date() for s in free}
        added = 0
        for start in wanted_times(datetime.now(timezone.utc)):
            if start.astimezone(SALON_TIMEZONE).date() not in filled_days:
                call(base, "POST", "/slots", {"start_time": start.isoformat()}, key)
                added += 1
        print(f"Added {added} free times. Open {base}/book to see them.")
    except urllib.error.HTTPError as err:
        sys.exit(f"{err.code} from {err.url}: {err.read().decode(errors='replace')}")


if __name__ == "__main__":
    main()
