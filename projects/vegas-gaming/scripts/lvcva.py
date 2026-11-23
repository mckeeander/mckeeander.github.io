#!/usr/bin/env python3
"""Download and parse the LVCVA's monthly tourism spreadsheets (Las Vegas sheet).

    python lvcva.py            # fetch any new workbooks, then rebuild the CSV

The LVCVA's executive-summary page links one workbook per year (2019 on). Files go to
data/raw/lvcva/ (not committed); data/manifest_lvcva.csv records URL, size and SHA-256.
Output: data/processed/lvcva_monthly.csv, one row per month, plus a flag column per
indicator ('r' = revised, 'e' = estimate) as printed by the LVCVA.

lvcva.com refuses requests without a browser-style User-Agent, so one is sent.
"""
import csv
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "lvcva"
MANIFEST = ROOT / "data" / "manifest_lvcva.csv"
OUT = ROOT / "data" / "processed" / "lvcva_monthly.csv"
PAGE = "https://www.lvcva.com/research/reports/post/lvcva-executive-summary-of-southern-nevada-tourism-indicators/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-data-pipeline; +https://mckeeander.github.io)"}

# Row label (start of the text, case-insensitive, leading spaces ignored) -> column name.
INDICATORS = [
    ("visitor volume", "visitors"),
    ("convention attendance", "convention_attendance"),
    ("available room inventory", "room_inventory"),
    ("total occupancy", "occupancy"),
    ("weekend occupancy", "occupancy_weekend"),
    ("midweek occupancy", "occupancy_midweek"),
    ("strip occupancy", "occupancy_strip"),
    ("downtown occupancy", "occupancy_downtown"),
    ("average daily room rate", "adr"),
    ("strip adr", "adr_strip"),
    ("downtown adr", "adr_downtown"),
    ("revenue per available room", "revpar"),
    ("strip revpar", "revpar_strip"),
    ("downtown revpar", "revpar_downtown"),
    ("total room nights occupied", "room_nights"),
    ("total en/deplaned passengers", "air_passengers"),
    ("gaming revenue : clark", "gaming_rev_clark"),
    ("gaming revenue: clark", "gaming_rev_clark"),
    ("gaming revenue: las vegas strip", "gaming_rev_strip"),
    ("gaming revenue: downtown", "gaming_rev_downtown"),
    ("gaming revenue: boulder", "gaming_rev_boulder"),
]
FIELDS = [c for _, c in INDICATORS if c != "gaming_rev_clark"] + ["gaming_rev_clark"]
FIELDS = list(dict.fromkeys(FIELDS))


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if MANIFEST.exists():
        with MANIFEST.open() as f:
            manifest = {r["file"]: r for r in csv.DictReader(f)}
    html = get(PAGE).decode("utf-8", "replace")
    links = sorted(set(re.findall(r'https?://[^"\' ]+\.xlsx', html)))
    for url in links:
        m = re.search(r"(20\d\d)", url.rsplit("/", 1)[-1])
        if not m:
            continue
        name = f"lvcva-{m.group(1)}.xlsx"
        data = get(url)
        sha = hashlib.sha256(data).hexdigest()
        if name in manifest and manifest[name]["sha256"] == sha and (RAW / name).exists():
            continue
        (RAW / name).write_bytes(data)
        manifest[name] = {"file": name, "url": url, "bytes": len(data), "sha256": sha,
                          "fetched": dt.date.today().isoformat()}
        print(f"  {name}: updated")
        time.sleep(0.3)
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "url", "bytes", "sha256", "fetched"])
        w.writeheader()
        for k in sorted(manifest):
            w.writerow(manifest[k])


def parse_book(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = next(wb[s] for s in wb.sheetnames if s.lower().startswith("las vegas"))
    header_row, cols = None, {}
    for row in ws.iter_rows():
        if row[0].value and str(row[0].value).strip().lower().startswith("tourism indicators"):
            header_row = row[0].row
            for c in row:
                if isinstance(c.value, (dt.datetime, dt.date)):
                    cols[c.column] = c.value.strftime("%Y-%m")
            break
    if not cols:
        raise ValueError(f"{path.name}: no month header row")
    months = {m: {"month": m} for m in cols.values()}
    for row in ws.iter_rows(min_row=header_row + 1):
        label = str(row[0].value or "").strip().lower()
        if label.startswith("change from previous"):
            break  # the year-over-year block below repeats the labels
        field = next((c for key, c in INDICATORS if label.startswith(key)), None)
        if not field:
            continue
        cells = {c.column: c.value for c in row}
        for col, month in cols.items():
            v = cells.get(col)
            flag = cells.get(col + 1)
            try:
                months[month][field] = float(v)
            except (TypeError, ValueError):
                continue  # blank, "N/A" (e.g. the 2020 closure) and other non-numbers are missing
            if isinstance(flag, str) and flag.strip().lower() in ("r", "e"):
                months[month][field + "_flag"] = flag.strip().lower()
    return [m for m in months.values() if len(m) > 1]


def main():
    try:
        fetch()
    except Exception as e:
        print(f"! could not refresh from lvcva.com ({e}); parsing files already on disk", file=sys.stderr)
    rows = {}
    for path in sorted(RAW.glob("lvcva-*.xlsx")):
        for r in parse_book(path):
            rows[r["month"]] = r  # later workbooks (with revisions) win
    out = sorted(rows.values(), key=lambda r: r["month"])
    fields = ["month"] + [x for f in FIELDS for x in (f, f + "_flag")]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} months: {out[0]['month']} to {out[-1]['month']}")


if __name__ == "__main__":
    main()
