"""Measures the running Online Library Management System and writes report/results/*.json.

Needs the stack running (docker compose up). Run:  python report/measure.py
Everything in the report's performance chapter comes from this script's output.
"""
import json
import os
import statistics
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

GW = "http://localhost:8080"          # API gateway
UI = "http://localhost:3000"          # frontend (nginx -> gateway)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sess():
    s = requests.Session()
    r = requests.post(GW + "/api/auth/login", json={"username": "librarian", "password": "librarian123"}, timeout=30)
    s.headers["Authorization"] = "Bearer " + r.json()["token"]
    return s


def save(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


def timed(session, method, url, **kw):
    t = time.perf_counter()
    r = session.request(method, url, timeout=30, **kw)
    return (time.perf_counter() - t) * 1000, r


def stats(v):
    return {"n": len(v), "mean": statistics.mean(v), "p50": pct(v, 50), "p95": pct(v, 95), "p99": pct(v, 99), "max": max(v)}


# ---------------------------------------------------------------- A. latency per endpoint
def latency():
    s = sess()
    eps = [("GET /api/books/1", GW + "/api/books/1"),
           ("GET /api/books/search?q=potter", GW + "/api/books/search?q=potter"),
           ("GET /api/members", GW + "/api/members"),
           ("GET /api/loans", GW + "/api/loans"),
           ("GET /api/fines", GW + "/api/fines"),
           ("GET /api/notifications", GW + "/api/notifications"),
           ("GET /api/books (10,000 rows)", GW + "/api/books")]
    res = {}
    for name, url in eps:
        for _ in range(10):                       # warm-up, not counted
            s.get(url, timeout=30)
        n = 30 if "10,000" in name else 200
        res[name] = stats([timed(s, "GET", url)[0] for _ in range(n)])
        print(name, res[name]["p50"])
    # gateway overhead: same call direct to member-service and through the gateway
    direct = [timed(s, "GET", "http://localhost:8082/api/members/1")[0] for _ in range(200)]
    via = [timed(s, "GET", GW + "/api/members/1")[0] for _ in range(200)]
    res["direct GET /api/members/1 (:8082)"] = stats(direct)
    res["gateway GET /api/members/1"] = stats(via)
    save("latency.json", res)


# ---------------------------------------------------------------- B. throughput vs concurrency
def throughput():
    out = []
    for workers in (1, 2, 4, 8, 16, 32):
        stop = time.time() + 6
        counts, errs = [0] * workers, [0] * workers

        def run(i):
            s = sess()
            while time.time() < stop:
                try:
                    r = s.get(GW + "/api/books/1", timeout=10)
                    if r.status_code == 200:
                        counts[i] += 1
                    else:
                        errs[i] += 1
                except Exception:
                    errs[i] += 1

        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(run, range(workers)))
        out.append({"workers": workers, "requests": sum(counts), "errors": sum(errs), "rps": sum(counts) / 6})
        print(out[-1])
    save("throughput.json", out)


# ---------------------------------------------------------------- C. full business cycles + event propagation
def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def cycles(n=30):
    s = sess()
    rows = []
    for i in range(n):
        book, member = 200 + i, 1 + (i % 15)
        t_issue, r = timed(s, "POST", GW + "/api/loans/issue", json={"bookId": book, "memberId": member})
        loan = r.json()
        lid = loan["id"]
        s.post(f"{GW}/api/loans/{lid}/simulate-overdue?days=20")
        t_ret0 = time.perf_counter()
        t_ret, r2 = timed(s, "POST", f"{GW}/api/loans/{lid}/return")
        # poll until fine-service has created the fine and notification-service has stored its message
        t_fine = t_note = None
        while time.perf_counter() - t_ret0 < 15 and (t_fine is None or t_note is None):
            if t_fine is None:
                f = s.get(f"{GW}/api/fines/member/{member}").json()
                if any(x["loanId"] == lid for x in f):
                    t_fine = (time.perf_counter() - t_ret0) * 1000
            if t_note is None:
                nts = s.get(f"{GW}/api/notifications/member/{member}").json()
                if any(x["type"] == "FINE_ASSESSED" and f'"{loan["bookTitle"]}"' in x["message"] for x in nts):
                    t_note = (time.perf_counter() - t_ret0) * 1000
            time.sleep(0.01)
        ev = s.get(f"{GW}/api/loans/{lid}/events").json()
        rows.append({"loan": lid, "issue_ms": t_issue, "return_ms": t_ret, "fine_visible_ms": t_fine, "notification_visible_ms": t_note,
                     "events": len(ev), "status": r2.json()["status"]})
    save("cycles.json", rows)
    print("cycles done", len(rows))


# ---------------------------------------------------------------- D. circuit breaker / outage
def outage():
    s = sess()
    subprocess.run(["docker", "compose", "stop", "book-service"], cwd=ROOT, capture_output=True)
    t0 = time.time()
    seq = []
    for i in range(24):
        ms, r = timed(s, "POST", GW + "/api/loans/issue", json={"bookId": 300 + i, "memberId": 1})
        seq.append({"t": time.time() - t0, "ms": ms, "status": r.status_code})
        time.sleep(0.5)
    t_restart = time.time() - t0
    subprocess.run(["docker", "compose", "start", "book-service"], cwd=ROOT, capture_output=True)
    rec = []
    ok_at = None
    while time.time() - t0 - t_restart < 180:
        ms, r = timed(s, "POST", GW + "/api/loans/issue", json={"bookId": 500 + len(rec), "memberId": 1})
        rec.append({"t": time.time() - t0, "ms": ms, "status": r.status_code})
        if r.status_code == 201:            # the circuit closed again and the saga completes synchronously
            ok_at = time.time() - t0
            break
        time.sleep(1)
    save("outage.json", {"during_outage": seq, "restart_at_s": t_restart, "recovery": rec, "first_success_s": ok_at})
    print("outage: first success after restart (s):", None if ok_at is None else ok_at - t_restart)


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["latency", "throughput", "cycles", "outage"]
    for w in which:
        print("==", w)
        globals()[w]()
