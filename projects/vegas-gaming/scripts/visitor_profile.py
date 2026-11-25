#!/usr/bin/env python3
"""Download and parse the LVCVA's Las Vegas Visitor Profile Study, 2003 on.

    python scripts/visitor_profile.py

The Visitor Profile Study is an annual survey of about 3,600 visitors (in person until
2021; an online component was added in 2022). Each report ends with summary tables
covering the last four or five years, so a handful of reports gives a continuous
series. Older reports come from the Nevada State Library's state-publications archive;
the latest is on lvcva.com along with a spreadsheet ("matrix") of the current year.
No survey was run in 2020.

Writes data/processed/visitor_profile.csv: share of visitors who gambled, trip gambling
budget (among those who gambled), and average trip spending on food and drink,
shopping and shows, plus lodging per night. Dollar values are as reported (nominal).
Where reports overlap, the later report's (sometimes restated) figure wins.
"""
import csv
import datetime as dt
import hashlib
import re
import subprocess
import time
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "visitor_profile"
MANIFEST = ROOT / "data" / "manifest_visitor_profile.csv"
OUT = ROOT / "data" / "processed" / "visitor_profile.csv"
UA = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-data-pipeline)"}
NSLA = "https://epubs.nsla.nv.gov/statepubs/epubs/442242-{y}.pdf"
# Reports whose summary tables together cover 2003-2024 (2006: 2003-06, 2011: 2007-11,
# 2016: 2012-16, 2021: 2016-21, 2024: 2019-24).
REPORTS = {y: NSLA.format(y=y) for y in (2006, 2011, 2016, 2021, 2024)}
MATRIX_2025 = ("https://assets.simpleviewcms.com/simpleview/raw/upload/v1/clients/lasvegas/"
               "2025_LasVegasVPS_Matrix_Snapshot_Excel_41461651-2aa7-464a-9b23-744c984c4e9b.xlsx")

ROWS = {
    "gambled_pct": r"(Proportion who gambled while visiting|Gambled while in Las Vegas \(% of all visitors\))",
    "gambling_budget": r"(Average trip gambling budget|Avg\. gambling budget for trip)",
    "food_drink": r"(Average trip expenditures for food and drink|Avg\. spend on Food and Drink)",
    "shopping": r"(Average trip expenditures for shopping|Avg\. spend on Shopping)",
    "shows": r"(Average trip expenditures for shows|Avg\. spend on Shows/Entertainment)",
    "lodging_night": r"(Lodging expenditures \(average per|Avg\. per night spend on Lodging)",
}
MATRIX_ROWS = {"gambled_pct": "Gambled During Visit", "gambling_budget": "Gambling Budget (among those who gambled)",
               "food_drink": "Average Spent per Trip on Food and Drink", "shopping": "Average Spent per Trip on Shopping",
               "shows": "Average Spent per Trip on Show / Entertainment"}
FIELDS = ["year", *ROWS, "source"]


def fetch(url, dest):
    if not dest.exists():
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            dest.write_bytes(r.read())
        time.sleep(1)
    data = dest.read_bytes()
    return {"file": dest.name, "url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "fetched": dt.date.today().isoformat()}


def value(v):
    v = v.replace("$", "").replace(",", "")
    return float(v[:-1]) / 100 if v.endswith("%") else float(v)


def summary_tables(pdf):
    """{field: {year: value}} from a report's summary tables."""
    lines = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.splitlines()
    out, header = {}, None
    for i, line in enumerate(lines):
        years = re.findall(r"\b(20[0-2]\d)\b", line)
        if len(years) >= 4 and re.fullmatch(r"[\s\d]+", line):
            header = [int(y) for y in years]
        for field, pat in ROWS.items():
            if header and field not in out and re.search(pat, line, re.I):
                for j in range(i, min(i + 3, len(lines))):   # labels can wrap onto the next line
                    tail = re.sub(r"^.*?[A-Za-z)]\s{2,}", "", lines[j]) if j == i else lines[j]
                    vals = [v for v in re.findall(r"(\$?[\d,]+\.?\d*%?)(?=\s|$)", tail.strip()) if re.search(r"\d", v)]
                    if len(vals) == len(header):
                        out[field] = {y: value(v) for y, v in zip(header, vals)}
                        break
    return out


def matrix_2025(xlsx):
    ws = openpyxl.load_workbook(xlsx, data_only=True).active
    out = {}
    for row in ws.iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        for field, label in MATRIX_ROWS.items():
            if len(cells) > 2 and isinstance(cells[1], str) and cells[1].strip() == label:
                out[field] = float(cells[2])   # first number column is all visitors
    return out


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest, series = [], {}
    for y, url in REPORTS.items():
        dest = RAW / f"vps-{y}.pdf"
        manifest.append(fetch(url, dest))
        for field, by_year in summary_tables(dest).items():
            for yr, v in by_year.items():
                series.setdefault(yr, {})[field] = v
                series[yr]["source"] = f"Visitor Profile {y}"
    dest = RAW / "vps-2025-matrix.xlsx"
    manifest.append(fetch(MATRIX_2025, dest))
    series[2025] = {**matrix_2025(dest), "source": "Visitor Profile 2025 (matrix)"}

    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "url", "bytes", "sha256", "fetched"])
        w.writeheader()
        w.writerows(manifest)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for yr in sorted(series):
            w.writerow({"year": yr, **{k: series[yr].get(k) for k in FIELDS[1:]}})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(series)} years ({min(series)}-{max(series)})")


if __name__ == "__main__":
    main()
