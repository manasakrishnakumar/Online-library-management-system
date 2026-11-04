"""Draws every figure of the report from report/results/*.json and the real dataset.  python report/make_figs.py"""
import csv
import json
import os
import re
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "assets")
GOODBOOKS = os.environ.get("GOODBOOKS_CSV", "C:/Users/MANASA~1/AppData/Local/Temp/gb10k/books.csv")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({"font.family": "serif", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 150})
BLUE, ORANGE, GREEN, RED, GREY = "#2f5bea", "#e8833a", "#2a9d6f", "#c8442f", "#8a93a6"


def J(n):
    return json.load(open(os.path.join(RES, n), encoding="utf-8"))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- dataset
def dataset_figs():
    rows = list(csv.DictReader(open(GOODBOOKS, encoding="utf-8", newline="")))
    years = []
    for r in rows:
        try:
            years.append(int(float(r["original_publication_year"])))
        except ValueError:
            pass
    ratings = [float(r["average_rating"]) for r in rows]
    counts = [int(r["ratings_count"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.hist([y for y in years if y >= 1900], bins=range(1900, 2021, 5), color=BLUE, edgecolor="white")
    ax.set_xlabel("Original publication year (1900-2020, 5-year bins)")
    ax.set_ylabel("Number of books")
    save(fig, "ds_years.png")

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.hist(ratings, bins=30, color=GREEN, edgecolor="white")
    ax.axvline(statistics.mean(ratings), color=RED, ls="--", label=f"mean {statistics.mean(ratings):.2f}")
    ax.set_xlabel("Average Goodreads rating")
    ax.set_ylabel("Number of books")
    ax.legend()
    save(fig, "ds_ratings.png")

    auth = {}
    for r in rows:
        a = r["authors"].split(",")[0].strip()
        auth[a] = auth.get(a, 0) + 1
    top = sorted(auth.items(), key=lambda x: -x[1])[:10][::-1]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.barh([a for a, _ in top], [c for _, c in top], color=ORANGE)
    ax.set_xlabel("Titles in the catalogue")
    for i, (_, c) in enumerate(top):
        ax.text(c + 0.3, i, str(c), va="center", fontsize=8)
    save(fig, "ds_authors.png")

    cp = {}
    for line in open(os.path.join(ROOT, "book-service/src/main/resources/books.csv"), encoding="utf-8").read().split("\n")[1:]:
        if line.strip():
            c = int(line.split("|")[4])
            cp[c] = cp.get(c, 0) + 1
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.bar([str(k) for k in sorted(cp)], [cp[k] for k in sorted(cp)], color=BLUE)
    ax.set_xlabel("Copies per title")
    ax.set_ylabel("Number of titles")
    for i, k in enumerate(sorted(cp)):
        ax.text(i, cp[k] + 20, str(cp[k]), ha="center", fontsize=8)
    save(fig, "ds_copies.png")
    return {"n": len(rows), "mean_rating": statistics.mean(ratings), "median_ratings_count": statistics.median(counts),
            "year_min": min(years), "year_max": max(years), "copies": cp}


# ---------------------------------------------------------------- performance
def perf_figs():
    lat, base = J("latency.json"), J("latency_h2_baseline.json")
    names = [k for k in lat if k.startswith("GET /api") and "10,000" not in k]
    short = lambda n: n.replace("GET ", "").replace("/api/", "")
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    x = range(len(names))
    ax.bar([i - 0.2 for i in x], [lat[n]["p50"] for n in names], 0.4, label="median (p50)", color=BLUE)
    ax.bar([i + 0.2 for i in x], [lat[n]["p95"] for n in names], 0.4, label="p95", color=ORANGE)
    ax.set_xticks(list(x))
    ax.set_xticklabels([short(n) for n in names], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Latency through the gateway (ms)")
    ax.legend()
    save(fig, "perf_latency.png")

    # baseline (H2, no login, no tracing) versus final system (PostgreSQL, JWT check, tracing at 100 percent)
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.bar([i - 0.2 for i in x], [base[n]["p50"] for n in names], 0.4, label="first version: H2, no login, no tracing", color=GREY)
    ax.bar([i + 0.2 for i in x], [lat[n]["p50"] for n in names], 0.4, label="final: PostgreSQL, JWT, tracing", color=BLUE)
    ax.set_xticks(list(x))
    ax.set_xticklabels([short(n) for n in names], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Median latency (ms)")
    ax.legend(fontsize=8)
    save(fig, "perf_compare.png")

    d, g = lat["direct GET /api/members/1 (:8082)"], lat["gateway GET /api/members/1"]
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.bar(["direct to\nmember-service", "via API gateway"], [d["p50"], g["p50"]], color=[GREEN, BLUE], width=0.5)
    ax.bar(["direct to\nmember-service", "via API gateway"], [d["p95"] - d["p50"], g["p95"] - g["p50"]], bottom=[d["p50"], g["p50"]],
           color=["#9bd6bd", "#9fb3f5"], width=0.5)
    ax.set_ylabel("ms (solid = p50, light = up to p95)")
    for i, v in enumerate((d["p50"], g["p50"])):
        ax.text(i, v / 2, f"{v:.1f}", ha="center", color="white", fontsize=9)
    save(fig, "perf_gateway.png")

    t, tb = J("throughput.json"), J("throughput_h2_baseline.json")
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.plot([r["workers"] for r in tb], [r["rps"] for r in tb], "s--", color=GREY, label="first version")
    ax.plot([r["workers"] for r in t], [r["rps"] for r in t], "o-", color=BLUE, label="final")
    for r in t:
        ax.annotate(f'{r["rps"]:.0f}', (r["workers"], r["rps"]), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8, color=BLUE)
    ax.set_xscale("log", base=2)
    ax.set_xticks([r["workers"] for r in t])
    ax.set_xticklabels([str(r["workers"]) for r in t])
    ax.set_xlabel("Concurrent client threads")
    ax.set_ylabel("Requests per second")
    ax.set_ylim(0, max(r["rps"] for r in tb + t) * 1.2)
    ax.legend()
    save(fig, "perf_throughput.png")

    c = J("cycles.json")
    fine = [x["fine_visible_ms"] for x in c]
    note = [x["notification_visible_ms"] for x in c]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.hist(fine, bins=12, alpha=0.8, color=ORANGE, label=f"fine created (mean {statistics.mean(fine):.0f} ms)")
    ax.hist(note, bins=12, alpha=0.7, color=BLUE, label=f"notification stored (mean {statistics.mean(note):.0f} ms)")
    ax.set_xlabel("Milliseconds after the return call completed (outbox relay every 300 ms)")
    ax.set_ylabel("Number of loans (30 cycles)")
    ax.legend()
    save(fig, "perf_events.png")

    before, after = J("outage_before.json"), J("outage.json")
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.6), sharey=True)
    for ax, o, title in ((axs[0], before, "first version: 503 after long hangs"), (axs[1], after, "final: 202 accepted, saga finishes later")):
        seq = o["during_outage"] + o["recovery"]
        ok = [s for s in seq if s["status"] == 201]
        ax.scatter([s["t"] for s in seq if s["status"] not in (201,)], [s["ms"] for s in seq if s["status"] not in (201,)], s=10,
                   color=RED if o is before else ORANGE, label="503" if o is before else "202 pending")
        if ok:
            ax.scatter([s["t"] for s in ok], [s["ms"] for s in ok], s=28, color=GREEN, label="201 success")
        ax.axvline(o["restart_at_s"], color=GREY, ls="--")
        ax.set_yscale("log")
        ax.set_xlabel("Seconds since book-service was stopped")
        ax.set_title(title, fontsize=8.5)
        ax.legend(loc="upper right", fontsize=7)
    axs[0].set_ylabel("Response time (ms, log scale)")
    save(fig, "perf_outage.png")

    e = J("experiments.json")
    items = [("accepted while\nbook-service is down", e["E2_saga_outage"]["seconds_to_accept"]),
             ("saga completes after\nbook-service restart", e["E2_saga_outage"]["seconds_until_issued_after_book_service_restart"]),
             ("outbox drained after\nRabbitMQ restart", e["E1_outbox"]["seconds_until_outbox_empty_after_broker_restart"])]
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    ax.barh([a for a, _ in items][::-1], [b for _, b in items][::-1], color=[ORANGE, BLUE, GREEN][::-1])
    for i, (_, v) in enumerate(items[::-1]):
        ax.text(v + 0.3, i, f"{v:.1f} s", va="center", fontsize=9)
    ax.set_xlabel("Seconds")
    ax.set_xlim(0, max(v for _, v in items) * 1.2)
    save(fig, "exp_times.png")


# ---------------------------------------------------------------- system facts
def system_figs():
    st = {}
    for line in open(os.path.join(RES, "startup.txt")):
        m = re.match(r"([\w-]+)\|Started \w+ in ([\d.]+) seconds", line)
        if m:
            st[m.group(1)] = float(m.group(2))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ks = sorted(st, key=st.get)
    ax.barh(ks, [st[k] for k in ks], color=BLUE)
    for i, k in enumerate(ks):
        ax.text(st[k] + 0.5, i, f"{st[k]:.1f}", va="center", fontsize=8)
    ax.set_xlabel("Spring Boot start-up time (s), all services starting together")
    save(fig, "sys_startup.png")

    mem = {}
    for line in open(os.path.join(RES, "docker_stats_idle.txt")):
        n, m, _ = line.strip().split("|")
        v = float(re.match(r"([\d.]+)", m).group(1))
        mem[n.replace("librarymanagement-", "").replace("-1", "")] = v
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ks = sorted(mem, key=mem.get)
    ax.barh(ks, [mem[k] for k in ks], color=GREEN)
    for i, k in enumerate(ks):
        ax.text(mem[k] + 5, i, f"{mem[k]:.0f}", va="center", fontsize=8)
    ax.set_xlabel("Memory used by the container when idle (MiB, docker stats)")
    save(fig, "sys_memory.png")

    loc = {}
    for m in ("config-server", "discovery-server", "api-gateway", "book-service", "member-service", "lending-service", "fine-service", "notification-service"):
        n = 0
        for dp, _, fs in os.walk(os.path.join(ROOT, m, "src", "main")):
            for f in fs:
                if f.endswith((".java", ".yml")):
                    n += len(open(os.path.join(dp, f), encoding="utf-8").read().split("\n"))
        loc[m] = n
    loc["frontend"] = sum(len(open(os.path.join(ROOT, "frontend/public", f), encoding="utf-8").read().split("\n")) for f in ("index.html", "app.js", "styles.css"))
    json.dump(loc, open(os.path.join(RES, "loc.json"), "w"), indent=1)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ks = sorted(loc, key=loc.get)
    ax.barh(ks, [loc[k] for k in ks], color=ORANGE)
    for i, k in enumerate(ks):
        ax.text(loc[k] + 4, i, str(loc[k]), va="center", fontsize=8)
    ax.set_xlabel("Lines of Java, YAML, HTML, JS and CSS per module")
    save(fig, "sys_loc.png")


# ---------------------------------------------------------------- diagrams
def box(ax, x, y, w, h, text, fc="#e8eefc", ec=BLUE, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")


def arrow(ax, a, b, text="", color="#444", style="-|>", ls="-", off=(0, 0.08)):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=10, color=color, lw=1.1, ls=ls))
    if text:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], text, fontsize=7, ha="center", color=color)


def architecture():
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8.6)
    ax.axis("off")
    box(ax, 3.7, 7.8, 2.6, 0.6, "Browser", "#fff", GREY)
    box(ax, 3.4, 6.85, 3.2, 0.65, "Frontend (nginx) :3000", "#e7f6ef", GREEN)
    box(ax, 0.1, 5.55, 9.8, 0.75, "API Gateway :8080   |   login (JWT)  -  role rules  -  routing  -  CORS", "#e8eefc", BLUE, bold=True, fs=9)
    box(ax, 0.1, 6.85, 2.5, 0.65, "Config Server :8888", "#fff4e6", ORANGE)
    box(ax, 7.4, 6.85, 2.5, 0.65, "Eureka Registry :8761", "#fff4e6", ORANGE)
    arrow(ax, (5, 7.8), (5, 7.5)); arrow(ax, (5, 6.85), (5, 6.3), "/api + Bearer token", off=(1.1, 0))
    svc = [("Book\n:8081\nbookdb", 0.1), ("Member\n:8082\nmemberdb", 2.1), ("Lending\n:8083\nlendingdb\n+ outbox", 4.1), ("Fine\n:8084\nfinedb", 6.1), ("Notification\n:8085\nnotificationdb", 8.1)]
    for t, x in svc:
        box(ax, x, 3.5, 1.8, 1.3, t, "#e8eefc", BLUE, fs=8)
        arrow(ax, (x + 0.9, 5.55), (x + 0.9, 4.8), color=BLUE)
    for xt in (1.0, 3.0):
        ax.add_patch(FancyArrowPatch((4.6, 3.5), (xt, 3.5), arrowstyle="-|>", mutation_scale=10, color=GREEN, lw=1.3, connectionstyle="arc3,rad=0.3"))
    ax.text(2.8, 2.95, "saga steps over REST (Feign)\n+ circuit breaker + idempotency key", fontsize=7.5, color=GREEN, ha="center")
    box(ax, 2.2, 1.45, 5.6, 0.6, "RabbitMQ topic exchange  library.events", "#fbe9e6", RED, fs=8.5)
    arrow(ax, (4.8, 3.5), (4.5, 2.05), "", RED, ls="--"); arrow(ax, (6.9, 3.5), (6.2, 2.05), "", RED, ls="--"); arrow(ax, (9.0, 3.5), (7.6, 2.05), "", RED, ls="--")
    ax.text(3.45, 2.5, "outbox relay:\nloan.issued / loan.returned", fontsize=7.2, color=RED, ha="center")
    ax.text(7.7, 2.55, "fine.assessed", fontsize=7.2, color=RED, ha="center")
    box(ax, 0.1, 0.1, 4.4, 0.7, "PostgreSQL 16: five databases, five logins", "#eef2f7", GREY, fs=8)
    box(ax, 5.0, 0.1, 4.9, 0.7, "Zipkin (traces)  |  Prometheus -> Grafana (metrics)", "#eef7ee", GREEN, fs=8)
    save(fig, "diag_architecture.png")


def saga():
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    steps = [(0.1, "1  Save loan\nPENDING\n(lending DB)", "#e8eefc", BLUE), (2.6, "2  Reserve a copy\nbook-service\nkey loan-{id}-borrow", "#e8eefc", BLUE),
             (5.1, "3  Mark ISSUED +\nwrite outbox row\n(one transaction)", "#e8eefc", BLUE), (7.6, "4  Relay to\nRabbitMQ\n(every 300 ms)", "#fbe9e6", RED)]
    for x, t, fc, ec in steps:
        box(ax, x, 3.9, 2.3, 1.3, t, fc, ec, fs=8)
    for i in range(3):
        arrow(ax, (steps[i][0] + 2.3, 4.55), (steps[i + 1][0], 4.55))
    box(ax, 2.6, 1.9, 2.3, 1.0, "409 rejected\nloan -> FAILED\n(nothing to undo)", "#fdecea", RED, fs=8)
    box(ax, 5.1, 1.9, 2.3, 1.0, "step 3 fails:\ncompensate, return copy\nkey loan-{id}-compensate", "#fff4e6", ORANGE, fs=8)
    box(ax, 2.6, 0.2, 2.3, 1.0, "503 / timeout:\nloan stays PENDING\n202 Accepted", "#fff4e6", ORANGE, fs=8)
    box(ax, 5.1, 0.2, 2.3, 1.0, "Recovery job (5 s):\nreplays steps 2 and 3\nsame keys, safe to repeat", "#e7f6ef", GREEN, fs=8)
    arrow(ax, (3.75, 3.9), (3.75, 2.9), "", RED)
    arrow(ax, (6.25, 3.9), (6.25, 2.9), "", ORANGE)
    arrow(ax, (2.35, 3.9), (2.35, 0.7), "", ORANGE, style="-", ls="--")
    arrow(ax, (2.35, 0.7), (2.6, 0.7), "", ORANGE)
    arrow(ax, (4.9, 0.7), (5.1, 0.7), "", GREEN)
    ax.text(0.2, 2.6, "Failure paths\nof step 2 and 3", fontsize=8.5, fontweight="bold")
    save(fig, "diag_saga.png")


def sequence():
    fig, ax = plt.subplots(figsize=(6.8, 4.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8.4)
    ax.axis("off")
    actors = [("Librarian\n(UI)", 0.8), ("Gateway", 2.3), ("Lending", 3.9), ("Member", 5.4), ("Book", 6.6), ("RabbitMQ", 7.9), ("Fine /\nNotification", 9.2)]
    for n, x in actors:
        box(ax, x - 0.55, 7.6, 1.1, 0.6, n, "#e8eefc", BLUE, fs=7.5)
        ax.plot([x, x], [0.3, 7.6], color=GREY, lw=0.8, ls=":")
    X = dict((n.split("\n")[0], x) for n, x in actors)
    msgs = [("Librarian", "Gateway", 7.1, "POST /api/loans/issue + JWT", BLUE), ("Gateway", "Lending", 6.6, "verify token, role, route", BLUE),
            ("Lending", "Lending", 6.1, "save Loan PENDING", "#444"),
            ("Lending", "Member", 5.6, "GET /api/members/{id}", BLUE), ("Member", "Lending", 5.2, "active = true", GREEN),
            ("Lending", "Book", 4.7, "PUT .../borrow (Idempotency-Key)", BLUE), ("Book", "Lending", 4.3, "200 OK, copies minus 1", GREEN),
            ("Lending", "Lending", 3.8, "ISSUED + outbox row (one tx)", "#444"), ("Lending", "Librarian", 3.3, "201 Loan (due date)", GREEN),
            ("Lending", "RabbitMQ", 2.8, "relay loan.issued", RED), ("RabbitMQ", "Fine /", 2.3, "deliver to subscribers", RED),
            ("Fine /", "Fine /", 1.8, "store notification (dedupe)", "#444")]
    for a, b, y, t, c in msgs:
        xa, xb = X[a], X[b]
        if a == b:
            ax.annotate("", xy=(xa + 0.5, y - 0.2), xytext=(xa, y), arrowprops=dict(arrowstyle="-|>", color=c, lw=1, connectionstyle="arc3,rad=-0.6"))
            ax.text(xa + 0.55, y - 0.05, t, fontsize=7, color=c)
        else:
            arrow(ax, (xa, y), (xb, y), color=c, ls="--" if c == GREEN else "-")
            ax.text((xa + xb) / 2, y + 0.08, t, fontsize=7, ha="center", color=c)
    save(fig, "diag_sequence.png")


def datamodel():
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.7)
    ax.axis("off")
    ents = [("bookdb", 0.05, 1.8, "Book\nid, title, author,\nisbn, category,\ntotalCopies,\navailableCopies\n\nStockOp\nopKey (primary key),\nbookId"),
            ("memberdb", 2.0, 1.7, "Member\nid, name, email,\nactive"),
            ("lendingdb", 3.9, 2.3, "Loan\nid, bookId, bookTitle,\nmemberId, memberName,\nissueDate, dueDate,\nreturnDate, status,\nfailureReason, createdAt\n\nLoanEvent\nid, loanId, type,\noccurredAt, details\n\nOutboxEvent\nid, routingKey, payload,\ncreatedAt, sentAt"),
            ("finedb", 6.4, 1.7, "Fine\nid, loanId (unique),\nmemberId, daysOverdue,\namount, paid"),
            ("notificationdb", 8.3, 1.65, "Notification\nid, memberId, type,\nmessage, eventId\n(unique), createdAt")]
    for s, x, w, t in ents:
        ax.text(x + w / 2, 4.4, s, ha="center", fontsize=8, fontweight="bold")
        box(ax, x, 0.95, w, 3.3, t, "#e8eefc", BLUE, fs=7)
    ax.text(5, 0.4, "No foreign keys between databases: only copied IDs and small snapshots (bookTitle, memberName).\nEach database has its own PostgreSQL login; other logins get 'permission denied'.", ha="center", fontsize=7.8, style="italic")
    save(fig, "diag_data.png")


def deployment():
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.2, 0.3), 9.6, 5.0, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#fafafa", ec=GREY, lw=1.2, ls="--"))
    ax.text(0.45, 5.0, "Docker Compose network (one host, 14 containers)", fontsize=9, fontweight="bold")
    names = [("frontend", GREEN), ("api-gateway", BLUE), ("config-server", ORANGE), ("discovery-server", ORANGE), ("postgres", GREY),
             ("book-service", BLUE), ("member-service", BLUE), ("lending-service", BLUE), ("fine-service", BLUE), ("notification-service", BLUE),
             ("rabbitmq", RED), ("zipkin", GREEN), ("prometheus", GREEN), ("grafana", GREEN)]
    for i, (n, c) in enumerate(names):
        r, col = divmod(i, 5)
        box(ax, 0.5 + col * 1.85, 3.5 - r * 1.35, 1.65, 0.85, n.replace("-", "-\n", 1) if len(n) > 12 else n, "#ffffff", c, fs=7.5)
    ax.text(5, 0.6, "Images from one multi-stage Dockerfile (maven:3.9 -> eclipse-temurin:17-jre); healthchecks order start-up; volume pgdata keeps the data", ha="center", fontsize=7.2, style="italic")
    save(fig, "diag_deploy.png")


if __name__ == "__main__":
    info = dataset_figs()
    json.dump(info, open(os.path.join(RES, "dataset_info.json"), "w"), indent=1)
    perf_figs()
    system_figs()
    architecture()
    sequence()
    saga()
    datamodel()
    deployment()
    print(info)
