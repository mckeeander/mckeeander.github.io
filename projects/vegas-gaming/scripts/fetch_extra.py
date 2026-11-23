#!/usr/bin/env python3
"""Context data: inflation, Clark County population, LVCVA annual history.

    python scripts/fetch_extra.py

Writes to data/processed/:
  cpi_monthly.csv        CPI-U, U.S. city average, not seasonally adjusted (BLS series CUUR0000SA0)
  clark_population.csv   Census Bureau county population estimates, Clark County NV (vintages 2020 and 2025)
  lvcva_annual.csv       LVCVA "Las Vegas Historic Tourism Statistics" 1970 on (visitors, conventions, rooms, occupancy)
Raw downloads go to data/raw/extra/ (not committed).
"""
import csv
import json
import re
import urllib.request
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "extra"
OUT = ROOT / "data" / "processed"
UA = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-data-pipeline; +https://mckeeander.github.io)"}
BLS = "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0?startyear={a}&endyear={b}"
CENSUS = {
    "co-est2020-alldata.csv": ("https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/totals/co-est2020-alldata.csv", range(2010, 2020)),
    "co-est2025-alldata.csv": ("https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/co-est2025-alldata.csv", range(2020, 2026)),
}
HIST_PAGE = "https://www.lvcva.com/research/reports/post/historical-visitation-statistics-1970-2025/"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return r.read()


def cpi():
    rows = {}
    for a, b in ((2010, 2019), (2020, 2029)):
        d = json.loads(get(BLS.format(a=a, b=b)))
        (RAW / f"bls_{a}.json").write_text(json.dumps(d))
        for x in d["Results"]["series"][0]["data"]:
            if x["period"].startswith("M") and x["period"] != "M13":
                try:
                    rows[f"{x['year']}-{x['period'][1:]}"] = float(x["value"])
                except ValueError:
                    pass  # unpublished month (e.g. Oct 2025, federal shutdown); interpolated in SQL
    with (OUT / "cpi_monthly.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["month", "cpi_u"]); w.writerows(sorted(rows.items()))
    return len(rows)


def population():
    pop = {}
    for name, (url, years) in CENSUS.items():
        path = RAW / name
        path.write_bytes(get(url))
        r = next(x for x in csv.DictReader(path.open(encoding="latin-1")) if x["STATE"] == "32" and x["COUNTY"] == "003")
        for y in years:
            pop[y] = int(r[f"POPESTIMATE{y}"])
    with (OUT / "clark_population.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["year", "population"]); w.writerows(sorted(pop.items()))
    return len(pop)


def history():
    html = get(HIST_PAGE).decode("utf-8", "replace")
    url = re.search(r'https?://[^"\' ]+Historical[^"\' ]+\.pdf', html).group(0)
    (RAW / "hist.pdf").write_bytes(get(url))
    text = pdfplumber.open(RAW / "hist.pdf").pages[0].extract_text()
    out = []
    for line in text.split("\n"):
        m = re.match(r"^(19[7-9]\d|20\d\d)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(\S+)\s+(\S+)\s+([\d.]+)%", line)
        if m:
            y, vis, conv, inv, _, _, occ = m.groups()
            out.append((int(y), int(vis.replace(",", "")), int(conv.replace(",", "")), int(inv.replace(",", "")), float(occ) / 100))
    with (OUT / "lvcva_annual.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["year", "visitors", "convention_attendance", "room_inventory", "occupancy"]); w.writerows(out)
    return len(out)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"CPI months: {cpi()}; population years: {population()}; LVCVA history years: {history()}")
