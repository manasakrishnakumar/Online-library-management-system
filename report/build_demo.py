"""Builds the one-page demo script (Word) and docs/DEMO_SCRIPT.md from report/demo_steps.py.   python report/build_demo.py"""
import os
import sys

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from demo_steps import STEPS, TIPS  # noqa: E402

FONT = "Times New Roman"
TEAM = "Manasa Krishnakumar (1RV23IS067), Gauri G Singh (1RV23IS051), Akanksha Rani (1RV23IS010)"
ACCOUNTS = [("Librarian (full access)", "librarian", "librarian123"), ("Member (own data only)", "asha.rao@example.com", "member123")]
LINKS = [("Application", "http://localhost:3000"), ("Eureka", "http://localhost:8761"), ("Zipkin", "http://localhost:9411"),
         ("Grafana", "http://localhost:3001"), ("RabbitMQ", "http://localhost:15672 (guest / guest)"), ("Prometheus", "http://localhost:9090")]


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def borders(tbl):
    b = OxmlElement("w:tblBorders")
    for k in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "888888")
        b.append(e)
    tbl._tbl.tblPr.append(b)


def text(cell_or_par, s, size=10, bold=False, color=None):
    par = cell_or_par.paragraphs[0] if hasattr(cell_or_par, "paragraphs") else cell_or_par
    r = par.add_run(s)
    r.font.name, r.font.size, r.bold = FONT, Pt(size), bold
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    par.paragraph_format.space_after = Pt(1)
    return par


d = docx.Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(1.6)
sec.top_margin = sec.bottom_margin = Cm(1.4)

p = d.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
text(p, "Online Library Management System – Demo Script", 18, True, "1F3FBF")
p = d.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
text(p, "IS373TA Microservices Architecture • " + TEAM, 9)
p = d.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
text(p, "Guide: Sushmitha N, Assistant Professor, Dept. of ISE, RV College of Engineering", 9)

t = d.add_table(rows=1 + len(LINKS) // 2, cols=4)
borders(t)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = ["Logins", "", "Addresses", ""]
for j, h in enumerate(("Account", "Username / password", "Address", "URL")):
    text(t.rows[0].cells[j], h, 9, True)
    shade(t.rows[0].cells[j], "D9E2F3")
for i in range(len(LINKS) // 2):
    a = ACCOUNTS[i] if i < len(ACCOUNTS) else ("", "", "")
    text(t.rows[i + 1].cells[0], a[0], 9)
    text(t.rows[i + 1].cells[1], (a[1] + " / " + a[2]) if a[1] else "", 9)
    text(t.rows[i + 1].cells[2], LINKS[i * 2][0] + " / " + LINKS[i * 2 + 1][0], 9)
    text(t.rows[i + 1].cells[3], LINKS[i * 2][1] + "   |   " + LINKS[i * 2 + 1][1], 8)

d.add_paragraph().paragraph_format.space_after = Pt(2)
t = d.add_table(rows=1, cols=3)
borders(t)
for j, (h, w) in enumerate((("#", 0.8), ("What to do", 8.2), ("What it shows / what to say", 8.2))):
    c = t.rows[0].cells[j]
    c.width = Cm(w)
    text(c, h, 10, True)
    shade(c, "D9E2F3")
for n, do, say in STEPS:
    row = t.add_row()
    for j, (v, w) in enumerate(((n, 0.8), (do, 8.2), (say, 8.2))):
        row.cells[j].width = Cm(w)
        text(row.cells[j], v, 9.5, j == 0)
    trPr = row._tr.get_or_add_trPr()
    cs = OxmlElement("w:cantSplit")
    cs.set(qn("w:val"), "true")
    trPr.append(cs)

d.add_paragraph().paragraph_format.space_after = Pt(2)
p = d.add_paragraph()
text(p, "Tips", 11, True, "1F3FBF")
for tip in TIPS:
    p = d.add_paragraph()
    text(p, "• " + tip, 9.5)
out = os.path.join(HERE, "Online_Library_Management_System_Demo_Script.docx")
d.save(out)

md = ["# Demo Script", "", "IS373TA Microservices Architecture. About ten minutes.", "",
      "| Account | Username | Password |", "|---|---|---|"] + [f"| {a} | `{u}` | `{pw}` |" for a, u, pw in ACCOUNTS] + ["", "| Address | URL |", "|---|---|"] + [f"| {n} | {u} |" for n, u in LINKS] + ["", "| # | What to do | What it shows |", "|---|---|---|"]
md += [f"| {n} | {do} | {say} |" for n, do, say in STEPS] + ["", "## Tips", ""] + [f"- {t}" for t in TIPS] + [""]
open(os.path.join(ROOT, "docs", "DEMO_SCRIPT.md"), "w", encoding="utf-8").write("\n".join(md))
print("saved", out, "and docs/DEMO_SCRIPT.md")
