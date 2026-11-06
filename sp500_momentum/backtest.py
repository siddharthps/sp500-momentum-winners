"""Backtests of monthly stock-picking rules: the baseline grid now, the model rules later.

The flow follows the class's: a rule is a 0/1 `pred*` column on the monthly table (1 = buy this
member at the next open), and a simulation turns any `pred*` column into monthly returns.

Simulation (staggered portfolios, the standard way to test an X-month hold):
- The money is split into X slots. Each month-end one slot sells what it holds and buys that
  month's picks, equal weight, so 1/X of the money enters each month and every position is held
  X months. Between refreshes a slot is buy-and-hold (weights drift with prices).
- The portfolio's monthly return is the average over slots (the slots are rebalanced to equal
  size each month; that rebalancing is not charged). Before X slots exist, it averages the slots
  that do, so every grid cell is fully invested from the first month.
- Trades happen at the next trading day's open (`entry_px`). A cost of `cost` per side is charged
  on the value bought and sold when a slot is refreshed. A stock kept from the old picks into the
  new ones is only traded by the weight difference.
- A stock that leaves the index stays held until its slot refreshes. A delisted stock is valued at
  its last price and then held as cash, the same rule as the targets in the monthly table.

Returns are labelled by the month they're earned in: a decision at the end of January buys at the
first open of February and is valued at the first open of March, so it's February's return.
Periods (the test years, 2020-22) are set by **decision date** for every strategy, as for the
models: `earned_months` turns a decision window into the months its returns are earned in.

Strategy versions (#14, for 1-month holds):
- **Weighting:** equal (the main version), or inverse volatility: each pick's target weight is
  proportional to 1 / its 3-month volatility at the decision month-end.
- **Hold buffer:** buy the top N, but keep a holding while it still ranks within the top
  BUFFER_MULTIPLE x N; a sold name is replaced by the best-ranked name not already held.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from sp500_momentum.config import (
    BUFFER_MULTIPLE,
    COST_PER_SIDE,
    RULE_LOOKBACKS,
    RULE_TOP_NS,
    START_DOLLARS,
    TREND_MONTHS,
)

TREND = "_trend"  # suffix of a strategy's trend-filtered version

Picks = dict[pd.Period, list[str] | dict[str, float]]  # names (equal weight) or target weights

TINY = 1e-12  # a standard deviation below this is zero up to rounding (a constant series)


def rule_name(signal: str, top_n: int) -> str:
    """`pred_mom_12_1m_top10`: the top 10 members by `ret_12_1m`."""
    return f"pred_mom_{signal.removeprefix('ret_')}_top{top_n}"


def eligible(panel: pd.DataFrame) -> pd.Series:
    """Members that can be bought at the next open: priced, with a trade price."""
    return panel["has_price"].astype(bool) & panel["entry_px"].notna()


def add_rule_preds(
    panel: pd.DataFrame,
    signals: Iterable[str] = RULE_LOOKBACKS,
    top_ns: Iterable[int] = RULE_TOP_NS,
) -> pd.DataFrame:
    """Add a 0/1 `pred_mom_*` column per (look-back, N): the N eligible members with the highest
    past return at each month-end. Ties go to the alphabetically first ticker."""
    out = panel.copy()
    ok = eligible(out)
    for s in signals:
        valid = ok & out[s].notna()
        sub = out.loc[valid, ["date", "ticker", s]].sort_values(["date", "ticker"])
        rank = sub.groupby("date")[s].rank(method="first", ascending=False)
        for n in top_ns:
            out[rule_name(s, n)] = (rank <= n).reindex(out.index, fill_value=False).astype("int8")
    return out


def add_score_preds(
    panel: pd.DataFrame,
    scores: pd.DataFrame,
    names: Iterable[str],
    top_ns: Iterable[int] = RULE_TOP_NS,
) -> pd.DataFrame:
    """Add a 0/1 `pred_<name>_top<N>` column per model score: the N eligible members with the
    highest out-of-sample score at each month-end (ties to the alphabetically first ticker).

    `scores` has date, ticker and one column per name (from the training step); months or
    members without a score get no picks."""
    out = merge_scores(panel, scores, names)
    ok = eligible(out)
    for name in names:
        valid = ok & out[name].notna()
        sub = out.loc[valid, ["date", "ticker", name]].sort_values(["date", "ticker"])
        rank = sub.groupby("date")[name].rank(method="first", ascending=False)
        for n in top_ns:
            col = f"pred_{name}_top{n}"
            out[col] = (rank <= n).reindex(out.index, fill_value=False).astype("int8")
    return out.drop(columns=list(names))


def merge_scores(panel: pd.DataFrame, scores: pd.DataFrame, names: Iterable[str]) -> pd.DataFrame:
    """The panel with one column per model score (blank where a member-month has none)."""
    names = list(names)
    return panel.merge(scores[["date", "ticker", *names]], on=["date", "ticker"], how="left")


def ranked(panel: pd.DataFrame, signal: str) -> dict[pd.Period, list[str]]:
    """{decision month: eligible price tickers, best `signal` first} (ties: alphabetical ticker)."""
    ok = eligible(panel) & panel[signal].notna()
    sub = panel.loc[ok, ["date", "ticker", "price_ticker", signal]]
    sub = sub.sort_values(["date", signal, "ticker"], ascending=[True, False, True])
    months = pd.PeriodIndex(sub["date"], freq="M")
    return {m: g.tolist() for m, g in sub.groupby(months, sort=True)["price_ticker"]}


def buffered_picks(
    ranks: dict[pd.Period, list[str]], n: int, keep: int | None = None
) -> dict[pd.Period, list[str]]:
    """Top-n picks with a hold buffer: a name held from last month stays while it ranks within
    the top `keep` (default BUFFER_MULTIPLE x n); the free places go to the best-ranked names not
    held. `keep == n` gives the plain top n. A name with no rank this month (it left the index or
    has no score) is sold."""
    keep = BUFFER_MULTIPLE * n if keep is None else keep
    if keep < n:
        raise ValueError("the buffer must be at least the basket size")
    held: list[str] = []
    out = {}
    for m in sorted(ranks):
        order = ranks[m]
        within = set(order[:keep])
        kept = [t for t in held if t in within]
        fresh = [t for t in order if t not in kept][: n - len(kept)]
        held = sorted(kept + fresh)
        out[m] = held
    return out


def inverse_vol_weights(picks: dict[pd.Period, list[str]], vol: pd.Series) -> Picks:
    """Target weights proportional to 1 / volatility at each decision month. `vol` is indexed by
    (decision month, price ticker). A pick with no volatility (too short a history) gets the
    basket's median; a basket with none at all is equal weight."""
    out = {}
    for m, names in picks.items():
        v = pd.Series([vol.get((m, t), np.nan) for t in names], index=names, dtype=float)
        v = v.where(v > 0)
        v = v.fillna(v.median()) if v.notna().any() else v.fillna(1.0)
        w = 1 / v
        out[m] = (w / w.sum()).to_dict()
    return out


def volatility_lookup(features: pd.DataFrame, column: str) -> pd.Series:
    """`column` from the feature table, indexed by (decision month, price ticker)."""
    idx = pd.MultiIndex.from_arrays(
        [pd.PeriodIndex(features["date"], freq="M"), features["price_ticker"]]
    )
    return pd.Series(features[column].to_numpy(), index=idx).dropna()


def earned_months(index: pd.PeriodIndex, start: str | None = None, end: str | None = None):
    """The months in `index` whose returns come from decisions made in [start, end): a decision
    at a month-end earns its return the next month."""
    months = index
    if start:
        months = months[months >= pd.Period(start, freq="M") + 1]
    if end:
        months = months[months < pd.Period(end, freq="M") + 1]
    return months


def value_matrix(prices: pd.DataFrame, end: pd.Period | None = None) -> pd.DataFrame:
    """Month x price_ticker table of the price a position is valued at after each month-end.

    That's `entry_px` (the next open). In a series' last month there is no next open, so the
    month-end close is used, and after that the value stays flat (cash). Rows stop at `end`
    (default: the last month SPY has an entry price, the end of the market's data).
    """
    p = prices.copy()
    p["month"] = pd.PeriodIndex(p["month"], freq="M")
    p["value"] = p["entry_px"].fillna(p["close_adj"])
    v = p.pivot_table(index="month", columns="price_ticker", values="value", aggfunc="last")
    v = v.reindex(pd.period_range(v.index.min(), v.index.max(), freq="M"))
    if end is None:
        spy = p[(p["price_ticker"] == "SPY") & p["entry_px"].notna()]
        end = spy["month"].max()
    return v.ffill().loc[:end]


def picks_by_month(panel: pd.DataFrame, pred: str) -> dict[pd.Period, list[str]]:
    """{decision month: price tickers to buy} for one `pred*` column."""
    chosen = panel[panel[pred] == 1]
    months = pd.PeriodIndex(chosen["date"], freq="M")
    return {m: sorted(g) for m, g in chosen.groupby(months)["price_ticker"]}


def simulate(
    picks: Picks,
    values: pd.DataFrame,
    hold: int,
    cost: float = COST_PER_SIDE,
    invested: pd.Series | None = None,
    cash_return: pd.Series | None = None,
) -> pd.DataFrame:
    """Staggered-portfolio simulation of one rule (see the module docstring).

    `picks` maps a decision month to the names to buy (equal weight) or to target weights that
    sum to 1. Runs every month from the first decision to the end of `values`; a month without
    picks keeps the due slot's holdings. Returns one row per month earned: `ret` (net of costs),
    `gross` and `cost` (the fraction of the portfolio paid in costs that month), indexed by the
    month the return is earned in.

    Trend filter: `invested` (bool by decision month; missing = invested) switches the strategy
    off. At an "off" decision every slot is sold at the next open (costs charged) and the money
    earns `cash_return` (by month earned) until an "on" decision, when every slot buys that
    month's picks.
    """
    if invested is not None and cash_return is None:
        raise ValueError("a trend filter needs the return earned on cash")
    slots: list[dict[str, float] | None] = [None] * hold
    months = values.index[(values.index >= min(picks)) & (values.index < values.index.max())]
    rows = {}
    in_cash = False
    for i, m in enumerate(months):
        s = i % hold
        new = picks.get(m, [])
        paid = [0.0] * hold
        on = True if invested is None else bool(invested.get(m, True))
        if not on or (in_cash and not new):
            # the portfolio is the slots held so far: selling out trades all of it
            fee = cost if any(slots) else 0.0
            slots = [None] * hold
            in_cash = True
            r = float(cash_return.get(m + 1, np.nan))
            if np.isnan(r):
                raise ValueError(f"No cash return for {m + 1}")
            rows[m + 1] = {"ret": (1 - fee) * (1 + r) - 1, "gross": r, "cost": fee}
            continue
        if in_cash and new:  # back in: every slot buys this month's picks
            target = dict(new) if isinstance(new, dict) else {t: 1 / len(new) for t in new}
            slots = [dict(target) for _ in range(hold)]
            paid = [cost] * hold
            in_cash = False
            new = []
        if new:
            target = dict(new) if isinstance(new, dict) else {t: 1 / len(new) for t in new}
            old = slots[s] or {}
            # sorted: a set's order changes between runs, and so would the last digit of the sum
            names = sorted(set(target) | set(old))
            turnover = sum(abs(target.get(t, 0) - old.get(t, 0)) for t in names)
            paid[s] = cost * turnover
            slots[s] = target
        gross, net, fees = [], [], []
        for k, w in enumerate(slots):
            if not w:
                continue
            tickers = list(w)
            growth = (values.loc[m + 1, tickers] / values.loc[m, tickers]).to_numpy()
            if np.isnan(growth).any():
                missing = [t for t, g in zip(tickers, growth) if np.isnan(g)]
                raise ValueError(f"No value for {missing} in {m} or {m + 1}")
            weights = np.array([w[t] for t in tickers])
            r = float(weights @ growth) - 1
            slots[k] = dict(zip(tickers, weights * growth / (1 + r)))
            gross.append(r)
            net.append((1 - paid[k]) * (1 + r) - 1)
            fees.append(paid[k])
        if net:
            rows[m + 1] = {"ret": np.mean(net), "gross": np.mean(gross), "cost": np.mean(fees)}
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "month"
    return out


def trend_signal(
    prices: pd.DataFrame, ticker: str = "SPY", months: int = TREND_MONTHS
) -> pd.Series:
    """True by decision month when `ticker`'s month-end adjusted close is above the average of
    its last `months` month-end closes (this one included): known at the decision's close.
    Months without a full average are left out (callers treat a missing month as invested)."""
    p = prices[prices["price_ticker"] == ticker].copy()
    p["month"] = pd.PeriodIndex(p["month"], freq="M")
    close = p.set_index("month")["close_adj"].sort_index()
    average = close.rolling(months).mean()
    return (close > average)[average.notna()].rename("invested")


def cash_returns(rf: pd.Series, index: pd.PeriodIndex) -> pd.Series:
    """The monthly return on cash (the risk-free rate) for every month in `index`; a month the
    rate isn't published for yet takes the latest known rate."""
    return rf.reindex(rf.index.union(index)).sort_index().ffill().reindex(index)


def benchmark_returns(panel: pd.DataFrame, values: pd.DataFrame) -> pd.DataFrame:
    """Monthly returns (by month earned) of SPY and of an equal-weight basket of every eligible
    member, rebalanced monthly. Both gross: SPY's fee is already in its price, and the basket's
    costs are left out (it's a yardstick, not a strategy)."""
    spy = values["SPY"].pct_change()  # row m+1 = value(m+1) / value(m) - 1, earned in m+1
    ew_picks = picks_by_month(panel.assign(_all=eligible(panel).astype(int)), "_all")
    ew = simulate(ew_picks, values, hold=1, cost=0.0)["ret"]
    return pd.DataFrame({"spy": spy, "equal_weight": ew}).dropna()


def run_grid(
    panel: pd.DataFrame,
    values: pd.DataFrame,
    holds: Iterable[int],
    signals: Iterable[str] = RULE_LOOKBACKS,
    top_ns: Iterable[int] = RULE_TOP_NS,
    cost: float = COST_PER_SIDE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate every (look-back, N, hold) cell. `panel` must already have the `pred_mom_*`
    columns. Returns (net monthly returns, monthly cost paid), one column per cell, named
    `<pred>_h<hold>`."""
    rets, costs = {}, {}
    for s in signals:
        for n in top_ns:
            picks = picks_by_month(panel, rule_name(s, n))
            for h in holds:
                sim = simulate(picks, values, hold=h, cost=cost)
                name = f"{rule_name(s, n)}_h{h}"
                rets[name], costs[name] = sim["ret"], sim["cost"]
    return pd.DataFrame(rets), pd.DataFrame(costs)


VERSIONS = ["equal", "equal_buffer", "inv_vol", "inv_vol_buffer"]


def strategy_versions(ranks: dict[pd.Period, list[str]], n: int, vol: pd.Series) -> dict:
    """The four pre-declared versions of a top-n, 1-month-hold strategy: equal or inverse-vol
    weights, without or with the hold buffer."""
    plain = buffered_picks(ranks, n, keep=n)
    buffer = buffered_picks(ranks, n)
    return {
        "equal": plain,
        "equal_buffer": buffer,
        "inv_vol": inverse_vol_weights(plain, vol),
        "inv_vol_buffer": inverse_vol_weights(buffer, vol),
    }


def run_strategies(
    panel: pd.DataFrame,
    values: pd.DataFrame,
    signals: dict[str, str],
    vol: pd.Series,
    top_ns: Iterable[int] = RULE_TOP_NS,
    cost: float = COST_PER_SIDE,
    invested: pd.Series | None = None,
    cash_return: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate every (strategy, N, version) with a 1-month hold. `signals` maps a strategy name
    to the panel column it ranks by (a model score or a past return). Returns (net monthly
    returns, monthly cost paid), one column per `<strategy>_top<N>_<version>`. With a trend
    filter (`invested`, `cash_return`), every column gets the `_trend` suffix."""
    rets, costs = {}, {}
    suffix = TREND if invested is not None else ""
    for name, col in signals.items():
        ranks = ranked(panel, col)
        for n in top_ns:
            for version, picks in strategy_versions(ranks, n, vol).items():
                sim = simulate(picks, values, 1, cost, invested, cash_return)
                key = f"{name}_top{n}_{version}{suffix}"
                rets[key], costs[key] = sim["ret"], sim["cost"]
    return pd.DataFrame(rets), pd.DataFrame(costs)


def parse_strategy(name: str) -> dict:
    """`xgb_reg_top10_inv_vol_buffer_trend` -> strategy xgb_reg, top_n 10, version
    inv_vol_buffer, trend True. Any other name (a benchmark, the chosen grid rule) gets blank
    N and version; a `_trend` suffix is read either way."""
    trend = name.endswith(TREND)
    base = name.removesuffix(TREND)
    if "_top" in base:
        strategy, rest = base.rsplit("_top", 1)
        n, _, version = rest.partition("_")
        if n.isdigit() and version in VERSIONS:
            return {"strategy": strategy, "top_n": int(n), "version": version, "trend": trend}
    return {"strategy": base, "top_n": pd.NA, "version": pd.NA, "trend": trend}


def dollars(r: pd.Series, cost: pd.Series | None = None, start: float = START_DOLLARS) -> dict:
    """What `start` dollars grow to over `r`'s months (net of costs), and the fees paid in
    dollars: each month's cost is a fraction of the value at the start of that month."""
    r = r.dropna()
    value = start * (1 + r).cumprod()
    out = {"end_value": value.iloc[-1] if len(r) else np.nan}
    if cost is not None:
        before = value.shift(1, fill_value=start)
        out["fees_dollars"] = float((cost.reindex(r.index).fillna(0) * before).sum())
    return out


def strategy_table(
    rets: pd.DataFrame,
    costs: pd.DataFrame,
    bench: pd.DataFrame,
    rf: pd.Series,
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """One row per strategy (plus SPY and the equal-weight basket) for the returns from decisions
    made in [start, end): the grid's numbers, plus START_DOLLARS grown, fees in dollars and the
    traded share of the portfolio per year (buys plus sells)."""
    months = earned_months(rets.index, start, end)
    spy = bench["spy"]
    rows = []
    for c in rets:
        r, k = rets.loc[months, c], costs[c]
        row = parse_strategy(c) | performance(r, spy, rf, k) | dollars(r, k.reindex(months))
        row["traded_per_year"] = row["cost_per_year"] / COST_PER_SIDE
        rows.append({"name": c} | row)
    for b in bench:
        r = bench[b].reindex(months)
        rows.append({"name": b} | parse_strategy(b) | performance(r, spy, rf) | dollars(r))
    out = pd.DataFrame(rows).set_index("name")
    out["top_n"] = out["top_n"].astype("Int64")
    out.loc["spy", ["beats_spy_months", "t_vs_spy", "cagr_vs_spy"]] = np.nan
    return out


def version_effect(
    table: pd.DataFrame,
    strategies: Iterable[str],
    top_n: int,
    measures: Iterable[str] = ("cagr", "sharpe", "max_drawdown", "traded_per_year"),
) -> pd.DataFrame:
    """Each version minus the plain equal-weight version of the same strategy, averaged over
    `strategies` at one basket size (a `strategy_table`). One row per non-plain version."""
    measures = list(measures)
    t = table[(table["top_n"] == top_n) & table["strategy"].isin(list(strategies))]
    if "trend" in t:
        t = t[~t["trend"].astype(bool)]  # versions compared without the trend filter
    wide = t.set_index(["version", "strategy"])[measures]
    base = wide.loc["equal"]
    return pd.DataFrame(
        {v: (wide.loc[v] - base).mean() for v in VERSIONS if v != "equal"}
    ).T.rename_axis("version")


def filter_effect(
    table: pd.DataFrame,
    measures: Iterable[str] = ("cagr", "sharpe", "max_drawdown", "traded_per_year"),
) -> pd.DataFrame:
    """The trend-filtered version minus the same strategy unfiltered, for every pair in a
    `strategy_table`: averaged by version (all basket sizes and strategies), plus the share of
    pairs where the filter raised the Sharpe ratio."""
    measures = list(measures)
    trend = table[table["trend"].astype(bool)]
    plain = table.loc[[n.removesuffix(TREND) for n in trend.index]]
    diff = trend[measures].to_numpy() - plain[measures].to_numpy()
    d = pd.DataFrame(diff, index=trend.index, columns=measures)
    d["version"] = trend["version"].fillna("other").to_numpy()
    out = d.groupby("version")[measures].mean()
    out["sharpe_up_share"] = (d["sharpe"] > 0).groupby(d["version"]).mean()
    out["pairs"] = d.groupby("version").size()
    return out


def off_decisions(invested: pd.Series, start: str, end: str | None = None) -> list[pd.Period]:
    """The decisions in [start, end) at which the trend filter is out of the market."""
    m = invested.index
    keep = m >= pd.Period(start, freq="M")
    if end:
        keep &= m < pd.Period(end, freq="M")
    s = invested[keep].astype(bool)
    return list(s.index[~s])


def months_off(invested: pd.Series, start: str, end: str | None = None) -> int:
    """How many decisions in [start, end) the trend filter kept out of the market."""
    return len(off_decisions(invested, start, end))


def window(rets: pd.DataFrame, start: str | None, end: str | None = None) -> pd.DataFrame:
    """The rows of `rets` earned from decisions in [start, end)."""
    return rets.loc[earned_months(rets.index, start, end)]


def value_paths(rets: pd.DataFrame, start_value: float = START_DOLLARS) -> pd.DataFrame:
    """What `start_value` grows to by the end of each month, per column."""
    return start_value * (1 + rets).cumprod()


def drawdowns(rets: pd.DataFrame) -> pd.DataFrame:
    """For each column, the fall from its previous peak at every month (0 at a new high)."""
    growth = (1 + rets).cumprod()
    peak = np.maximum(growth.cummax(), 1.0)  # the starting amount counts as the first peak
    return growth / peak - 1


def rolling_excess(rets: pd.DataFrame, spy: pd.Series, window: int = 12) -> pd.DataFrame:
    """Each column's compounded return over the last `window` months minus SPY's (blank until a
    full window exists)."""
    roll = (1 + rets).rolling(window).apply(np.prod, raw=True) - 1
    spy_roll = (1 + spy.reindex(rets.index)).rolling(window).apply(np.prod, raw=True) - 1
    return roll.sub(spy_roll, axis=0)


# ---------------------------------------------------------------------------------------------
# The course-style vector simulation (#47): a cross-check of the exact simulator above
# ---------------------------------------------------------------------------------------------

VECTOR_STAKE = 100.0  # dollars per pick


def add_vector_sim(
    panel: pd.DataFrame,
    pred: str,
    prefix: str,
    hold: int,
    cost: float = COST_PER_SIDE,
    stake: float = VECTOR_STAKE,
) -> pd.DataFrame:
    """Add `<prefix>_gross`, `<prefix>_fees` and `<prefix>_net` per prediction row: every pick
    (`pred` == 1) invests `stake` at the next open for `hold` months, and pays `cost` on the buy
    and on the sell (a full round trip, even when the same stock is picked again). Rows that
    aren't picks, or whose holding period hasn't ended yet, get 0 / blank.

    Unlike `simulate`, nothing compounds and kept stocks aren't netted: it's the course's simple
    method, kept as an independent cross-check."""
    out = panel.copy()
    picked = out[pred] == 1
    ret = out[f"fwd_ret_{hold}m"]
    out[f"{prefix}_gross"] = np.where(picked, stake * ret, 0.0)
    out[f"{prefix}_fees"] = np.where(picked, stake * 2 * cost, 0.0)
    out[f"{prefix}_net"] = out[f"{prefix}_gross"] - out[f"{prefix}_fees"]
    unfinished = picked & ret.isna()  # the holding period runs past the data
    out.loc[unfinished, [f"{prefix}_gross", f"{prefix}_fees", f"{prefix}_net"]] = np.nan
    return out


def vector_summary(
    panel: pd.DataFrame,
    pred: str,
    prefix: str,
    hold: int,
    start: str,
    end: str | None = None,
    stake: float = VECTOR_STAKE,
) -> dict:
    """The course's summary for decisions in [start, end): trades, net profit, the capital needed
    (stake x hold x picks per decision month at the 75th percentile, since `hold` months of
    positions overlap), growth of that capital, CAGR over the window, and profit per trade."""
    m = pd.PeriodIndex(pd.to_datetime(panel["date"]), freq="M")
    keep = m >= pd.Period(start, freq="M")
    if end:
        keep &= m < pd.Period(end, freq="M")
    rows = panel[keep & (panel[pred] == 1) & panel[f"{prefix}_net"].notna()]
    # the span the capital was in use: first decision to the end of the last completed hold
    # (decisions whose holding period hasn't ended carry no result and no months)
    done = pd.PeriodIndex(pd.to_datetime(rows["date"]), freq="M")
    months = (done.max() - done.min()).n + hold if len(done) else 0
    per_month = rows.groupby("date").size()
    capital = stake * hold * float(per_month.quantile(0.75)) if len(per_month) else np.nan
    net = float(rows[f"{prefix}_net"].sum())
    growth = (capital + net) / capital if capital else np.nan
    return {
        "trades": len(rows),
        "net profit": net,
        "capital needed": capital,
        "growth": growth,
        "CAGR": growth ** (12 / months) - 1 if months and growth > 0 else np.nan,
        "profit per trade": net / len(rows) if len(rows) else np.nan,
        "months": months,
    }


def risk_free(fedfunds: pd.DataFrame) -> pd.Series:
    """Monthly risk-free return by month: the Fed Funds monthly average (%) / 1200. Used only to
    score results after the fact, so no publication lag applies."""
    f = fedfunds.assign(month=pd.PeriodIndex(pd.to_datetime(fedfunds["date"]), freq="M"))
    return f.set_index("month")["value"] / 1200


def performance(
    r: pd.Series, spy: pd.Series, rf: pd.Series, cost: pd.Series | None = None
) -> dict:
    """Headline numbers for one monthly return series, against SPY over the same months."""
    r = r.dropna()
    spy, rf = spy.reindex(r.index), rf.reindex(r.index).fillna(0)
    years = len(r) / 12
    growth = (1 + r).cumprod()
    excess = r - spy
    out = {
        "cagr": growth.iloc[-1] ** (1 / years) - 1,
        "spy_cagr": (1 + spy).prod() ** (1 / years) - 1,
        "volatility": r.std() * np.sqrt(12),
        "sharpe": (r - rf).mean() / r.std() * np.sqrt(12) if r.std() > TINY else np.nan,
        # the starting amount is the first peak, so a loss in the first month counts
        "max_drawdown": min((growth / np.maximum(growth.cummax(), 1.0) - 1).min(), 0.0),
        "beats_spy_months": (excess > 0).mean(),
        # t-statistic of the mean monthly return over SPY: about 2 or more is unlikely to be luck
        # for one rule, but the grid tests 60, so a cell needs well above 2 to stand out.
        "t_vs_spy": (
            excess.mean() / (excess.std() / np.sqrt(len(excess)))
            if excess.std() > TINY
            else np.nan
        ),
        "months": len(r),
    }
    out["cagr_vs_spy"] = out["cagr"] - out["spy_cagr"]
    if cost is not None:
        out["cost_per_year"] = cost.reindex(r.index).mean() * 12
    return out


def benchmark_table(bench: pd.DataFrame, rf: pd.Series) -> pd.DataFrame:
    """Headline numbers for the benchmarks alone (SPY's comparison with itself left blank)."""
    out = pd.DataFrame({b: performance(bench[b], bench["spy"], rf) for b in bench}).T
    out.loc["spy", ["beats_spy_months", "t_vs_spy", "cagr_vs_spy"]] = np.nan
    return out


def grid_summary(table: pd.DataFrame, by: str) -> pd.DataFrame:
    """How many grid cells beat SPY on return and on Sharpe, grouped by one grid dimension."""
    spy = table.loc["spy"]
    cells = table.dropna(subset=["top_n"])
    return cells.groupby(by).agg(
        cells=("cagr", "size"),
        higher_return=("cagr", lambda s: int((s > spy["cagr"]).sum())),
        higher_sharpe=("sharpe", lambda s: int((s > spy["sharpe"]).sum())),
        median_cagr=("cagr", "median"),
        median_sharpe=("sharpe", "median"),
        median_max_drawdown=("max_drawdown", "median"),
    )


def selection_check(
    rets: pd.DataFrame,
    bench: pd.DataFrame,
    rf: pd.Series,
    costs: pd.DataFrame,
    split: str,
) -> tuple[str, pd.DataFrame, int]:
    """Pick the cell with the best Sharpe on returns from decisions before `split`, then score
    it, SPY and the equal-weight basket on both sides of the split. Returns (cell, table, its
    Sharpe rank among all cells after the split)."""
    before = grid_table(rets, bench, rf, costs, end=split)
    after = grid_table(rets, bench, rf, costs, start=split)
    best = before.drop(index=bench.columns).index[0]
    rows = [best, *bench.columns]
    cols = ["cagr", "volatility", "sharpe", "max_drawdown", "beats_spy_months", "months"]
    table = pd.concat({"before": before.loc[rows, cols], "after": after.loc[rows, cols]})
    rank = list(after.drop(index=bench.columns).index).index(best) + 1
    return best, table, rank


def parse_cell(name: str) -> dict:
    """`pred_mom_12_1m_top10_h3` -> look-back `ret_12_1m`, top_n 10, hold 3."""
    rule, h = name.rsplit("_h", 1)
    body, n = rule.removeprefix("pred_mom_").rsplit("_top", 1)
    return {"lookback": f"ret_{body}", "top_n": int(n), "hold": int(h)}


def grid_table(
    rets: pd.DataFrame,
    bench: pd.DataFrame,
    rf: pd.Series,
    costs: pd.DataFrame | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """One row per grid cell (plus SPY and the equal-weight basket) for the returns from
    decisions made in [start, end), sorted by Sharpe."""
    months = earned_months(rets.index, start, end)
    spy = bench["spy"]
    rows = []
    for c in rets:
        row = parse_cell(c) | performance(
            rets.loc[months, c], spy, rf, None if costs is None else costs[c]
        )
        rows.append({"cell": c} | row)
    for b in bench:
        rows.append({"cell": b} | performance(bench[b].reindex(months), spy, rf))
    out = pd.DataFrame(rows).set_index("cell")
    out[["top_n", "hold"]] = out[["top_n", "hold"]].astype("Int64")  # blank for benchmarks
    out.loc["spy", ["beats_spy_months", "t_vs_spy"]] = np.nan  # SPY against itself
    return out.sort_values("sharpe", ascending=False)
