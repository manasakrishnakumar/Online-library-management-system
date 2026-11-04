"""Loads every measured result once, so the report text and tables never contain hand-typed numbers."""
import csv
import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(HERE, "results")
GOODBOOKS = os.environ.get("GOODBOOKS_CSV", "C:/Users/MANASA~1/AppData/Local/Temp/gb10k/books.csv")


def J(name):
    return json.load(open(os.path.join(RES, name), encoding="utf-8"))


lat = J("latency.json")
lat0 = J("latency_h2_baseline.json")
thr = J("throughput.json")
thr0 = J("throughput_h2_baseline.json")
cyc = J("cycles.json")
cyc0 = J("cycles_h2_baseline.json")
out_after = J("outage.json")
out_before = J("outage_before.json")
exp = J("experiments.json")
loc = J("loc.json")
ds = J("dataset_info.json")
COLD = J("coldstart.json")

HW = {"cpu": "AMD Ryzen 7 260 with Radeon 780M Graphics", "cores": 8, "threads": 16, "ram": "23.3 GB", "os": "Windows 11 Home (build 26300)",
      "docker": "Docker Engine 29.9.2, Compose 5.6.1", "docker_ram": "11.33 GiB visible to the Docker VM"}

startup = {}
for line in open(os.path.join(RES, "startup.txt"), encoding="utf-8"):
    m = re.match(r"([\w-]+)\|Started \w+ in ([\d.]+) seconds", line)
    if m:
        startup[m.group(1)] = float(m.group(2))

memory = {}
for line in open(os.path.join(RES, "docker_stats_idle.txt"), encoding="utf-8"):
    n, m, _ = line.strip().split("|")
    memory[n.replace("librarymanagement-", "").replace("-1", "")] = float(re.match(r"([\d.]+)", m).group(1))

images = {}
for line in open(os.path.join(RES, "image_sizes.txt"), encoding="utf-8"):
    n, s = line.strip().split("|")
    images[n.replace("librarymanagement-", "")] = s


def stat(v):
    return {"mean": statistics.mean(v), "min": min(v), "max": max(v), "median": statistics.median(v)}


fine_ms = [x["fine_visible_ms"] for x in cyc]
note_ms = [x["notification_visible_ms"] for x in cyc]
issue_ms = [x["issue_ms"] for x in cyc]
return_ms = [x["return_ms"] for x in cyc]
fine_ms0 = [x["fine_visible_ms"] for x in cyc0]
note_ms0 = [x["notification_visible_ms"] for x in cyc0]
issue0 = [x["issue_ms"] for x in cyc0]
return0 = [x["return_ms"] for x in cyc0]

# dataset facts straight from the Goodbooks-10k file
rows = list(csv.DictReader(open(GOODBOOKS, encoding="utf-8", newline="")))
years = []
for r in rows:
    try:
        years.append(int(float(r["original_publication_year"])))
    except ValueError:
        pass
ratings = [float(r["average_rating"]) for r in rows]
langs = {}
for r in rows:
    k = r["language_code"] or "unknown"
    langs[k] = langs.get(k, 0) + 1
authors = {}
for r in rows:
    a = r["authors"].split(",")[0].strip()
    authors[a] = authors.get(a, 0) + 1
DS = {"n": len(rows), "years_known": len(years), "years_missing": len(rows) - len(years), "mean_rating": statistics.mean(ratings),
      "min_rating": min(ratings), "max_rating": max(ratings), "languages": len(langs), "eng_share": sum(v for k, v in langs.items() if k.startswith("en")) / len(rows),
      "distinct_authors": len(authors), "top_authors": sorted(authors.items(), key=lambda x: -x[1])[:5],
      "median_ratings_count": statistics.median(int(r["ratings_count"]) for r in rows)}
csvrows = [l.split("|") for l in open(os.path.join(ROOT, "book-service/src/main/resources/books.csv"), encoding="utf-8").read().split("\n")[1:] if l.strip()]
DS["total_copies"] = sum(int(r[4]) for r in csvrows)
DS["gb_ids"] = sum(1 for r in csvrows if r[2].startswith("GB-"))

# tests: parse the test sources so the table lists the real test names
TESTS = []
for mod, path in (("api-gateway", "api-gateway/src/test/java/com/library/gateway"), ("book-service", "book-service/src/test/java/com/library/book"),
                  ("lending-service", "lending-service/src/test/java/com/library/lending"), ("fine-service", "fine-service/src/test/java/com/library/fine")):
    d = os.path.join(ROOT, path)
    for f in sorted(os.listdir(d)):
        src = open(os.path.join(d, f), encoding="utf-8").read()
        for m in re.finditer(r"@Test\s+(?:@\w+(?:\([^)]*\))?\s+)*void (\w+)\(", src):
            name = re.sub(r"([A-Z])", r" \1", m.group(1)).lower()
            TESTS.append((mod, f.replace(".java", ""), name))

# OpenAPI operations
OPS = []
for svc in ("book", "member", "lending", "fine", "notification"):
    spec = json.load(open(os.path.join(ROOT, "docs", "openapi", f"{svc}-service.json"), encoding="utf-8"))
    for p, methods in sorted(spec["paths"].items()):
        for m in sorted(methods):
            OPS.append((f"{svc}-service", m.upper(), p, methods[m].get("operationId", "")))

COMMITS = 0


def f(v, n=1):
    return f"{v:.{n}f}"
