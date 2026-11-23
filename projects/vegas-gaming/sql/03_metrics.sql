-- 03_metrics: the views the dashboard reads. Rows in fct_area_month are one per
-- calendar month with no gaps (see dim_month), so LAG(…, 12) is exactly a year earlier.

-- Revenue by area and month, with year-over-year change and rolling 12-month totals.
CREATE OR REPLACE VIEW v_area_monthly AS
WITH base AS (
    SELECT month, area_key, source, valid, total_win, tables_win, slots_win,
           slots_win / nullif(total_win, 0)                                          AS slot_share,
           total_win / nullif(LAG(total_win, 12) OVER w, 0) - 1                       AS yoy,
           -- a 12-month total only when all 12 months are present
           CASE WHEN count(total_win) OVER r12 = 12 THEN sum(total_win) OVER r12 END  AS win_12m
    FROM fct_area_month
    WINDOW w   AS (PARTITION BY area_key ORDER BY month),
           r12 AS (PARTITION BY area_key ORDER BY month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
)
SELECT *,
       win_12m / nullif(LAG(win_12m, 12) OVER (PARTITION BY area_key ORDER BY month), 0) - 1 AS yoy_12m
FROM base;

-- Game mix: win by game group, and each group's share of the area's win that month.
CREATE OR REPLACE VIEW v_game_mix AS
SELECT month, area_key, game_group, section,
       sum(win)                                                        AS win,
       sum(win) / nullif(sum(sum(win)) OVER (PARTITION BY month, area_key), 0) AS share
FROM fct_game_month
GROUP BY month, area_key, game_group, section;

-- Baccarat on the Strip: the most volatile line in the casino. A few high-stakes players
-- can swing the house's win (its "hold") by millions in a month, so the dashboard shows
-- monthly hold against its own trailing two-year average.
CREATE OR REPLACE VIEW v_baccarat AS
WITH b AS (
    SELECT month,
           sum(win)                                                   AS baccarat_win,
           sum(win) FILTER (WHERE game = 'Baccarat')                  AS big_table_win,
           max(hold) FILTER (WHERE game = 'Baccarat')                 AS hold,
           max(units) FILTER (WHERE game = 'Baccarat')                AS tables
    FROM fct_game_month
    WHERE area_key = 'strip' AND game_group = 'Baccarat'
    GROUP BY month
)
SELECT b.month, b.baccarat_win, b.big_table_win, b.hold, b.tables,
       avg(b.hold) OVER (ORDER BY b.month ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING) AS hold_trailing_24m,
       b.baccarat_win / nullif(a.tables_win, 0)                                        AS share_of_tables,
       b.baccarat_win / nullif(a.total_win, 0)                                         AS share_of_total
FROM b
JOIN fct_area_month a ON a.month = b.month AND a.area_key = 'strip';

-- The Strip and its visitors (2019 on). Visitor volume covers all of Las Vegas, so
-- "win per visitor" is Strip win divided by every visitor to the city: an index, not a spend.
CREATE OR REPLACE VIEW v_strip_tourism AS
SELECT t.month,
       a.total_win                                   AS strip_win,
       t.visitors, t.convention_attendance,
       a.total_win / nullif(t.visitors, 0)           AS win_per_visitor,
       t.occupancy_strip, t.adr_strip, t.revpar_strip,
       t.visitors / nullif(LAG(t.visitors, 12) OVER (ORDER BY t.month), 0) - 1 AS visitors_yoy,
       t.adr_strip / nullif(LAG(t.adr_strip, 12) OVER (ORDER BY t.month), 0) - 1 AS adr_strip_yoy
FROM fct_tourism_month t
LEFT JOIN fct_area_month a ON a.month = t.month AND a.area_key = 'strip';

-- Seasonality: each month's win as a share of its own year's monthly average, averaged
-- over complete, normal years (no COVID, no partial year).
CREATE OR REPLACE VIEW v_seasonality AS
WITH years AS (
    SELECT area_key, year(month) AS year
    FROM fct_area_month JOIN dim_month USING (month)
    GROUP BY ALL
    HAVING count(total_win) = 12 AND bool_and(period = 'normal')
),
idx AS (
    SELECT a.area_key, year(a.month) AS year, month(a.month) AS month_num,
           a.total_win / avg(a.total_win) OVER (PARTITION BY a.area_key, year(a.month)) AS index
    FROM fct_area_month a
    JOIN years y ON y.area_key = a.area_key AND y.year = year(a.month)
)
SELECT area_key, month_num, strftime(make_date(2000, month_num, 1), '%b') AS month_name,
       avg(index) AS index, min(index) AS index_min, max(index) AS index_max, count(*) AS years
FROM idx
GROUP BY ALL;

-- Headline numbers for the latest month the Strip has data.
CREATE OR REPLACE VIEW v_kpi_latest AS
WITH latest AS (SELECT max(month) AS month FROM v_area_monthly WHERE area_key = 'strip' AND total_win IS NOT NULL)
SELECT v.month, v.total_win AS strip_win, v.yoy AS strip_yoy, v.win_12m AS strip_win_12m,
       v.yoy_12m AS strip_yoy_12m, v.slot_share AS strip_slot_share,
       s.visitors, s.visitors_yoy, s.occupancy_strip, s.adr_strip, s.adr_strip_yoy, s.win_per_visitor,
       sw.total_win AS statewide_win, sw.yoy AS statewide_yoy
FROM latest
JOIN v_area_monthly v  ON v.month = latest.month AND v.area_key = 'strip'
LEFT JOIN v_strip_tourism s ON s.month = latest.month
LEFT JOIN v_area_monthly sw ON sw.month = latest.month AND sw.area_key = 'statewide';
