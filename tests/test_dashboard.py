"""Offline tests for the dashboard (#40): its logic, its agreement with the package, and a smoke
run of the whole Streamlit app against small local files (no network)."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
sys.path.insert(0, str(DASHBOARD))
import logic

from sp500_momentum import monitoring, plots


def _returns():
    months = [str(m) for m in pd.period_range("2022-11", periods=5, freq="M")]
    return pd.DataFrame(
        {
            "month_earned": months,
            "model": [0.01, -0.02, 0.03, 0.0, 0.01],
            "rule_6m": [0.02, 0.02, -0.01, 0.01, 0.0],
            "chosen_rule": [0.0, 0.05, -0.05, 0.02, 0.01],
            "spy": [0.01, 0.01, 0.01, 0.01, 0.01],
            "equal_weight": [0.0] * 5,
        }
    )


def test_palette_and_drift_reading_match_the_package():
    assert logic.SLOTS == plots.SLOTS
    for v in (0.05, 0.2, 0.4, np.nan):
        assert logic.drift_level(v) == monitoring.drift_level(v)


def test_window_and_value_paths_start_at_ten_thousand():
    w = logic.window(_returns(), "2023-02")
    assert w.index.tolist() == ["2023-02", "2023-03"]
    paths = logic.value_paths(w[["spy"]])
    assert paths.index.tolist() == ["2023-01", "2023-02", "2023-03"]
    assert paths["spy"].tolist() == pytest.approx([10_000, 10_100, 10_201])


def test_summary_counts_a_first_month_loss_as_a_fall():
    s = logic.summary(pd.DataFrame({"x": [-0.1, 0.2]}))
    assert s.loc["x", "worst fall"] == pytest.approx(-0.1)
    assert s.loc["x", "$10,000 became"] == pytest.approx(10_800)


def test_live_summary_and_latest_drift():
    live = pd.DataFrame(
        {
            "decision": ["2026-11", "2026-11", "2026-12", "2026-12"],
            "strategy": ["model", "rule", "model", "rule"],
            "ret": [0.03, 0.01, -0.01, 0.02],
            "spy": [0.01, 0.01, 0.0, 0.0],
            "beat": [6, 4, 3, 7],
            "priced": [10, 10, 10, 10],
            "base_rate": [0.5, 0.5, 0.4, 0.4],
        }
    )
    s = logic.live_summary(live)
    assert s.loc["Headline model", "months"] == 2
    assert s.loc["Headline model", "picks beating SPY"] == pytest.approx(0.45)
    assert s.loc["Headline model", "average month vs SPY"] == pytest.approx(0.005)
    drift = pd.DataFrame(
        {
            "month": ["2026-09", "2026-10", "2026-10"],
            "feature": ["a", "a", "b"],
            "psi": [0.5, 0.05, 0.3],
        }
    )
    month, t = logic.latest_drift(drift, {"a": "Feature A"})
    assert month == "2026-10"
    assert t["feature"].tolist() == ["b", "Feature A"] and t["reading"].tolist() == [
        "major",
        "stable",
    ]


@pytest.fixture
def data_dir(tmp_path):
    pd.DataFrame(
        {
            "decision_date": "2026-10-30",
            "strategy": ["model", "rule"],
            "rank": [1, 1],
            "ticker": ["A", "B"],
            "price_ticker": ["A", "B"],
            "sector": ["Tech", "Energy"],
            "score": [0.01, 1.5],
            "made_at": "2026-11-05 10:00",
        }
    ).to_csv(tmp_path / "live_picks.csv", index=False)
    _returns().to_parquet(tmp_path / "strategy_returns.parquet")
    monitoring.live_record(None, pd.DataFrame(), pd.Period("2026-11", freq="M"), None).to_parquet(
        tmp_path / "live_record.parquet"
    )
    pd.DataFrame({"month": ["2026-10"], "feature": ["vol_3m"], "psi": [0.12]}).to_parquet(
        tmp_path / "monitoring.parquet"
    )
    meta = {
        "status": "preview",
        "updated": "2026-11-05 12:00",
        "headline": "XGBoost, by how much",
        "validation_from": "2022-11",
        "test_from": "2023-02",
        "drift_features": {"vol_3m": "Volatility (3 months)"},
        "latest_decision": "2026-10-30",
    }
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    return tmp_path


def test_the_app_runs_end_to_end_offline(data_dir, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DASHBOARD_DATA_DIR", str(data_dir))
    monkeypatch.chdir(DASHBOARD)  # the app imports its sibling module `logic`
    at = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 5
    assert any("not investment advice" in w.value for w in at.warning)
    at.radio[0].set_value("2020–2022 (where the model was chosen)").run()
    assert not at.exception, at.exception
