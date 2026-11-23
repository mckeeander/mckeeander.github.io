"""Phase 1 probe: parse the current-month Las Vegas Strip table from an NGCB
monthly revenue report (both the pre-2019 and current layouts) and check that
the game rows add up to the report's own totals.

    python3 -I parse_ngcb.py REPORT.pdf [REPORT.pdf ...]
"""
import re
import sys

import pdfplumber

NUM = re.compile(r"^\(?-?[\d,]+(?:\.\d+)?\)?$")


def num(tok):
    neg = tok.startswith("(") or tok.startswith("-")
    v = float(tok.strip("()").replace(",", "").lstrip("-"))
    return -v if neg else v


def strip_page(pdf):
    for page in pdf.pages:
        text = page.extract_text() or ""
        head = " ".join(text.split("\n")[:3]).upper()
        if "LAS VEGAS STRIP AREA" in head and "ALL NONRESTRICTED" in head:
            return text
    return None


def first_period(name, nums):
    """Win amount for the current month from one row's numbers (first of three periods)."""
    per = nums[: len(nums) // 3] if len(nums) % 3 == 0 and len(nums) >= 6 else nums
    n = len(per)
    if n == 5:        # locations, units, win, % change, win %
        idx = 2
    elif n == 4:      # "other" rows: units, win, % change, win %; everything else: locations, units, win, % change
        idx = 1 if name.upper().startswith("OTHER") else 2
    elif n == 3:      # units, win, % change
        idx = 1
    elif n == 2:      # win, % change (total gaming)
        idx = 0
    else:
        return None, per
    return per[idx], per


def split_row(line):
    """Return (name, numbers-for-all-periods) for both layouts."""
    if "|" in line:
        parts = [p.strip() for p in line.split("|")]
        name = parts[0]
        periods = [p for p in parts[1:] if p]
        if not periods:
            return name, []
        toks = periods[0].split()
        if not toks or not all(NUM.match(t) for t in toks):
            return name, []
        return name, [num(t) for t in toks] * 3  # treat first period only
    toks = line.split()
    k = len(toks)
    while k > 0 and NUM.match(toks[k - 1]):
        k -= 1
    nums = toks[k:]
    while nums and len(nums) % 3:       # e.g. "Race Book (1) 35 ..." -> move "(1)" into the name
        toks_k = nums.pop(0)
        k += 1
    name = " ".join(toks[:k])
    return name, [num(t) for t in nums]


def parse(path):
    with pdfplumber.open(path) as pdf:
        text = strip_page(pdf)
    if text is None:
        return {"file": path, "error": "no Strip page with text (scanned image?)"}
    rows, section = [], None
    totals = {}
    for line in text.split("\n"):
        up = line.upper()
        if up.startswith("GAMES AND TABLES") or up.startswith("TABLE, COUNTER AND CARD GAMES"):
            section = "tables"; continue
        if up.startswith("SLOT MACHINES"):
            section = "slots"; continue
        if section is None:
            continue
        name, nums = split_row(line)
        if not nums or not name:
            continue
        key = name.upper().replace("-", " ").strip()
        win, _ = first_period(name, nums)
        if win is None:
            continue
        if key.startswith("TOTAL GAMING"):
            totals["gaming"] = win; break
        if key.startswith("TOTAL"):
            totals[section] = win; continue
        rows.append((section, name, win))
    return {"file": path, "rows": rows, "totals": totals}


def check(res):
    if "error" in res:
        return f"{res['file'].split('/')[-1]}: {res['error']}"
    rows, t = res["rows"], res["totals"]
    out = [f"{res['file'].split('/')[-1]}: {len(rows)} rows"]
    for sec in ("tables", "slots"):
        s = sum(w for sc, n, w in rows if sc == sec)
        card = sum(w for sc, n, w in rows if sc == sec and "CARD GAMES" in n.upper())
        tot = t.get(sec)
        ok = tot is not None and (abs(s - tot) <= 2 or abs(s - card - tot) <= 2)
        out.append(f"  {sec:6s} rows sum {s:>10,.0f}  (excl. card games {s - card:>10,.0f})  report total {tot}  {'OK' if ok else 'MISMATCH'}")
    if "gaming" in t:
        card_outside = sum(w for sc, n, w in rows if "CARD GAMES" in n.upper()) if abs(sum(w for sc, n, w in rows if sc == "tables") - t.get("tables", 0)) > 2 else 0
        recon = t.get("tables", 0) + t.get("slots", 0) + card_outside
        out.append(f"  total gaming (report) {t['gaming']:,.0f}  vs tables+slots{'+card games' if card_outside else ''} {recon:,.0f}  {'OK' if abs(recon - t['gaming']) <= 2 else 'MISMATCH'}")
    bac = [w for sc, n, w in rows if n.upper() == "BACCARAT"]
    out.append(f"  baccarat {bac}")
    return "\n".join(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(check(parse(p)))
