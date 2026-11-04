"""Offline tests for the rule columns and the staggered-portfolio simulation."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum import backtest as bt
from sp500_momentum.monthly import prefer_alphavantage

M = pd.Period("2020-01", freq="M")


def _values(cols: dict[str, list[float]], start=M) -> pd.DataFrame:
    n = len(next(iter(cols.values())))
    return pd.DataFrame(cols, index=pd.period_range(start, periods=n, freq="M"))


def test_add_rule_preds_picks_top_n_per_date_among_eligible():
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * 4 + ["2020-02-28"] * 2),
            "ticker": ["A", "B", "C", "D", "A", "B"],
            "has_price": [True, True, True, False, True, True],
            "entry_px": [1.0, 1.0, 1.0, 1.0, 1.0, np.nan],
            "ret_1m": [0.1, 0.3, 0.3, 0.9, 0.0, 0.5],
        }
    )
    out = bt.add_rule_preds(panel, signals=["ret_1m"], top_ns=[1, 2])
    # D has no price and B in Feb has no trade price: neither can be picked.
    # B and C tie in Jan; the alphabetically first wins the single slot.
    assert out["pred_mom_1m_top1"].tolist() == [0, 1, 0, 0, 1, 0]
    assert out["pred_mom_1m_top2"].tolist() == [0, 1, 1, 0, 1, 0]


def test_value_matrix_uses_last_close_then_holds_cash_and_stops_at_spy_end():
    months = [str(M + i) for i in range(4)]
    prices = pd.DataFrame(
        {
            "month": months * 2,
            "price_ticker": ["SPY"] * 4 + ["X"] * 4,
            "close_adj": [1, 1, 1, 1, 10, 11, 12, np.nan],
            "entry_px": [1, 1, 1, np.nan, 10, 11, np.nan, np.nan],
        }
    )
    v = bt.value_matrix(prices)
    assert v.index.max() == M + 2  # SPY's last entry price
    assert v["X"].tolist() == [10, 11, 12]  # last month: its close; nothing after


def test_simulate_hold_1_without_costs_is_the_mean_return_of_the_picks():
    values = _values({"A": [10, 11, 11], "B": [20, 18, 27]})
    picks = {M: ["A", "B"], M + 1: ["A", "B"]}
    sim = bt.simulate(picks, values, hold=1, cost=0)
    assert sim.index.tolist() == [M + 1, M + 2]  # labelled by the month earned
    assert sim["ret"].tolist() == pytest.approx([(0.1 - 0.1) / 2, (0.0 + 0.5) / 2])


def test_simulate_charges_only_what_is_traded():
    values = _values({"A": [10, 10, 10, 10], "B": [10, 10, 10, 10]})
    picks = {M: ["A"], M + 1: ["A"], M + 2: ["B"]}
    sim = bt.simulate(picks, values, hold=1, cost=0.001)
    # buy A (1 side), keep A (nothing), swap A for B (2 sides)
    assert sim["cost"].tolist() == pytest.approx([0.001, 0.0, 0.002])


def test_simulate_staggered_slots_are_buy_and_hold():
    values = _values({"A": [10, 20, 20, 20], "B": [10, 10, 5, 5]})
    picks = {M: ["A", "B"], M + 1: ["B"], M + 2: ["B"]}
    sim = bt.simulate(picks, values, hold=2, cost=0)
    # month 1: only slot 0 exists (A+B): +50%
    # month 2: slot 0 now 2/3 A (flat) + 1/3 B (-50%) = -1/6; slot 1 holds B: -50%
    assert sim["ret"].tolist() == pytest.approx([0.5, (-1 / 6 - 0.5) / 2, 0.0])


def test_simulate_values_a_delisted_stock_as_cash():
    prices = pd.DataFrame(
        {
            "month": [str(M + i) for i in range(4)] * 2,
            "price_ticker": ["SPY"] * 4 + ["X"] * 4,
            "close_adj": [1, 1, 1, 1, 10, 5, np.nan, np.nan],
            "entry_px": [1, 1, 1, 1, 10, np.nan, np.nan, np.nan],
        }
    )
    values = bt.value_matrix(prices)
    sim = bt.simulate({M: ["X"]}, values, hold=3, cost=0)
    assert sim["ret"].tolist() == pytest.approx([-0.5, 0.0, 0.0])


def test_simulate_fails_loudly_on_a_missing_price():
    values = _values({"A": [10, np.nan]})
    with pytest.raises(ValueError, match="No value"):
        bt.simulate({M: ["A"]}, values, hold=1)


def test_parse_cell_round_trips_rule_name():
    name = f"{bt.rule_name('ret_12_1m', 10)}_h3"
    assert name == "pred_mom_12_1m_top10_h3"
    assert bt.parse_cell(name) == {"lookback": "ret_12_1m", "top_n": 10, "hold": 3}


def test_performance_on_a_known_series():
    idx = pd.period_range(M, periods=12, freq="M")
    r = pd.Series([0.01] * 12, index=idx)
    spy = pd.Series([0.0] * 6 + [0.02] * 6, index=idx)
    rf = pd.Series(0.0, index=idx)
    p = bt.performance(r, spy, rf)
    assert p["cagr"] == pytest.approx(1.01**12 - 1)
    assert p["volatility"] == pytest.approx(0) and np.isnan(p["sharpe"])
    assert p["beats_spy_months"] == 0.5
    assert p["max_drawdown"] == 0


def test_selection_uses_only_months_before_the_split():
    idx = pd.period_range("2021-01", periods=24, freq="M")
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.01, 24)
    good_early = np.where(idx < pd.Period("2022-01", freq="M"), 0.03, -0.02) + noise
    good_late = np.where(idx < pd.Period("2022-01", freq="M"), -0.02, 0.03) + noise
    rets = pd.DataFrame(
        {"pred_mom_1m_top1_h1": good_early, "pred_mom_3m_top1_h1": good_late}, index=idx
    )
    costs = rets * 0
    bench = pd.DataFrame({"spy": 0.005 + noise / 2, "equal_weight": 0.004 + noise / 3}, index=idx)
    rf = pd.Series(0.0, index=idx)
    best, table, rank = bt.selection_check(rets, bench, rf, costs, split="2022-01-01")
    assert best == "pred_mom_1m_top1_h1"  # the late winner is never seen when choosing
    assert rank == 2
    assert table.loc[("before", best), "months"] == 12
    summary = bt.grid_summary(bt.grid_table(rets, bench, rf, costs), by="top_n")
    assert summary.loc[1, "cells"] == 2


def test_prefer_alphavantage_drops_the_yahoo_copy_of_a_ticker():
    prices = pd.DataFrame(
        {
            "price_ticker": ["CPWR", "CPWR", "KO"],
            "source": ["yahoo", "alphavantage", "yahoo"],
        }
    )
    out = prefer_alphavantage(prices)
    assert out[["price_ticker", "source"]].values.tolist() == [
        ["CPWR", "alphavantage"],
        ["KO", "yahoo"],
    ]
