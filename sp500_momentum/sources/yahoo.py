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


def yahoo_usable(span: pd.DataFrame, removed_date: pd.Series) -> pd.Series:
    """True when yfinance covers the stock's time in the index.

    Not usable: no rows, a 1-row stub (Yahoo keeps only the last print of some recent
    delistings), or data that starts after the removal date (the ticker was reused).
    """
    first = pd.to_datetime(span["yf_first"]).dt.tz_localize(None)
    return (span["yf_rows"] > 1) & (first <= removed_date)
