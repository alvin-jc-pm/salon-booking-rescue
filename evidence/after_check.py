"""Send the same requests as before_check.py to a running copy of the
rescued app, and check each one now gets the right answer.

Usage:
    ADMIN_API_KEY=... python evidence/after_check.py http://localhost:8080

Only the standard library is used, so this runs anywhere. It exits with
status 1 if any check fails. It adds a few services, slots and bookings,
so point it at a test or demo database, not one with real customers.
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone


def request(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    all_headers = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(url, data=data, method=method, headers=all_headers)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except OSError as e:
        return "NO RESPONSE", f"{type(e).__name__}: {e}"


def run(base, admin_key):
    """Returns a list of (label, method, path, body, expected, got, text)."""
    admin = {"X-Admin-Key": admin_key}
    tag = uuid.uuid4().hex[:6]  # keeps repeated runs apart
    when = (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0)
    results = []
    state = {}

    def check(label, method, path, expected, body=None, headers=None, keep=None):
        got, text = request(method, base + path, body, headers)
        if keep and got == expected:
            state[keep] = json.loads(text)
        results.append((label, method, path, body, expected, got, text[:160]))
        return got, text

    check("1. Host sets PORT and probes it", "GET", "/", 200)
    check("3. Health check a host would call", "GET", "/health", 200)
    check("4. Add a normal service", "POST", "/services", 201,
          {"name": f"Haircut {tag}", "price": "25.00", "duration": 30}, admin, keep="service")
    check("5. Add a service with an apostrophe", "POST", "/services", 201,
          {"name": f"Men's cut {tag}", "price": "20.00", "duration": 30}, admin)
    check("6. Add a time slot", "POST", "/slots", 201,
          {"start_time": when.isoformat()}, admin, keep="slot")
    service_id = state.get("service", {}).get("id", 0)
    slot_id = state.get("slot", {}).get("id", 0)
    check("7. Book the slot", "POST", "/bookings", 201,
          {"customer_name": "Ada", "phone": "0800 000 001", "service_id": service_id, "slot_id": slot_id},
          keep="booking")
    check("8. Book the same slot again", "POST", "/bookings", 409,
          {"customer_name": "Ben", "phone": "0800 000 002", "service_id": service_id, "slot_id": slot_id})
    check("9. Book a service that does not exist", "POST", "/bookings", 404,
          {"customer_name": "Cy", "phone": "0800 000 003", "service_id": 999999, "slot_id": slot_id})
    check("10. Slot time that is not a time", "POST", "/slots", 422, {"start_time": "whenever"}, admin)
    check("11. Admin list with the old key from the source code", "GET", "/admin/bookings?key=admin123", 401)
    check("11b. Admin list with the real key, in a header", "GET", "/admin/bookings", 200, headers=admin)
    booking_id = state.get("booking", {}).get("id", 0)
    check("12. Admin delete with no key at all", "DELETE", f"/admin/bookings/{booking_id}", 401)
    payload = f"x', 0, 0); DELETE FROM bookings; -- {tag}"
    check("13. SQL injection attempt through the service name", "POST", "/services", 201,
          {"name": payload, "price": "1.00", "duration": 5}, admin)
    got, text = check("14. Bookings after the injection attempt", "GET", "/admin/bookings", 200, headers=admin)

    # The status codes alone do not prove 13 and 14. Check the data too.
    names = [s["name"] for s in json.loads(request("GET", base + "/services")[1])]
    results.append(("13b. Injection text was saved as plain text", "", "", None, True, payload in names, ""))
    still_there = got == 200 and any(b["id"] == booking_id for b in json.loads(text))
    results.append(("14b. Ada's booking survived steps 12 and 13", "", "", None, True, still_there, ""))
    return results


def report(results):
    lines = []
    for label, method, path, body, expected, got, text in results:
        mark = "ok  " if got == expected else "FAIL"
        lines.append(f"[{mark}] {label}")
        if method:
            lines.append(f"   {method} {path}" + (f"  body={json.dumps(body)}" if body else ""))
            lines.append(f"   -> {got}  (expected {expected})  {text}")
        else:
            lines.append(f"   -> {got}  (expected {expected})")
        lines.append("")
    failed = [r for r in results if r[5] != r[4]]
    lines.append(f"{len(results) - len(failed)} of {len(results)} checks passed.")
    return "\n".join(lines), not failed


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.environ.get("ADMIN_API_KEY"):
        sys.exit(__doc__)
    text, ok = report(run(sys.argv[1].rstrip("/"), os.environ["ADMIN_API_KEY"]))
    print(text)
    sys.exit(0 if ok else 1)
