"""Offline tests for the data helpers (no network calls)."""

import pandas as pd

from sp500_momentum.sources import alphavantage as av
from sp500_momentum.sources.wikipedia import classify_reason, normalize_ticker, removed_since
from sp500_momentum.sources.yahoo import yahoo_usable


def test_normalize_ticker():
    assert normalize_ticker(" brk.b ") == "BRK-B"


def test_classify_reason():
    assert classify_reason("Capital One acquired Discover Financial.") == "acquired"
    assert classify_reason("Market capitalization changes.") == "market_cap"
    assert classify_reason("Ceridian changed its ticker symbol from CDAY to DAY.") == "ticker_change"
    assert classify_reason("SVB Financial Group failed and was taken over by the FDIC.") == "bankrupt_failed"
    assert classify_reason(None) == "other"


def test_removed_since_drops_current_members_and_keeps_latest_removal():
    changes = pd.DataFrame(
        {
            "date": pd.to_datetime(["2012-01-01", "2020-01-01", "2021-01-01", "2005-01-01"]),
            "added_ticker": None,
            "added_name": None,
            "removed_ticker": ["XYZ", "XYZ", "AAPL", "OLD"],
            "removed_name": ["Xyz", "Xyz", "Apple", "Old"],
            "reason": ["Market cap", "Acquired by Foo", "Market cap", "Market cap"],
        }
    )
    current = pd.DataFrame({"ticker": ["AAPL"]})
    out = removed_since(changes, current, "2010-01-01")
    assert out["ticker"].tolist() == ["XYZ"]
    assert out["removed_date"].iloc[0] == pd.Timestamp("2020-01-01")


def test_yahoo_usable_rejects_stubs_and_reused_tickers():
    span = pd.DataFrame(
        {
            "yf_rows": [5000, 1, 300, 0],
            "yf_first": pd.to_datetime(["2000-01-03", "2026-08-26", "2024-08-15", None]),
        }
    )
    removed = pd.Series(pd.to_datetime(["2022-01-01", "2021-12-20", "2023-03-15", "2020-01-01"]))
    assert yahoo_usable(span, removed).tolist() == [True, False, False, False]


def test_av_validate():
    removed = pd.Timestamp("2022-10-27")
    ok = pd.DataFrame({"timestamp": pd.to_datetime(["2013-12-31", "2022-10-28"])})
    reused = pd.DataFrame({"timestamp": pd.to_datetime(["2024-03-28", "2026-11-02"])})
    early = pd.DataFrame({"timestamp": pd.to_datetime(["2013-12-31", "2021-01-29"])})
    assert av.validate(ok, removed) == "ok"
    assert av.validate(reused, removed) == "reused_ticker"
    assert av.validate(early, removed) == "ends_early"
    assert av.validate(None, removed) == "no_data"


def test_av_classify_error():
    assert av.classify_error('{"Error Message": "Invalid API call."}') == "no_data"
    burst = "Please consider spreading out your free API requests more sparingly (1 request per second)."
    assert av.classify_error(burst) == "burst"
    assert av.classify_error("standard API rate limit is 25 requests per day") == "quota"


def test_build_queue_order_and_skips():
    cov = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D", "E"],
            "removed_date": pd.to_datetime(["2020-01-01", "2023-03-15", "2021-01-01", "2024-01-01", "2019-01-01"]),
            "reason_cat": ["market_cap", "bankrupt_failed", "acquired", "acquired", "ticker_change"],
            "yahoo_ok": [False, False, False, True, False],
        }
    )
    manifest = pd.DataFrame({"ticker": ["C"]})
    q = av.build_queue(cov, manifest)
    assert q["ticker"].tolist() == ["B", "A"]  # bankrupt first; C done, D on yfinance, E is a rename
