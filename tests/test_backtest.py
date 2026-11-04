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


def test_add_score_preds_picks_top_n_by_model_score():
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * 3 + ["2020-02-28"] * 2),
            "ticker": ["A", "B", "C", "A", "B"],
            "has_price": True,
            "entry_px": [1.0, 1.0, np.nan, 1.0, 1.0],
        }
    )
    scores = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * 3),  # no scores for February
            "ticker": ["A", "B", "C"],
            "xgb": [0.2, 0.6, 0.9],
        }
    )
    out = bt.add_score_preds(panel, scores, ["xgb"], top_ns=[1])
    # C scores highest but can't be traded (no next open), so B is the pick; February has none
    assert out["pred_xgb_top1"].tolist() == [0, 1, 0, 0, 0]
    assert "xgb" not in out.columns


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
    # by decision date: the Dec 2021 decision earns Jan 2022, so "before" holds Jan 2021-Jan 2022
    assert table.loc[("before", best), "months"] == 13
    assert table.loc[("after", best), "months"] == 11
    summary = bt.grid_summary(bt.grid_table(rets, bench, rf, costs), by="top_n")
    assert summary.loc[1, "cells"] == 2


def test_earned_months_follow_the_decision_window():
    idx = pd.period_range("2022-10", periods=6, freq="M")
    out = bt.earned_months(idx, start="2022-12-01", end="2023-02-01")
    assert [str(m) for m in out] == ["2023-01", "2023-02"]  # decisions Dec 2022 and Jan 2023


def test_buffered_picks_keep_holdings_within_twice_the_basket():
    ranks = {
        M: ["A", "B", "C", "D"],
        M + 1: ["C", "D", "B", "E"],  # B is 3rd: inside the top 4 buffer, so it stays
        M + 2: ["C", "E", "F", "G", "B"],  # B is 5th: out; A left the index
    }
    assert bt.buffered_picks(ranks, n=2, keep=2) == {
        M: ["A", "B"],
        M + 1: ["C", "D"],
        M + 2: ["C", "E"],
    }
    assert bt.buffered_picks(ranks, n=2) == {M: ["A", "B"], M + 1: ["B", "C"], M + 2: ["C", "E"]}
    with pytest.raises(ValueError):
        bt.buffered_picks(ranks, n=2, keep=1)


def test_inverse_vol_weights_fill_a_missing_volatility_with_the_basket_median():
    vol = pd.Series({(M, "A"): 0.1, (M, "B"): 0.2, (M, "C"): 0.3, (M + 1, "A"): np.nan}).dropna()
    w = bt.inverse_vol_weights({M: ["A", "B"], M + 1: ["A", "B"]}, vol)
    assert w[M] == pytest.approx({"A": 2 / 3, "B": 1 / 3})
    assert w[M + 1] == pytest.approx({"A": 0.5, "B": 0.5})  # no volatility at all: equal weight


def test_simulate_takes_target_weights_and_charges_only_the_difference():
    values = _values({"A": [10, 20, 20], "B": [10, 10, 10]})
    picks = {M: {"A": 0.5, "B": 0.5}, M + 1: {"A": 0.5, "B": 0.5}}
    sim = bt.simulate(picks, values, hold=1, cost=0.001)
    # month 1: +50%; A drifts to 2/3, so getting back to 50/50 trades 1/6 + 1/6
    assert sim["gross"].tolist() == pytest.approx([0.5, 0.0])
    assert sim["cost"].tolist() == pytest.approx([0.001, 0.001 / 3])


def test_dollars_and_fees_follow_the_value_path():
    idx = pd.period_range(M, periods=2, freq="M")
    out = bt.dollars(pd.Series([0.1, -0.5], index=idx), pd.Series([0.01, 0.02], index=idx), 100)
    assert out["end_value"] == pytest.approx(55)
    assert out["fees_dollars"] == pytest.approx(0.01 * 100 + 0.02 * 110)


def test_parse_strategy_round_trips_versions():
    assert bt.parse_strategy("xgb_reg_top10_inv_vol_buffer") == {
        "strategy": "xgb_reg",
        "top_n": 10,
        "version": "inv_vol_buffer",
    }
    assert bt.parse_strategy("spy")["version"] is pd.NA


def test_strategy_table_and_version_effect_on_a_tiny_market():
    idx = pd.period_range("2022-12", periods=4, freq="M")  # months earned
    rets = pd.DataFrame(
        {f"m_top10_{v}": [0.01 * (i + 1)] * 4 for i, v in enumerate(bt.VERSIONS)}, index=idx
    )
    costs = rets * 0 + 0.001
    bench = pd.DataFrame({"spy": [0.0] * 4, "equal_weight": [0.0] * 4}, index=idx)
    rf = pd.Series(0.0, index=idx)
    t = bt.strategy_table(rets, costs, bench, rf, start="2023-01-01")
    # decisions from Jan 2023 earn Feb 2023 on: Feb and Mar of Dec 2022-Mar 2023
    assert t.loc["m_top10_equal", "months"] == 2
    assert t.loc["m_top10_equal", "end_value"] == pytest.approx(10_000 * 1.01**2)
    assert t.loc["m_top10_equal", "traded_per_year"] == pytest.approx(12)
    assert t.loc["spy", "end_value"] == pytest.approx(10_000)
    eff = bt.version_effect(t, ["m"], top_n=10)
    assert eff.loc["inv_vol_buffer", "cagr"] == pytest.approx(1.04**12 - 1.01**12)


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
