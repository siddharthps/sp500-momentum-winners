"""Offline tests for the monthly run's checks and pick handling (#17)."""

import pandas as pd
import pytest

from sp500_momentum.modeling import predict as pr


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        ("2026-10", "2026-10-30"),  # an ordinary month: the last Friday
        ("2027-05", "2027-05-28"),  # 31 May 2027 is Memorial Day
        ("2024-03", "2024-03-28"),  # 29 March 2024 was Good Friday
        ("2026-11", "2026-11-30"),  # Thanksgiving (26 Nov) isn't the last weekday
        ("2026-01", "2026-01-30"),  # 31 Jan 2026 is a Saturday
    ],
)
def test_last_trading_day(month, expected):
    assert pr.last_trading_day(pd.Period(month, freq="M")) == pd.Timestamp(expected)


def _features(date="2026-10-30", priced=(True, True, True, True)):
    return pd.DataFrame(
        {
            "date": pd.Timestamp(date),
            "ticker": list("ABCD")[: len(priced)],
            "sector": "Tech",
            "has_price": list(priced),
        }
    )


def _prices(month="2026-10", close=500.0):
    return pd.DataFrame({"price_ticker": ["SPY"], "month": [month], "close_adj": [close]})


def test_month_end_checks_pass_on_a_complete_month():
    assert pr.month_end_problems(_features(), _prices(), pd.Timestamp("2026-11-02"), 0.95) == []


def test_month_end_checks_catch_each_problem():
    today = pd.Timestamp("2026-11-02")
    early = pr.month_end_problems(_features("2026-10-29"), _prices(), today, 0.95)
    assert any("last trading day" in p for p in early)  # the final day hadn't arrived
    unfinished = pr.month_end_problems(_features(), _prices(), pd.Timestamp("2026-10-31"), 0.95)
    assert any("isn't over" in p for p in unfinished)
    thin = pr.month_end_problems(
        _features(priced=(True, False, False, True)), _prices(), today, 0.95
    )
    assert any("have a price" in p for p in thin)
    no_spy = pr.month_end_problems(_features(), _prices(close=float("nan")), today, 0.95)
    assert any("SPY" in p for p in no_spy)


def test_top_picks_ranks_by_score_with_ties_alphabetical():
    rows = pd.DataFrame(
        {
            "date": pd.Timestamp("2026-10-30"),
            "ticker": ["B", "A", "C", "D"],
            "sector": ["x", "y", "z", "w"],
        }
    )
    picks = pr.top_picks(rows, pd.Series([0.5, 0.5, 0.9, None]), n=2, strategy="model")
    assert picks["ticker"].tolist() == ["C", "A"]  # D has no score; A beats B on the tie
    assert picks["rank"].tolist() == [1, 2]
    assert picks["decision_date"].unique().tolist() == ["2026-10-30"]


def test_append_record_replaces_a_rerun_month():
    def picks(month, tickers):
        return pd.DataFrame(
            {
                "decision_date": month,
                "strategy": "rule",
                "rank": range(1, len(tickers) + 1),
                "ticker": tickers,
                "sector": None,
                "score": 0.0,
                "made_at": "now",
            }
        )

    record = pr.append_record(None, picks("2026-10-30", ["A", "B"]))
    record = pr.append_record(record, picks("2026-11-30", ["C"]))
    record = pr.append_record(record, picks("2026-10-30", ["Z"]))  # a forced rerun of October
    assert record["ticker"].tolist() == ["Z", "C"]


def test_a_member_without_a_sector_stops_the_run():
    f = _features().assign(sector=["Tech", "Unknown", "Tech", "Tech"])
    problems = pr.month_end_problems(f, _prices(), pd.Timestamp("2026-11-02"), 0.95)
    assert any("no sector for B" in p for p in problems)


def test_column_problems_and_trained_columns():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    from sp500_momentum.modeling import prep

    X = pd.DataFrame({"ret_1m": [0.1, -0.2, 0.3, 0.0], "vol_3m": [0.2, 0.3, 0.1, 0.4]})
    pipe = Pipeline(
        [("prep", prep.preprocessor("impute_clip_scale")), ("model", LogisticRegression())]
    )
    pipe.fit(X, [1, 0, 1, 0])
    assert pr.trained_columns(pipe) == ["ret_1m", "vol_3m"]
    passthrough = Pipeline([("prep", "passthrough"), ("model", LogisticRegression())]).fit(
        X, [1, 0, 1, 0]
    )
    assert pr.trained_columns(passthrough) == ["ret_1m", "vol_3m"]


def test_headline_settings_reads_the_tuned_parameters():
    comparison = pd.DataFrame({"model": ["tree", "xgb"], "headline": [False, True]})
    cv = pd.DataFrame(
        {
            "model": ["xgb", "xgb", "tree"],
            "try": [0, 1, 0],
            "selection_score": [0.4, 0.6, 0.9],
            "params": ['{"max_depth": 2}', '{"max_depth": 3}', '{"max_depth": 9}'],
        }
    )
    assert pr.headline_settings(comparison, cv) == ("xgb", {"max_depth": 3})


# --- #39: the record, not a local picks file, decides whether a month is done ---------------


def _record(*decision_dates):
    return pd.DataFrame({"decision_date": list(decision_dates), "strategy": "model", "rank": 1})


def test_done_months_reads_the_running_record():
    rec = _record("2026-09-30", "2026-10-30")
    assert pr.done_months(rec) == {pd.Period("2026-09", "M"), pd.Period("2026-10", "M")}
    assert pr.done_months(None) == set()
    assert pr.done_months(_record()) == set()


def test_is_due_on_a_weekday_when_last_month_is_missing():
    rec = _record("2026-10-30")
    assert pr.is_due(rec, pd.Timestamp("2026-12-01"))  # Tue: November's picks are missing
    assert not pr.is_due(rec, pd.Timestamp("2026-11-11"))  # October's are done
    assert pr.is_due(None, pd.Timestamp("2026-11-11"))  # an empty record: everything is due


def test_is_due_waits_for_a_weekday():
    rec = _record("2026-10-30")
    assert not pr.is_due(rec, pd.Timestamp("2026-08-01"))  # a Saturday
    assert not pr.is_due(rec, pd.Timestamp("2026-08-02"))  # a Sunday


def test_is_due_catches_up_later_in_the_month():
    # Missed the first weekday (the job didn't run): still due until the picks exist.
    assert pr.is_due(_record("2026-10-30"), pd.Timestamp("2026-12-09"))
    # A January run looks for December's picks across the year boundary.
    assert pr.is_due(_record("2026-11-30"), pd.Timestamp("2027-01-04"))
    assert not pr.is_due(_record("2026-12-31"), pd.Timestamp("2027-01-04"))
