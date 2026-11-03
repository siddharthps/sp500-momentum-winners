from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODELS_DIR = PROJ_ROOT / "models"

REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Raw data, one folder per source
WIKIPEDIA_DIR = RAW_DATA_DIR / "wikipedia"
ALPHAVANTAGE_DIR = RAW_DATA_DIR / "alphavantage"
AV_MONTHLY_DIR = ALPHAVANTAGE_DIR / "monthly_adjusted"
AV_MANIFEST = ALPHAVANTAGE_DIR / "_manifest.csv"
REMOVED_COVERAGE = INTERIM_DATA_DIR / "removed_coverage.csv"
YAHOO_DIR = RAW_DATA_DIR / "yahoo"
YAHOO_DAILY_DIR = YAHOO_DIR / "daily"  # one parquet file per ticker
YAHOO_MANIFEST = YAHOO_DIR / "_manifest.csv"

MONTHLY_PANEL = PROCESSED_DATA_DIR / "monthly_panel.parquet"
MONTHLY_COVERAGE = INTERIM_DATA_DIR / "monthly_coverage.csv"
PRICE_FLAGS = INTERIM_DATA_DIR / "price_flags.csv"

# Study settings
START_DATE = "2010-01-01"  # first month-end decision date in the backtest
# Daily prices start 3 years earlier, so 12- and 24-month features, 200-day averages and
# 12-month beta all exist from the first decision date (and the 2008 crash is in the regime data).
PRICE_START = "2007-01-01"

# Benchmark and regime series from yfinance: SPY, the 11 SPDR sector ETFs, and VIX.
# XLRE starts in 2015 and XLC in 2018; the sector features have to allow for that.
BENCHMARKS = [
    "SPY",
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
    "^VIX",
]

# Hold periods (months) for the forward-return targets. 24 was dropped (decisions.md).
HOLD_MONTHS = [1, 3, 6, 12]

# Renames: the same company kept trading under a new ticker. In Wikipedia's changes table,
# rows dated inside [from, to] get `old` rewritten to `new`. That way the stock is one member
# under today's ticker, and yfinance's history for the new ticker covers the old years.
# Dates matter because tickers get reused: "Q" was Qwest (to 2011), QuintilesIMS (2017) and
# is Qnity now; "UA" was Under Armour class A until 2016, then class C.
# Only true renames; mergers (e.g. BMS -> AMCR) are different companies.
RENAMES = [
    # (old, new, rows from, rows to)
    ("FB", "META", "2013-12-01", "2013-12-31"),  # Facebook -> Meta, 2022 (no rename row)
    ("DLPH", "APTV", "2012-12-01", "2012-12-31"),  # Delphi Automotive -> Aptiv, 2017
    ("KORS", "CPRI", "2013-11-01", "2013-11-30"),  # Michael Kors -> Capri, 2018
    ("FLT", "CPAY", "2018-06-01", "2018-06-30"),  # FleetCor -> Corpay, 2024
    ("RE", "EG", "2017-06-01", "2017-06-30"),  # Everest Re -> Everest Group, 2023
    ("UA", "UAA", "2014-05-01", "2014-05-01"),  # Under Armour class A took UAA in 2016
    ("UA-C", "UA", "2016-04-01", "2016-04-30"),  # class C took UA
    ("SATS", "ECHO", "2026-03-01", "2026-03-31"),  # EchoStar
    ("GOOGL", "GOOG", "2014-04-03", "2014-04-03"),  # the 2014 row added class C (GOOG)
    ("JOYG", "JOY", "2011-02-01", "2011-02-28"),  # Joy Global
    ("CDAY", "DAY", "2021-01-01", "2024-02-29"),  # Ceridian -> Dayforce, 2024
    ("WLTW", "WTW", "2016-01-01", "2022-01-31"),  # Willis Towers Watson, 2022
    ("Q", "IQV", "2017-08-01", "2017-11-30"),  # QuintilesIMS -> IQVIA, 2017
    ("KFT", "MDLZ", "2012-10-01", "2012-10-31"),  # Kraft Foods -> Mondelez, 2012
]

# Current members that joined after the study start but have no "added" row in Wikipedia.
# Without one, the backward walk would treat them as members all the way back.
MISSING_ADDS = {
    "SW": "2024-07-08",  # Smurfit Westrock (new listing; older "SW" data is another security)
}

# A yfinance series whose median daily dollar volume over its member months is below this
# can't be an S&P 500 stock: it's a different security that reused the ticker (e.g. CPWR, EP).
MIN_MEMBER_DOLLAR_VOLUME = 10e6
YAHOO_SUSPECT = INTERIM_DATA_DIR / "yahoo_suspect.csv"  # removed members sent to Alpha Vantage

# Removal reasons the keyword match gets wrong. Bemis was acquired by Amcor; the text says
# "changed to AMCR", which reads like a ticker change, so it was kept out of the AV queue.
REASON_OVERRIDES = {"BMS": "acquired"}

# Alpha Vantage free tier: 25 requests a day and 1 a second. Keep a small buffer
# for ad-hoc checks, and sleep a bit longer than one second between calls.
AV_DAILY_BUDGET = 23
AV_SLEEP_SECONDS = 1.5

HTTP_HEADERS = {"User-Agent": "sp500-momentum-winners research script"}

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
