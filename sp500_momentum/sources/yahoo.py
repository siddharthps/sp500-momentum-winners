"""yfinance helpers. (Named yahoo.py so it doesn't shadow the yfinance package.)"""

import logging
import warnings

import pandas as pd
import yfinance as yf


def history_span(tickers: list[str], start: str = "1995-01-01", chunk: int = 50) -> pd.DataFrame:
    """Rows, first and last date of adjusted daily closes yfinance has for each ticker."""
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    out = []
    for i in range(0, len(tickers), chunk):
        part = tickers[i : i + chunk]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = yf.download(
                part,
                start=start,
                progress=False,
                auto_adjust=True,
                group_by="ticker",
                threads=True,
            )
        for t in part:
            try:
                s = data[t]["Close"].dropna()
            except KeyError:
                s = pd.Series(dtype=float)
            out.append(
                {
                    "ticker": t,
                    "yf_rows": len(s),
                    "yf_first": s.index.min() if len(s) else pd.NaT,
                    "yf_last": s.index.max() if len(s) else pd.NaT,
                }
            )
    return pd.DataFrame(out)


DAILY_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividends",
    "Stock Splits": "stock_splits",
}


def price_universe(
    current: pd.DataFrame, coverage: pd.DataFrame, benchmarks: list[str]
) -> pd.DataFrame:
    """Every ticker to download from yfinance, with its group and removal date.

    Groups: `current` (today's members), `removed` (left the index since the start date and
    yfinance has their history, i.e. `yahoo_ok`), `benchmark` (SPY, sector ETFs, VIX).
    """
    cur = pd.DataFrame({"ticker": current["ticker"], "group": "current", "removed_date": pd.NaT})
    rem = coverage.loc[coverage["yahoo_ok"].astype(bool), ["ticker", "removed_date"]].copy()
    rem["group"] = "removed"
    bench = pd.DataFrame({"ticker": benchmarks, "group": "benchmark", "removed_date": pd.NaT})
    out = pd.concat([cur, rem, bench], ignore_index=True)
    out["removed_date"] = pd.to_datetime(out["removed_date"])
    return out.drop_duplicates("ticker").reset_index(drop=True)[
        ["ticker", "group", "removed_date"]
    ]


def file_name(ticker: str) -> str:
    """`^VIX` -> `_VIX.parquet` (keeps the file names plain)."""
    return ticker.replace("^", "_") + ".parquet"


def tidy_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """One ticker's yf.download frame -> date + lower-case columns, empty rows dropped.

    Prices are kept **unadjusted** next to `adj_close`, so the adjusted open (the trade price)
    can be rebuilt as open * adj_close / close, and dividends and splits stay visible.
    """
    df = raw.rename(columns=DAILY_COLUMNS)
    df = df[[c for c in DAILY_COLUMNS.values() if c in df.columns]]
    df = df.dropna(subset=["close"])
    df.index = pd.to_datetime(df.index).tz_localize(None).astype("datetime64[ns]")
    df.index.name = "date"
    return df.reset_index()


def download_daily(
    tickers: list[str], start: str, end: str, chunk: int = 50
) -> dict[str, pd.DataFrame]:
    """Daily OHLCV, adjusted close, dividends and splits from yfinance, for [start, end).

    `end` is exclusive, so passing today's date leaves out a half-finished trading day.
    Tickers yfinance has nothing for come back as empty frames.
    """
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    out = {}
    for i in range(0, len(tickers), chunk):
        part = tickers[i : i + chunk]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = yf.download(
                part,
                start=start,
                end=end,
                progress=False,
                auto_adjust=False,
                actions=True,
                group_by="ticker",
                threads=True,
            )
        for t in part:
            try:
                df = tidy_daily(data[t])
                # yfinance's `end` lets futures (GC=F, CL=F) through with today's half-finished
                # bar, because they trade overnight. Keep strictly before `end`.
                out[t] = df[df["date"] < pd.Timestamp(end)].reset_index(drop=True)
            except KeyError:
                out[t] = pd.DataFrame(columns=["date", *DAILY_COLUMNS.values()])
    return out


def check_daily(df: pd.DataFrame, removed_date=None) -> str:
    """`ok`, `no_data`, `stub` (1 row), `bad_prices` (zero or negative closes) or
    `reused_ticker` (a removed member whose data starts after its removal date)."""
    if df is None or df.empty:
        return "no_data"
    if len(df) <= 1:
        return "stub"
    if (df["close"] <= 0).any() or (df["adj_close"] <= 0).any():
        return "bad_prices"
    if pd.notna(removed_date) and df["date"].min() > pd.Timestamp(removed_date):
        return "reused_ticker"
    return "ok"


def yahoo_usable(span: pd.DataFrame, removed_date: pd.Series) -> pd.Series:
    """True when yfinance covers the stock's time in the index.

    Not usable: no rows, a 1-row stub (Yahoo keeps only the last print of some recent
    delistings), or data that starts after the removal date (the ticker was reused).
    """
    first = pd.to_datetime(span["yf_first"]).dt.tz_localize(None)
    return (span["yf_rows"] > 1) & (first <= removed_date)
