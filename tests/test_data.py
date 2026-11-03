"""Offline tests for the data helpers (no network calls)."""

import pandas as pd
import pytest

from sp500_momentum.sources import alphavantage as av
from sp500_momentum.sources.wikipedia import classify_reason, normalize_ticker, removed_since
from sp500_momentum.sources import yahoo
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


def test_price_universe_groups_and_dedup():
    current = pd.DataFrame({"ticker": ["AAPL", "MSFT"]})
    cov = pd.DataFrame(
        {
            "ticker": ["OLD", "GONE"],
            "removed_date": pd.to_datetime(["2015-01-01", "2020-01-01"]),
            "yahoo_ok": [True, False],
        }
    )
    u = yahoo.price_universe(current, cov, ["SPY", "AAPL"])
    assert u["ticker"].tolist() == ["AAPL", "MSFT", "OLD", "SPY"]
    assert u.set_index("ticker")["group"].to_dict() == {
        "AAPL": "current",
        "MSFT": "current",
        "OLD": "removed",
        "SPY": "benchmark",
    }


def test_tidy_daily_and_file_name():
    raw = pd.DataFrame(
        {
            "Open": [1.0, None],
            "High": [1.0, None],
            "Low": [1.0, None],
            "Close": [1.0, None],
            "Adj Close": [0.9, None],
            "Volume": [10, None],
            "Dividends": [0.0, None],
            "Stock Splits": [0.0, None],
            "Capital Gains": [0.0, None],
        },
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )
    df = yahoo.tidy_daily(raw)
    assert list(df.columns) == ["date", *yahoo.DAILY_COLUMNS.values()]
    assert len(df) == 1
    assert yahoo.file_name("^VIX") == "_VIX.parquet"


def test_check_daily():
    good = pd.DataFrame(
        {"date": pd.to_datetime(["2010-01-04", "2010-01-05"]), "close": [5.0, 6.0], "adj_close": [4.0, 5.0]}
    )
    assert yahoo.check_daily(good) == "ok"
    assert yahoo.check_daily(good, pd.Timestamp("2009-06-01")) == "reused_ticker"
    assert yahoo.check_daily(good.head(1)) == "stub"
    assert yahoo.check_daily(None) == "no_data"
    bad = good.assign(close=[5.0, 0.0])
    assert yahoo.check_daily(bad) == "bad_prices"


def test_point_in_time_walks_changes_backwards():
    from sp500_momentum.membership import point_in_time

    current = pd.DataFrame({"ticker": ["A", "NEW"]})
    changes = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-06-15"]),
            "added_ticker": ["NEW"],
            "removed_ticker": ["OLD"],
        }
    )
    dates = pd.to_datetime(["2020-05-29", "2020-06-15", "2020-06-30"])
    m = point_in_time(current, changes, dates)
    by = m.groupby("date")["ticker"].apply(set).to_dict()
    assert by[pd.Timestamp("2020-05-29")] == {"A", "OLD"}
    assert by[pd.Timestamp("2020-06-15")] == {"A", "NEW"}  # effective on its date


def test_month_ends_skips_the_unfinished_month():
    from sp500_momentum.membership import month_ends

    days = pd.Series(pd.to_datetime(["2026-09-30", "2026-10-29", "2026-10-30", "2026-11-02"]))
    out = month_ends(days, "2026-01-01", asof="2026-11-03")
    assert out.tolist() == [pd.Timestamp("2026-09-30"), pd.Timestamp("2026-10-30")]


def test_repair_changes_renames_in_window_and_adds_missing():
    from sp500_momentum.membership import repair_changes

    changes = pd.DataFrame(
        {
            "date": pd.to_datetime(["2013-12-23", "2022-01-10", "2025-11-03"]),
            "added_ticker": ["FB", "WTW", "Q"],
            "removed_ticker": ["XX", "WLTW", None],
            "reason": ["", "", ""],
        }
    )
    renames = [("FB", "META", "2013-12-01", "2013-12-31"), ("WLTW", "WTW", "2016-01-01", "2022-01-31")]
    renames += [("Q", "IQV", "2017-08-01", "2017-11-30")]
    out = repair_changes(changes, renames, {"SW": "2024-07-08"})
    assert "META" in set(out["added_ticker"])
    assert "WLTW" not in set(out["removed_ticker"].dropna())  # pure rename row dropped
    assert "Q" in set(out["added_ticker"])  # outside the Q window: Qnity keeps "Q"
    assert out.loc[out["added_ticker"] == "SW", "date"].iloc[0] == pd.Timestamp("2024-07-08")


def test_clean_ticker():
    from sp500_momentum.membership import clean_ticker

    assert clean_ticker("ALLE |") == "ALLE"
    assert normalize_ticker("JCP |") == "JCP"
    assert pd.isna(clean_ticker(None))


def test_add_returns_truncates_at_delisting():
    from sp500_momentum.monthly import add_returns

    months = pd.period_range("2023-01", "2023-04", freq="M")
    p = pd.DataFrame(
        {"month": months[:3], "close_adj": [100.0, 110.0, 1.0], "entry_px": [100.0, 110.0, 1.0]}
    )
    out = add_returns(p, holds=[1, 3], data_end=pd.Period("2023-12", "M"))
    assert out["fwd_ret_1m"].iloc[0] == pytest.approx(0.10)
    # held 3 months from Jan: prices stop in Mar, valued at the last price (1.0), then cash
    assert out["fwd_ret_3m"].iloc[0] == pytest.approx(-0.99)
    assert bool(out["fwd_trunc_3m"].iloc[0])
    assert out["ret_1m"].iloc[1] == pytest.approx(0.10)


def test_add_returns_unknown_after_data_end():
    from sp500_momentum.monthly import add_returns

    p = pd.DataFrame(
        {
            "month": pd.period_range("2026-08", "2026-10", freq="M"),
            "close_adj": [1.0, 2.0, 3.0],
            "entry_px": [1.0, 2.0, None],
        }
    )
    out = add_returns(p, holds=[1], data_end=pd.Period("2026-09", "M"))
    assert out["fwd_ret_1m"].iloc[0] == pytest.approx(1.0)
    assert out["fwd_ret_1m"].iloc[1:].isna().all()


def test_fred_parse_csv_drops_missing():
    from sp500_momentum.sources.fred import parse_csv

    text = "observation_date,DGS10\n2025-10-01,4.1\n2025-10-02,.\n2025-10-03,\n2025-10-06,4.2\n"
    df = parse_csv(text, "DGS10")
    assert list(df.columns) == ["date", "value"]
    assert df["value"].tolist() == [4.1, 4.2]
    assert df["date"].iloc[-1] == pd.Timestamp("2025-10-06")


def test_yahoo_monthly_entry_is_next_days_adjusted_open():
    from sp500_momentum.monthly import yahoo_monthly

    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28"]),
            "open": [10.0, 11.0, 20.0, 21.0],
            "close": [10.0, 12.0, 20.0, 22.0],
            "adj_close": [5.0, 6.0, 10.0, 11.0],  # adjustment factor 0.5
            "volume": [1e6, 3e6, 1e6, 1e6],
        }
    )
    m = yahoo_monthly(daily).set_index("month")
    jan = m.loc[pd.Period("2020-01", "M")]
    assert jan["close_adj"] == 6.0  # last adjusted close of January
    assert jan["entry_px"] == pytest.approx(10.0)  # Feb 3 open 20 * 10/20
    assert jan["dollar_vol"] == pytest.approx((10e6 + 36e6) / 2)  # median of the month's days
    assert pd.isna(m.loc[pd.Period("2020-02", "M"), "entry_px"])  # no March data yet


def test_av_monthly_keeps_the_removal_month_then_stops():
    from sp500_momentum.monthly import av_monthly

    av_rows = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2023-01-31", "2023-02-28", "2023-03-31", "2023-04-28"]),
            "adjusted close": [302.44, 288.11, 0.905, 0.07],
        }
    )
    m = av_monthly(av_rows, pd.Timestamp("2023-03-15"))
    assert m["month"].astype(str).tolist() == ["2023-01", "2023-02", "2023-03"]
    assert m["close_adj"].iloc[-1] == 0.905  # the crash month is kept
    assert (m["entry_px"] == m["close_adj"]).all()  # monthly data trades at the month-end close


def test_suspect_tickers_only_counts_member_months():
    from sp500_momentum.monthly import suspect_tickers

    months = pd.period_range("2015-01", "2015-04", freq="M")
    prices = pd.DataFrame(
        {
            "price_ticker": ["BIG"] * 4 + ["JUNK"] * 4,
            "month": list(months) * 2,
            # JUNK is liquid only in months when it wasn't a member
            "dollar_vol": [50e6] * 4 + [0.1e6, 0.1e6, 80e6, 80e6],
            "source": "yahoo",
        }
    )
    members = pd.DataFrame(
        {
            "date": pd.to_datetime(["2015-01-30", "2015-02-27"] * 2),
            "ticker": ["BIG", "BIG", "JUNK", "JUNK"],
        }
    )
    out = suspect_tickers(members, prices, min_dollar_vol=10e6)
    assert out.index.tolist() == ["JUNK"]


def test_coverage_for_av_treats_suspects_as_missing(tmp_path, monkeypatch):
    from sp500_momentum import dataset

    cov_path, sus_path = tmp_path / "cov.csv", tmp_path / "sus.csv"
    pd.DataFrame(
        {"ticker": ["CPWR", "OK"], "removed_date": ["2011-12-31", "2015-01-01"], "yahoo_ok": [True, True]}
    ).to_csv(cov_path, index=False)
    pd.DataFrame({"ticker": ["CPWR"]}).to_csv(sus_path, index=False)
    monkeypatch.setattr(dataset, "REMOVED_COVERAGE", cov_path)
    monkeypatch.setattr(dataset, "YAHOO_SUSPECT", sus_path)
    out = dataset._coverage_for_av().set_index("ticker")["yahoo_ok"]
    assert not out["CPWR"]
    assert out["OK"]
