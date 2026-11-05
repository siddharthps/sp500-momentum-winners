"""Offline tests for the diagnosis of picks (#16)."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum import diagnostics as dg

M = pd.Period("2020-01", freq="M")


def _rows():
    """Two months, four members each; the strategy picks A and B in both."""
    months = [M] * 4 + [M + 1] * 4
    return pd.DataFrame(
        {
            "month": months,
            "date": [m.to_timestamp(how="end").normalize() for m in months],
            "period": "p",
            "ticker": list("ABCD") * 2,
            "price_ticker": list("ABCD") * 2,
            "sector": ["Tech", "Tech", "Energy", "Energy"] * 2,
            "beat": [1, 1, 0, 0, 1, 0, 1, 0],
            "fwd_excess_1m": [0.10, 0.02, -0.01, -0.03, 0.04, -0.06, 0.01, -0.02],
            "pick": [1, 1, 0, 0, 1, 1, 0, 0],
        }
    )


def test_slice_table_averages_within_months_then_over_months():
    t = dg.slice_table(_rows(), "pick", "sector").loc[("p", "Tech")]
    assert t["months"] == 2 and t["picks"] == 4
    assert t["hit_rate"] == pytest.approx((1.0 + 0.5) / 2)
    assert t["hit_se"] == pytest.approx(np.std([1.0, 0.5], ddof=1) / np.sqrt(2))
    assert t["excess"] == pytest.approx((0.06 + -0.01) / 2)
    # base rate: all Tech members in those months (here the same two as the picks)
    assert t["base_rate"] == pytest.approx(0.75)


def test_mark_picks_and_sector_mix():
    rows = _rows().drop(columns="pick")
    rows = dg.mark_picks(rows, {M: ["A", "C"], M + 1: ["A"]}, "s")
    assert rows["s"].tolist() == [1, 0, 1, 0, 1, 0, 0, 0]
    mix = dg.sector_mix(rows, ["s"])
    assert mix.loc[("p", "Tech"), "members"] == pytest.approx(0.5)
    assert mix.loc[("p", "Tech"), "s"] == pytest.approx(2 / 3)


def test_left_index_only_counts_exits_inside_the_panel():
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-01-31", "2021-06-30"]),
            "ticker": ["GONE", "GONE", "STAYS", "STAYS"],
        }
    )
    rows = pd.DataFrame({"ticker": ["GONE", "STAYS"], "month": [M, M]})
    assert dg.left_index(panel, rows, within=12).tolist() == [True, False]
    # too close to the panel's end to know
    assert not dg.left_index(panel, rows.assign(month=M + 10), within=12).any()


def test_regimes_label_each_month():
    rows = _rows().assign(vix=[30] * 4 + [12] * 4, spy_fwd_ret_1m=[0.02] * 4 + [-0.01] * 4)
    on = pd.Series({M: False, M + 1: True})
    r = dg.regimes(rows, on, vix_cut=20)
    assert r.groupby("month")[["trend", "vix_level", "market"]].first().values.tolist() == [
        ["SPY below its trend", "VIX high", "SPY up next month"],
        ["SPY above its trend", "VIX low", "SPY down next month"],
    ]
