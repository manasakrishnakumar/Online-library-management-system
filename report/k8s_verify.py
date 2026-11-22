"""Applies k8s/library.yaml to the current kubectl context from a clean namespace and records what happened in report/results/k8s_run.json.
   python report/k8s_verify.py        (minikube must be running and the images loaded)"""
import json
import os
import subprocess
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "report", "results", "k8s_run.json")


def sh(*args, check=False):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout


def pods():
    d = json.loads(sh("kubectl", "get", "pods", "-n", "library", "-o", "json") or "{}")
    return d.get("items", [])


def ready(p):
    cs = p["status"].get("containerStatuses") or []
    return bool(cs) and all(c["ready"] for c in cs) and p["status"]["phase"] == "Running"


print("deleting the old namespace ...")
sh("kubectl", "delete", "namespace", "library", "--ignore-not-found", "--wait=true", "--timeout=180s")
t0 = time.time()
applied = sh("kubectl", "apply", "-f", "k8s/library.yaml")
objects = applied.count(" created")
print("applied", objects, "objects")
expected = 14 + 2        # 14 deployments, book and member run two replicas each
deadline = t0 + 900
while time.time() < deadline:
    items = pods()
    if len(items) >= expected and all(ready(p) for p in items):
        break
    time.sleep(5)
seconds = time.time() - t0
items = pods()
groups = {}
for p in items:
    app = p["metadata"]["labels"].get("app", p["metadata"]["name"])
    cs = p["status"].get("containerStatuses") or [{"restartCount": 0, "ready": False}]
    groups.setdefault(app, []).append((("1/1" if cs[0]["ready"] else "0/1"), cs[0]["restartCount"]))
rows = []
for app in sorted(groups):
    g = groups[app]
    name = app + (f" ({len(g)} replicas)" if len(g) > 1 else "")
    rows.append({"name": name, "ready": " and ".join(x[0] for x in g), "restarts": " and ".join(str(x[1]) for x in g)})
total_restarts = sum(x[1] for g in groups.values() for x in g)
print("pods ready:", all(ready(p) for p in items), "in", round(seconds), "s; restarts:", total_restarts)

# ------------------------------------------------ port-forwards for the checks
pf = [subprocess.Popen(["kubectl", "port-forward", "-n", "library", f"svc/{svc}", f"{lp}:{rp}"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      for svc, lp, rp in (("frontend", 13000, 80), ("prometheus", 19090, 9090), ("grafana", 13001, 3000))]
time.sleep(6)
res = {"pod_count": len(items), "objects": objects, "seconds_to_ready": seconds, "pods": rows, "total_restarts": total_restarts, "all_ready": all(ready(p) for p in items)}
try:
    base = "http://localhost:13000"
    token = None
    for _ in range(90):                       # the demo data is loaded by the lending service shortly after start
        try:
            token = requests.post(base + "/api/auth/login", json={"username": "librarian", "password": "librarian123"}, timeout=8).json().get("token")
            h = {"Authorization": "Bearer " + token}
            if token and len(requests.get(base + "/api/fines", headers=h, timeout=8).json()) >= 2:
                break
        except Exception:
            pass
        time.sleep(5)
    h = {"Authorization": "Bearer " + token}
    stats = requests.get(base + "/api/books/stats", headers=h, timeout=15).json()
    res["checks"] = {
        "login": bool(token),
        "books": stats["titles"],
        "loans": len(requests.get(base + "/api/loans", headers=h, timeout=10).json()),
        "fines": len(requests.get(base + "/api/fines", headers=h, timeout=10).json()),
        "no_token_status": requests.get(base + "/api/books/stats", timeout=10).status_code,
    }
    issued = requests.post(base + "/api/loans/issue", headers=h, json={"bookId": 2100, "memberId": 3}, timeout=30)
    res["checks"]["issue_status"] = issued.status_code
    if issued.ok:
        res["checks"]["return_status"] = requests.post(f"{base}/api/loans/{issued.json()['id']}/return", headers=h, timeout=30).status_code
    time.sleep(20)                            # let Prometheus scrape a few times
    tg = requests.get("http://localhost:19090/api/v1/targets", timeout=15).json()["data"]["activeTargets"]
    res["prom_total"], res["prom_up"] = len(tg), sum(1 for t in tg if t["health"] == "up")
    s = requests.get("http://localhost:13001/api/search?query=Online", timeout=15).json()
    res["grafana_dashboard"] = any(x.get("uid") == "library-overview" for x in s)
except Exception as e:                        # keep what was measured, report the failure
    res["error"] = repr(e)
finally:
    for p in pf:
        p.terminate()
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "pods"}, indent=1))
