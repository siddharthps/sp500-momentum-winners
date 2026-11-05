"""Offline tests for the Telegram notifications (#38). No message is ever really sent."""

from loguru import logger
import pandas as pd
import pytest
import requests

from sp500_momentum import notify as nt

TOKEN = "123456:SECRET-TOKEN"
ON = nt.Settings(token=TOKEN, channel="@channel", chat="42")


@pytest.fixture
def logs():
    lines: list[str] = []
    sink = logger.add(lambda m: lines.append(str(m)), level="DEBUG")
    yield lines
    logger.remove(sink)


class _Response:
    def __init__(self, ok=True, status=200):
        self.ok, self.status_code = ok, status


def test_send_posts_html_to_the_chat(monkeypatch):
    seen = {}

    def fake_post(url, json, timeout):
        seen.update(url=url, json=json)
        return _Response()

    monkeypatch.setattr(requests, "post", fake_post)
    assert nt.send("<b>hi</b>", "42", ON) is True
    assert seen["url"].endswith(f"bot{TOKEN}/sendMessage")
    assert seen["json"] == {
        "chat_id": "42",
        "text": "<b>hi</b>",
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def test_send_never_raises_and_never_logs_the_token(monkeypatch, logs):
    def boom(url, json, timeout):
        raise requests.ConnectionError(f"failed for {url}")  # the URL holds the token

    monkeypatch.setattr(requests, "post", boom)
    assert nt.send("x", "42", ON) is False
    monkeypatch.setattr(requests, "post", lambda url, json, timeout: _Response(False, 401))
    assert nt.send("x", "42", ON) is False
    text = "\n".join(logs)
    assert "ConnectionError" in text and "HTTP 401" in text
    assert TOKEN not in text


def test_unconfigured_or_dry_run_only_logs(monkeypatch, logs):
    monkeypatch.setattr(requests, "post", lambda *a, **k: pytest.fail("must not send"))
    assert nt.send("hello", "42", nt.Settings(None, None, None)) is False
    assert nt.send("hello", "42", ON, dry_run=True) is False
    assert sum("hello" in line for line in logs) == 2


def test_long_messages_are_cut_to_telegrams_limit(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        requests, "post", lambda url, json, timeout: sent.update(json) or _Response()
    )
    nt.send("x" * 5000, "42", ON)
    assert len(sent["text"]) <= nt.MAX_LENGTH


def test_tradeable_means_made_before_the_next_open():
    assert nt.tradeable("2026-12-01 07:00", "2026-11-30")  # the scheduled run
    assert not nt.tradeable("2026-11-05 10:20", "2026-10-30")  # the first, late file
    assert not nt.tradeable("2026-12-01 09:00", "2026-11-30")  # after the 08:30 open


def _record(made_at="2026-12-01 07:00"):
    return pd.DataFrame(
        {
            "decision_date": "2026-11-30",
            "strategy": ["model", "model", "rule"],
            "ticker": ["A", "B", "C"],
            "price_ticker": ["A", "B", "C"],
            "made_at": made_at,
        }
    )


def _prices():
    rows = []
    for t, entry, close in [("A", 10, 12), ("B", 10, 9), ("C", 20, 21), ("SPY", 100, 102)]:
        rows += [
            {"price_ticker": t, "month": "2026-11", "entry_px": entry, "close_adj": entry},
            {"price_ticker": t, "month": "2026-12", "entry_px": None, "close_adj": close},
        ]
    return pd.DataFrame(rows)


def test_live_result_scores_last_months_picks_once_the_month_is_over():
    r = nt.live_result(_record(), _prices(), pd.Period("2027-01", freq="M")).set_index("strategy")
    assert r.loc["model", "ret"] == pytest.approx((0.2 - 0.1) / 2)
    assert r.loc["model", "spy"] == pytest.approx(0.02)
    assert r.loc["model", "beat"] == 1 and r.loc["rule", "beat"] == 1
    # December not over yet, or picks made too late: nothing to report
    assert nt.live_result(_record(), _prices(), pd.Period("2026-12", freq="M")) is None
    late = _record(made_at="2026-12-05 10:00")
    assert nt.live_result(late, _prices(), pd.Period("2027-01", freq="M")) is None


def test_picks_message_has_both_lists_the_result_and_the_footer():
    picks = pd.DataFrame({"strategy": ["model", "rule"], "ticker": ["AT&T", "B"], "rank": [1, 1]})
    result = pd.DataFrame(
        [
            {
                "strategy": "model",
                "decision": "2026-11",
                "ret": 0.05,
                "spy": 0.02,
                "beat": 6,
                "priced": 10,
            }
        ]
    )
    msg = nt.picks_message(picks, pd.Timestamp("2026-11-30"), result, (["NEW"], ["OLD"]), 0.99)
    assert "AT&amp;T" in msg  # escaped for Telegram's HTML
    assert "Buy at the next open (Tue 01 Dec 2026)" in msg
    assert "+5.0% vs SPY +2.0%; 6 of 10 beat SPY" in msg
    assert "+1 (NEW), −1 (OLD)" in msg
    assert msg.endswith(nt.FOOTER)


def test_alert_and_av_messages():
    assert "no sector for KVUE" in nt.alert_message("Monthly run", ["no sector for KVUE"])
    msg = nt.av_message({"ok": 20, "reused_ticker": 3}, 146, 0, False)
    assert msg == "Alpha Vantage pull: 23 tried (ok 20, reused_ticker 3). 146 left."
    assert "queue is empty" in nt.av_message({}, 0, 0, False)


def test_chats_from_updates_lists_private_chats_and_channels():
    updates = {
        "result": [
            {"message": {"chat": {"id": 42, "type": "private", "first_name": "Me"}}},
            {"channel_post": {"chat": {"id": -100123, "type": "channel", "title": "Picks"}}},
            {"message": {"chat": {"id": 42, "type": "private", "first_name": "Me"}}},
        ]
    }
    assert nt.chats_from_updates(updates) == [
        {"id": 42, "type": "private", "name": "Me"},
        {"id": -100123, "type": "channel", "name": "Picks"},
    ]


def test_index_changes_in_the_window():
    changes = pd.DataFrame(
        {
            "date": ["2026-10-15", "2026-11-10", "2026-12-02"],
            "added_ticker": ["X", "Y", "Z"],
            "removed_ticker": ["P", None, "R"],
        }
    )
    assert nt.index_changes(changes, "2026-10-30", "2026-11-30") == (["Y"], [])
