# Data: Las Vegas gaming and tourism

Built by the scripts in `../scripts/`. Raw downloads live in `raw/` (not committed);
the manifests record every source file's URL, size and SHA-256 so each number can be
traced back to the exact document it came from.

## Rebuild

```sh
python scripts/fetch_ngcb.py      # download any new NGCB monthly reports
python scripts/parse_ngcb.py      # ~15 min for all years; exits non-zero if a report fails validation
python scripts/lvcva.py           # download and parse the LVCVA workbooks
python scripts/crosscheck.py      # NGCB vs LVCVA gaming revenue
python scripts/build_db.py        # DuckDB model + data tests + dashboard JSON
```

## SQL model (`../sql/`, DuckDB)

| File | What it does |
|---|---|
| `01_load.sql` | Loads the CSVs; lookup tables `dim_area` (stable area keys) and `dim_game` (canonical game names and dashboard groups, covering renames such as "100 Dollar" → "$100") |
| `02_model.sql` | `dim_month` (gap-free month spine, COVID period flagged), `fct_game_month`, `fct_area_month` (NGCB totals; closure and missing months filled from the LVCVA, with a `source` column), `fct_tourism_month` |
| `03_metrics.sql` | Dashboard views: `v_area_monthly` (YoY, rolling 12-month totals, slot share), `v_game_mix`, `v_baccarat` (hold vs. trailing 24-month average), `v_strip_tourism` (win per visitor, occupancy, ADR), `v_seasonality`, `v_kpi_latest` |
| `04_tests.sql` | Data tests; each must return no rows or the build stops before exporting |

`build_db.py` writes `dashboard/*.json` (column-oriented) for the website.

## Files in `processed/`

| File | Grain | Contents |
|---|---|---|
| `ngcb_games.csv` | month × area × game | locations, units, win ($000), % change vs. a year earlier, win % — current month only |
| `ngcb_totals.csv` | month × area | tables, card games, slots and total gaming win ($000); `valid` = passed the sum checks |
| `ngcb_checks.csv` | month × area | result of every validation check |
| `lvcva_monthly.csv` | month | visitors, convention attendance, room inventory, occupancy (all / weekend / midweek / Strip / downtown), ADR, RevPAR, room nights, air passengers, gaming revenue (Clark County, Strip, downtown, Boulder); `*_flag` = `r` revised or `e` estimate, as printed |
| `crosscheck.csv` | month × area | NGCB total gaming vs. the LVCVA's gaming revenue |

## Sources

- **Nevada Gaming Control Board, Monthly Gaming Revenue Report** (all nonrestricted
  locations, every area in Nevada). Jan 2010 – Sep 2026, 198 reports. Win is reported in
  thousands of dollars; "win" is gaming revenue before expenses.
- **LVCVA, Monthly visitor statistics workbooks** (Las Vegas sheet). Jan 2019 – Sep 2026.
  Monthly figures before 2019 are only published as annual summaries.

## Validation

Each NGCB area-month must satisfy (within $5,000, since every line is rounded to the
nearest thousand):

1. table-game rows sum to the report's tables total;
2. slot rows sum to the slots total;
3. tables + slots (+ card games, in the pre-2019 layout where they sit outside the tables
   total) equal total gaming;
4. the month printed on the report is the month expected.

Result: 4,895 of 4,900 area-months pass. **Statewide, the Las Vegas Strip and downtown
Las Vegas pass every month.** The 5 failures are small rural counties (Humboldt, Lyon,
Churchill) off by $6,000; they are flagged, not forced.

Cross-check with the LVCVA: 112 of 186 Strip/downtown months match to the dollar. Of the
64 that differ, 60 are values the LVCVA marks as revised after the original NGCB report
(median gap 0.016%, largest 0.49%).

## Known gaps

- **Apr and May 2020** (COVID closure): the NGCB reports are scanned images. Strip and
  downtown totals are available from the LVCVA workbook; game-level detail is not.
- **Jun, Jul and Oct 2025**: the full NGCB reports are not linked on the board's site.
  Strip and downtown totals are available from the LVCVA.
- **Oct 2026 onward**: not yet published at the time of writing.
- Small areas show games as a single "Other" row ("unit detail is shown separately only
  when there are 3 or more licensed locations").
- Game categories change over time (e.g. Megabucks discontinued, Ultimate Texas Hold'em
  added, mobile sports reported separately from 2024); `game_raw` keeps the printed name.
