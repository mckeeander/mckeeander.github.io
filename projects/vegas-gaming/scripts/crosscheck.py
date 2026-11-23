#!/usr/bin/env python3
"""Compare NGCB total gaming win with the LVCVA's gaming revenue lines.

    python crosscheck.py

Writes data/processed/crosscheck.csv and prints any month where the two sources
differ by more than $1,000 (NGCB reports in thousands, the LVCVA in dollars). The
LVCVA marks later revisions with 'r'; NGCB's original monthly report is not revised,
so a revised LVCVA figure may legitimately differ.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "data" / "processed"
PAIRS = {"Clark County Las Vegas Strip Area": "gaming_rev_strip",
         "Clark County Downtown Las Vegas Area": "gaming_rev_downtown"}


def main():
    ngcb = {(r["month"], r["area"]): r for r in csv.DictReader((P / "ngcb_totals.csv").open())}
    lv = {r["month"]: r for r in csv.DictReader((P / "lvcva_monthly.csv").open())}
    out, diffs = [], []
    for month, l in sorted(lv.items()):
        for area, col in PAIRS.items():
            n = ngcb.get((month, area))
            lval = float(l[col]) if l.get(col) else None
            nval = float(n["total_k"]) * 1000 if n and n["total_k"] else None
            status = "missing NGCB" if nval is None else "missing LVCVA" if lval is None else (
                "match" if abs(nval - lval) <= 1000 else "differs")
            row = dict(month=month, area=area, ngcb=nval, lvcva=lval, lvcva_flag=l.get(col + "_flag", ""),
                       diff=(nval - lval) if nval is not None and lval is not None else None, status=status)
            out.append(row)
            if status != "match":
                diffs.append(row)
    with (P / "crosscheck.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    n_match = sum(r["status"] == "match" for r in out)
    print(f"{n_match} of {len(out)} area-months match to within $1,000")
    for r in diffs:
        d = f"{r['diff']:+,.0f}" if r["diff"] is not None else ""
        print(f"  {r['month']} {r['area'][13:]:<24} {r['status']:<13} {d:>14}  LVCVA flag: {r['lvcva_flag'] or '-'}")


if __name__ == "__main__":
    main()
