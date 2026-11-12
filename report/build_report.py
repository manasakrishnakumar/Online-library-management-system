"""Builds the project report (Word) in the layout of the college template used for the climate project report.

   python report/build_report.py [pages.json]     ->  report/Online_Library_Management_System_Report.docx

The template is the user's existing DevOps report (cover, certificate, declaration, acknowledgement, abstract, lists, chapters, references).
Set TEMPLATE_DOCX to point at it. Front matter is edited in place; everything from Chapter 1 onward is regenerated from content_*.py.
"""
import copy
import json
import os
import re
import statistics
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt
from docx.text.paragraph import Paragraph

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_a, content_b, content_c, data  # noqa: E402

TEMPLATE = os.environ.get("TEMPLATE_DOCX", r"C:/Users/Manasa Krishnakumar/OneDrive/Desktop/bangalore_climate_app_final/devops_project/Project_Report_Silent_Failures_Kubernetes_v3.docx")
OUT = os.path.join(HERE, "Online_Library_Management_System_Report.docx")
PAGES = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) else {}
NAME1, NAME2, USN = "Manasa Krishnakumar", "[STUDENT NAME 2]", "[USN]"
TITLE = content_a.TITLE
FONT = "Times New Roman"
YEAR = "2026-2027"

ITEMS = content_a.CH1 + content_a.CH2 + content_a.CH3 + content_b.CH4 + content_b.CH5 + content_c.CH6 + content_c.CH7

d = docx.Document(TEMPLATE)
body = d.element.body
kids = list(body)


def P(i):
    return Paragraph(kids[i], d._body)


def set_text(p, text):
    runs = p.runs
    if not runs:
        p.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def strip_sect(el):
    for s in list(el.iter(qn("w:sectPr"))):
        s.getparent().remove(s)
    return el


# ---------- paragraph templates taken from the template before its chapters are removed ----------
BODY_P = strip_sect(copy.deepcopy(kids[236]))
CH_P = strip_sect(copy.deepcopy(kids[235]))
H3_P = strip_sect(copy.deepcopy(kids[240]))
assert "CHAPTER 1" in "".join(t.text or "" for t in kids[235].iter(qn("w:t")))

# ---------- numbering of figures and tables, so that {fig:key} and {tab:key} can be resolved ----------
NUM = {}
chapter = None
fc = tc = 0
for it in ITEMS:
    if it[0] == "h2":
        m = re.match(r"CHAPTER (\d+)", it[1])
        chapter, fc, tc = (m.group(1) if m else chapter), 0, 0
    elif it[0] == "fig":
        fc += 1
        if len(it) > 4:
            NUM["fig:" + it[4]] = f"Figure {chapter}.{fc}"
    elif it[0] == "table":
        tc += 1
        if len(it) > 4:
            NUM["tab:" + it[4]] = f"Table {chapter}.{tc}"


def R(text):
    return re.sub(r"\{(fig|tab):(\w+)\}", lambda m: NUM[f"{m.group(1)}:{m.group(2)}"], text)


# ---------- front matter ----------
ABSTRACT = []
lat, thr, exp, cyc = data.lat, data.thr, data.exp, data.cyc
ep = [k for k in lat if k.startswith("GET /api") and "10,000" not in k]
E1, E2, E7 = exp["E1_outbox"], exp["E2_saga_outage"], exp["E7_rejections"]
ABSTRACT.append(
    "A library is a simple and familiar domain, which makes it a good subject for studying the questions that matter when a system is built from independent services: where each service keeps its data, who may call what, what happens to a half-finished operation when a neighbour fails, and how a developer can follow one request across services. "
    f"This project builds the Online Library Management System as eight Java modules (a configuration server, a service registry, an API gateway and five business services for books, members, lending, fines and notifications), a web front end for librarians and members, one PostgreSQL database with its own login for each business service, a RabbitMQ message broker and a monitoring stack of Zipkin, Prometheus and Grafana, all started with one command. The catalogue holds {data.DS['n']:,} real books from the public Goodbooks-10k dataset.")
ABSTRACT.append(
    "The design follows the SEED(S) process, domain-driven design and event storming. The gateway issues and verifies JSON Web Tokens and applies role rules for librarians and members. Issuing a book is a saga: the loan is saved as pending, a copy is reserved in the book service with an idempotency key, and the loan is marked issued together with an outbox row in one transaction; a failing step is compensated or retried by a recovery job, and the outbox relay delivers events to the fine and notification services at least once, which tolerate duplicates. "
    f"Measured on one laptop, reads through the gateway take a median of {min(lat[k]['p50'] for k in ep):.1f} to {max(lat[k]['p50'] for k in ep):.1f} ms, throughput peaks at {max(r['rps'] for r in thr):.0f} requests per second, and a late return produces a fine and a notification within {statistics.mean(x['notification_visible_ms'] for x in cyc):.0f} ms on average. "
    f"Seven fault-injection experiments passed: with the broker stopped, {len(E1['http_status'])} of {len(E1['http_status'])} issue requests were accepted and every event was delivered {E1['seconds_until_outbox_empty_after_broker_restart']:.0f} s after it returned; with the book service stopped, a loan was accepted as pending in {E2['seconds_to_accept']:.1f} s and completed {E2['seconds_until_issued_after_book_service_restart']:.0f} s after the restart with the stock reduced exactly once; {E7['rejected_count']} business rejections did not open the circuit breaker. "
    "Twenty-three unit tests pass, and fourteen defects found by testing, measurement and deployment are documented with their fixes. The same system was also deployed to a single-node Kubernetes cluster, where all 14 pods became ready.")

set_text(P(11), TITLE)
P(11).alignment = WD_ALIGN_PARAGRAPH.CENTER
for r in P(11).runs:
    r.font.size = Pt(20)
    r.bold = True
set_text(P(13), "MICROSERVICES ARCHITECTURE - PROJECT REPORT")
set_text(P(16), f"{NAME1}\t{USN}")
set_text(P(17), f"{NAME2}\t{USN}")
set_text(P(23), "                                        [FACULTY NAME]")
set_text(P(24), "[Designation]")
t33 = P(33).text
set_text(P(33), t33.replace("2025-2026", YEAR))
set_text(P(46), (f"Certified that the project work titled \u201c{TITLE}\u201d is carried out by {NAME1} ({USN}) and {NAME2} ({USN}), who are bonafide student of R.V College of Engineering, Bangalore, in partial fulfillment for the award of degree of Bachelor of Engineering in Information Science and engineering of the Visvesvaraya Technological University, Belgaum during the year 2026-27. It is certified that all corrections/suggestions indicated for the internal Assessment have been incorporated in the report deposited in the departmental library. The project report has been approved as it satisfies the academic requirements in respect of project work as a part of the course \u201cMicroservices Architecture (IS373TA)\u201d prescribed by the institution for the said degree."))
set_text(P(74), f"We, {NAME1} and {NAME2}, students of seventh semester B.E., Department of Information Science and Engineering, RV College of Engineering, Bengaluru, hereby declare that the project titled \u201c{TITLE}\u201d has been carried out by us and submitted in partial fulfilment for the award of degree of Bachelor of Engineering in Information Science and Engineering during the year {YEAR}.")
ACK = ("We express our sincere gratitude to our faculty guide, [FACULTY NAME], Department of Information Science and Engineering, RV College of Engineering, for guidance, encouragement and valuable suggestions throughout this project. "
       "We thank the Head of the Department of Information Science and Engineering and the faculty of the department for the laboratory facilities and the environment that made this work possible, and the Principal of RV College of Engineering for the academic support. "
       "We thank the authors of the open-source software on which the project stands - Spring Boot, Spring Cloud, PostgreSQL, RabbitMQ, Docker, Zipkin, Prometheus and Grafana - and the author of the Goodbooks-10k dataset. "
       "Finally, we thank our families and friends for their patience and support.")
set_text(P(86), ACK)

# abstract: new paragraphs after the heading (kid 89), formatted like the acknowledgement paragraph
ref = kids[86]
anchor = kids[89]
for text in reversed(ABSTRACT):
    el = copy.deepcopy(ref)
    strip_sect(el)
    anchor.addnext(el)
    p = Paragraph(el, d._body)
    set_text(p, text)
    for r in p.runs:
        r.font.name, r.font.size = FONT, Pt(12)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_after = Pt(8)

# ---------- remove template chapters; keep the final section properties ----------
for el in kids[235:-1]:
    body.remove(el)
final_sect = body[-1]
assert final_sect.tag.endswith("sectPr")
HEADINGS, CAPTIONS = [], []


def new_p(template):
    el = copy.deepcopy(template)
    final_sect.addprevious(el)
    return Paragraph(el, d._body)


def para(text, align="j", size=12, bold=False, italic=False, spacing=1.5, after=6):
    p = new_p(BODY_P)
    set_text(p, R(text))
    for r in p.runs:
        r.font.name, r.font.size, r.bold, r.italic = FONT, Pt(size), bold, italic
    p.alignment = {"j": WD_ALIGN_PARAGRAPH.JUSTIFY, "c": WD_ALIGN_PARAGRAPH.CENTER, "l": WD_ALIGN_PARAGRAPH.LEFT}[align]
    p.paragraph_format.line_spacing = spacing
    p.paragraph_format.space_after = Pt(after)
    return p


def heading(kind, text, page_break=False):
    p = new_p(CH_P if kind == "h2" else H3_P)
    set_text(p, text)
    if kind == "h5":
        p.style = d.styles["Heading 5"]
    pPr = p._p.get_or_add_pPr()
    for n in list(pPr.findall(qn("w:numPr"))):
        pPr.remove(n)
    npr = OxmlElement("w:numPr")
    nid = OxmlElement("w:numId")
    nid.set(qn("w:val"), "0")
    npr.append(nid)
    pPr.append(npr)
    p.paragraph_format.left_indent = Cm(0)
    p.paragraph_format.first_line_indent = Cm(0)
    if kind in ("h3", "h5"):
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.keep_with_next = True
    if kind == "h2":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if page_break:
        p.paragraph_format.page_break_before = True
    HEADINGS.append((kind, text))
    return p


def bullets(items):
    for it in items:
        p = para("\u2022\t" + it, spacing=1.3, after=3)
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.6)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def borders(tbl):
    tblPr = tbl._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for k in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "444444")
        b.append(e)
    tblPr.append(b)


def table(header, rows, size=9.5, widths=None):
    n = len(header)
    if n >= 6:
        size = min(size, 8)
    elif n == 5:
        size = min(size, 8.5)
    tbl = d.add_table(rows=1 + len(rows), cols=n)
    final_sect.addprevious(tbl._tbl)
    borders(tbl)
    tbl.autofit = True
    for j, h in enumerate(header):
        c = tbl.rows[0].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size, r.font.name = True, Pt(size), FONT
        shade(c, "D9E2F3")
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = tbl.rows[i + 1].cells[j]
            c.text = ""
            r = c.paragraphs[0].add_run(R(str(v)))
            r.font.size, r.font.name = Pt(size), FONT
    for row in tbl.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
    if not widths:
        wts = []
        for j in range(n):
            L = [len(R(str(r[j]))) for r in rows] + [len(header[j])]
            wts.append(max(5, min(60, sum(L) / len(L))))
        tot = sum(wts)
        widths = [15.0 * w / tot for w in wts]
    for row in tbl.rows:
        for j, w in enumerate(widths):
            row.cells[j].width = Cm(w)
    trPr = tbl.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    for row in tbl.rows:               # keep a row on one page
        rp = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        rp.append(cs)
    return tbl


def caption(text, kind):
    p = para(text, align="c", size=11, bold=True, spacing=1.0, after=10)
    p.paragraph_format.keep_together = True
    CAPTIONS.append((kind, text))
    return p


def figure(path, cap, width_in):
    p = new_p(BODY_P)
    set_text(p, "")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(os.path.join(HERE, path), width=Inches(width_in))
    caption(cap, "fig")


def code(relpath, marker, n, cap):
    src = open(os.path.join(data.ROOT, relpath), encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(src) if marker in l)
    lines = []
    for l in src[i:i + n]:
        l = l.rstrip().replace("\t", "    ")
        indent = len(l) - len(l.lstrip())
        while len(l) > 96:                                   # wrap long source lines so nothing is cut off
            cut = l.rfind(" ", indent + 20, 96)
            cut = cut if cut > 0 else 96
            lines.append(l[:cut])
            l = " " * (indent + 6) + l[cut:].lstrip()
        lines.append(l)
    tbl = d.add_table(rows=1, cols=1)
    final_sect.addprevious(tbl._tbl)
    borders(tbl)
    c = tbl.rows[0].cells[0]
    shade(c, "F2F2F2")
    c.text = ""
    first = True
    for l in lines:
        p = c.paragraphs[0] if first else c.add_paragraph()
        first = False
        r = p.add_run(l if l else " ")
        r.font.name, r.font.size = "Courier New", Pt(7.5)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
    caption(cap, "code")


# ---------- render ----------
chapter, fc, tc, cc = None, 0, 0, 0
first_h2 = True
for it in ITEMS:
    k = it[0]
    if k == "h2":
        m = re.match(r"CHAPTER (\d+)", it[1])
        chapter, fc, tc, cc = m.group(1), 0, 0, 0
        heading("h2", it[1], page_break=not first_h2)
        first_h2 = False
    elif k in ("h3", "h5"):
        heading(k, it[1])
    elif k == "p":
        para(it[1])
    elif k == "bullets":
        bullets(it[1])
    elif k == "table":
        tc += 1
        table(it[1], it[2])
        caption(f"Table {chapter}.{tc}  {it[3]}", "table")
    elif k == "fig":
        fc += 1
        figure(it[1], f"Figure {chapter}.{fc}  {it[2]}", it[3])
    elif k == "code":
        cc += 1
        code(it[1], it[2], it[3], f"Listing {chapter}.{cc}  {it[4]}")


def references_and_appendices():
    heading("h2", "REFERENCES (IEEE FORMAT)", page_break=True)
    for i, r in enumerate(content_c.REFS, 1):
        p = para(f"[{i}]\t{r}", spacing=1.2, after=4)
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
    para(content_c.REF_NOTE, size=10, italic=True)

    heading("h2", "APPENDIX A  DATASET SAMPLE", page_break=True)
    para("The first fifteen and the last eight rows of books.csv, the catalogue file loaded by the book service. It was prepared from Goodbooks-10k as described in Section 4.2; the columns are title, author, ISBN (or GB-<book id> when the dataset has none), category (publication era) and the number of copies.")
    hdr = ["#", "Title", "Author", "ISBN", "Category", "Copies"]
    first = content_c.APPENDIX_A_FIRST
    table(hdr, [[str(i + 1)] + r for i, r in enumerate(first)], size=8)
    caption("Table A.1  First 15 rows of books.csv", "table")
    last = content_c.APPENDIX_A_LAST
    n0 = data.DS["n"] - len(last) + 1
    table(hdr, [[str(n0 + i)] + r for i, r in enumerate(last)], size=8)
    caption("Table A.2  Last 8 rows of books.csv", "table")

    heading("h2", "APPENDIX B  API OPERATIONS", page_break=True)
    para(f"The {len(data.OPS)} operations published by the five business services, read from the OpenAPI documents in docs/openapi that springdoc generated from the running services. The gateway additionally serves POST /api/auth/login. Operations marked internal are blocked by the gateway.")
    rows = []
    for svc, method, path, op in data.OPS:
        internal = "yes" if re.match(r"^/api/books/\{id\}/(borrow|return)$", path) else ""
        rows.append([svc, method, path, op, internal])
    table(["Service", "Method", "Path", "Operation id", "Internal"], rows, size=8)
    caption("Table B.1  Operations of the business services", "table")


references_and_appendices()
HEADINGS_ALL = HEADINGS

# ---------- lists in the front matter ----------


def pg(text):
    return str(PAGES.get(text, ""))


def rebuild_lines(first_k, last_k, model_k, entries):
    model = kids[model_k]
    keep_sect = None
    for k in range(first_k, last_k + 1):
        s = kids[k].find(".//" + qn("w:sectPr")) if kids[k].tag.endswith("}p") else None
        if s is not None:
            keep_sect = copy.deepcopy(s)
        if k != model_k and kids[k].getparent() is body:
            body.remove(kids[k])
    cur, ps = model, []
    for txt in entries:
        el = copy.deepcopy(model)
        for s in list(el.iter(qn("w:sectPr"))):
            s.getparent().remove(s)
        for n in list(el.iter(qn("w:numPr"))):
            n.getparent().remove(n)
        cur.addnext(el)
        cur = el
        p = Paragraph(el, d._body)
        set_text(p, txt)
        ps.append(p)
    body.remove(model)
    if keep_sect is not None and ps:
        ps[-1]._p.get_or_add_pPr().append(keep_sect)


def smart(s):
    small = ("of", "and", "the", "to", "with", "for")
    keep = ("API", "IEEE")
    return " ".join(w if w in keep else (w.lower() if w.lower() in small else w.capitalize()) for w in s.split())


toc = []
for kind, text in HEADINGS:
    if kind == "h2":
        m = re.match(r"CHAPTER (\d+):  (.*)", text)
        if m:
            label = f"Chapter {m.group(1)}  " + smart(m.group(2))
        elif text.startswith("REFERENCES"):
            label = "References (IEEE Format)"
        else:
            label = smart(text)
        toc.append(f"{label}\t{pg(text)}")
    elif kind == "h3":
        toc.append(f"      {text}\t{pg(text)}")
rebuild_lines(94, 146, 94, toc)
rebuild_lines(153, 193, 153, [f"{t.split('  ')[0]}   {t.split('  ', 1)[1]}\t{pg(t)}" for k, t in CAPTIONS if k == "fig"])

tt = d.tables[1]
model_row = copy.deepcopy(tt.rows[0]._tr)
for r in list(tt.rows):
    tt._tbl.remove(r._tr)
from docx.table import _Row  # noqa: E402
for t in [t for k, t in CAPTIONS if k == "table"]:
    tr = copy.deepcopy(model_row)
    tt._tbl.append(tr)
    row = _Row(tr, tt)
    a, b = t.split("  ", 1)
    for cell, val in zip(row.cells, (f"{a}   {b}", "", pg(t))):
        ps = cell.paragraphs
        if ps and ps[0].runs:
            set_text(ps[0], val)
        else:
            cell.paragraphs[0].add_run(val)

ABBR = [("AMQP", "Advanced Message Queuing Protocol"), ("API", "Application Programming Interface"), ("BCrypt", "Password hashing function"),
        ("CORS", "Cross-Origin Resource Sharing"), ("CQRS", "Command Query Responsibility Segregation"), ("CRUD", "Create, Read, Update, Delete"),
        ("DDD", "Domain-Driven Design"), ("H2", "In-memory Java database used by the first version and by tests"), ("HS256", "HMAC with SHA-256 (JWT signature)"),
        ("HTTP", "Hypertext Transfer Protocol"), ("IaC", "Infrastructure as Code"), ("JPA", "Java Persistence API"), ("JSON", "JavaScript Object Notation"),
        ("JVM", "Java Virtual Machine"), ("JWT", "JSON Web Token"), ("K8s", "Kubernetes"), ("OLMS", "Online Library Management System"),
        ("REST", "Representational State Transfer"), ("SEED(S)", "Seven Essential Evolutions of Design for Services"), ("SQL", "Structured Query Language"),
        ("UI", "User Interface"), ("YAML", "YAML Ain't Markup Language")]
rebuild_lines(206, 233, 206, [f"{a}\t-\t{b}" for a, b in ABBR])

# contents table: rows 1 and 2 hold Abstract and List of Figures, row 3 holds List of Tables and List of Abbreviations
tc0 = d.tables[0]


def set_cell(cell, text):
    ps = cell.paragraphs
    target = ps[-1]                  # in the template the page number is in the last (right-aligned) paragraph
    if target.runs:
        set_text(target, text)
    else:
        target.add_run(text)


set_cell(tc0.rows[1].cells[2], str(PAGES.get("__abstract", "i")))
set_cell(tc0.rows[2].cells[2], str(PAGES.get("__lof", "")))
cells = tc0.rows[3].cells
for cell, lines, al in ((cells[0], ["List of Tables", "List of Abbreviations"], WD_ALIGN_PARAGRAPH.LEFT),
                        (cells[2], [str(PAGES.get("__lot", "")), str(PAGES.get("__loa", ""))], WD_ALIGN_PARAGRAPH.RIGHT)):
    for extra in list(cell.paragraphs):
        extra._p.getparent().remove(extra._p)
    for ln in lines:
        pp = cell.add_paragraph()
        r = pp.add_run(ln)
        r.font.name, r.font.size, r.bold = FONT, Pt(12), True
        pp.alignment = al
        pp.paragraph_format.space_after = Pt(6)

# header and footer text
for rel in d.part.rels.values():
    if "header" in rel.reltype or "footer" in rel.reltype:
        for t in rel.target_part.element.iter(qn("w:t")):
            tx = (t.text or "").strip()
            if tx == "AIML Project Report":
                t.text = "IS373TA Project Report"
            elif tx == "Self-Healing ML Services on K8s":
                t.text = "Online Library Management System"
            elif tx == "2025-2026":
                t.text = YEAR

d.core_properties.title = TITLE
d.core_properties.author = NAME1
d.save(OUT)
json.dump({"headings": HEADINGS, "captions": CAPTIONS, "numbers": NUM}, open(os.path.join(HERE, "index.json"), "w", encoding="utf-8"), indent=0)
print("saved", OUT, len(HEADINGS), "headings", len(CAPTIONS), "captions")
