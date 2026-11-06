"""Offline tests for the run-all workflow's entry points (#19)."""

import pytest

from sp500_momentum import pipeline


def test_local_regime_touches_nothing():
    assert pipeline.get_data("local") == "used the files already on disk"


def test_unknown_regime_is_refused():
    with pytest.raises(ValueError, match="regime"):
        pipeline.get_data("cloud")


def test_hub_and_download_regimes_call_the_real_steps(monkeypatch):
    from sp500_momentum import hub
    from sp500_momentum.modeling import predict

    called = []
    monkeypatch.setattr(hub, "pull_snapshot", lambda: called.append("hub"))
    monkeypatch.setattr(predict, "update_data", lambda: called.append("download"))
    pipeline.get_data("hub")
    pipeline.get_data("download")
    assert called == ["hub", "download"]
