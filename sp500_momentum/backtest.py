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
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from sp500_momentum.config import COST_PER_SIDE, RULE_LOOKBACKS, RULE_TOP_NS

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
    picks: dict[pd.Period, list[str]],
    values: pd.DataFrame,
    hold: int,
    cost: float = COST_PER_SIDE,
) -> pd.DataFrame:
    """Staggered-portfolio simulation of one rule (see the module docstring).

    Runs every month from the first decision to the end of `values`; a month without picks keeps
    the due slot's holdings. Returns one row per month earned: `ret` (net of costs), `gross` and
    `cost` (the fraction of the portfolio paid in costs that month), indexed by the month the
    return is earned in.
    """
    slots: list[dict[str, float] | None] = [None] * hold
    months = values.index[(values.index >= min(picks)) & (values.index < values.index.max())]
    rows = {}
    for i, m in enumerate(months):
        s = i % hold
        new = picks.get(m, [])
        paid = [0.0] * hold
        if new:
            target = {t: 1 / len(new) for t in new}
            old = slots[s] or {}
            turnover = sum(abs(target.get(t, 0) - old.get(t, 0)) for t in set(target) | set(old))
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
        "max_drawdown": (growth / growth.cummax() - 1).min(),
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
    """Pick the cell with the best Sharpe on months earned before `split`, then score it, SPY and
    the equal-weight basket on both sides of the split. Returns (cell, table, its Sharpe rank
    among all cells after the split)."""
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
    """One row per grid cell (plus SPY and the equal-weight basket) for the months earned in
    [start, end), sorted by Sharpe."""
    months = rets.index
    if start:
        months = months[months >= pd.Period(start, freq="M")]
    if end:
        months = months[months < pd.Period(end, freq="M")]
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
