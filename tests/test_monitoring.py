"""Offline tests for drift and the live record (#40)."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum import monitoring as mon


def test_psi_is_zero_for_the_same_distribution_and_grows_with_a_shift():
    rng = np.random.default_rng(0)
    ref = pd.Series(rng.normal(0, 1, 5000))
    assert mon.psi(ref, ref) == pytest.approx(0.0, abs=1e-9)
    small = mon.psi(ref, pd.Series(rng.normal(0.1, 1, 2000)))
    big = mon.psi(ref, pd.Series(rng.normal(1.5, 1, 2000)))
    assert small < 0.1  # a small shift reads as stable
    assert big > 0.25  # a large one as a major shift
    assert np.isnan(mon.psi(pd.Series([1.0] * 100), ref))  # constant reference: no bins
    assert [mon.drift_level(v) for v in (0.05, 0.2, 0.4, np.nan)] == [
        "stable",
        "moderate",
        "major",
        "n/a",
    ]


def test_drift_table_compares_each_month_with_the_reference_years():
    dates = pd.to_datetime(["2015-01-30"] * 50 + ["2023-01-31"] * 50 + ["2023-02-28"] * 50)
    rng = np.random.default_rng(1)
    x = np.concatenate([rng.normal(0, 1, 50), rng.normal(0, 1, 50), rng.normal(3, 1, 50)])
    f = pd.DataFrame({"date": dates, "x": x})
    t = mon.drift_table(f, ["x"], ref=("2010-01-01", "2022-12-31"), since="2023-01-01")
    assert t["month"].tolist() == ["2023-01", "2023-02"]
    assert t["psi"].iloc[1] > 0.25 > t["psi"].iloc[0]


def test_live_record_with_a_base_rate():
    record = pd.DataFrame(
        {
            "decision_date": "2026-11-30",
            "strategy": ["model", "model"],
            "ticker": ["A", "B"],
            "price_ticker": ["A", "B"],
            "made_at": "2026-12-01 07:00",
        }
    )
    rows = []
    for t, entry, close in [("A", 10, 12), ("B", 10, 9), ("C", 10, 10.1), ("SPY", 100, 102)]:
        rows += [
            {"price_ticker": t, "month": "2026-11", "entry_px": entry, "close_adj": entry},
            {"price_ticker": t, "month": "2026-12", "entry_px": None, "close_adj": close},
        ]
    prices = pd.DataFrame(rows)
    members = pd.DataFrame({"date": pd.Timestamp("2026-11-30"), "price_ticker": ["A", "B", "C"]})
    table = mon.live_record(
        record, prices, pd.Period("2027-01", freq="M"), lambda m, d: True, members
    )
    r = table.iloc[0]
    assert (r["decision"], r["beat"], r["priced"]) == ("2026-11", 1, 2)
    assert r["base_rate"] == pytest.approx(1 / 3)  # only A of A, B, C beat SPY's +2%
    empty = mon.live_record(None, prices, pd.Period("2027-01", freq="M"), lambda m, d: True)
    assert empty.empty and "base_rate" in empty.columns
