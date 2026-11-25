-- 04_tests: data tests. Each query must return zero rows; build_db.py fails otherwise.
-- The comment line before each query is its name.

-- test: every game maps to a known canonical game
SELECT DISTINCT g.game FROM raw_ngcb_games g LEFT JOIN dim_game d ON d.game_raw = g.game WHERE d.game IS NULL;

-- test: one row per month, area and game after mapping
SELECT month, area_key, game, count(*) AS n FROM fct_game_month GROUP BY ALL HAVING count(*) > 1;

-- test: no gaps in the month spine
SELECT month FROM (SELECT month, LAG(month) OVER (ORDER BY month) AS prev FROM dim_month)
WHERE prev IS NOT NULL AND month <> prev + INTERVAL 1 MONTH;

-- test: dashboard areas have a total for every month (NGCB, or LVCVA for the gaps)
SELECT month, area_key FROM fct_area_month
WHERE area_key IN ('strip', 'downtown') AND total_win IS NULL;

-- test: game rows add up to the area total (within $10K) wherever NGCB supplied both
SELECT a.month, a.area_key, a.total_win, sum(g.win) AS games
FROM fct_area_month a JOIN fct_game_month g USING (month, area_key)
WHERE a.area_key IN ('statewide', 'strip', 'downtown') AND a.source = 'ngcb'
GROUP BY ALL HAVING abs(sum(g.win) - a.total_win) > 10000;

-- test: hold (win %) stays in a believable range for the big table games on the Strip
SELECT month, game, hold FROM fct_game_month
WHERE area_key = 'strip' AND game IN ('Blackjack', 'Craps', 'Roulette') AND (hold < -0.5 OR hold > 0.6);

-- test: shares in the game mix sum to 1
SELECT month, area_key, sum(share) FROM v_game_mix GROUP BY ALL HAVING abs(sum(share) - 1) > 1e-9;

-- test: every month in the spine has an inflation factor
SELECT month FROM dim_cpi WHERE to_2025_dollars IS NULL;

-- test: every area maps to a market
SELECT DISTINCT area_key FROM v_area_annual WHERE market = 'other' AND area_key IN ('strip', 'downtown', 'boulder', 'north_lv', 'clark_rest');

-- test: the Abstract has every fiscal year from 1990, each one read and checked
SELECT y AS fy FROM range(1990, (SELECT max(fy) + 1 FROM raw_abstract_strip)) t(y)
WHERE y NOT IN (SELECT fy FROM raw_abstract_strip WHERE total IS NOT NULL);

-- test: Abstract departments add up exactly to total revenue
SELECT fy FROM raw_abstract_strip WHERE gaming + rooms + food + beverage + other <> total;

-- test: Abstract gaming revenue (old basis) agrees with the monthly reports' Strip win (within 10%)
SELECT d.fy, d.gaming, w.win FROM v_strip_departments d
JOIN (SELECT year(month + INTERVAL 6 MONTH) AS fy, sum(total_win) AS win, count(*) AS n
      FROM fct_area_month WHERE area_key = 'strip' GROUP BY ALL) w USING (fy)
WHERE w.n = 12 AND abs(d.gaming / w.win - 1) > 0.10;

-- test: every Abstract year and Visitor Profile year has an inflation factor
SELECT fy FROM v_strip_departments WHERE to_2025_dollars IS NULL
UNION ALL SELECT year FROM raw_visitor_profile v
WHERE NOT EXISTS (SELECT 1 FROM v_cpi_annual c WHERE c.basis = 'calendar' AND c.year = v.year);

-- test: Visitor Profile shares are believable
SELECT year, gambled_pct FROM raw_visitor_profile WHERE gambled_pct NOT BETWEEN 0.5 AND 1;
