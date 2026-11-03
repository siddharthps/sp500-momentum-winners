"""Point-in-time S&P 500 membership, rebuilt from today's list and Wikipedia's changes.

Start from today's members and walk the changes backwards: undoing a change means taking the
added ticker out and putting the removed ticker back. Members on date t are today's list with
every change dated after t undone. A change takes effect on its date (before the open), so a
stock added on t counts as a member on t.
"""

import re

import pandas as pd


def clean_ticker(t):
    """Drop stray characters from scraped tickers ("ALLE |" -> "ALLE"); keep NaN as NaN."""
    if pd.isna(t):
        return t
    return re.sub(r"[^A-Z0-9-]", "", str(t).upper())


def repair_changes(
    changes: pd.DataFrame, renames: list[tuple], missing_adds: dict[str, str]
) -> pd.DataFrame:
    """Fix the known gaps in Wikipedia's changes table before the backward walk.

    - Renames: inside each (old, new, from, to) window, `old` becomes `new`. A row that then
      adds and removes the same ticker (a pure rename row) does nothing and is dropped.
    - Missing adds: a synthetic "added" row for current members that joined without one.
    """
    ch = changes.copy()
    for col in ["added_ticker", "removed_ticker"]:
        ch[col] = ch[col].map(clean_ticker)
    for old, new, start, end in renames:
        window = ch["date"].between(pd.Timestamp(start), pd.Timestamp(end))
        for col in ["added_ticker", "removed_ticker"]:
            ch.loc[window & (ch[col] == old), col] = new
    ch = ch[ch["added_ticker"].isna() | (ch["added_ticker"] != ch["removed_ticker"])]
    extra = pd.DataFrame(
        {
            "date": pd.to_datetime(list(missing_adds.values())),
            "added_ticker": list(missing_adds.keys()),
            "removed_ticker": pd.NA,
            "reason": "synthetic add (missing from Wikipedia)",
        }
    )
    return pd.concat([ch, extra], ignore_index=True)


def month_ends(trading_days: pd.Series, start: str, asof=None) -> pd.Series:
    """The last trading day of each month from `start` on (the decision dates).

    The month containing `asof` (default: today) is left out: it isn't over yet, so its
    "last trading day so far" isn't a month-end.
    """
    days = pd.Series(pd.to_datetime(trading_days)).sort_values()
    me = days.groupby(days.dt.to_period("M")).max()
    current = pd.Timestamp(asof if asof is not None else pd.Timestamp.now()).to_period("M")
    me = me[me.index < current]
    return me[me >= pd.Timestamp(start)].reset_index(drop=True)


def point_in_time(current: pd.DataFrame, changes: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    """One row per (date, ticker) for every ticker in the index on each date."""
    members = set(current["ticker"])
    rows = changes.sort_values("date", ascending=False).to_dict("records")
    i, out = 0, []
    for d in sorted(pd.to_datetime(dates), reverse=True):
        while i < len(rows) and rows[i]["date"] > d:
            r = rows[i]
            if pd.notna(r["added_ticker"]):
                members.discard(r["added_ticker"])
            if pd.notna(r["removed_ticker"]):
                members.add(r["removed_ticker"])
            i += 1
        out.extend((d, t) for t in members)
    df = pd.DataFrame(out, columns=["date", "ticker"])
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)
