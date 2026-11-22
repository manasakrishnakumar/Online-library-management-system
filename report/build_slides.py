"""Builds the project presentation in the layout of the college slides (RV logo, blue Times New Roman headings, blue-header tables).

   python report/build_slides.py     ->  report/Online_Library_Management_System_Presentation.pptx

The base file is the user's existing deck; its master (logo and tagline), title photo and Thank-You slide are kept.
Set TEMPLATE_PPTX to point at it. All numbers come from report/results via data.py.
"""
import copy
import os
import re
import statistics
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data  # noqa: E402

TEMPLATE = os.environ.get("TEMPLATE_PPTX", r"C:/Users/Manasa Krishnakumar/Desktop/ALL DEKTOP/final_ppt_updated.pptx")
OUT = os.path.join(HERE, "Online_Library_Management_System_Presentation.pptx")
BLUE = RGBColor(0x00, 0x00, 0xFF)
FONT = "Times New Roman"
TITLE = "ONLINE LIBRARY MANAGEMENT SYSTEM USING MICROSERVICES ARCHITECTURE"
TEAM = ["Akanksha Rani - 1RV23IS010", "Gauri G Singh - 1RV23IS051", "Manasa Krishnakumar - 1RV23IS067"]
GUIDE = "GUIDE: Sushmitha N, Assistant Professor, Dept. of ISE, RV College of Engineering"

prs = Presentation(TEMPLATE)
layout = prs.slide_layouts[0]
SW, SH = prs.slide_width, prs.slide_height

# ---------------------------------------------------------------- facts from the measurements
lat, thr, exp, cyc = data.lat, data.thr, data.exp, data.cyc
ep = [k for k in lat if k in data.lat0 and k.startswith("GET /api") and "10,000" not in k]
E1, E2, E3, E4, E5, E6, E7 = (exp[k] for k in ("E1_outbox", "E2_saga_outage", "E3_rejection", "E4_idempotency", "E5_duplicates", "E6_trace", "E7_rejections"))
peak = max(thr, key=lambda r: r["rps"])


# ---------------------------------------------------------------- helpers
def delete_slide(index):
    lst = prs.slides._sldIdLst
    sld = lst[index]
    prs.part.drop_rel(sld.rId)
    lst.remove(sld)


def new_slide():
    s = prs.slides.add_slide(layout)
    for ph in list(s.placeholders):          # the college slides use plain text boxes, not the layout placeholders
        ph._element.getparent().remove(ph._element)
    return s


def run(par, text, size, bold=False, color=None, italic=False):
    r = par.add_run()
    r.text = text
    r.font.name, r.font.size, r.font.bold, r.font.italic = FONT, Pt(size), bold, italic
    if color is not None:
        r.font.color.rgb = color
    return r


def title(slide, text, size=32):
    tb = slide.shapes.add_textbox(Inches(1.6), Inches(0.12), SW - Inches(3.2), Inches(0.75))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run(p, text, size, bold=True, color=BLUE)
    return tb


def rich(par, text, size):
    """**bold** markers inside a line become bold runs."""
    for i, chunk in enumerate(re.split(r"\*\*", text)):
        if chunk:
            run(par, chunk, size, bold=(i % 2 == 1))


def bullets(slide, items, left, top, width, height, size=18, gap=6):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for it in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        sub = it.startswith("  ")
        p.space_after = Pt(gap)
        rich(p, ("    - " if sub else "\u2022 ") + it.strip(), size - 2 if sub else size)
    return tb


def picture(slide, path, left, top, width=None, height=None, caption=None, cap_size=11):
    pic = slide.shapes.add_picture(path, left, top, width=width, height=height)
    if caption:
        tb = slide.shapes.add_textbox(pic.left, pic.top + pic.height + Inches(0.02), pic.width, Inches(0.3))
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run(p, caption, cap_size, italic=True)
    return pic


def table(slide, header, rows, left, top, width, col_w, size=10, row_h=0.4):
    shape = slide.shapes.add_table(len(rows) + 1, len(header), left, top, width, Inches(row_h * (len(rows) + 1)))
    tbl = shape.table
    total = sum(col_w)
    for i, w in enumerate(col_w):
        tbl.columns[i].width = int(width * w / total)
    tbl.rows[0].height = Inches(0.5)
    for k in range(1, len(rows) + 1):
        tbl.rows[k].height = Inches(row_h)
    for j, h in enumerate(header):
        c = tbl.cell(0, j)
        c.text = ""
        run(c.text_frame.paragraphs[0], h, size + 1, bold=True)
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            c = tbl.cell(i, j)
            c.text = ""
            c.text_frame.word_wrap = True
            rich(c.text_frame.paragraphs[0], str(v), size)
    return tbl


def path(*p):
    return os.path.join(HERE, *p)


# ---------------------------------------------------------------- keep slide 1 (photo) and the last slide (Thank You)
n_old = len(prs.slides)
for i in range(n_old - 2, 0, -1):
    delete_slide(i)
first, thank = prs.slides[0], prs.slides[1]
from pptx.opc.packuri import PackURI  # noqa: E402
thank.part.partname = PackURI("/ppt/slides/slide999.xml")      # keep its name unique: new slides are numbered from 2

tb = [sh for sh in first.shapes if sh.has_text_frame][0]
pars = tb.text_frame.paragraphs


def set_par(par, text, size=18):
    for r in list(par.runs)[1:]:
        r._r.getparent().remove(r._r)
    if par.runs:
        par.runs[0].text = text
        par.runs[0].font.size = Pt(size)
    else:
        run(par, text, size, bold=True, color=BLUE)


set_par(pars[0], "MICROSERVICES ARCHITECTURE (IS373TA) \u2013 PROJECT PRESENTATION")
set_par(pars[2], "TITLE: " + TITLE)
set_par(pars[4], "NAME OF THE TEAM MEMBERS:")
set_par(pars[5], TEAM[0]); set_par(pars[6], TEAM[1]); set_par(pars[7], TEAM[2])
extra = pars[8]._p
extra.getparent().remove(extra)
blank = copy.deepcopy(pars[3]._p)
pars[7]._p.addnext(blank)
guide = copy.deepcopy(pars[7]._p)
blank.addnext(guide)
set_par(tb.text_frame.paragraphs[9], GUIDE, 22)
for par in tb.text_frame.paragraphs:
    for r in par.runs:
        r.font.size = Pt(18 if par.runs and par.runs[0].text.startswith(("TITLE", "MICRO")) else r.font.size.pt if r.font.size else 18)
tb.top = Inches(3.35)

# ---------------------------------------------------------------- 2 introduction
s = new_slide(); title(s, "INTRODUCTION")
bullets(s, [
    "A library looks simple: books, members, loans and fines. As **one program with one database** it becomes hard to change, deploy and scale.",
    "**Microservices** split the system into small services that are built, deployed and scaled **independently**, each owning its own data.",
    "The price: services must be **found**, calls must be **secured**, a failing neighbour must not leave **half-finished operations**, and a request must be **traceable**.",
    f"This project builds the **Online Library Management System (OLMS)**: 8 Java modules, a web UI, PostgreSQL (one database per service), RabbitMQ events, Zipkin, Prometheus and Grafana, with **{data.DS['n']:,} real books** (Goodbooks-10k).",
    "**Users:** a **member** browses books and follows own loans; a **librarian** issues and returns books and manages the catalogue and fines.",
    "**Motivation:** one failing part, such as the broker or the book service, should not stop the whole library or corrupt a loan.",
], Inches(0.7), Inches(1.0), Inches(12), Inches(5.9), size=23, gap=12)


# ---------------------------------------------------------------- 3-4 literature survey (2 slides, IEEE or Springer, 2020 onwards, checked in Crossref)
LIT = [
    ("S. Aydin and C. Cebi, \"Comparison of Choreography vs Orchestration Based Saga Patterns in Microservices,\" IEEE ICECET, 2022",
     "Compares how choreography and orchestration implement a saga; discusses rollback problems with isolated NoSQL databases", "Saga styles for distributed transactions", "Orchestrated saga in lending-service with a compensating step"),
    ("A. Megargel, C. Poskitt and V. Shankararaman, \"Microservices Orchestration vs. Choreography: A Decision Framework,\" IEEE EDOC, 2021",
     "Proposes a decision framework for choosing between orchestration and choreography", "Choice of interaction style", "Orchestration for issue-book, events for fines and notifications"),
    ("X. Zhou et al., \"Fault Analysis and Debugging of Microservice Systems: Industrial Survey, Benchmark System, and Empirical Study,\" IEEE Trans. Software Eng., 2021",
     "Industrial survey of fault analysis and debugging, a benchmark system and an empirical study of faults", "Faults in microservice systems", "Motivated the fault-injection experiments and tracing"),
    ("H. Vural and M. Koyuncu, \"Does Domain-Driven Design Lead to Finding the Optimal Modularity of a Microservice?\" IEEE Access, 2021",
     "Investigates whether domain-driven design leads to optimal microservice modularity", "Service boundaries", "Bounded contexts found by event storming"),
    ("A. Singjai, U. Zdun and O. Zimmermann, \"Practitioner Views on the Interrelation of Microservice APIs and Domain-Driven Design,\" IEEE ICSA, 2021",
     "Grey-literature study of how practitioners relate microservice APIs to domain-driven design", "API design from the domain model", "SEED(S) actions and queries published as OpenAPI"),
    ("N. Stanley S A and S. Sebastian, \"Circuit Breaker: A Resilience Mechanism for Cloud Native Architecture,\" IEEE GCITC, 2023",
     "Presents the circuit breaker as a resilience mechanism for cloud-native architectures", "Failure isolation", "Resilience4j breaker around every remote call"),
    ("K. Sivakumar, J. Sebastian and P. S. Thilagam, \"Self-Adaptive Circuit Breaker Open-State Interval for Enhancing Resiliency of Microservices,\" IEEE OCIT, 2024",
     "Proposes adapting the open-state interval of a circuit breaker to improve resiliency", "Circuit breaker tuning", "Half-open behaviour seen in experiment E7; adaptive interval is future work"),
    ("B. Li et al., \"Enjoy your observability: an industrial survey of microservice tracing and analysis,\" Empirical Software Eng. (Springer), 2022",
     "Interviews with developers and operation engineers of microservice systems from ten companies", "Tracing in practice", "Zipkin traces, trace id in every log line"),
    ("M. Usman, S. Ferlin, A. Brunstrom and J. Taheri, \"A Survey on Observability of Distributed Edge & Container-Based Microservices,\" IEEE Access, 2022",
     "Surveys observability (metrics, logs, traces) for edge and container-based microservices", "Observability techniques", "Prometheus, Grafana and Zipkin from the start"),
    ("J. Bogner, J. Fritzsch, S. Wagner and A. Zimmermann, \"Industry practices and challenges for the evolvability assurance of microservices,\" Empirical Software Eng. (Springer), 2021",
     "Interview study and grey-literature review of how industry assures the evolvability of microservices", "Maintainability of services", "Small modules, own databases, tests per module"),
]
HEAD = ["Title, Author and Year of Publication", "Key Findings", "Scope of the Work", "Use in This Project"]
for part, chunk in enumerate((LIT[:5], LIT[5:]), 1):
    s = new_slide(); title(s, f"LITERATURE SURVEY ({part}/2)", 30)
    table(s, HEAD, chunk, Inches(0.45), Inches(0.95), SW - Inches(0.9), [3.7, 3.6, 2.0, 3.1], size=12, row_h=1.0)

# ---------------------------------------------------------------- 5 problem statement and objectives
s = new_slide(); title(s, "PROBLEM STATEMENT & OBJECTIVES", 30)
bullets(s, [
    "**Problem statement:** Design and implement a library management system as microservices with their own databases, so that a librarian can issue and take back books and members can follow their own loans, while multi-service operations stay **consistent** when a service or the broker fails, access is **controlled by role**, and every request can be **traced and measured**.",
    "**Objectives**",
    "  Decompose the domain with SEED(S), domain-driven design and event storming",
    f"  Build 5 business services, gateway, registry and config server; load **{data.DS['n']:,} real books**",
    "  Secure with JWT login and role rules at the gateway",
    "  Keep data consistent without a distributed transaction: **saga, outbox, idempotency keys**",
    "  Make the system observable: traces, metrics, dashboards",
    "  Containerise (Docker Compose, Kubernetes), test, measure and report honestly",
], Inches(0.6), Inches(0.95), Inches(12.2), Inches(6.3), size=24, gap=10)

# ---------------------------------------------------------------- 6 methodology: architecture
s = new_slide(); title(s, "METHODOLOGY")
picture(s, path("assets", "diag_architecture.png"), Inches(0.4), Inches(0.95), height=Inches(6.2), caption="Architecture of the Online Library Management System", cap_size=12)
bullets(s, [
    "**Browser → nginx → API Gateway**: JWT login, role rules, routing",
    "**Eureka** finds services by name; **Config Server** shares settings",
    "**Book, Member, Lending, Fine, Notification**: one PostgreSQL database and login each",
    "**REST + circuit breaker** for questions that need an answer now",
    "**RabbitMQ events** for everything else",
    "**Zipkin, Prometheus, Grafana** observe every service",
    "**Database per service:** another service's login gets permission denied",
    "**Docker Compose and Kubernetes** run the same images",
], Inches(7.6), Inches(1.0), Inches(5.6), Inches(6.2), size=18, gap=7)

# ---------------------------------------------------------------- 7 methodology: SEED(S) and boundaries
s = new_slide(); title(s, "METHODOLOGY – SEED(S) DESIGN", 30)
bullets(s, [
    "**Actors:** Member, Librarian, Administrator",
    "**Jobs:** find a book • borrow and return • know due dates and fines • keep the catalogue correct",
    "**Interaction pattern** (sequence diagram): the issue-book request crosses gateway, lending, member and book",
    f"**Actions and queries:** {len(data.OPS)} operations, published as **OpenAPI**",
    "**Event storming:** Book Added → Loan Requested → Book Issued → Book Returned → Fine Assessed → Member Notified",
    "**Bounded contexts:** Catalogue, Membership, Lending, Fines, Notifications = 5 services",
    "**Operating model:** 3 stream-aligned teams + 1 platform team",
    "**Design document:** all SEED(S) artefacts are kept in docs/DESIGN.md",
], Inches(0.4), Inches(0.95), Inches(6.9), Inches(6.3), size=19, gap=9)
picture(s, path("assets", "diag_sequence.png"), Inches(7.4), Inches(1.0), width=Inches(5.6), caption="Sequence of issuing a book", cap_size=12)

# ---------------------------------------------------------------- 8 saga and outbox
s = new_slide(); title(s, "SAGA + TRANSACTIONAL OUTBOX", 30)
picture(s, path("assets", "diag_saga.png"), Inches(0.3), Inches(0.95), width=Inches(7.0), caption="Issue saga and its failure paths", cap_size=12)
bullets(s, [
    "Loan saved as **PENDING**, copy reserved with key **loan-{id}-borrow**",
    "**ISSUED + outbox row** in one transaction; relay sends events to RabbitMQ (at least once)",
    "**409 refused** → loan FAILED, nothing to undo",
    "**Unknown outcome** → 202 pending; recovery job replays the same keyed step",
    "**Last step fails** → compensation releases the copy",
    "Consumers ignore duplicate message ids",
    "**Idempotency keys:** a repeated reserve changes the stock only once",
    "Checked by fault-injection experiments E1 to E5",
], Inches(7.5), Inches(1.0), Inches(5.6), Inches(6.2), size=19, gap=9)

# ---------------------------------------------------------------- 9 tools and techniques
s = new_slide(); title(s, "TOOLS & TECHNIQUES")
table(s, ["Area", "Tools used"], [
    ["Services", "Java 17, Spring Boot 3.2.5, Spring Cloud 2023.0.1 (Gateway, Eureka, Config, OpenFeign), Resilience4j"],
    ["Data and events", "PostgreSQL 16 (database per service), RabbitMQ 3.13 (topic exchange), JPA"],
    ["Security", "JWT (HS256, jjwt) with librarian and member roles, BCrypt, token refresh, change password"],
    ["Front end", "HTML, JavaScript, CSS served by nginx; server-side search and paging"],
    ["Observability", "Micrometer Tracing + Zipkin, Prometheus, Grafana dashboard (business counters)"],
    ["Delivery", "Docker Compose (14 containers), Kubernetes manifests verified on minikube, GitHub Actions CI"],
    ["Testing", "JUnit 5 + Mockito (31 unit tests), scripted fault-injection experiments (13 checks)"],
    ["Dataset", "Goodbooks-10k: 10,000 real books (titles, authors, ISBNs)"],
], Inches(0.5), Inches(1.0), SW - Inches(1.0), [2.0, 9.4], size=17, row_h=0.7)

# ---------------------------------------------------------------- 10 implementation: UI
PIC_H = Inches(3.0)


def two_pictures(slide, p1, c1, p2, c2):
    a = picture(slide, p1, Inches(0.5), Inches(0.95), height=PIC_H, caption=c1, cap_size=12)
    gap = Inches(0.4)
    total = a.width + gap + (PIC_H * 16 // 9)
    b = picture(slide, p2, a.left + a.width + gap, Inches(0.95), height=PIC_H, caption=c2, cap_size=12)
    shift = (SW - (b.left + b.width - a.left)) // 2 - a.left
    for sh in slide.shapes:
        if sh.shape_type is not None or sh.has_text_frame:
            if sh.top > Inches(0.9):
                sh.left = sh.left + shift
    return a, b


s = new_slide(); title(s, "IMPLEMENTATION – WEB APPLICATION", 30)
two_pictures(s, path("shots", "dashboard.jpg"), "Librarian dashboard (live data from 4 services)", path("shots", "books.jpg"), "Book-cover grid: server-side search and paging")
bullets(s, [
    "Login page with **role-based menus** (librarian and member views)",
    "Dashboard: live counts of books, members, loans and fines from four services",
    f"Books page: **{data.DS['n']:,} titles** as cover grid or table, searched and paged on the server",
    "Librarian: issue, return, make overdue, fines, notifications",
    "Member: only own loans, fines and notifications",
    "Loan history popup, change password, automatic token refresh",
], Inches(0.6), Inches(4.55), Inches(12.2), Inches(2.9), size=18, gap=5)

# ---------------------------------------------------------------- 11 implementation: roles and screens
s = new_slide(); title(s, "IMPLEMENTATION – ROLES AND LENDING", 30)
two_pictures(s, path("shots", "lending.jpg"), "Librarian: lending page with status and actions", path("shots", "member_loans.jpg"), "Member: only own loans (enforced at the gateway)")
bullets(s, [
    "No token or bad token → **401**",
    "Wrong role or another member's data → **403**",
    "Stock endpoints (borrow, return) are internal: blocked for everybody at the gateway",
    "Lending page shows ISSUED, RETURNED and PENDING loans with actions",
    "Issue dialog searches the catalogue on the server (50 matches at most)",
    "A late return creates a fine and a notification automatically from events",
], Inches(0.6), Inches(4.55), Inches(12.2), Inches(2.9), size=18, gap=5)

# ---------------------------------------------------------------- 12 results: performance
s = new_slide(); title(s, "RESULTS & DISCUSSION – PERFORMANCE", 30)
two_pictures(s, path("assets", "perf_latency.png"), "Latency through the gateway (median and p95)", path("assets", "perf_throughput.png"), "Throughput against client threads")
peak23 = max(r["rps"] for r in data.thr23)
bullets(s, [
    f"Reads take a median of **{min(lat[k]['p50'] for k in ep):.1f}–{max(lat[k]['p50'] for k in ep):.1f} ms**, p95 below **{max(lat[k]['p95'] for k in ep):.0f} ms**",
    f"Peak **{peak['rps']:.0f} requests/s** on one laptop (idle), no failed request",
    f"A late return gives a fine in **{statistics.mean(data.fine_ms):.0f} ms** and a notification in **{statistics.mean(data.note_ms):.0f} ms** (asynchronous path)",
    f"Rerun on 23 Nov while the machine was busy: **{peak23:.0f} requests/s**, below the 300 goal, so results depend on load",
    "System and data ready about **110 s** after docker compose up",
], Inches(0.6), Inches(4.55), Inches(12.2), Inches(2.9), size=18, gap=6)

# ---------------------------------------------------------------- 13 results: fault injection (table)
s = new_slide(); title(s, "RESULTS – FAULT INJECTION", 30)
table(s, ["Fault injected", "Observed"], [
    ["RabbitMQ stopped, 5 loans issued", f"all {len(E1['http_status'])} accepted (201); {E1['outbox_pending_during_outage']} events kept in the outbox; delivered {E1['seconds_until_outbox_empty_after_broker_restart']:.0f} s after restart"],
    ["book-service stopped during an issue", f"202 pending in {E2['seconds_to_accept']:.1f} s; ISSUED {E2['seconds_until_issued_after_book_service_restart']:.0f} s after restart; stock reduced exactly once"],
    ["Last copy requested twice", f"second request {E3['second_status']} ({E3['second_message']}); loan {E3['loan_state']}; stock unchanged"],
    ["Same idempotency key sent 3 times", f"stock decreased by {E4['decrement']}"],
    ["3 events relayed twice", f"notifications {E5['notifications_before']} → {E5['notifications_after']} (duplicates ignored)"],
    ["12 business rejections in a row", "circuit breaker stays closed; next valid request succeeds"],
    ["One issue request", f"one trace: {E6['spans']} spans, {len(E6['services'])} services, {E6['duration_ms']:.0f} ms"],
], Inches(0.5), Inches(0.95), SW - Inches(1.0), [3.3, 8.7], size=16, row_h=0.8)

# ---------------------------------------------------------------- 14 results: what the experiments showed
s = new_slide(); title(s, "RESULTS – EXPERIMENT SUMMARY", 30)
bullets(s, [
    "All **13 checks** of the 7 experiments pass, on the laptop and in the GitHub Actions workflow",
    "No event is lost when RabbitMQ is down: the **outbox** keeps it and the relay delivers it after the restart",
    "A loan is never issued twice and stock never changes twice: **idempotency keys** make retries safe",
    "Business rejections (409) do not open the **circuit breaker**; only server errors and timeouts count",
    "Experiments found two real defects: **10-second default timeouts** and a **breaker counting business errors** (both fixed and re-measured)",
    "Right after a restart the half-open breaker can answer 202 instead of 409; the **recovery job** finishes such loans",
    "One request can be followed end to end in **Zipkin** across four services",
], Inches(0.7), Inches(1.0), Inches(12), Inches(6.2), size=22, gap=11)

# ---------------------------------------------------------------- 15 observability
s = new_slide(); title(s, "OBSERVABILITY", 32)
two_pictures(s, path("shots", "zipkin_trace.jpg"), "Zipkin: one request across gateway, lending, member and book", path("shots", "grafana.jpg"), "Grafana dashboard: business counters, p95, circuit breaker, JVM")
bullets(s, [
    "Every log line carries the **trace id**",
    "**Zipkin** shows the spans of one request across services",
    "**Prometheus** scrapes 6 services every 5 s",
    "**Grafana** dashboard is provisioned automatically (Compose and Kubernetes)",
    "Business metrics: loans issued, returned, pending; outbox events waiting; fines; notifications",
    "Technical metrics: p95 latency, circuit breaker state, JVM heap",
], Inches(0.6), Inches(4.55), Inches(12.2), Inches(2.9), size=18, gap=5)

# ---------------------------------------------------------------- 16 testing and deployment
s = new_slide(); title(s, "TESTING AND DEPLOYMENT", 32)
bullets(s, [
    "**31 unit tests** pass (gateway 14, book 8, lending 7, fine 2); GitHub Actions builds, tests and builds all images on every push",
    "**13 automated experiment checks** run in a second workflow against the full system",
    "**17 defects** found by live checks, measurement, design review and deployment, each fixed and re-verified",
    "**Docker Compose:** 14 containers; system and data ready about **110 s** after docker compose up",
    "**Kubernetes (minikube):** 16 pods ready in about 5 minutes with 1 restart; init containers give the start order; Prometheus (6 of 6 targets up) and Grafana deployed too",
    "Database isolation proved: another service's login gets **permission denied**",
    "**Repeatable:** measurements from 12 Nov and 23 Nov are both kept and compared in the report",
], Inches(0.7), Inches(1.0), Inches(12), Inches(6.2), size=23, gap=11)

# ---------------------------------------------------------------- 17 conclusion
s = new_slide(); title(s, "CONCLUSION & FUTURE SCOPE", 30)
bullets(s, [
    "**Conclusion:** the system meets its quality goals on one idle laptop: fast reads, safe multi-service operations, role-based access, full observability",
    "Saga + outbox + idempotent receivers keep **stock and loans consistent** without a distributed transaction",
    "**Limitation:** one machine and one-node Kubernetes; the throughput goal was missed when the laptop was busy",
    "**Limitation:** demo users live in configuration; a changed password is kept in memory only",
    "**Limitation:** the outbox relay polls every 300 ms, without publisher confirms",
    "**Overall:** 31 unit tests, 13 experiment checks and a 16-pod Kubernetes run all passed, with every defect found fixed and re-verified",
    "**Future scope:** identity provider (OpenID Connect), search index (CQRS read model), multi-node cluster with autoscaling, adaptive circuit breaker, trace-based anomaly detection",
], Inches(0.7), Inches(1.0), Inches(12), Inches(6.2), size=23, gap=11)

# ---------------------------------------------------------------- 18-19 references (IEEE style; IEEE or Springer sources, taken from the report)
import content_c  # noqa: E402
R = content_c.REFS
pick = [25, 26, 29, 31, 32, 33, 34, 35, 36, 30, 0, 1, 6, 7, 14, 17, 38, 20, 2, 3]
REFS = [R[i] for i in pick]
for part, chunk in enumerate((REFS[:10], REFS[10:]), 1):
    s = new_slide(); title(s, "REFERENCES")
    tb = s.shapes.add_textbox(Inches(0.6), Inches(0.9), SW - Inches(1.2), Inches(6.3))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, r in enumerate(chunk):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(4)
        run(p, f"[{(0 if part == 1 else 10) + i + 1}] {r}", 14)

# ---------------------------------------------------------------- move the Thank-You slide back to the end
lst = prs.slides._sldIdLst
elem = lst[1]
lst.remove(elem)
lst.append(elem)


# ---------------------------------------------------------------- Times New Roman everywhere (text boxes, tables, title slide)
def force_font(shapes):
    for sh in shapes:
        if sh.has_text_frame:
            for par in sh.text_frame.paragraphs:
                for r in par.runs:
                    r.font.name = FONT
        if getattr(sh, "has_table", False) and sh.has_table:
            for row in sh.table.rows:
                for c in row.cells:
                    for par in c.text_frame.paragraphs:
                        for r in par.runs:
                            r.font.name = FONT


for sl in prs.slides:
    force_font(sl.shapes)
prs.save(OUT)
print("saved", OUT, "with", len(prs.slides), "slides")
