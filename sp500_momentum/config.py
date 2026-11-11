from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
# (The template logged PROJ_ROOT here; removed: notebooks would publish the local path and username.)

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

FRED_DIR = RAW_DATA_DIR / "fred"  # one CSV per series: date, value

# FRED series: the class's set (Week 2). The yield-curve slope (DGS10 - DGS1) is derived later.
# `lag_months`: how many months after an observation's own date it's safe to use, so no
# feature sees a figure before it was published (decisions.md, A4). A monthly figure is dated
# the 1st of its month, so lag 1 means "July's value is used from the end of August on".
# - CPILFESL (core CPI, monthly): released mid-next-month -> 1.
# - FEDFUNDS (monthly average): released on the first days of the next month -> 1.
# - DGS1/DGS5/DGS10 (daily yields): published the next business day; features use the last
#   value strictly before the decision date -> 0 months, plus that 1-day rule.
# - GDPPOT (CBO potential GDP, quarterly): a projection published in advance -> 0. FRED keeps
#   only the latest projection, not past vintages, so this one is a mild, accepted look-ahead.
FRED_SERIES = {
    "CPILFESL": {"name": "Core CPI (index, monthly)", "lag_months": 1},
    "FEDFUNDS": {"name": "Fed Funds rate (monthly average)", "lag_months": 1},
    "DGS1": {"name": "1-year Treasury yield (daily)", "lag_months": 0},
    "DGS5": {"name": "5-year Treasury yield (daily)", "lag_months": 0},
    "DGS10": {"name": "10-year Treasury yield (daily)", "lag_months": 0},
    "GDPPOT": {"name": "Real potential GDP, CBO (quarterly)", "lag_months": 0},
}
FRED_START = "2005-01-01"  # a year before PRICE_START, so yearly changes exist from 2007

MONTHLY_PANEL = PROCESSED_DATA_DIR / "monthly_panel.parquet"
MODEL_SCORES = PROCESSED_DATA_DIR / "model_scores.parquet"  # out-of-sample model scores, 2014 on
# The monthly run (#17): one CSV of picks per decision month (committed), the running record of
# every live pick (for monitoring), and the latest refitted headline model.
PICKS_DIR = REPORTS_DIR / "picks"
LIVE_PICKS = PROCESSED_DATA_DIR / "live_picks.csv"
LIVE_MODEL = MODELS_DIR / "live_headline.joblib"
LIVE_TOP_N = 10
LIVE_RULE_SIGNAL = "ret_6m"  # the plain rule published next to the model (decisions.md, 5 Nov)
LIVE_MIN_PRICED = 0.95  # share of the month's members that must have a month-end price
# Shown on the public dataset card and the dashboard; changes to "final" in #20.
DATA_STATUS = "preview: the download of delisted companies is still running"
FEATURES_TABLE = PROCESSED_DATA_DIR / "features.parquet"  # the monthly panel + every feature

# GICS sectors for members removed since 2010 (Wikipedia's changes table has none). Written by hand
# from each company's last sector; checked against Yahoo's sector field on 3 Nov 2026 (90% agreement,
# vs 95% for current members; the mismatches are taxonomy differences or reused tickers).
REMOVED_SECTORS = PROJ_ROOT / "references" / "removed_sectors.csv"

# Sector fund for each GICS sector. XLRE starts Oct 2015 and XLC Jun 2018; before that, Real Estate
# uses XLF (REITs were in Financials) and Communication Services uses SPY.
SECTOR_ETF = {
    "Information Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}
SECTOR_ETF_FALLBACK = {"XLRE": "XLF", "XLC": "SPY"}

# Market series for growth features (decisions.md, A5: US-focused). The 10-year yield is from FRED.
MARKET_SERIES = {"spy": "SPY", "dji": "^DJI", "gold": "GC=F", "wti": "CL=F"}
MONTHLY_COVERAGE = INTERIM_DATA_DIR / "monthly_coverage.csv"
# Every usable monthly price series (member months or not), for backtests that keep holding a
# stock after it leaves the index.
MONTHLY_PRICES = INTERIM_DATA_DIR / "monthly_prices.parquet"

# Baseline rule (decisions.md, "Hold periods and evaluation"): the look-backs that define a
# "winner", the basket sizes, and the trading cost charged on every buy and every sell.
RULE_LOOKBACKS = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_12_1m"]
RULE_TOP_NS = [1, 5, 10]
COST_PER_SIDE = 0.001  # 10 bps
PRICE_FLAGS = INTERIM_DATA_DIR / "price_flags.csv"

# Study settings
START_DATE = "2010-01-01"  # first month-end decision date in the backtest
# Daily prices start 10 years earlier. Features are computed on MONTHLY bars for every stock
# (decisions.md: so stocks with only Alpha Vantage monthly data are treated the same), and the
# longest monthly indicators need years of warm-up: MACD ~3 years, the Hilbert-transform cycle
# indicators ~5. Alpha Vantage files mostly start in 1999 anyway.
PRICE_START = "2000-01-01"

# Benchmark, market and regime series from yfinance: SPY, the 11 SPDR sector ETFs, VIX, and the
# US-focused market set for growth features (decisions.md, A5): Dow Jones, gold and WTI futures.
# The 10-year yield comes from FRED (DGS10). XLRE starts in 2015 and XLC in 2018.
# WTI futures traded below zero on 20 Apr 2020, so CL=F shows as `bad_prices` in the manifest;
# its month-end values are fine.
BENCHMARKS = [
    "^DJI",
    "GC=F",
    "CL=F",
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

# Time split (decisions.md, A2). Decision dates, inclusive. Models use 1-month gaps between sets.
SPLIT = {
    "train": ("2010-01-01", "2019-12-31"),
    "validation": ("2020-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2099-12-31"),
}
# Anything that could steer modelling choices (feature analysis, tuning) uses decisions up to this
# date only, so the test period stays unseen until the final evaluation.
RESEARCH_END = SPLIT["validation"][1]
# The best baseline rule is chosen on decisions before this date and followed after it: the
# models' test window, so rules and models are scored on exactly the same untouched months.
# Windows are set by decision date for every strategy: a decision at a month-end earns its return
# the next month, so the test returns start the month after this (decisions.md, 4 Nov).
RULE_CHECK_FROM = SPLIT["test"][0]
# Model and rule strategies (#14): the starting amount shown in dollars, the hold-buffer width
# (keep a holding while it ranks within BUFFER_MULTIPLE x N), and the volatility used for the
# inverse-volatility weights (known at the month-end close).
START_DOLLARS = 10_000
BUFFER_MULTIPLE = 2
INVERSE_VOL_FEATURE = "vol_3m"
# SPY trend filter (#15): invested only when SPY's month-end close is above its TREND_MONTHS-month
# average (Faber 2007's monthly version of the 200-day rule; a convention, not tuned). Otherwise
# everything is sold and the cash earns the Fed Funds rate.
TREND_MONTHS = 10

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
    # Discovery -> Warner Bros. Discovery, 11 Apr 2022: Discovery, Inc. acquired WarnerMedia and
    # renamed itself; the same entity continued and DISCA shares became WBD 1:1. Alpha Vantage's
    # WBD series runs from 2005 without a break and tracks Discovery's class C (DISCK) at a 0.98
    # monthly correlation before 2022, while "DISCA" now returns another security (6 Nov).
    ("DISCA", "WBD", "2022-04-11", "2022-04-11"),
]

# Price overrides (#59): in some takeovers the buyer kept or took the target's ticker, and the data
# sources file the buyer's history under that ticker. The membership lines are right (two companies,
# two lines), so this isn't a rename: only the price series a member's rows use changes, inside a
# window of decision dates. `None` means no free source has that company's own history, so its rows
# stay unpriced rather than carry another company's prices. Each was checked on dividends and price
# levels against the two companies (9 Nov, local files only):
PRICE_OVERRIDES = [
    # (member ticker, price series or None, decisions from, decisions to)
    # ACE bought Chubb (14 Jan 2016) and took its name and CB ticker. Yahoo's CB before 2016 is
    # ACE's (dividends 0.63-0.67; +0.8% on the 1 Jul 2015 deal day), not the old Chubb's.
    ("ACE", "CB", "2010-01-01", "2016-01-18"),
    ("CB", None, "2010-01-01", "2016-01-18"),
    # Tyco bought Johnson Controls (Sep 2016) and took the JCI ticker. Yahoo's JCI before then is
    # Tyco's (its dividends are Tyco's 0.16/0.18/0.205 divided by the merger's 0.955 reverse split).
    ("TYC", "JCI", "2010-01-01", "2016-09-05"),
    ("JCI", None, "2010-01-01", "2016-09-05"),
    # Dow Chemical merged with DuPont as DowDuPont (DWDP, Sep 2017), which renamed itself DuPont
    # and took DD in 2019. Yahoo's DD is Dow Chemical's history before 2017 (dividends and the
    # end-2015 close are Dow's x 1.786), so it prices the old Dow and DowDuPont, not the old DuPont.
    ("DOW", "DD", "2010-01-01", "2017-08-31"),
    ("DWDP", "DD", "2017-09-01", "2019-06-30"),
    ("DD", None, "2010-01-01", "2017-08-31"),
    # AGL Resources bought Nicor (Dec 2011) and took the GAS ticker. Alpha Vantage's GAS before
    # then is AGL's (closes $36-39 and dividends 0.44-0.45; Nicor traded near $50).
    ("GAS", None, "2010-01-01", "2011-12-11"),
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

# Yahoo: tickers still empty after the first small-batch retry get one more round after this
# pause (seconds). Rate limits are more common on cloud runners (#39).
YAHOO_RETRY_PAUSE = 30

HTTP_HEADERS = {"User-Agent": "sp500-momentum-winners research script"}

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
