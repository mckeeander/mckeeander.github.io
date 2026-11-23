#!/usr/bin/env python3
"""Parse NGCB monthly revenue reports into tidy CSVs, with validation.

    python parse_ngcb.py

Reads data/raw/ngcb/ngcb-YYYY-MM.pdf and writes:
  data/processed/ngcb_games.csv     one row per month x area x game (current month only)
  data/processed/ngcb_totals.csv    one row per month x area: tables, card games, slots, total
  data/processed/ngcb_checks.csv    every validation result

Numbers are placed in columns by their horizontal position on the page, using the
column headings (LOC'S/Loc*, UNITS, AMOUNT, CHANGE/Chg, PERCENT) as anchors, so blank
cells can't shift values into the wrong column. Win amounts are in $ thousands, as
printed. A report fails validation if its game rows don't add up to its own totals.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ngcb"
OUT = ROOT / "data" / "processed"

NUM = re.compile(r"^\(?-?[\d,]*\.?\d+\)?$")
HEAD_WORDS = {"LOC'S": "locations", "LOC*": "locations", "UNITS": "units", "AMOUNT": "win",
              "CHANGE": "pct_change", "CHG": "pct_change", "PERCENT": "win_pct"}
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
          "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
TOL = 5  # $000: each line is rounded to the nearest thousand, so long sums can drift a few thousand

# One canonical name per game across both layouts and the years.
CANON = {
    "TWENTY ONE": "Blackjack", "CRAPS": "Craps", "ROULETTE": "Roulette", "3 CARD POKER": "3-Card Poker",
    "BACCARAT": "Baccarat", "MINI BACCARAT": "Mini-Baccarat", "KENO": "Keno", "BINGO": "Bingo",
    "CARIBBEAN STUD": "Caribbean Stud", "LET IT RIDE": "Let It Ride", "PAI GOW": "Pai Gow",
    "PAI GOW POKER": "Pai Gow Poker", "RACE BOOK": "Race Book", "SPORTS POOL": "Sports Pool",
    "CARD GAMES": "Card Games", "OTHER GAMES": "Other Games", "OTHER": "Other",
    "ULTIM TEXAS HOLD EM": "Ultimate Texas Hold'em", "ULTIMATE TEXAS HOLD EM": "Ultimate Texas Hold'em",
    "1 CENT": "1¢", "5 CENT": "5¢", "25 CENT": "25¢", "1 DOLLAR": "$1", "MEGABUCKS": "Megabucks",
    "5 DOLLARS": "$5", "25 DOLLARS": "$25", "100 DOLLARS": "$100",
    "MULTI DENOMINATION": "Multi-denomination", "OTHER SLOT MACHINES": "Other",
}


def num(tok):
    neg = tok.startswith("(") or tok.startswith("-")
    v = float(tok.strip("()").lstrip("-").replace(",", ""))
    return -v if neg else v


def norm(name):
    s = re.sub(r"\(\d\)", "", name.upper())
    s = re.sub(r"[^A-Z0-9 ]", " ", s.replace("'", ""))
    return re.sub(r"\s+", " ", s).strip()


def canon(name, section):
    key = norm(name)
    if key == "OTHER":
        return "Other games" if section == "tables" else "Other slots"
    if key in ("OTHER GAMES",):
        return "Other games"
    if key in ("OTHER SLOT MACHINES",):
        return "Other slots"
    return CANON.get(key, name.strip().title())


def lines_of(page):
    """Group words into lines by vertical position."""
    words = [w for w in page.extract_words(keep_blank_chars=False) if w["text"] not in ("|", "||")]
    rows = defaultdict(list)
    for w in words:
        rows[round(w["top"] / 2.5)].append(w)
    return [sorted(rows[k], key=lambda w: w["x0"]) for k in sorted(rows)]


def column_anchors(line):
    """If this line is a column-heading line, return [(x1, field)] for the current-month period."""
    heads = [(w["x1"], HEAD_WORDS[w["text"].upper()]) for w in line if w["text"].upper() in HEAD_WORDS]
    if len(heads) >= 15:
        return heads[:5], heads[0][0] - 22  # anchors, left edge of the number area
    return None


def area_title(text):
    first = " ".join(text.split("\n")[:4])
    m = re.search(r"(?:Gaming Revenue Report\s+)?([A-Za-z .']+?)\s*(?:-|\|)?\s*ALL NONRESTRICTED LOCATIONS", first, re.I)
    if not m:
        return None
    name = re.sub(r"^(NEVADA (STATE )?GAMING CONTROL BOARD\s*)?(GAMING REVENUE REPORT\s*)?", "", m.group(1).strip(), flags=re.I)
    return re.sub(r"\s+", " ", name).strip().title()


def report_month(text):
    m = re.search(r"CURRENT MONTH(?: SUMMARY)?\s*-\s*([A-Z]+)[,-]\s*(\d{4})", text.upper())
    return f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}" if m else None


def parse_page(page):
    rows, totals = [], {}
    section, anchors, left = None, None, None
    for line in lines_of(page):
        text = " ".join(w["text"] for w in line)
        up = text.upper()
        if up.startswith("GAMES AND TABLES") or up.startswith("TABLE, COUNTER AND CARD GAMES"):
            section = "tables"
        elif up.startswith("SLOT MACHINES"):
            section = "slots"
        got = column_anchors(line)
        if got:
            anchors, left = got
            continue
        if section is None or anchors is None:
            continue
        name = " ".join(w["text"] for w in line if w["x1"] < left)
        nums = [w for w in line if w["x1"] >= left and NUM.match(w["text"])]
        if not name or not nums:
            continue
        vals = {}
        period_right = anchors[-1][0] + 12
        for w in nums:
            if w["x1"] > period_right:
                break  # three- and twelve-month columns
            field = min(anchors, key=lambda a: abs(a[0] - w["x1"]))[1]
            vals[field] = num(w["text"])
        key = norm(name)
        if key.startswith("TOTAL GAMING"):
            # the total row has only win and % change; take the first number in the period
            first = [w for w in nums if w["x1"] <= period_right]
            totals["gaming"] = num(first[0]["text"]) if first else None
            break
        if "win" not in vals:
            if key.startswith("TOTAL") or key in CANON or key in ("OTHER",):
                vals.setdefault("win", 0.0)  # blank current-month cell, e.g. a discontinued game
            else:
                continue
        if key.startswith("TOTAL"):
            totals[section] = vals["win"]
            continue
        rows.append(dict(section=section, game_raw=name.strip(), game=canon(name, section), **vals))
    return rows, totals


def check(rows, totals):
    """Return (ok, card_outside_tables, notes)."""
    notes = []
    for sec in ("tables", "slots"):
        # Small areas print a single "Other" row and no total line for a section
        # ("unit detail is shown separately only when there are 3 or more locations").
        # Use the rows; the total-gaming check below still ties them to the report.
        if sec not in totals and any(r["section"] == sec for r in rows):
            totals[sec] = sum(r["win"] for r in rows if r["section"] == sec)
            notes.append(f"no {sec} total line")
    tables = sum(r["win"] for r in rows if r["section"] == "tables")
    card = sum(r["win"] for r in rows if r["game"] == "Card Games")
    slots = sum(r["win"] for r in rows if r["section"] == "slots")
    card_outside = abs(tables - totals.get("tables", float("nan"))) > TOL and abs(tables - card - totals.get("tables", 0)) <= TOL
    t_ok = abs((tables - card if card_outside else tables) - totals.get("tables", float("nan"))) <= TOL
    s_ok = abs(slots - totals.get("slots", float("nan"))) <= TOL
    g = totals.get("tables", 0) + totals.get("slots", 0) + (card if card_outside else 0)
    g_ok = abs(g - totals.get("gaming", float("nan"))) <= TOL
    if not t_ok: notes.append(f"tables rows {tables:,.0f} vs total {totals.get('tables')}")
    if not s_ok: notes.append(f"slot rows {slots:,.0f} vs total {totals.get('slots')}")
    if not g_ok: notes.append(f"tables+slots {g:,.0f} vs total gaming {totals.get('gaming')}")
    ok = t_ok and s_ok and g_ok
    return ok, card_outside, "; ".join(notes) if not ok or notes else ""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    games, tots, checks = [], [], []
    for path in sorted(RAW.glob("ngcb-*.pdf")):
        month = path.stem.split("-", 1)[1]
        with pdfplumber.open(path) as pdf:
            if not (pdf.pages[3].extract_text() or "").strip():
                checks.append(dict(month=month, area="(all)", ok="scanned", notes="image-only PDF; no text"))
                print(f"{month}: scanned image, skipped")
                continue
            n_ok = n_bad = 0
            for page in pdf.pages:
                text = page.extract_text() or ""
                area = area_title(text)
                if not area:
                    continue
                printed = report_month(text)
                rows, totals = parse_page(page)
                ok, card_outside, notes = check(rows, totals)
                if printed != month:
                    ok, notes = False, f"report says {printed}; " + notes
                checks.append(dict(month=month, area=area, ok="yes" if ok else "NO", notes=notes))
                n_ok += ok; n_bad += not ok
                for r in rows:
                    games.append(dict(month=month, area=area, section=r["section"], game=r["game"],
                                      game_raw=r["game_raw"], locations=r.get("locations"), units=r.get("units"),
                                      win_k=r["win"], pct_change=r.get("pct_change"), win_pct=r.get("win_pct")))
                card = sum(r["win"] for r in rows if r["game"] == "Card Games")
                tots.append(dict(month=month, area=area,
                                 tables_k=totals.get("tables"), card_games_k=card,
                                 card_games_in_tables="no" if card_outside else "yes",
                                 slots_k=totals.get("slots"), total_k=totals.get("gaming"),
                                 valid="yes" if ok else "no"))
        print(f"{month}: {n_ok} areas ok" + (f", {n_bad} FAILED" if n_bad else ""))

    for name, data in (("ngcb_games.csv", games), ("ngcb_totals.csv", tots), ("ngcb_checks.csv", checks)):
        with (OUT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader(); w.writerows(data)
    bad = [c for c in checks if c["ok"] == "NO"]
    print(f"\n{len(games):,} game rows; {len(tots):,} area-months; {len(bad)} failed checks")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
