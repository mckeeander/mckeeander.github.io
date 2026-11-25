#!/usr/bin/env python3
"""Download the Nevada Gaming Control Board's annual Gaming Abstract, FY1990 on.

    python scripts/fetch_abstract.py

The Abstract is the board's yearly summary of casino financial statements: revenue,
expenses and income by department (gaming, rooms, food, beverage, other) for groups
of licensees. The PDFs are linked from the board's Abstract page under irregular
names, so links are read from that page and matched to fiscal years.

Files go to data/raw/abstract/ (not committed: ~200 MB). Every download is recorded
in data/manifest_abstract.csv with its URL, size and SHA-256, which is committed.
"""
import csv
import datetime as dt
import hashlib
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "abstract"
MANIFEST = ROOT / "data" / "manifest_abstract.csv"
PAGE = "https://gaming.nv.gov/about/abstract/report/"
SITE = "https://gaming.nv.gov"
UA = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-data-pipeline)"}


def get(url):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&%"), headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def links():
    """{fiscal year: url} for every Abstract PDF on the board's page."""
    html = get(PAGE).decode("utf-8", "replace")
    found = {}
    for href in re.findall(r'href="([^"]+\.pdf)"', html, re.I):
        if "press-release" in href.lower():
            continue
        m = re.search(r"(?:^|[^\d])((?:19|20)\d\d)(?:[^\d]|$)", href.rsplit("/", 1)[-1])
        if m:
            found[int(m.group(1))] = href if href.startswith("http") else SITE + href
    return dict(sorted(found.items()))


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = {}
    if MANIFEST.exists():
        rows = {int(r["fy"]): r for r in csv.DictReader(MANIFEST.open())}
    for fy, url in links().items():
        dest = RAW / f"{fy}-abstract.pdf"
        if not dest.exists():
            print(f"FY{fy}: downloading")
            dest.write_bytes(get(url))
            time.sleep(1)
        data = dest.read_bytes()
        rows[fy] = {"fy": fy, "url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                    "fetched": rows.get(fy, {}).get("fetched") or dt.date.today().isoformat()}
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fy", "url", "bytes", "sha256", "fetched"])
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))
    print(f"{len(rows)} Abstracts in {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
