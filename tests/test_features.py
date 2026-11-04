"""Offline tests for the feature step, focused on the golden rule (no look-ahead)."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum import features as ft


def test_bars_from_daily_adjusts_and_rolls_up():
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-02", "2020-01-31", "2020-02-03"]),
            "open": [10.0, 11.0, 12.0],
            "high": [12.0, 13.0, 14.0],
            "low": [9.0, 10.0, 11.0],
            "close": [11.0, 12.0, 13.0],
            "adj_close": [5.5, 6.0, 13.0],  # factor 0.5 in January, 1.0 in February
            "volume": [100.0, 200.0, 300.0],
        }
    )
    b = ft.bars_from_daily(daily)
    jan = b.loc[pd.Period("2020-01", "M")]
    assert jan["open"] == pytest.approx(5.0)  # first open, adjusted
    assert jan["high"] == pytest.approx(6.5)
    assert jan["close"] == 6.0  # last adjusted close
    assert jan["dollar_vol"] == pytest.approx(11 * 100 + 12 * 200)  # raw close x volume
    assert jan["volume"] == pytest.approx(600.0)  # volume in adjusted units (/ 0.5)


def test_bars_from_av_adjusts_raw_prices_and_cuts_after_removal():
    av = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2008-03-31", "2008-04-30", "2008-05-30"]),
            "open": [40.0, 30.0, 31.0],
            "high": [42.0, 32.0, 33.0],
            "low": [38.0, 28.0, 29.0],
            "close": [40.0, 30.0, 31.0],
            "adjusted close": [20.0, 30.0, 31.0],  # a 2-for-1 split shows as factor 0.5
            "volume": [1000.0, 2000.0, 2000.0],
        }
    )
    b = ft.bars_from_av(av, pd.Timestamp("2008-04-15"))
    assert b.index.astype(str).tolist() == ["2008-03", "2008-04"]  # May is after the removal month
    mar = b.loc[pd.Period("2008-03", "M")]
    assert mar["high"] == pytest.approx(21.0)
    assert mar["volume"] == pytest.approx(2000.0)  # 1000 pre-split shares = 2000 adjusted shares
    assert mar["dollar_vol"] == pytest.approx(40_000.0)


def test_monthly_lagged_uses_the_published_month_and_fills_gaps():
    series = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-08-01", "2025-09-01", "2025-11-01"]),  # Oct missing
            "value": [1.0, 2.0, 4.0],
        }
    )
    months = pd.PeriodIndex(["2025-09", "2025-11", "2025-12"], freq="M")
    out = ft.monthly_lagged(series, months, lag=1)
    # at the end of Sep, August's figure is the latest published; at the end of Nov, October's
    # (missing, so September's carried forward); at the end of Dec, November's
    assert out.tolist() == [1.0, 2.0, 4.0]


def test_yield_before_is_strictly_before_the_decision_date():
    s = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-28", "2026-10-29", "2026-10-30"]),
            "value": [1.0, 2.0, 3.0],
        }
    )
    out = ft.yield_before(s, pd.Series(pd.to_datetime(["2026-10-30"])))
    assert out.iloc[0] == 2.0  # 30 Oct's own value is only published the next day


def test_ta_features_are_scale_free():
    rng = np.random.default_rng(0)
    close = 100 * np.cumprod(1 + rng.normal(0.01, 0.05, 120))
    b = pd.DataFrame(
        {
            "open": close * 0.99,
            "high": close * 1.03,
            "low": close * 0.97,
            "close": close,
            "volume": rng.uniform(1e6, 2e6, 120),
            "dollar_vol": 1.0,
        },
        index=pd.period_range("2010-01", periods=120, freq="M"),
    )
    a = ft.ta_features(b)
    scaled = b.copy()
    scaled[["open", "high", "low", "close"]] *= 50  # same stock, 50x the share price
    z = ft.ta_features(scaled)
    pd.testing.assert_frame_equal(a, z, rtol=1e-6)


def test_cross_section_ranks_stay_within_each_date():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * 2 + ["2020-02-28"] * 2),
            "month_p": pd.PeriodIndex(["2020-01"] * 2 + ["2020-02"] * 2, freq="M"),
            "ticker": ["A", "B", "A", "B"],
            "sector": "Energy",
            "ret_1m": [0.10, 0.20, -0.50, -0.40],  # February is a crash month for both
            "ret_3m": 0.0,
            "ret_6m": 0.0,
            "ret_12m": 0.0,
            "ret_12_1m": 0.0,
            "mkt_spy_ret_1m": 0.0,
            "mkt_spy_ret_12m": 0.0,
            "sector_etf_ret_1m": 0.0,
            "sector_etf_ret_12m": 0.0,
            "above_ma10": 1.0,
        }
    )
    monthly_ret = pd.DataFrame({"A": [0.1, -0.5], "B": [0.2, -0.4]}, index=df["month_p"].unique())
    out = ft.cross_section_features(df, monthly_ret)
    # B is the best stock in both months, even though February's returns are all negative
    assert out.loc[out["ticker"] == "B", "rank_ret_1m"].tolist() == [1.0, 1.0]


def _bars(close, start="2010-01", div=None):
    close = np.asarray(close, dtype=float)
    b = pd.DataFrame(
        {
            "open": close,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": 1e6,
            "dollar_vol": 1e8,
        },
        index=pd.period_range(start, periods=len(close), freq="M"),
    )
    if div is not None:
        b["div_yield"] = div
    return b


def test_dividend_yield_is_the_same_for_both_sources_and_ignores_splits():
    # Yahoo: daily rows, split-adjusted close and dividends; a $1 dividend on a $50 close
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-03-02", "2020-03-16", "2020-03-31"]),
            "open": 50.0,
            "high": 51.0,
            "low": 49.0,
            "close": 50.0,
            "adj_close": 50.0,
            "volume": 100.0,
            "dividends": [0.0, 1.0, 0.0],
        }
    )
    # Alpha Vantage: raw prices; the same 2% dividend, paid before a 2-for-1 split
    av = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2020-03-31", "2020-04-30"]),
            "open": [100.0, 50.0],
            "high": [101.0, 51.0],
            "low": [99.0, 49.0],
            "close": [100.0, 50.0],
            "adjusted close": [50.0, 50.0],
            "volume": 100.0,
            "dividend amount": [2.0, 0.0],
        }
    )
    y = ft.bars_from_daily(daily).loc[pd.Period("2020-03", "M"), "div_yield"]
    a = ft.bars_from_av(av, pd.Timestamp("2020-12-31"))["div_yield"]
    assert y == pytest.approx(0.02)
    assert a.tolist() == pytest.approx([0.02, 0.0])  # the split doesn't change the yield


def test_new_stock_features_use_only_past_months():
    rng = np.random.default_rng(1)
    close = 100 * np.cumprod(1 + rng.normal(0.01, 0.06, 96))
    b = _bars(close, div=np.r_[np.zeros(95), 0.01])
    spy = pd.Series(rng.normal(0.01, 0.04, 96), index=b.index)
    full = ft.stock_features(b, spy)
    # Cut the data at month 60: every value up to month 60 must be unchanged (no look-ahead).
    cut = ft.stock_features(b.iloc[:61], spy.iloc[:61])
    new = [
        "div_yield_12m",
        "mom_12_1m_per_vol",
        "drawdown_ath",
        "resid_mom_12_1m",
        "ivol_36m",
        "max_ret_12m",
        "seasonality_5y",
    ]
    pd.testing.assert_frame_equal(full[new].iloc[:61], cut[new])
    r = b["close"].pct_change()
    t = b.index[60]
    assert full.loc[t, "max_ret_12m"] == pytest.approx(r.iloc[49:61].max())
    # seasonality at the end of month t averages the returns of month t+1 in past years
    assert full.loc[t, "seasonality_5y"] == pytest.approx(
        np.mean([r.iloc[61 - 12 * k] for k in range(1, 6)])
    )
    assert full["drawdown_ath"].max() <= 0


def test_months_in_index_uses_the_latest_add_on_or_before_each_date():
    changes = pd.DataFrame(
        {
            "date": pd.to_datetime(["2012-01-03", "2015-06-01"]),
            "added_ticker": ["NEW", "NEW"],  # added, (removed in between), re-added
            "removed_ticker": [pd.NA, pd.NA],
        }
    )
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2011-12-30", "2013-01-31", "2015-06-30", "2013-01-31"]),
            "ticker": ["NEW", "NEW", "NEW", "OLD"],
        }
    )
    out = ft.months_in_index(df, changes)
    assert out.iloc[0] == 120  # before any add row: joined before the record, capped
    assert out.iloc[1] == pytest.approx(13, abs=0.1)
    assert out.iloc[2] == pytest.approx(1, abs=0.1)  # the later add counts, not the first
    assert out.iloc[3] == 120  # no add row at all


def test_check_sets_flags_unassigned_columns():
    with pytest.raises(ValueError, match="unassigned"):
        ft.check_sets(["a", "b"], {"X": ["a"]})
