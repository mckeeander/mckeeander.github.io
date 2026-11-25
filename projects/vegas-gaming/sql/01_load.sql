-- 01_load: raw tables straight from the processed CSVs, plus small lookup tables.
-- Paths are relative to the project folder (scripts/build_db.py runs from there).

CREATE OR REPLACE TABLE raw_ngcb_games AS
SELECT * FROM read_csv('data/processed/ngcb_games.csv', header = true,
    types = {'month': 'VARCHAR', 'win_k': 'DOUBLE', 'units': 'DOUBLE', 'locations': 'DOUBLE',
             'pct_change': 'DOUBLE', 'win_pct': 'DOUBLE'});

CREATE OR REPLACE TABLE raw_ngcb_totals AS
SELECT * FROM read_csv('data/processed/ngcb_totals.csv', header = true, types = {'month': 'VARCHAR'});

CREATE OR REPLACE TABLE raw_lvcva AS
SELECT * FROM read_csv('data/processed/lvcva_monthly.csv', header = true, types = {'month': 'VARCHAR'});

-- Context (scripts/fetch_extra.py): inflation, population, LVCVA annual history.
CREATE OR REPLACE TABLE raw_cpi AS
SELECT * FROM read_csv('data/processed/cpi_monthly.csv', header = true, types = {'month': 'VARCHAR', 'cpi_u': 'DOUBLE'});
CREATE OR REPLACE TABLE raw_population AS
SELECT * FROM read_csv('data/processed/clark_population.csv', header = true);
CREATE OR REPLACE TABLE raw_lvcva_annual AS
SELECT * FROM read_csv('data/processed/lvcva_annual.csv', header = true);
-- Gaming Abstract: the Strip's annual income statement by department, FY1990 on (parse_abstract.py).
CREATE OR REPLACE TABLE raw_abstract_strip AS
SELECT * FROM read_csv('data/processed/abstract_strip.csv', header = true);
-- LVCVA Visitor Profile Study: gambling and spending per visitor, 2003 on (visitor_profile.py).
CREATE OR REPLACE TABLE raw_visitor_profile AS
SELECT * FROM read_csv('data/processed/visitor_profile.csv', header = true);

-- Areas: one short, stable key per area (the board renamed "Boulder Strip" to "Boulder" in 2018).
-- market: 'locals' marks the areas whose casinos mostly serve residents (Boulder Strip, North Las Vegas,
-- and the rest of the county outside the Strip, downtown, Laughlin and Mesquite).
CREATE OR REPLACE TABLE dim_area (area_raw VARCHAR, area_key VARCHAR, area_name VARCHAR, in_dashboard BOOLEAN, market VARCHAR);
INSERT INTO dim_area VALUES
    ('Statewide',                            'statewide', 'Nevada statewide',     true, 'statewide'),
    ('Clark County',                         'clark',     'Clark County',         false, 'county'),
    ('Clark County Las Vegas Strip Area',    'strip',     'Las Vegas Strip',      true, 'tourist'),
    ('Clark County Downtown Las Vegas Area', 'downtown',  'Downtown Las Vegas',   true, 'tourist'),
    ('Clark County Boulder Strip Area',      'boulder',   'Boulder Strip',        false, 'locals'),
    ('Clark County Boulder Area',            'boulder',   'Boulder Strip',        false, 'locals'),
    ('Clark County North Las Vegas Area',    'north_lv',  'North Las Vegas',      false, 'locals'),
    ('Clark County Laughlin Area',           'laughlin',  'Laughlin',             false, 'tourist'),
    ('Clark County Mesquite Area',           'mesquite',  'Mesquite',             false, 'tourist'),
    ('Washoe County Reno Area',              'reno',      'Reno',                 false, 'other'),
    ('Washoe County Sparks Area',            'sparks',    'Sparks',               false, 'other'),
    ('Clark County Balance Of County',       'clark_rest', 'Rest of Clark County (incl. Henderson)', false, 'locals');
-- Areas not listed keep their printed name as the key (see stg_* below).

-- Games: one canonical name and a group for the dashboard. Fixes names the parser
-- produced before its mapping was completed, so old CSVs and new ones agree.
CREATE OR REPLACE TABLE dim_game (game_raw VARCHAR, game VARCHAR, game_group VARCHAR);
INSERT INTO dim_game VALUES
    ('Blackjack', 'Blackjack', 'Blackjack'),
    ('Baccarat', 'Baccarat', 'Baccarat'),
    ('Mini-Baccarat', 'Mini-Baccarat', 'Baccarat'),
    ('Craps', 'Craps', 'Craps'),
    ('Roulette', 'Roulette', 'Roulette'),
    ('3-Card Poker', '3-Card Poker', 'Poker-style table games'),
    ('Pai Gow Poker', 'Pai Gow Poker', 'Poker-style table games'),
    ('Pai Gow', 'Pai Gow', 'Poker-style table games'),
    ('Let It Ride', 'Let It Ride', 'Poker-style table games'),
    ('Caribbean Stud', 'Caribbean Stud', 'Poker-style table games'),
    ('Ultim Texas Hold''Em', 'Ultimate Texas Hold''em', 'Poker-style table games'),
    ('Ultimate Texas Hold''em', 'Ultimate Texas Hold''em', 'Poker-style table games'),
    ('Card Games', 'Card games (poker room)', 'Poker room'),
    ('Sports Pool', 'Sports betting', 'Sports & race'),
    ('Race Book', 'Race book', 'Sports & race'),
    ('Keno', 'Keno', 'Other tables'),
    ('Bingo', 'Bingo', 'Other tables'),
    ('Other games', 'Other games', 'Other tables'),
    ('Other Games & Tables', 'Other games', 'Other tables'),
    ('1¢', '1¢', 'Penny slots'),
    ('5¢', '5¢', 'Other slots'),
    ('25¢', '25¢', 'Other slots'),
    ('$1', '$1', 'Other slots'),
    ('$5', '$5', 'High-limit slots ($5+)'),
    ('5 Dollar', '$5', 'High-limit slots ($5+)'),
    ('$25', '$25', 'High-limit slots ($5+)'),
    ('25 Dollar', '$25', 'High-limit slots ($5+)'),
    ('$100', '$100', 'High-limit slots ($5+)'),
    ('100 Dollar', '$100', 'High-limit slots ($5+)'),
    ('Megabucks', 'Megabucks', 'Other slots'),
    ('Multi-denomination', 'Multi-denomination', 'Multi-denomination slots'),
    ('Other slots', 'Other slots', 'Other slots');
