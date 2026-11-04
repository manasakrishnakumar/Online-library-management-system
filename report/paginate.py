"""Reads the PDF made by Word and writes pages.json: the page number (chapter numbering starts at 1) of every heading and caption,
and the roman page numbers of the front-matter lists.   python report/paginate.py report/x.pdf report/pages.json"""
import json
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
pdf, out = sys.argv[1], sys.argv[2]
index = json.load(open(os.path.join(HERE, "index.json"), encoding="utf-8"))
doc = pymupdf.open(pdf)
norm = lambda s: re.sub(r"\s+", " ", s).strip()
texts = [norm(p.get_text()) for p in doc]

ch1 = next(i for i, t in enumerate(texts) if "CHAPTER 1: INTRODUCTION" in t)
pages = {"__chapter1_pdf_index": ch1, "__pdf_pages": len(doc)}


def roman(n):
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    s = ""
    for v, r in vals:
        while n >= v:
            s += r
            n -= v
    return s


def find(needle, start):
    needle = norm(needle)
    for i in range(start, len(texts)):
        if needle in texts[i]:
            return i
    return None


missing = []
for kind, text in index["headings"]:
    key = norm(text)
    i = find(key, ch1)
    if i is None:
        missing.append(text)
    else:
        pages[text] = i - ch1 + 1
for kind, text in index["captions"]:
    if kind == "code":
        continue
    i = find(text[:70], ch1)
    if i is None:
        missing.append(text)
    else:
        pages[text] = i - ch1 + 1

# front matter: roman numerals count the pages before Chapter 1, the first page after the cover and certificate pages being i
fm = {"__abstract": "ABSTRACT", "__lof": "LIST OF FIGURES", "__lot": "LIST OF TABLES", "__loa": "LIST OF ABBREVIATIONS"}
abstract_idx = next(i for i in range(ch1) if texts[i].startswith("ABSTRACT") or " ABSTRACT " in texts[i][:80] or texts[i][:200].find("ABSTRACT") >= 0)
for k, h in fm.items():
    i = next((j for j in range(abstract_idx, ch1) if re.search(r"(^|\s)" + h + r"(\s|$)", texts[j][:120]) and "CONTENTS" not in texts[j][:60]), None)
    pages[k] = roman(i - abstract_idx + 1) if i is not None else ""
json.dump(pages, open(out, "w", encoding="utf-8"), indent=1)
print("chapter 1 at pdf page", ch1 + 1, "of", len(doc), "; missing:", missing[:10], len(missing))
print({k: v for k, v in pages.items() if k.startswith("__")})
