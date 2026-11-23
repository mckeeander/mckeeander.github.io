#!/usr/bin/env python3
"""Download Nevada Gaming Control Board monthly revenue reports.

    python fetch_ngcb.py                 # everything from Jan 2010 that isn't downloaded yet
    python fetch_ngcb.py --since 2025-01 # only months from Jan 2025

Reports up to May 2025 live at a predictable legacy URL. Later reports are on the
board's new site under irregular file names, so they are found by reading the
gaming-revenue listing page and matching each link to its month.

Files go to data/raw/ngcb/ (not committed: ~80 MB). Every download is recorded in
data/manifest_ngcb.csv with its URL, size and SHA-256, which is committed.
"""
import argparse
import csv
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ngcb"
MANIFEST = ROOT / "data" / "manifest_ngcb.csv"

LEGACY = "https://gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/{y}{mon}-gri.pdf"
LISTING = "https://gaming.nv.gov/about/gaming-revenue/information/"
SITE = "https://gaming.nv.gov"
LEGACY_LAST = (2025, 5)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FULL = ["january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-data-pipeline; +https://mckeeander.github.io)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")


def new_site_links():
    """{(year, month): url} for full monthly reports linked from the listing page."""
    html, _ = get(LISTING)
    html = html.decode("utf-8", "replace")
    found = {}
    for href in re.findall(r'href="([^"]+\.pdf)"', html, flags=re.I):
        name = href.lower().rsplit("/", 1)[-1]
        if "revenue-report" not in name or name.startswith("mrr"):
            continue  # skip the 2-page press releases
        m = re.search(r"(" + "|".join(FULL) + r")[-_ ]*(20\d\d)", name)
        if m:
            found[(int(m.group(2)), FULL.index(m.group(1)) + 1)] = href if href.startswith("http") else SITE + href
    return found


def months(since):
    y, m = since
    today = dt.date.today()
    while (y, m) <= (today.year, today.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2010-01")
    args = ap.parse_args()
    since = tuple(int(x) for x in args.since.split("-"))

    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if MANIFEST.exists():
        with MANIFEST.open() as f:
            manifest = {r["month"]: r for r in csv.DictReader(f)}

    links = {}
    try:
        links = new_site_links()
    except Exception as e:  # listing page down: legacy months can still be fetched
        print(f"! listing page unavailable: {e}", file=sys.stderr)

    missing = []
    for y, m in months(since):
        key = f"{y}-{m:02d}"
        path = RAW / f"ngcb-{key}.pdf"
        if path.exists() and key in manifest:
            continue
        url = LEGACY.format(y=y, mon=MONTHS[m - 1]) if (y, m) <= LEGACY_LAST else links.get((y, m))
        if not url:
            missing.append(key)
            continue
        try:
            data, ctype = get(url)
        except Exception as e:
            print(f"  {key}: failed ({e})", file=sys.stderr)
            missing.append(key)
            continue
        if not data.startswith(b"%PDF"):
            print(f"  {key}: not a PDF ({ctype})", file=sys.stderr)
            missing.append(key)
            continue
        path.write_bytes(data)
        manifest[key] = {"month": key, "url": url, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(),
                         "fetched": dt.date.today().isoformat()}
        print(f"  {key}: {len(data) / 1e6:.1f} MB")
        time.sleep(0.5)  # be polite to the state's server

    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["month", "url", "bytes", "sha256", "fetched"])
        w.writeheader()
        for k in sorted(manifest):
            w.writerow(manifest[k])
    print(f"{len(manifest)} reports on record; not found: {', '.join(missing) or 'none'}")


if __name__ == "__main__":
    main()
