"""Alpha Vantage monthly adjusted prices for delisted S&P 500 members.

Free tier facts (checked Nov 2026):
- 25 requests a day, 1 a second.
- TIME_SERIES_DAILY with outputsize=full is premium; free daily is the last 100 days only.
- TIME_SERIES_MONTHLY_ADJUSTED is free with full history, and its adjusted close
  includes dividends and splits (KO matched yfinance within 0.1%, 2005-2026).
- Some old tickers return the company that reused the symbol later (e.g. STI),
  so every pull is checked against the removal date.

The pull is resumable: each run reads the manifest, skips tickers already done,
and stops at the daily budget or when Alpha Vantage says the quota is used up.
"""

import io
import os
import time

import pandas as pd
import requests

from sp500_momentum.config import AV_SLEEP_SECONDS

URL = "https://www.alphavantage.co/query"

# Pull order: the reasons that bias idea H most come first.
PRIORITY = {"bankrupt_failed": 0, "acquired": 1, "market_cap": 2, "spin_off": 3, "other": 4}


class QuotaExhausted(Exception):
    """Alpha Vantage refused the call because the daily limit is used up."""


def api_key() -> str:
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY is not set (put it in .env)")
    return key


def fetch_monthly_adjusted(symbol: str, key: str, retries: int = 2) -> pd.DataFrame | None:
    """Monthly adjusted OHLCV for one symbol, oldest first. None if AV has no data."""
    for attempt in range(retries + 1):
        text = requests.get(
            URL,
            params={
                "function": "TIME_SERIES_MONTHLY_ADJUSTED",
                "symbol": symbol,
                "apikey": key,
                "datatype": "csv",
            },
            timeout=60,
        ).text
        if text.startswith("timestamp"):
            df = pd.read_csv(io.StringIO(text), parse_dates=["timestamp"])
            return df.sort_values("timestamp").reset_index(drop=True)
        kind = classify_error(text)
        if kind == "no_data":
            return None
        if kind == "burst" and attempt < retries:
            time.sleep(AV_SLEEP_SECONDS * 2)
            continue
        if kind in ("quota", "burst"):
            raise QuotaExhausted(text[:200])
        raise RuntimeError(f"Unexpected Alpha Vantage response for {symbol}: {text[:200]}")
    return None


def classify_error(text: str) -> str:
    """Sort an Alpha Vantage non-CSV reply into no_data / burst / quota / unknown."""
    t = text.lower()
    if "invalid api call" in t or "error message" in t:
        return "no_data"
    # The burst and daily-quota messages are similar (both mention the per-second and
    # per-day limits), so a burst is retried and only treated as quota if it persists.
    if "per second" in t or "spreading out" in t:
        return "burst"
    if "per day" in t or "rate limit" in t or "premium" in t:
        return "quota"
    return "unknown"


def validate(df: pd.DataFrame | None, removed_date: pd.Timestamp) -> str:
    """Check a pull against the date the stock left the index.

    ok             history covers the time in the index
    no_data        Alpha Vantage has nothing
    reused_ticker  data starts after the removal date: a different company now uses the symbol
    ends_early     data stops more than ~3 months before the removal date
    """
    if df is None or df.empty:
        return "no_data"
    first, last = df["timestamp"].min(), df["timestamp"].max()
    if first > removed_date:
        return "reused_ticker"
    if last < removed_date - pd.Timedelta(days=95):
        return "ends_early"
    return "ok"


def build_queue(coverage: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    """Removed tickers yfinance can't cover, not yet pulled, highest-impact first."""
    q = coverage[~coverage["yahoo_ok"] & (coverage["reason_cat"] != "ticker_change")].copy()
    if not manifest.empty:
        q = q[~q["ticker"].isin(set(manifest["ticker"]))]
    q["priority"] = q["reason_cat"].map(PRIORITY).fillna(9)
    return q.sort_values(["priority", "removed_date"], ascending=[True, False]).reset_index(
        drop=True
    )
