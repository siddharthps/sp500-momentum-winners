"""Offline tests for the exploratory-analysis functions."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum import eda


def _panel(months=3, n=20, seed=0):
    """A small synthetic monthly table: next month's return rises with `sig`."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in pd.date_range("2015-01-31", periods=months, freq="ME"):
        sig = rng.normal(size=n)
        fwd = 0.01 * sig + rng.normal(scale=0.001, size=n)
        for i in range(n):
            rows.append(
                {
                    "date": d,
                    "ticker": f"T{i}",
                    "has_price": True,
                    "sig": sig[i],
                    "shared": 1.0,  # same for every stock (like a macro feature)
                    "ret_1m": sig[i],
                    "fwd_ret_1m": fwd[i],
                    "spy_fwd_ret_1m": 0.0,
                    "fwd_excess_1m": fwd[i],
                    "is_beat_spy_1m": int(fwd[i] > 0),
                    "fwd_trunc_1m": False,
                }
            )
    return pd.DataFrame(rows)


def test_monthly_ic_finds_signal_and_skips_shared_features():
    df = _panel()
    ic = eda.monthly_ic(df, "sig")
    assert len(ic) == 3 and (ic > 0.9).all()
    assert eda.monthly_ic(df, "shared").empty  # one value per month can't rank stocks


def test_research_rows_stop_at_the_end_date():
    df = _panel(months=6)
    out = eda.research_rows(df, end="2015-03-31")
    assert out["date"].max() == pd.Timestamp("2015-03-31")


def test_distinct_signals_collapses_identical_features():
    ic = pd.DataFrame(
        {"ic_mean": [0.02, 0.02, -0.01], "ic_std": [0.1, 0.1, 0.2]},
        index=["ret_1m", "rank_ret_1m", "vol_12m"],
    )
    out = eda.distinct_signals(ic)
    assert out.index.tolist() == ["ret_1m", "vol_12m"]
    assert out.loc["ret_1m", "same_as"] == ["rank_ret_1m"]


def test_plain_rule_picks_the_top_n_by_signal():
    df = _panel(months=2, n=10)
    m = eda.plain_rule_returns(df, signal="sig", top_ns=(1,))
    for d, g in df.groupby("date"):
        best = g.loc[g["sig"].idxmax(), "fwd_ret_1m"]
        assert m.loc[d, "top_1"] == pytest.approx(best)
        assert m.loc[d, "equal_weight"] == pytest.approx(g["fwd_ret_1m"].mean())


def test_performance_summary_cagr_and_drawdown():
    monthly = pd.DataFrame(
        {"a": [0.10, -0.50, 0.10] * 4, "spy": [0.0] * 12},
        index=pd.date_range("2020-01-31", periods=12, freq="ME"),
    )
    s = eda.performance_summary(monthly)
    growth = (1.1 * 0.5 * 1.1) ** 4
    assert s.loc["a", "growth_of_1"] == pytest.approx(growth)
    assert s.loc["a", "cagr"] == pytest.approx(growth - 1)  # exactly one year of months
    assert s.loc["a", "max_drawdown"] < -0.5
    assert s.loc["spy", "cagr"] == pytest.approx(0.0)


def test_removal_gap_counts_suspects_as_missing():
    cov = pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "reason_cat": ["acquired", "acquired", "market_cap"],
            "yahoo_ok": [True, False, True],
        }
    )
    t = eda.removal_gap(cov, suspects={"A"})
    assert t.loc["acquired", "missing"] == 2
    assert t.loc["market_cap", "on_yahoo"] == 1
