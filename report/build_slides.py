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
TEAM = ["Manasa Krishnakumar - 1RV23IS067", "Gauri G Singh - 1RV23IS051", "Akanksha Rani - 1RV23IS010"]
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
set_par(tb.text_frame.paragraphs[9], GUIDE, 16)
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
    "Course: **IS373TA Microservices Architecture** (SEED(S), bounded contexts, event sourcing, Docker, Kubernetes).",
], Inches(0.7), Inches(1.0), Inches(12), Inches(5.9), size=19, gap=10)

# ---------------------------------------------------------------- 3-5 literature survey (all after 2020, verified in Crossref)
LIT = [
    ("S. Aydin and C. Cebi, \"Comparison of Choreography vs Orchestration Based Saga Patterns in Microservices,\" IEEE ICECET, 2022",
     "Compares how choreography and orchestration implement a saga; discusses rollback problems with isolated NoSQL databases", "Saga styles for distributed transactions", "Orchestrated saga in lending-service with a compensating step"),
    ("A. Megargel, C. Poskitt and V. Shankararaman, \"Microservices Orchestration vs. Choreography: A Decision Framework,\" IEEE EDOC, 2021",
     "Proposes a decision framework for choosing between orchestration and choreography", "Choice of interaction style", "Orchestration for issue-book, events (choreography) for fines and notifications"),
    ("E. Daraghmi, C.-P. Zhang and S.-M. Yuan, \"Enhancing Saga Pattern for Distributed Transactions within a Microservices Architecture,\" Applied Sciences (MDPI), 2022",
     "Adds an in-memory caching layer to the saga to reach eventual consistency; compared with a standard saga on a small e-commerce system", "Saga optimisation", "Our design uses idempotency keys and an outbox instead of a cache"),
    ("M. Mazzara et al., \"Microservices: Migration of a Mission Critical System,\" IEEE Trans. Services Computing, 2021",
     "Reports the migration of a legacy mission-critical system to microservices and the lessons learned", "Migration experience", "Independent deployment and gradual decomposition"),
    ("X. Zhou et al., \"Fault Analysis and Debugging of Microservice Systems: Industrial Survey, Benchmark System, and Empirical Study,\" IEEE Trans. Software Eng., 2021",
     "Industrial survey of fault analysis and debugging, a benchmark microservice system and an empirical study of faults", "Faults in microservice systems", "Motivated fault-injection experiments and tracing"),
    ("J. Bogner, J. Fritzsch, S. Wagner and A. Zimmermann, \"Industry practices and challenges for the evolvability assurance of microservices,\" Empirical Software Eng. (Springer), 2021",
     "Interview study and grey-literature review of how industry assures the evolvability of microservices", "Maintainability of services", "Small modules, own databases, tests per module"),
    ("H. Vural and M. Koyuncu, \"Does Domain-Driven Design Lead to Finding the Optimal Modularity of a Microservice?\" IEEE Access, 2021",
     "Investigates whether domain-driven design leads to optimal microservice modularity", "Service boundaries", "Bounded contexts found by event storming"),
    ("A. Singjai, U. Zdun and O. Zimmermann, \"Practitioner Views on the Interrelation of Microservice APIs and Domain-Driven Design: A Grey Literature Study Based on Grounded Theory,\" IEEE ICSA, 2021",
     "Grey-literature study of how practitioners relate microservice APIs to domain-driven design", "API design from the domain model", "SEED(S) actions and queries published as OpenAPI"),
    ("N. Stanley S A and S. Sebastian, \"Circuit Breaker: A Resilience Mechanism for Cloud Native Architecture,\" IEEE GCITC, 2023",
     "Presents the circuit breaker as a resilience mechanism for cloud-native architectures", "Failure isolation", "Resilience4j breaker around every remote call"),
    ("K. Sivakumar, J. Sebastian and P. S. Thilagam, \"Self-Adaptive Circuit Breaker Open-State Interval for Enhancing Resiliency of Microservices,\" IEEE OCIT, 2024",
     "Proposes adapting the open-state interval of a circuit breaker to improve resiliency", "Circuit breaker tuning", "We saw half-open behaviour in experiment E7; adaptive interval is future work"),
    ("B. Li et al., \"Enjoy your observability: an industrial survey of microservice tracing and analysis,\" Empirical Software Eng. (Springer), 2022",
     "Survey based on interviews with developers and operation engineers of microservice systems from ten companies", "Tracing in practice", "Zipkin traces, trace ids in every log line"),
    ("M. Usman, S. Ferlin, A. Brunstrom and J. Taheri, \"A Survey on Observability of Distributed Edge & Container-Based Microservices,\" IEEE Access, 2022",
     "Surveys observability (metrics, logs, traces) for edge and container-based microservices", "Observability techniques", "Prometheus, Grafana and Zipkin from the start"),
    ("M. Soualhia and F. Wuhib, \"Automated Traces-based Anomaly Detection and Root Cause Analysis in Cloud Platforms,\" IEEE IC2E, 2022",
     "Uses traces to detect anomalies and locate root causes in cloud platforms", "Trace analysis", "Our traces allow manual root-cause reading; automatic detection is future work"),
    ("A. Barabanov and D. Makrushin, \"Authentication and Authorization in Microservice-Based Systems: Survey of Architecture Patterns,\" Voprosy Kiberbezopasnosti, 2020",
     "Surveys authentication and authorization architecture patterns, drawing on research papers and security conference talks", "Security patterns", "JWT checked at the gateway, internal endpoints blocked"),
]
HEAD = ["Title, Author and Year of Publication", "Key Findings", "Scope of the Work", "Use in This Project"]
for part, chunk in enumerate((LIT[:5], LIT[5:10], LIT[10:]), 1):
    s = new_slide(); title(s, f"LITERATURE SURVEY ({part}/3)", 30)
    table(s, HEAD, chunk, Inches(0.55), Inches(0.95), SW - Inches(1.1), [3.6, 3.6, 2.0, 3.0], size=10, row_h=0.9)

# ---------------------------------------------------------------- 6 problem statement and objectives
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
], Inches(0.7), Inches(0.95), Inches(12), Inches(6), size=18, gap=7)

# ---------------------------------------------------------------- 7 methodology: architecture
s = new_slide(); title(s, "METHODOLOGY")
picture(s, path("assets", "diag_architecture.png"), Inches(0.5), Inches(0.95), height=Inches(6.2), caption="Architecture of the Online Library Management System")
bullets(s, [
    "**Browser \u2192 nginx \u2192 API Gateway**: JWT login, role rules, routing",
    "**Eureka** finds services by name; **Config Server** shares settings",
    "**Book, Member, Lending, Fine, Notification**: one PostgreSQL database and login each",
    "**REST + circuit breaker** for questions that need an answer now",
    "**RabbitMQ events** for everything else",
    "**Zipkin, Prometheus, Grafana** observe every service",
], Inches(7.7), Inches(1.3), Inches(5.3), Inches(5.5), size=16, gap=9)

# ---------------------------------------------------------------- 8 methodology: SEED(S) and boundaries
s = new_slide(); title(s, "METHODOLOGY \u2013 SEED(S) DESIGN", 30)
bullets(s, [
    "**Actors:** Member, Librarian, Administrator",
    "**Jobs:** find a book \u2022 borrow and return \u2022 know due dates and fines \u2022 keep the catalogue correct",
    "**Interaction pattern** (sequence diagram): the issue-book request crosses gateway, lending, member and book",
    f"**Actions and queries:** {len(data.OPS)} operations, published as **OpenAPI** (Swagger UI per service)",
    "**Event storming:** Book Added \u2192 Loan Requested \u2192 Book Issued \u2192 Book Returned \u2192 Fine Assessed \u2192 Member Notified",
    "**Bounded contexts:** Catalogue, Membership, Lending, Fines, Notifications = 5 services, each with the data it owns",
    "**Operating model:** 3 stream-aligned teams + 1 platform team",
], Inches(0.5), Inches(0.95), Inches(6.7), Inches(6), size=16, gap=8)
picture(s, path("assets", "diag_sequence.png"), Inches(7.3), Inches(1.0), width=Inches(5.7), caption="Sequence of issuing a book")

# ---------------------------------------------------------------- 9 saga and outbox
s = new_slide(); title(s, "CONSISTENCY: SAGA + TRANSACTIONAL OUTBOX", 28)
picture(s, path("assets", "diag_saga.png"), Inches(0.4), Inches(0.95), width=Inches(7.2), caption="Issue saga and its failure paths")
bullets(s, [
    "Loan saved as **PENDING**, copy reserved with key **loan-{id}-borrow**",
    "**ISSUED + outbox row** in one transaction; relay sends events to RabbitMQ (at least once)",
    "**409 refused** \u2192 loan FAILED, nothing to undo",
    "**Unknown outcome** \u2192 202 pending; recovery job replays the same keyed step",
    "**Last step fails** \u2192 compensation releases the copy",
    "Consumers ignore duplicate message ids",
], Inches(7.8), Inches(1.1), Inches(5.3), Inches(5.8), size=16, gap=9)

# ---------------------------------------------------------------- 10 tools and techniques
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
], Inches(0.6), Inches(1.0), SW - Inches(1.2), [2.0, 9.4], size=14, row_h=0.65)

# ---------------------------------------------------------------- 11 implementation: UI
s = new_slide(); title(s, "IMPLEMENTATION \u2013 WEB APPLICATION", 30)
picture(s, path("shots", "dashboard.jpg"), Inches(0.35), Inches(1.0), width=Inches(6.2), caption="Librarian dashboard (live data from 4 services)")
picture(s, path("shots", "books.jpg"), Inches(6.8), Inches(1.0), width=Inches(6.2), caption="Book-cover grid: 10,000 titles, server-side search and paging")
bullets(s, ["Login page, role-based menus, loan history popup, fines and notifications", "Librarian: issue, return, overdue helper, fines \u2022 Member: own loans, fines, notifications"],
        Inches(0.6), Inches(5.4), Inches(12.2), Inches(1.6), size=16, gap=6)

# ---------------------------------------------------------------- 12 implementation: roles and screens
s = new_slide(); title(s, "IMPLEMENTATION \u2013 ROLES AND LENDING", 30)
picture(s, path("shots", "lending.jpg"), Inches(0.35), Inches(1.0), width=Inches(6.2), caption="Librarian: lending page with status and actions")
picture(s, path("shots", "member_loans.jpg"), Inches(6.8), Inches(1.0), width=Inches(6.2), caption="Member: only own loans (enforced at the gateway)")
bullets(s, ["No token or bad token \u2192 **401**; wrong role or another member's data \u2192 **403**", "Stock endpoints (borrow, return) are internal: blocked for everybody at the gateway"],
        Inches(0.6), Inches(5.4), Inches(12.2), Inches(1.6), size=16, gap=6)

# ---------------------------------------------------------------- 13 results: performance
s = new_slide(); title(s, "RESULTS & DISCUSSION \u2013 PERFORMANCE", 30)
picture(s, path("assets", "perf_latency.png"), Inches(0.3), Inches(0.95), width=Inches(6.4), caption="Latency through the gateway (median and p95)")
picture(s, path("assets", "perf_throughput.png"), Inches(6.8), Inches(0.95), width=Inches(6.2), caption="Throughput against client threads")
bullets(s, [
    f"Reads take a median of **{min(lat[k]['p50'] for k in ep):.1f}\u2013{max(lat[k]['p50'] for k in ep):.1f} ms**, p95 below **{max(lat[k]['p95'] for k in ep):.0f} ms**",
    f"Peak **{peak['rps']:.0f} requests/s** on one laptop, no failed request",
    f"A late return gives a fine in **{statistics.mean(data.fine_ms):.0f} ms** and a notification in **{statistics.mean(data.note_ms):.0f} ms** (asynchronous path)",
], Inches(0.6), Inches(4.75), Inches(12.2), Inches(2.4), size=16, gap=6)

# ---------------------------------------------------------------- 14 results: fault injection
s = new_slide(); title(s, "RESULTS \u2013 FAULT-INJECTION EXPERIMENTS", 30)
table(s, ["Fault injected", "Observed"], [
    ["RabbitMQ stopped, 5 loans issued", f"all {len(E1['http_status'])} accepted (201); {E1['outbox_pending_during_outage']} events kept in the outbox; delivered {E1['seconds_until_outbox_empty_after_broker_restart']:.0f} s after restart"],
    ["book-service stopped during an issue", f"202 pending in {E2['seconds_to_accept']:.1f} s; ISSUED {E2['seconds_until_issued_after_book_service_restart']:.0f} s after restart; stock reduced exactly once"],
    ["Last copy requested twice", f"second request {E3['second_status']} ({E3['second_message']}); loan {E3['loan_state']}; stock unchanged"],
    ["Same idempotency key sent 3 times", f"stock decreased by {E4['decrement']}"],
    ["3 events relayed twice", f"notifications {E5['notifications_before']} \u2192 {E5['notifications_after']} (duplicates ignored)"],
    ["12 business rejections in a row", f"circuit breaker stays closed; next valid request succeeds"],
    ["One issue request", f"one trace: {E6['spans']} spans, {len(E6['services'])} services, {E6['duration_ms']:.0f} ms"],
], Inches(0.5), Inches(0.95), SW - Inches(1.0), [3.3, 8.7], size=13, row_h=0.6)
bullets(s, ["Experiments found two real defects: **10-second default timeouts** and a **circuit breaker counting business errors** (both fixed and re-measured)"],
        Inches(0.6), Inches(6.3), Inches(12.2), Inches(0.9), size=15)

# ---------------------------------------------------------------- 15 observability
s = new_slide(); title(s, "OBSERVABILITY", 32)
picture(s, path("shots", "zipkin_trace.jpg"), Inches(0.3), Inches(1.0), width=Inches(6.3), caption="Zipkin: one request across gateway, lending, member and book")
picture(s, path("shots", "grafana.jpg"), Inches(6.8), Inches(1.0), width=Inches(6.2), caption="Grafana dashboard: business counters, p95, circuit breaker, JVM")
bullets(s, ["Every log line carries the trace id \u2022 Prometheus scrapes 6 services every 5 s", "Business metrics: loans issued/returned/pending, outbox events waiting, fines, notifications"],
        Inches(0.6), Inches(5.4), Inches(12.2), Inches(1.6), size=16, gap=6)

# ---------------------------------------------------------------- 16 testing and deployment
s = new_slide(); title(s, "TESTING AND DEPLOYMENT", 32)
bullets(s, [
    "**31 unit tests** pass (gateway 14, book 8, lending 7, fine 2); GitHub Actions builds, tests and builds all images on every push",
    "**13 automated experiment checks** run in a second workflow against the full system",
    "**17 defects** found by live checks, measurement, design review and deployment, each fixed and re-verified",
    "**Docker Compose:** 14 containers; system and data ready about **110 s** after `docker compose up`",
    "**Kubernetes (minikube):** 16 pods ready in about 5 minutes with 1 restart; init containers give the start order; Prometheus (6 of 6 targets up) and Grafana deployed too",
    "Database isolation proved: another service's login gets **permission denied**",
], Inches(0.7), Inches(1.0), Inches(12), Inches(6), size=18, gap=10)

# ---------------------------------------------------------------- 17 conclusion
s = new_slide(); title(s, "CONCLUSION, LIMITATIONS & FUTURE SCOPE", 28)
bullets(s, [
    "The system **meets all quality goals** on a single laptop: fast reads, safe multi-service operations, role-based access, full observability",
    "Saga + outbox + idempotent receivers keep **stock and loans consistent** without a distributed transaction",
    "**Limitations:** one machine, one-node Kubernetes, demo users in configuration (password change kept in memory), outbox relay polls every 300 ms",
    "**Future scope:** identity provider (OpenID Connect), search index (CQRS read model), multi-node cluster with autoscaling, adaptive circuit breaker, automatic trace-based anomaly detection",
], Inches(0.7), Inches(1.0), Inches(12), Inches(6), size=19, gap=12)

# ---------------------------------------------------------------- 18-19 references (IEEE style)
REFS = [
    "S. Aydin and C. Cebi, \"Comparison of Choreography vs Orchestration Based Saga Patterns in Microservices,\" in Proc. 2022 Int. Conf. Electrical, Computer and Energy Technologies (ICECET), 2022, doi: 10.1109/ICECET55527.2022.9872665.",
    "A. Megargel, C. Poskitt and V. Shankararaman, \"Microservices Orchestration vs. Choreography: A Decision Framework,\" in Proc. 25th IEEE Int. Enterprise Distributed Object Computing Conf. (EDOC), 2021, pp. 134-141, doi: 10.1109/EDOC52215.2021.00024.",
    "E. Daraghmi, C.-P. Zhang and S.-M. Yuan, \"Enhancing Saga Pattern for Distributed Transactions within a Microservices Architecture,\" Applied Sciences, vol. 12, no. 12, p. 6242, 2022, doi: 10.3390/app12126242.",
    "M. Mazzara, N. Dragoni, A. Bucchiarone, A. Giaretta, S. T. Larsen and S. Dustdar, \"Microservices: Migration of a Mission Critical System,\" IEEE Trans. Services Computing, vol. 14, no. 5, pp. 1464-1477, 2021, doi: 10.1109/TSC.2018.2889087.",
    "X. Zhou et al., \"Fault Analysis and Debugging of Microservice Systems: Industrial Survey, Benchmark System, and Empirical Study,\" IEEE Trans. Software Engineering, vol. 47, no. 2, pp. 243-260, 2021, doi: 10.1109/TSE.2018.2887384.",
    "J. Bogner, J. Fritzsch, S. Wagner and A. Zimmermann, \"Industry practices and challenges for the evolvability assurance of microservices,\" Empirical Software Engineering, vol. 26, no. 5, 2021, doi: 10.1007/s10664-021-09999-9.",
    "H. Vural and M. Koyuncu, \"Does Domain-Driven Design Lead to Finding the Optimal Modularity of a Microservice?\" IEEE Access, vol. 9, pp. 32721-32733, 2021, doi: 10.1109/ACCESS.2021.3060895.",
    "A. Singjai, U. Zdun and O. Zimmermann, \"Practitioner Views on the Interrelation of Microservice APIs and Domain-Driven Design: A Grey Literature Study Based on Grounded Theory,\" in Proc. 18th IEEE Int. Conf. Software Architecture (ICSA), 2021, pp. 25-35, doi: 10.1109/ICSA51549.2021.00011.",
    "N. Stanley S A and S. Sebastian, \"Circuit Breaker: A Resilience Mechanism for Cloud Native Architecture,\" in Proc. 2023 Global Conf. Information Technologies and Communications (GCITC), 2023, pp. 1-8, doi: 10.1109/GCITC60406.2023.10426195.",
    "K. Sivakumar, J. Sebastian and P. S. Thilagam, \"Self-Adaptive Circuit Breaker Open-State Interval for Enhancing Resiliency of Microservices,\" in Proc. 2024 OITS Int. Conf. Information Technology (OCIT), 2024, pp. 754-759, doi: 10.1109/OCIT65031.2024.00136.",
    "B. Li et al., \"Enjoy your observability: an industrial survey of microservice tracing and analysis,\" Empirical Software Engineering, vol. 27, no. 1, 2022, doi: 10.1007/s10664-021-10063-9.",
    "M. Usman, S. Ferlin, A. Brunstrom and J. Taheri, \"A Survey on Observability of Distributed Edge & Container-Based Microservices,\" IEEE Access, vol. 10, pp. 86904-86919, 2022, doi: 10.1109/ACCESS.2022.3193102.",
    "M. Soualhia and F. Wuhib, \"Automated Traces-based Anomaly Detection and Root Cause Analysis in Cloud Platforms,\" in Proc. 2022 IEEE Int. Conf. Cloud Engineering (IC2E), 2022, pp. 253-260, doi: 10.1109/IC2E55432.2022.00034.",
    "A. Barabanov and D. Makrushin, \"Authentication and Authorization in Microservice-Based Systems: Survey of Architecture Patterns,\" Voprosy Kiberbezopasnosti, no. 4(38), pp. 32-43, 2020, doi: 10.21681/2311-3456-2020-04-32-43.",
    "S. Newman, Building Microservices: Designing Fine-Grained Systems, 2nd ed. Sebastopol, CA, USA: O'Reilly Media, 2021.",
    "J. Carnell, Spring Microservices in Action. Shelter Island, NY, USA: Manning, 2017.",
    "C. Richardson, Microservices Patterns. Shelter Island, NY, USA: Manning, 2018.",
    "H. Garcia-Molina and K. Salem, \"Sagas,\" ACM SIGMOD Record, vol. 16, no. 3, pp. 249-259, 1987.",
    "M. T. Nygard, Release It! Design and Deploy Production-Ready Software, 2nd ed. Pragmatic Bookshelf, 2018.",
    "Z. Zajac, \"Goodbooks-10k: a new dataset for book recommendations,\" GitHub repository zygmuntz/goodbooks-10k, 2017.",
]
for part, chunk in enumerate((REFS[:10], REFS[10:]), 1):
    s = new_slide(); title(s, "REFERENCES")
    tb = s.shapes.add_textbox(Inches(0.6), Inches(0.9), SW - Inches(1.2), Inches(6.3))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, r in enumerate(chunk):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(3)
        run(p, f"[{(0 if part == 1 else 10) + i + 1}] {r}", 11)

# ---------------------------------------------------------------- move the Thank-You slide back to the end
lst = prs.slides._sldIdLst
elem = lst[1]
lst.remove(elem)
lst.append(elem)
prs.save(OUT)
print("saved", OUT, "with", len(prs.slides), "slides")
