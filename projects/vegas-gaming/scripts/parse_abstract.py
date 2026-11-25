#!/usr/bin/env python3
"""Extract the Las Vegas Strip's income statement from every Gaming Abstract, FY1990 on.

    python scripts/parse_abstract.py        # needs pdftotext, pdftoppm and tesseract

For the group "Clark County - Las Vegas Strip Area, gaming revenue of $1,000,000 and
over" (in practice, every Strip casino of any size) it writes data/processed/abstract_strip.csv:
revenue by department, the comps the casino gave away, and departmental income for
the casino and the rooms department.

Two kinds of PDF:
- FY2018 on: text PDFs, read with pdftotext.
- FY1990-2017: scanned images. The pages are OCR'd with tesseract. OCR misreads digits,
  so a reading is accepted only if it passes checks the page itself makes possible:
  the five departments must sum exactly to the printed total and match their printed
  percentages (to 0.1 point); departmental income plus expenses must equal revenue.
  A value that fails is left blank rather than guessed.

Accounting change: from FY2019 casinos follow ASC 606, which takes the value of comps
out of gaming revenue ("contra revenue") instead of counting it as a casino expense.
The new-basis figures are kept as printed, and the contra amounts are stored so the
SQL model can put every year on the old basis (see v_strip_departments).
"""
import csv
import itertools
import os
import re
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "abstract"
CACHE = ROOT / "data" / "raw" / "abstract_ocr"
OUT = ROOT / "data" / "processed" / "abstract_strip.csv"
GROUP = "Las Vegas Strip Area, Gaming Revenue of $1,000,000 and over"
DEPTS = ["gaming", "rooms", "food", "beverage", "other"]
# Where the Strip summary page sits in each scanned Abstract (found by searching;
# every page is still checked before it's used, and searched for if the hint is wrong).
PAGE_HINTS = {1990: 66, 1991: 66, 1992: 66, 1993: 74, 1994: 73, 1995: 65, 1996: 66, 1997: 73,
              1998: 73, 1999: 74, 2000: 73, 2001: 73, 2002: 74, 2003: 78, 2004: 78, 2005: 73,
              2006: 76, 2007: 74, 2008: 77, 2009: 77, 2010: 72, 2011: 72, 2012: 72, 2013: 72,
              2014: 72, 2015: 73, 2016: 73, 2017: 72}
FIELDS = ["fy", "licensees", "method", *DEPTS, "total",
          *[f"contra_{d}" for d in DEPTS], "casino_comps", "casino_dept_income", "rooms_dept_income"]


# ---------- numbers from noisy OCR ----------

PCT = r"(\d{1,3})\s?[.,]\s?(\d)\s?[%t?*Z2]?$"


def tidy(line):
    """Drop trailing junk (marks from the page edge) after the last number."""
    tok = re.sub(r"(\d)(100[.,]0%)", r"\1 \2", line).split()
    while tok and not re.search(r"\d", tok[-1]):
        tok.pop()
    return " ".join(tok)


def pct(line):
    m = re.search(PCT, tidy(line))
    return float(f"{m.group(1)}.{m.group(2)}") if m else None


def digits(line):
    line = re.sub(r"\s" + PCT, "", tidy(line))
    m = re.search(r"([\d,;.\s£€]+)$", line)
    return re.sub(r"\D", "", m.group(1)) if m else ""


def readings(line, lo=7, hi=11, misreads=1):
    """Every value the digits could be: OCR adds leading junk and reads a comma as a digit."""
    variants = {digits(line)}
    for _ in range(misreads):
        variants |= {v[:i] + v[i + 1:] for v in variants for i in range(len(v))}
    return {int(v[k:]) for v in variants for k in range(len(v)) if lo <= len(v[k:]) <= hi}


def subseq(a, b):
    it = iter(b)
    return all(c in it for c in a)


# ---------- OCR ----------

def render(pdf, page, dpi):
    png = CACHE / f"{pdf.stem}_p{page}_{dpi}.png"
    if not png.exists():
        base = str(png)[:-4]
        subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(page), "-l", str(page),
                        "-png", "-singlefile", str(pdf), base], check=True)
    return png


def ocr(pdf, page, dpi=200, crop=None, digits_only=False):
    tag = f"_c{crop}" if crop else ""
    txt = CACHE / f"{pdf.stem}_p{page}_{dpi}{tag}.txt"
    if txt.exists():
        return txt.read_text()
    img = render(pdf, page, dpi)
    if crop:
        im = Image.open(img)
        w, h = im.size
        cut = CACHE / f"{pdf.stem}_p{page}_{dpi}{tag}.png"
        im.crop((int(w * crop), int(h * 0.10), w, int(h * 0.45))).save(cut)
        img = cut
    cmd = ["tesseract", str(img), "-", "--psm", "6"]
    if digits_only:
        cmd += ["-c", "tessedit_char_whitelist=0123456789,.%"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    txt.write_text(out)
    return out


def is_summary(t):
    return (re.search(r"SUMMARY", t, re.I) and re.search(r"Strip", t, re.I) and not re.search(r"BOULDER", t, re.I)
            and re.search(r"1,?000,?000 and over", t, re.I) and re.search(r"TOTAL\s+REVEN", t, re.I))


def solve_revenue(rows):
    """Five department rows + total row -> values that sum exactly to the total and match the
    printed percents. Totals are tried largest first: a reading with digits trimmed off is always
    smaller than the true value, so the first total that works is the real one."""
    if len(rows) < 6:
        return None
    pcts = [pct(r) for r in rows[:5]]
    if any(p is None for p in pcts):
        return None
    cands = [readings(r) for r in rows[:5]]
    for total in sorted(readings(rows[5], misreads=2), reverse=True):
        if total < 1e9:
            break
        fits = [[v for v in c if abs(100 * v / total - p) <= 0.1] for c, p in zip(cands, pcts)]
        if all(fits):
            for combo in itertools.product(*fits):
                if sum(combo) == total:
                    return dict(zip(DEPTS, combo), total=total)
    return None


def scanned_summary(pdf, page):
    # 1) the numbers column alone, digits only: the cleanest reading
    for x0 in (0.55, 0.50, 0.60, 0.45):
        t = ocr(pdf, page, 400, crop=x0, digits_only=True)
        t = re.sub(r"(\d)(100[.,]0%)", r"\1 \2", t)
        lines = [l.strip(" ,.") for l in t.splitlines()]
        rows = [l for l in lines if re.search(r"\d{3}\D{0,2}\d{3}.*\d\s?[.,]\s?\d\s?%?$", l)]
        res = solve_revenue(rows)
        if res:
            return res, f"OCR, numbers column (x={x0})"
    # 2) the full page, rows found by their labels
    for dpi in (200, 300):
        t = ocr(pdf, page, dpi)
        lines = t.splitlines()
        rows = []
        for pat in (r"^\s*GAM", r"^\s*ROOM", r"^\s*FOO", r"^\s*BEV", r"^\s*OTHER", r"^\s*TOTAL\s+REVEN"):
            hit = [l for l in lines if re.search(pat, l, re.I)]
            if not hit:
                break
            rows.append(hit[0])
        res = solve_revenue(rows)
        if res:
            return res, f"OCR, full page ({dpi} dpi)"
    return None, None


def scanned_detail(pdf, page, gaming, rooms):
    """Casino and rooms departments from the detail page that follows the summary."""
    out = {"casino_comps": None, "casino_dept_income": None, "rooms_dept_income": None}
    for dpi in (300, 400):
        lines = ocr(pdf, page, dpi).splitlines()
        idx = {k: next((i for i, l in enumerate(lines) if re.search(k + r"\s+DEPARTMENT", l, re.I)), None)
               for k in ("CASINO", "ROOMS", "FOOD")}
        if idx["CASINO"] is None or idx["ROOMS"] is None:
            continue
        blocks = {"casino": (lines[idx["CASINO"]:idx["ROOMS"]], gaming),
                  "rooms": (lines[idx["ROOMS"]:idx["FOOD"] or len(lines)], rooms)}
        for name, (block, revenue) in blocks.items():
            exp = next((l for l in block if re.search(r"TOTAL\s+DEPARTMENTAL\s+EXP", l, re.I)), None)
            inc = next((l for l in block if re.search(r"DEPARTMENTAL\s+INCOME", l, re.I)), None)
            if exp and inc and out[f"{name}_dept_income"] is None:
                for e, i in itertools.product(readings(exp, 6), readings(inc, 6)):
                    if e + i == revenue:
                        out[f"{name}_dept_income"] = i
                        break
            if name == "casino" and out["casino_comps"] is None:
                comp = next((l for l in block if re.search(r"Complimentary\s+Expense", l, re.I)), None)
                if comp and pct(comp) is not None:
                    ok = sorted(v for v in readings(comp, 6) if abs(100 * v / revenue - pct(comp)) <= 0.1)
                    out["casino_comps"] = ok[-1] if ok else None
        if all(v is not None for v in out.values()):
            break
    return out


def licensees(pdf, page):
    m = re.search(r"Represent\S*\s+(\d+)", ocr(pdf, page, 200), re.I)
    return int(m.group(1)) if m else None


def scanned_year(fy):
    pdf = RAW / f"{fy}-abstract.pdf"
    hint = PAGE_HINTS.get(fy, 70)
    pages = [hint] + [p for p in range(55, 100) if p != hint]
    page = next(p for p in pages if is_summary(ocr(pdf, p, 200)))
    rev, method = scanned_summary(pdf, page)
    row = {"fy": fy, "licensees": licensees(pdf, page), "method": method or "OCR failed checks"}
    if rev:
        row.update(rev)
        row.update(scanned_detail(pdf, page + 1, rev["gaming"], rev["rooms"]))
    for d in DEPTS:
        row[f"contra_{d}"] = 0
    return row


# ---------- text PDFs (FY2018 on) ----------

def num(s):
    return int(s.replace(",", "").replace("(", "-").replace(")", ""))


def text_year(fy):
    pdf = RAW / f"{fy}-abstract.pdf"
    pages = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.split("\f")
    grp = [p for p in pages if GROUP in p]
    summ = next(p for p in grp if "Income Statement - Summary" in p)
    row = {"fy": fy, "method": "text"}
    for label, key in [("Gaming", "gaming"), ("Rooms", "rooms"), ("Food", "food"), ("Beverage", "beverage"),
                       ("Other", "other"), ("Total Revenue", "total")]:
        row[key] = num(re.search(rf"^\s*{label}\s+([\d,]+)\s+[\d.]+\s*$", summ, re.M).group(1))
    assert sum(row[d] for d in DEPTS) == row["total"], fy
    row["licensees"] = int(re.search(r"Amounts represent (\d+)", summ).group(1))
    detail = "\n".join(p for p in grp if re.search(r"Income Statement - Detail", p, re.I))
    contra = [-num(x) for x in re.findall(r"Contra Revenue \(Complimentary Expense\)\s+(\([\d,]+\)|[\d,]+)", detail)][:5]
    contra += [0] * (5 - len(contra))
    for d, c in zip(DEPTS, contra):
        row[f"contra_{d}"] = c
    income = [num(x) for x in re.findall(r"Departmental Income \(Loss\)\s+(\([\d,]+\)|[\d,]+)", detail)]
    row["casino_dept_income"], row["rooms_dept_income"] = income[0], income[1]
    if contra[0]:
        row["casino_comps"] = contra[0]
    else:  # old basis: comps are the casino department's first "Complimentary Expense" line
        casino = detail[detail.index("Casino Department"):detail.index("Rooms Department")]
        row["casino_comps"] = num(re.search(r"Complimentary Expense\s+([\d,]+)", casino).group(1))
    return row


def year_row(fy):
    return text_year(fy) if fy >= 2018 else scanned_year(fy)


def main():
    os.environ["OMP_THREAD_LIMIT"] = "1"   # one thread per tesseract; the pool runs four at once
    CACHE.mkdir(parents=True, exist_ok=True)
    years = sorted(int(p.name[:4]) for p in RAW.glob("*-abstract.pdf"))
    with Pool(4) as pool:   # OCR is slow; scanned years run in parallel
        rows = pool.map(year_row, years)
    for row in rows:
        fy = row["fy"]
        share = f"{row['gaming'] / row['total']:.1%}" if row.get("total") else "-"
        print(f"FY{fy}: {row['method']}, gaming share {share}", flush=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    failed = [r["fy"] for r in rows if not r.get("total")]
    print(f"wrote {OUT.relative_to(ROOT)}; {len(rows) - len(failed)} of {len(rows)} years passed the checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
