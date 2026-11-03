"""Run the unchanged prototype the way a host would, and record what breaks."""
import json, os, subprocess, sys, time, urllib.request, urllib.error

PROJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run")  # copy the unchanged main.py into evidence/run first
PY = sys.executable  # run this with the project virtualenv python
db = os.path.join(PROJ, "salon.db")
if os.path.exists(db):
    os.remove(db)


def req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, resp.read().decode()[:160]
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()[:160]
        except Exception:
            body = "(no readable body)"
        return e.code, body
    except Exception as e:
        return "NO RESPONSE", type(e).__name__ + ": " + str(e)[:120]


env = dict(os.environ, PORT="8080")
logf = open(os.path.join(PROJ, "server.log"), "w")
p = subprocess.Popen([PY, "main.py"], cwd=PROJ, env=env, stdout=logf, stderr=subprocess.STDOUT, text=True)
time.sleep(4)
results = []
def check(label, method, url, body=None):
    results.append((label, method, url.replace("http://", ""), body, *req(method, url, body)))

H = "http://127.0.0.1"
check("1. Host sets PORT=8080 and probes it", "GET", "http://localhost:8080/")
check("2. App is actually on 127.0.0.1:8000", "GET", H + ":8000/")
check("3. Health check a host would call", "GET", H + ":8000/health")
check("4. Add a normal service", "POST", H + ":8000/services", {"name": "Haircut", "price": 25, "duration": 30})
check("5. Add a service with an apostrophe", "POST", H + ":8000/services", {"name": "Men's cut", "price": 20, "duration": 30})
check("6. Add a time slot", "POST", H + ":8000/slots", {"start_time": "2026-11-08T10:00"})
check("7. Book the slot", "POST", H + ":8000/bookings", {"customer_name": "Ada", "phone": "0800", "service_id": 1, "slot_id": 1})
check("8. Book the same slot again", "POST", H + ":8000/bookings", {"customer_name": "Ben", "phone": "0801", "service_id": 1, "slot_id": 1})
check("9. Book a service that does not exist", "POST", H + ":8000/bookings", {"customer_name": "Cy", "phone": "0802", "service_id": 999, "slot_id": 1})
check("10. Slot time that is not a time", "POST", H + ":8000/slots", {"start_time": "whenever"})
check("11. Admin list with the key from the source code", "GET", H + ":8000/admin/bookings?key=admin123")
check("12. Admin delete with no key at all", "DELETE", H + ":8000/admin/bookings/1")
check("13. SQL injection attempt through the service name", "POST", H + ":8000/services", {"name": "x', 0, 0); DELETE FROM bookings; --", "price": 1, "duration": 1})
check("14. Bookings after the injection attempt", "GET", H + ":8000/admin/bookings?key=admin123")

p.terminate()
try:
    p.wait(timeout=5)
except Exception:
    p.kill()
logf.close()
out = open(os.path.join(PROJ, "server.log")).read()

for label, m, u, b, code, text in results:
    print(f"{label}\n   {m} {u}" + (f"  body={json.dumps(b)}" if b else "") + f"\n   -> {code}  {text}\n")
print("SERVER LOG (last lines):")
print("\n".join([l for l in out.splitlines() if l.strip()][-25:]))
print("\nsalon.db created next to the code:", os.path.exists(db))
