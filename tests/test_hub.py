"""Offline tests for the Hugging Face snapshots (#18). Nothing is uploaded or downloaded."""

import pandas as pd
import pytest
import typer

from sp500_momentum import hub


def test_repo_ids_from_the_account(monkeypatch):
    monkeypatch.setenv("HF_USER", "someone")
    assert hub.repo_ids() == ("someone/sp500-momentum-data", "someone/sp500-momentum-winners")
    monkeypatch.delenv("HF_USER")
    with pytest.raises(typer.BadParameter):
        hub.repo_ids()


def test_without_prices_keeps_returns_and_drops_vendor_figures():
    df = pd.DataFrame(
        {
            "ticker": ["A"],
            "close_adj": [10.0],
            "entry_px": [10.1],
            "dollar_vol": [1e9],
            "source": ["yahoo"],
            "ret_6m": [0.2],
        }
    )
    assert hub.without_prices(df).columns.tolist() == ["ticker", "ret_6m"]


def test_files_with_secrets_names_the_file_only(tmp_path):
    (tmp_path / "clean.csv").write_text("a,b\n1,2\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "leak.log").write_text("key=SUPERSECRET123 here")
    assert hub.files_with_secrets([tmp_path], ["SUPERSECRET123"]) == ["leak.log"]
    assert hub.files_with_secrets([tmp_path], ["short"]) == []  # too short to be a real key


def test_stage_public_writes_derived_tables_and_a_card(tmp_path, monkeypatch):
    src = tmp_path / "src"
    (src / "reports").mkdir(parents=True)
    table = pd.DataFrame({"ticker": ["A"], "close_adj": [1.0], "ret_1m": [0.1]})
    for name in ["features.parquet", "monthly_panel.parquet", "model_scores.parquet"]:
        table.to_parquet(src / name)
    (src / "reports" / "grid.csv").write_text("x\n1\n")
    monkeypatch.setattr(hub, "FEATURES_TABLE", src / "features.parquet")
    monkeypatch.setattr(hub, "MONTHLY_PANEL", src / "monthly_panel.parquet")
    monkeypatch.setattr(hub, "MODEL_SCORES", src / "model_scores.parquet")
    monkeypatch.setattr(hub, "LIVE_PICKS", src / "missing.csv")
    monkeypatch.setattr(hub, "REPORTS_DIR", src / "reports")

    out = tmp_path / "out"
    files = hub.stage_public(out, status="preview")
    assert set(files) == {
        "features.parquet",
        "monthly_panel.parquet",
        "model_scores.parquet",
        "reports/grid.csv",
        "README.md",
    }
    assert "close_adj" not in pd.read_parquet(out / "features.parquet").columns
    card = (out / "README.md").read_text(encoding="utf-8")
    assert "**Status:** preview" in card and "Raw prices are not included" in card
