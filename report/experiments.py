"""Fault-injection experiments for the saga, the outbox, idempotent consumers and tracing.
Needs the full stack running.  python report/experiments.py   ->  report/results/experiments.json
"""
import json
import os
import subprocess
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "report", "results", "experiments.json")
GW = "http://localhost:8080"
BOOK_DIRECT = "http://localhost:8081"


def dc(*args):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def psql(db, user, pw, sql):
    return subprocess.run(["docker", "compose", "exec", "-T", "-e", f"PGPASSWORD={pw}", "postgres", "psql", "-h", "localhost", "-U", user, "-d", db, "-tAc", sql],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()


def login():
    r = requests.post(GW + "/api/auth/login", json={"username": "librarian", "password": "librarian123"})
    return {"Authorization": "Bearer " + r.json()["token"]}


H = login()


def get(path):
    return requests.get(GW + path, headers=H, timeout=30)


def post(path, body=None):
    return requests.post(GW + path, headers=H, json=body, timeout=30)


def book(i):
    return get(f"/api/books/{i}").json()


def wait(cond, timeout=180, step=0.5):
    t = time.time()
    while time.time() - t < timeout:
        v = cond()
        if v:
            return time.time() - t
        time.sleep(step)
    return None


res = {}


def quiet():
    """Wait until no saga is pending and the outbox is empty, so every experiment starts from a quiet system."""
    wait(lambda: int(psql("lendingdb", "lendinguser", "lending123", "select count(*) from loan where status = 'PENDING'")) == 0
         and int(psql("lendingdb", "lendinguser", "lending123", "select count(*) from outbox_event where sent_at is null")) == 0, 120)
    time.sleep(2)


quiet()

# ------------------------------------------------------------ E1 outbox: broker outage
print("E1 outbox during a RabbitMQ outage")
notes_before = len(get("/api/notifications").json())
dc("stop", "rabbitmq")
time.sleep(3)
issued = [post("/api/loans/issue", {"bookId": 700 + i, "memberId": 1 + i}) for i in range(5)]
time.sleep(2)
pending = int(psql("lendingdb", "lendinguser", "lending123", "select count(*) from outbox_event where sent_at is null"))
statuses = [r.status_code for r in issued]
t_start = time.time()
dc("start", "rabbitmq")
drain = wait(lambda: int(psql("lendingdb", "lendinguser", "lending123", "select count(*) from outbox_event where sent_at is null")) == 0, 240)
wait(lambda: len(get("/api/notifications").json()) - notes_before >= 5, 60)
res["E1_outbox"] = {"loans_requested": 5, "http_status": statuses, "outbox_pending_during_outage": pending,
                    "seconds_until_outbox_empty_after_broker_restart": drain,
                    "notifications_created": len(get("/api/notifications").json()) - notes_before}
print(res["E1_outbox"])

# ------------------------------------------------------------ E2 saga: book-service outage, forward recovery
print("E2 saga with book-service down")
before = book(800)["availableCopies"]
dc("stop", "book-service")
time.sleep(1)
t0 = time.time()
r = post("/api/loans/issue", {"bookId": 800, "memberId": 4})
t_accept = time.time() - t0
loan = r.json()
lid = loan["id"]
dc("start", "book-service")
t1 = time.time()
done = wait(lambda: get(f"/api/loans/{lid}").json()["status"] == "ISSUED", 240)
after = book(800)["availableCopies"]
ev = [e["type"] for e in get(f"/api/loans/{lid}/events").json()]
res["E2_saga_outage"] = {"http_status_during_outage": r.status_code, "loan_status_when_accepted": loan["status"], "seconds_to_accept": t_accept,
                         "seconds_until_issued_after_book_service_restart": done, "copies_before": before, "copies_after": after, "events": ev}
print(res["E2_saga_outage"])

# ------------------------------------------------------------ E3 saga: rejection without side effects
print("E3 saga rejection")
gid = 5   # The Great Gatsby, one copy
first = post("/api/loans/issue", {"bookId": gid, "memberId": 5})
copies_mid = book(gid)["availableCopies"]
second = post("/api/loans/issue", {"bookId": gid, "memberId": 6})
lid2 = max(x["id"] for x in get("/api/loans").json())
l2 = get(f"/api/loans/{lid2}").json()
res["E3_rejection"] = {"first_status": first.status_code, "copies_after_first": copies_mid, "second_status": second.status_code,
                       "second_message": second.json().get("message"), "loan_state": l2["status"], "failure_reason": l2["failureReason"],
                       "copies_after_second": book(gid)["availableCopies"], "events": [e["type"] for e in get(f"/api/loans/{lid2}/events").json()]}
post(f"/api/loans/{first.json()['id']}/return")
print(res["E3_rejection"])

# ------------------------------------------------------------ E4 idempotent stock operation
print("E4 idempotency key on book-service")
bid = 900
c0 = book(bid)["availableCopies"]
for _ in range(3):
    requests.put(f"{BOOK_DIRECT}/api/books/{bid}/borrow", headers={"Idempotency-Key": "experiment-key-1"})
c1 = book(bid)["availableCopies"]
requests.put(f"{BOOK_DIRECT}/api/books/{bid}/return", headers={"Idempotency-Key": "experiment-key-1-return"})
res["E4_idempotency"] = {"copies_before": c0, "calls_with_same_key": 3, "copies_after": c1, "decrement": c0 - c1}
print(res["E4_idempotency"])

# ------------------------------------------------------------ E5 duplicate event delivery
print("E5 duplicate delivery")
n0 = len(get("/api/notifications").json())
ids = psql("lendingdb", "lendinguser", "lending123", "select id from outbox_event order by created_at desc limit 3").split()
psql("lendingdb", "lendinguser", "lending123", "update outbox_event set sent_at = null where id in (select id from outbox_event order by created_at desc limit 3)")
wait(lambda: int(psql("lendingdb", "lendinguser", "lending123", "select count(*) from outbox_event where sent_at is null")) == 0, 30)
time.sleep(2)
n1 = len(get("/api/notifications").json())
res["E5_duplicates"] = {"events_resent": len(ids), "notifications_before": n0, "notifications_after": n1}
print(res["E5_duplicates"])

# ------------------------------------------------------------ E7 business rejections must not open the circuit breaker
print("E7 rejections vs circuit breaker")
xid = 15   # one copy only, not used by the demo data
ok = post("/api/loans/issue", {"bookId": xid, "memberId": 8})
rej = [post("/api/loans/issue", {"bookId": xid, "memberId": 9}).status_code for _ in range(12)]
after_ok = post("/api/loans/issue", {"bookId": 960, "memberId": 9})
res["E7_rejections"] = {"first_status": ok.status_code, "rejected_statuses": sorted(set(rej)), "rejected_count": len(rej),
                        "next_valid_request_status": after_ok.status_code}
print(res["E7_rejections"])

# ------------------------------------------------------------ E6 distributed trace of one issue request
print("E6 tracing")
r = post("/api/loans/issue", {"bookId": 950, "memberId": 7})
time.sleep(4)
traces = requests.get("http://localhost:9411/api/v2/traces", params={"serviceName": "api-gateway", "limit": 30}).json()
best = None
for t in traces:
    svcs = {s.get("localEndpoint", {}).get("serviceName") for s in t}
    if {"api-gateway", "lending-service", "member-service", "book-service"} <= svcs and any("issue" in (s.get("name", "") + s.get("tags", {}).get("http.url", "") + s.get("tags", {}).get("uri", "")) for s in t):
        best = t
        break
if best:
    res["E6_trace"] = {"trace_id": best[0]["traceId"], "spans": len(best), "services": sorted({s["localEndpoint"]["serviceName"] for s in best if "localEndpoint" in s}),
                       "duration_ms": (max(s["timestamp"] + s.get("duration", 0) for s in best) - min(s["timestamp"] for s in best)) / 1000.0}
else:
    res["E6_trace"] = {"found": False, "traces_seen": len(traces)}
print(res["E6_trace"])

json.dump(res, open(OUT, "w"), indent=1)
print("saved", OUT)
