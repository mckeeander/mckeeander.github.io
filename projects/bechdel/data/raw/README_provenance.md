# data/raw — provenance log

All files here are read-only after acquisition. Nothing downstream touches the
network. Acquired 2026-07-04 unless noted.

## Pudding film dialogue (2 files)
- `pudding_character_list5.csv` — character grain (23,048 rows): script_id,
  imdb_character_name, words, gender, age.
- `pudding_meta_data7.csv` — film grain (2,000 rows): script_id, imdb_id, title,
  year, gross (inflation-adjusted domestic, $M), lines_data.
- Source: github.com/matthewfdaniels/scripts, `graphs` branch (raw.githubusercontent.com).
- Fetched programmatically via notebooks/00_ingest.ipynb. Files are latin-1 encoded.

## Bechdel test
- `bechdel_tidytuesday_2021.csv` — ADOPTED SOURCE (2026-07-05). Mirror of the
  full bechdeltest.com DB published by TidyTuesday 2021-03-09
  (github.com/rfordatascience/tidytuesday). 8,839 films (1888–2021), 5,464 in
  the 1990–2015 window. Columns: year, id, imdb_id, title, rating (0–3).
  vs. the live API: films rated after Mar 2021 are absent, and there is no
  `dubious` flag — both documented as limitations. imdb_id has the "tt" prefix
  and leading zeros stripped; MUST be read as string and normalized
  (zfill(7) + "tt") before joining.
- `bechdel_all_movies.json` — intended primary from
  https://bechdeltest.com/api/v1/getAllMovies; NOT acquired. The endpoint
  failed server-side (empty reply at ~60s) on 9+ attempts across 2026-07-04/05.
  The guarded cell in 00_ingest.ipynb remains — if a later run succeeds, the
  fresh pull supersedes the mirror (re-run downstream notebooks).
- **UPDATE 2026-07-12: API permanently disabled — stop retrying.** The
  endpoint now returns HTTP 410 with `{"description":"API has been disabled"}`
  (v1 doc endpoint too). The site itself is alive (10,866 films) but offers no
  bulk export. The TidyTuesday mirror is therefore the FINAL source, not a
  stopgap; its limitations (no post-Mar-2021 ratings, no `dubious` flag) are
  permanent for this project. The guarded cell in 00_ingest.ipynb can no
  longer succeed and is kept only as a record of the attempt.
- License: CC BY-NC 3.0 (attribution, non-commercial) — applies to both routes.

## The Numbers box office / budgets (two mirror snapshots)
Original plan was a polite scrape of the-numbers.com/movie/budgets/all. On
2026-07-04 that URL no longer serves the budgets table to ANY client (browser
included) — the site returns its homepage with HTTP 404; the public table has
been removed. Two documented static mirrors were used instead.

**UPDATE 2026-07-12 — root cause found.** The Numbers announced ("The new The
Numbers", homepage news post dated 2026-03-11) a ground-up rebuild of the site
on new infrastructure; historical pages including the budgets table are
"under construction" and being restored "prioritizing the most popular pages
first," with a promise the site stays free. As of 2026-07-12 the budgets URL
still redirects to the homepage and no budgets page appears in the new site's
navigation. So the table was never paywalled or deliberately removed — it just
hasn't been rebuilt yet. It may return at some point, but since the study
window ends in 2015 and both mirrors post-date all grosses in it, a restored
live table would add nothing; the mirror union stands as the final source.

- `tidytuesday_movie_profit.csv` — 3,401 films; release_date, movie,
  production_budget, domestic_gross (nominal), worldwide_gross, distributor,
  mpaa_rating, genre. Snapshot of the-numbers.com scraped Oct 2018 by the
  TidyTuesday project (github.com/rfordatascience/tidytuesday, 2018-10-23).
  Coverage: budgets $250K–$175M — deep coverage of small/mid films, but films
  with budgets >$175M are ABSENT (top-truncated).
- `wwu_mirror_pages/all_*.html` — 10 pages × 100 rows = top 1,000 films by
  production budget, early-2023 snapshot of the same table, mirrored for
  WWU DATA 311 (facultyweb.cs.wwu.edu/~wehrwes/courses/data311_23w/lab5/).
  Columns: rank, release date, movie, production budget, domestic gross
  (nominal), worldwide gross. Covers exactly the >$175M films TidyTuesday lacks.
- Planned use: parse WWU pages, UNION with TidyTuesday, dedupe on
  normalized title + year. Since the study window ends 2015, grosses were final
  at both snapshot dates; the vintage difference (2018 vs 2023) does not affect
  pre-2016 films. Both grosses are NOMINAL dollars (do not mix with Pudding's
  inflation-adjusted gross).

## Scratch / superseded
- `the_numbers_pages/all_0001.mhtml` — browser save made while diagnosing
  the-numbers.com; captured the homepage decoy (no budget data). Deleted 2026-07-04.
