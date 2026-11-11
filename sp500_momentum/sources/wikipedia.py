"""S&P 500 membership from Wikipedia: today's list plus the table of historical changes.

The changes table moved off the main list page to its own article,
"Historical components of the S&P 500" (checked Nov 2026).
"""

import io
import re

import pandas as pd
import requests

from sp500_momentum.config import HTTP_HEADERS
from sp500_momentum.retries import with_retries

CURRENT_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CHANGES_URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"


def normalize_ticker(t: str) -> str:
    """Wikipedia writes class shares as BRK.B; yfinance and Alpha Vantage use BRK-B.

    Stray characters are dropped too (one row reads "ALLE |")."""
    return re.sub(r"[^A-Z0-9-]", "", str(t).upper().replace(".", "-"))


def _get_tables(url: str) -> list[pd.DataFrame]:
    def fetch() -> str:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=30)
        r.raise_for_status()  # an error page must not be parsed as the list
        return r.text

    return pd.read_html(io.StringIO(with_retries(fetch, "Wikipedia")))


def fetch_current() -> pd.DataFrame:
    """Today's members: ticker, name, GICS sector and sub-industry, date added, CIK."""
    df = _get_tables(CURRENT_URL)[0]
    df = df.rename(
        columns={
            "Symbol": "ticker",
            "Security": "name",
            "GICS Sector": "sector",
            "GICS Sub-Industry": "sub_industry",
            "Date added": "date_added",
            "CIK": "cik",
        }
    )
    df["ticker"] = df["ticker"].map(normalize_ticker)
    df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
    return df[["ticker", "name", "sector", "sub_industry", "date_added", "cik"]]


def fetch_changes() -> pd.DataFrame:
    """One row per change: date, added ticker/name, removed ticker/name, reason."""
    tables = _get_tables(CHANGES_URL)
    df = next(
        t
        for t in tables
        if isinstance(t.columns, pd.MultiIndex) and "Removed" in t.columns.get_level_values(0)
    )
    df.columns = [
        "_".join(dict.fromkeys(c)) for c in df.columns
    ]  # ('Added','Ticker') -> 'Added_Ticker'
    df = df.rename(
        columns={
            "Effective Date": "date",
            "Added_Ticker": "added_ticker",
            "Added_Security": "added_name",
            "Removed_Ticker": "removed_ticker",
            "Removed_Security": "removed_name",
            "Reason": "reason",
        }
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["added_ticker", "removed_ticker"]:
        df[col] = df[col].where(df[col].isna(), df[col].map(normalize_ticker))
    return df[["date", "added_ticker", "added_name", "removed_ticker", "removed_name", "reason"]]


# Order matters: the first pattern that matches wins.
REASON_PATTERNS = [
    ("ticker_change", r"changed its ticker|ticker symbol|renamed"),
    ("bankrupt_failed", r"bankrupt|chapter 11|fail|fdic|receivership|collapse|seized"),
    ("spin_off", r"spin|split"),
    ("acquired", r"acqui|merge|bought|purchas|take|buyout|private|combin"),
    (
        "market_cap",
        r"market cap|capitaliz|index|float|liquidity|sector|representat|rebalanc|eligib|criteria",
    ),
]


def classify_reason(reason) -> str:
    """Rough bucket from Wikipedia's free-text 'Reason' column (keyword match)."""
    text = str(reason).lower() if pd.notna(reason) else ""
    for label, pattern in REASON_PATTERNS:
        if re.search(pattern, text):
            return label
    return "other"


def removed_since(changes: pd.DataFrame, current: pd.DataFrame, start: str) -> pd.DataFrame:
    """Tickers removed on or after `start` that aren't members today.

    A ticker removed more than once keeps its latest removal.
    """
    rem = changes.dropna(subset=["removed_ticker"]).copy()
    rem = rem[rem["date"] >= start]
    rem = rem.sort_values("date", ascending=False).drop_duplicates("removed_ticker")
    rem = rem[~rem["removed_ticker"].isin(set(current["ticker"]))]
    rem["reason_cat"] = rem["reason"].map(classify_reason)
    return rem.rename(
        columns={"removed_ticker": "ticker", "removed_name": "name", "date": "removed_date"}
    )[["ticker", "name", "removed_date", "reason", "reason_cat"]].reset_index(drop=True)
