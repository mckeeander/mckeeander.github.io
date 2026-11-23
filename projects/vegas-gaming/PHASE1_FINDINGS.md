# Las Vegas gaming dashboard: Phase 1 findings (data feasibility)

Tested November 2026. Not yet linked from the site.

## Nevada Gaming Control Board (NGCB) monthly revenue reports

- **Coverage.** Every month from Jan 2010 to May 2025 is at a predictable URL:
  `https://gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/{YYYY}{Mon}-gri.pdf`
  (e.g. `2024Dec-gri.pdf`). From Jun 2025 the files moved to the new site with
  irregular names; they are linked from
  `https://gaming.nv.gov/about/gaming-revenue/information/` and must be matched to
  months by their link text. Jun, Jul and Oct 2025 were not linked there at test time.
- **Format.** 48-page text PDFs. The Las Vegas Strip "All Nonrestricted Locations"
  table is on page 15 in every sample. Two layouts:
  - pre-2019: pipe-separated columns, capitals (`TWENTY-ONE`), minus signs for negatives;
  - 2019 on: plain columns, title case (`Twenty One`), brackets for negatives.
  Each row gives locations, units, win ($000), % change and win % for the current
  month, three months and twelve months.
- **Scanned months.** Apr and May 2020 (the COVID closure) are scanned images with no
  text. All other sampled months have text.
- **Accounting quirk.** In the old layout "Card Games" sit outside "Total Games" but
  inside "Total Gaming"; in the new layout they are inside the tables total.
- **Parsing.** Counting numbers per row works for most months but breaks when a cell is
  blank (e.g. Megabucks in Feb 2020; blank % change in Jun 2021). Phase 2 should place
  numbers by their x-position on the page. The validation (rows sum to the report's own
  section totals; tables + slots = total gaming) caught every bad month.

Samples checked: Dec 2010, Jul 2015, Jul 2019, Feb-Dec 2020, Jan and Jun 2021, Jul and
Dec 2024, Sep 2025, Jan 2026. All text months reconcile at the total-gaming level.

## LVCVA Executive Summary (tourism)

- Monthly 2-page PDF. Page 2 ("Data Detail") has visitor volume, convention attendance,
  room inventory, occupancy (all / weekend / midweek / Strip / downtown), ADR, RevPAR,
  room nights, air passengers, auto traffic, and gaming revenue for Clark County, the
  Strip, downtown and the Boulder Strip, for the month and year to date.
- Text extracts cleanly.
- **Cross-check.** LVCVA's Strip gaming revenue matches NGCB total gaming exactly
  (Dec 2024: $881,255,000 in both), so each month can be validated against a second source.
- **Access.** lvcva.com returns 403 to requests without a browser-style User-Agent.
  The PDFs are hosted on assets.simpleviewcms.com with hashed file names, so the
  monthly links have to be found from LVCVA's report pages. This is the most fragile
  part of the future automation.
- A "Historical Visitation Statistics: 1970-2025" report exists (likely annual figures).

## Recommendation for Phase 2

1. Build the NGCB parser on word positions; keep the sum checks as hard failures.
2. Range: Jan 2010 to present. Fill Apr/May 2020 from NGCB press releases or LVCVA
   totals, and mark them as the closure.
3. Scope v1 to the Strip, downtown and statewide; add other areas later if wanted.
4. Collect LVCVA summaries for the same range; use the gaming revenue line as a
   cross-check.
