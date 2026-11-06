"""Offline tests for the run-all workflow's entry points (#19)."""

import pytest

from sp500_momentum import pipeline


def test_local_regime_touches_nothing():
    assert pipeline.get_data("local") == "used the files already on disk"


def test_unknown_regime_is_refused():
    with pytest.raises(ValueError, match="regime"):
        pipeline.get_data("cloud")


def test_rebuild_steps_follow_the_rerun_order():
    names = [n for n, _ in pipeline.rebuild_steps(tag="final-2026-11")]
    assert names[0] == "monthly table" and names[1] == "features"
    assert names[2].startswith("models") and names[3] == "all notebooks"
    assert names[4] == "Hugging Face snapshots (tag final-2026-11)"
    short = [n for n, _ in pipeline.rebuild_steps(retrain_models=False, publish=False)]
    assert short == ["monthly table", "features", "all notebooks"]


def test_run_steps_stops_at_the_first_failure():
    import typer

    ran = []

    def boom():
        raise RuntimeError("bad data")

    steps = [("a", lambda: ran.append("a")), ("b", boom), ("c", lambda: ran.append("c"))]
    with pytest.raises(typer.Exit):
        pipeline.run_steps(steps)
    assert ran == ["a"]  # c never ran
    assert [n for n, _ in pipeline.run_steps([("a", lambda: None)])] == ["a"]


def test_hub_and_download_regimes_call_the_real_steps(monkeypatch):
    from sp500_momentum import hub
    from sp500_momentum.modeling import predict

    called = []
    monkeypatch.setattr(hub, "pull_snapshot", lambda: called.append("hub"))
    monkeypatch.setattr(predict, "update_data", lambda: called.append("download"))
    pipeline.get_data("hub")
    pipeline.get_data("download")
    assert called == ["hub", "download"]
