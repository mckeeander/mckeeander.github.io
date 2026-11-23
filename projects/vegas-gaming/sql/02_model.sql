-- 02_model: clean, typed tables the metrics are built on. All money in dollars.

-- Every calendar month in the study window, so gaps are explicit rather than silent.
CREATE OR REPLACE TABLE dim_month AS
SELECT CAST(m AS DATE) AS month,
       year(m) AS year, month(m) AS month_num, strftime(m, '%b') AS month_name,
       CASE WHEN m BETWEEN DATE '2020-03-01' AND DATE '2021-06-01' THEN 'covid'
            ELSE 'normal' END AS period
FROM range(DATE '2010-01-01',
           (SELECT max(CAST(month || '-01' AS DATE)) FROM raw_ngcb_totals) + INTERVAL 1 MONTH,
           INTERVAL 1 MONTH) t(m);

-- One row per month x area x game.
CREATE OR REPLACE TABLE fct_game_month AS
SELECT CAST(g.month || '-01' AS DATE)              AS month,
       coalesce(a.area_key, g.area)                AS area_key,
       g.section,
       coalesce(d.game, g.game)                    AS game,
       coalesce(d.game_group,
                CASE g.section WHEN 'slots' THEN 'Other slots' ELSE 'Other tables' END) AS game_group,
       g.units,
       g.win_k * 1000                              AS win,
       g.win_pct / 100                             AS hold      -- win as a share of amount wagered
FROM raw_ngcb_games g
LEFT JOIN dim_area a ON a.area_raw = g.area
LEFT JOIN dim_game d ON d.game_raw = g.game;

-- One row per month x area: NGCB totals, with the months NGCB can't supply (scanned
-- closure months, unpublished reports) filled from the LVCVA where it has the area.
CREATE OR REPLACE TABLE fct_area_month AS
WITH ngcb AS (
    SELECT CAST(t.month || '-01' AS DATE) AS month,
           coalesce(a.area_key, t.area)   AS area_key,
           t.tables_k * 1000 + CASE WHEN t.card_games_in_tables = 'no' THEN t.card_games_k * 1000 ELSE 0 END AS tables_win,
           t.slots_k * 1000  AS slots_win,
           t.total_k * 1000  AS total_win,
           t.valid = 'yes'   AS valid
    FROM raw_ngcb_totals t
    LEFT JOIN dim_area a ON a.area_raw = t.area
),
lvcva AS (
    SELECT CAST(month || '-01' AS DATE) AS month, 'strip' AS area_key, gaming_rev_strip AS total_win FROM raw_lvcva
    UNION ALL
    SELECT CAST(month || '-01' AS DATE), 'downtown', gaming_rev_downtown FROM raw_lvcva
),
keys AS (SELECT DISTINCT area_key FROM ngcb)
SELECT m.month, k.area_key,
       n.tables_win, n.slots_win,
       coalesce(n.total_win, l.total_win)                         AS total_win,
       CASE WHEN n.total_win IS NOT NULL THEN 'ngcb'
            WHEN l.total_win IS NOT NULL THEN 'lvcva' END          AS source,
       coalesce(n.valid, l.total_win IS NOT NULL)                  AS valid
FROM dim_month m
CROSS JOIN keys k
LEFT JOIN ngcb  n ON n.month = m.month AND n.area_key = k.area_key
LEFT JOIN lvcva l ON l.month = m.month AND l.area_key = k.area_key;

-- Tourism, one row per month (2019 on). Rates as fractions, money in dollars.
CREATE OR REPLACE TABLE fct_tourism_month AS
SELECT CAST(month || '-01' AS DATE) AS month,
       visitors, convention_attendance, room_inventory,
       occupancy, occupancy_weekend, occupancy_midweek, occupancy_strip, occupancy_downtown,
       adr, adr_strip, adr_downtown, revpar, revpar_strip, revpar_downtown,
       room_nights, air_passengers,
       (coalesce(visitors_flag, '') = 'r') AS visitors_revised
FROM raw_lvcva;
