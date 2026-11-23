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

-- Areas: one short, stable key per area (the board renamed "Boulder Strip" to "Boulder" in 2018).
CREATE OR REPLACE TABLE dim_area (area_raw VARCHAR, area_key VARCHAR, area_name VARCHAR, in_dashboard BOOLEAN);
INSERT INTO dim_area VALUES
    ('Statewide',                            'statewide', 'Nevada statewide',     true),
    ('Clark County',                         'clark',     'Clark County',         false),
    ('Clark County Las Vegas Strip Area',    'strip',     'Las Vegas Strip',      true),
    ('Clark County Downtown Las Vegas Area', 'downtown',  'Downtown Las Vegas',   true),
    ('Clark County Boulder Strip Area',      'boulder',   'Boulder Strip',        false),
    ('Clark County Boulder Area',            'boulder',   'Boulder Strip',        false),
    ('Clark County North Las Vegas Area',    'north_lv',  'North Las Vegas',      false),
    ('Clark County Laughlin Area',           'laughlin',  'Laughlin',             false),
    ('Clark County Mesquite Area',           'mesquite',  'Mesquite',             false),
    ('Washoe County Reno Area',              'reno',      'Reno',                 false),
    ('Washoe County Sparks Area',            'sparks',    'Sparks',               false);
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
