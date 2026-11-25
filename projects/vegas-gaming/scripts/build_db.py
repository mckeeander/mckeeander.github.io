#!/usr/bin/env python3
"""Build the DuckDB database, run the data tests, export JSON for the dashboard.

    python scripts/build_db.py

Runs sql/01_load.sql, 02_model.sql and 03_metrics.sql in order, then every query in
sql/04_tests.sql (each must return no rows), then writes data/dashboard/*.json.
Exits non-zero if any test fails, so a bad month can't reach the dashboard.
"""
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "vegas.duckdb"
EXPORT = ROOT / "data" / "dashboard"

EXPORTS = {
    "area_monthly": "SELECT * FROM v_area_monthly WHERE area_key IN ('statewide','strip','downtown') ORDER BY area_key, month",
    "game_mix": "SELECT * FROM v_game_mix WHERE area_key IN ('statewide','strip','downtown') ORDER BY area_key, month, game_group",
    "baccarat": "SELECT * FROM v_baccarat ORDER BY month",
    "strip_tourism": "SELECT * FROM v_strip_tourism ORDER BY month",
    "seasonality": "SELECT * FROM v_seasonality WHERE area_key IN ('statewide','strip','downtown') ORDER BY area_key, month_num",
    "kpi_latest": "SELECT * FROM v_kpi_latest",
    "market_per_resident": "SELECT * FROM v_market_per_resident ORDER BY year",
    "covid_recovery": "SELECT * FROM v_covid_recovery ORDER BY month",
    "visitors_annual": "SELECT * FROM v_visitors_annual ORDER BY year",
    "strip_rooms_annual": "SELECT * FROM v_strip_rooms_annual ORDER BY year",
    "table_economics": "SELECT * FROM v_table_economics ORDER BY game, year",
    "baccarat_by_year": "SELECT * FROM v_baccarat_by_year ORDER BY year",
    # Gaming Abstract, one row per fiscal year, consistent (pre-ASC 606) basis, nominal dollars.
    "strip_departments": """SELECT fy, gaming, rooms, food, beverage, other, total, gaming_share,
                            casino_dept_income, rooms_dept_income, to_2025_dollars
                            FROM v_strip_departments ORDER BY fy""",
}


def tests(sql):
    """Yield (name, query) pairs from a file of '-- test: name' + query blocks."""
    for block in re.split(r"\n(?=-- test:)", sql):
        m = re.match(r"-- test:\s*(.+?)\n(.+)", block.strip(), re.S)
        if m:
            yield m.group(1).strip(), m.group(2).strip().rstrip(";")


def clean(v):
    if isinstance(v, float):
        return None if math.isnan(v) else round(v, 6)
    if isinstance(v, date):
        return v.strftime("%Y-%m")
    return v


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    import os
    os.chdir(ROOT)  # SQL reads CSVs by relative path
    for name in ("01_load.sql", "02_model.sql", "03_metrics.sql"):
        con.execute((ROOT / "sql" / name).read_text())
        print(f"ran {name}")

    failed = 0
    for name, q in tests((ROOT / "sql" / "04_tests.sql").read_text()):
        rows = con.execute(q).fetchall()
        status = "ok" if not rows else f"FAILED ({len(rows)} rows, e.g. {rows[:3]})"
        failed += bool(rows)
        print(f"  test: {name}: {status}")
    if failed:
        print(f"{failed} test(s) failed; dashboard data not exported")
        return 1

    EXPORT.mkdir(parents=True, exist_ok=True)
    for name, q in EXPORTS.items():
        cur = con.execute(q)
        cols = [d[0] for d in cur.description]
        rows = [[clean(v) for v in r] for r in cur.fetchall()]
        # Column-oriented: compact, and easy to turn into chart rows in the browser.
        data = {"columns": cols, "rows": rows}
        (EXPORT / f"{name}.json").write_text(json.dumps(data, separators=(",", ":")))
        print(f"exported {name}.json ({len(rows)} rows)")

    # Compact game mix for the dashboard: one month list, then per area and game group an
    # array of win in whole $ thousands (null = no game detail that month).
    months = [clean(r[0]) for r in con.execute("SELECT month FROM dim_month ORDER BY month").fetchall()]
    idx = {m: i for i, m in enumerate(months)}
    areas = {}
    for month, area, group, win in con.execute(
            "SELECT month, area_key, game_group, win FROM v_game_mix "
            "WHERE area_key IN ('statewide','strip','downtown')").fetchall():
        arr = areas.setdefault(area, {}).setdefault(group, [None] * len(months))
        arr[idx[clean(month)]] = round(win / 1000)
    (EXPORT / "dash_game_mix.json").write_text(json.dumps({"months": months, "areas": areas}, separators=(",", ":")))
    print(f"exported dash_game_mix.json ({len(months)} months)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
