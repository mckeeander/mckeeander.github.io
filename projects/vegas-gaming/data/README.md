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
python scripts/fetch_extra.py     # CPI, Clark County population, LVCVA annual history
python scripts/fetch_abstract.py  # NGCB Gaming Abstract PDFs, FY1990 on
python scripts/parse_abstract.py  # Strip income statement by year (OCR for FY1990-2017; needs tesseract)
python scripts/visitor_profile.py # LVCVA Visitor Profile Study summary tables, 2003 on
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

## Dashboard (`../dashboard/`)

`dashboard.html` (markup), `dashboard.css` and `dashboard.js` are copied next to the project page by the
site's `build.py` (site.json: `"dashboard"` and `"dashboard_data"`), along with `data/dashboard/*.json`.
The page reads `area_monthly`, `strip_tourism`, `seasonality`, `baccarat` and `dash_game_mix` (a compact,
nested game-mix file) and draws with the site's chart theme (`window.siteChart` in `assets/charts.js`).

## Files in `processed/`

| File | Grain | Contents |
|---|---|---|
| `ngcb_games.csv` | month × area × game | locations, units, win ($000), % change vs. a year earlier, win % — current month only |
| `ngcb_totals.csv` | month × area | tables, card games, slots and total gaming win ($000); `valid` = passed the sum checks |
| `ngcb_checks.csv` | month × area | result of every validation check |
| `lvcva_monthly.csv` | month | visitors, convention attendance, room inventory, occupancy (all / weekend / midweek / Strip / downtown), ADR, RevPAR, room nights, air passengers, gaming revenue (Clark County, Strip, downtown, Boulder); `*_flag` = `r` revised or `e` estimate, as printed |
| `crosscheck.csv` | month × area | NGCB total gaming vs. the LVCVA's gaming revenue |
| `cpi_monthly.csv` | month | CPI-U, U.S. city average, not seasonally adjusted (BLS CUUR0000SA0), 1989 on. 2010 on from the BLS API; 1989–2009 from the datasets/cpi-us mirror of the same series, used only after it matches BLS in every overlapping month. Oct 2025 was never published and is interpolated in SQL |
| `clark_population.csv` | year | Census Bureau population estimates, Clark County (vintage 2020 for 2010–19, vintage 2025 for 2020–25) |
| `lvcva_annual.csv` | year | LVCVA Historic Tourism Statistics, 1970 on: visitors, convention attendance, room inventory, occupancy |
| `abstract_strip.csv` | fiscal year | NGCB Gaming Abstract, Las Vegas Strip casinos with $1M+ gaming revenue: revenue by department (gaming, rooms, food, beverage, other) as printed, contra revenue (comps) by department from FY2019, casino comps, and casino and rooms departmental income. `method` says how the year was read |
| `visitor_profile.csv` | year | LVCVA Visitor Profile Study: share of visitors who gambled, trip gambling budget (among gamblers), trip spending on food and drink, shopping and shows, lodging per night (nominal dollars). No survey in 2020 |

## Sources

- **Nevada Gaming Control Board, Monthly Gaming Revenue Report** (all nonrestricted
  locations, every area in Nevada). Jan 2010 – Sep 2026, 198 reports. Win is reported in
  thousands of dollars; "win" is gaming revenue before expenses.
- **LVCVA, Monthly visitor statistics workbooks** (Las Vegas sheet). Jan 2019 – Sep 2026.
  Monthly figures before 2019 are only published as annual summaries.

- **Nevada Gaming Control Board, Gaming Abstract** (annual summary of licensees' financial
  statements). FY1990 – FY2025, 36 reports; fiscal years run July–June. The group used is
  "Clark County – Las Vegas Strip Area, gaming revenue of $1,000,000 and over" (37–54
  licensees a year). FY1990–2017 are scanned images; FY2018 on are text.
- **LVCVA, Las Vegas Visitor Profile Study** (annual survey of about 3,600 visitors). Summary
  tables from the 2006, 2011, 2016, 2021 and 2024 reports (Nevada State Library archive) and
  the 2025 matrix spreadsheet (lvcva.com). From 2022 an online component was added to the
  in-person interviews.

## Gaming Abstract: OCR checks and the accounting change

A scanned year is accepted only if the OCR reading passes checks the page makes possible:
the five departments sum exactly to the printed total, each matches its printed percent
(to 0.1 point), and departmental income plus departmental expenses equal revenue. Totals are
tried largest first, because OCR more often adds or drops a leading digit than invents one.
A value that fails is left blank, not guessed.

From FY2019 casinos follow ASC 606: the retail value of comps is subtracted from each
department's revenue ("contra revenue") instead of being booked as a casino expense. The
printed gaming share drops from 34% to 27% in one year as a result. `v_strip_departments`
adds the contra amounts back so every year is on the old basis. On that basis, Abstract gaming
revenue comes to 91–99% of the monthly reports' Strip win in every fiscal year both cover
(FY2011 on); the gap is casinos outside the Abstract group. A data test keeps it within 10%.
Comps themselves are valued differently after the change (closer to retail), so comps as a
share of win are compared within each basis, not across FY2019.

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
- Inflation uses the national CPI-U; Las Vegas prices may differ. Money compared across years is in 2025 dollars.
- The "locals market" is the Boulder Strip, North Las Vegas and the rest of Clark County (incl. Henderson); it is a proxy, since no public data splits bets between residents and tourists.
- Game categories change over time (e.g. Megabucks discontinued, Ultimate Texas Hold'em
  added, mobile sports reported separately from 2024); `game_raw` keeps the printed name.
