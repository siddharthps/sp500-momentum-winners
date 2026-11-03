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
