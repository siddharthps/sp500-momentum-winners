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


def test_check_sets_flags_unassigned_columns():
    with pytest.raises(ValueError, match="unassigned"):
        ft.check_sets(["a", "b"], {"X": ["a"]})
