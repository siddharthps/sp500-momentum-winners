"""Features for the monthly member table.

    uv run python -m sp500_momentum.features build     # after `monthly build`

Every feature is computed from MONTHLY bars (open/high/low/close/volume per month), for every stock
the same way: Yahoo's daily prices are rolled up into monthly bars, and Alpha Vantage is monthly
already. Daily-only features would be blank exactly for the companies that are later delisted
(they only have Alpha Vantage data), and a model would learn "blank = will be delisted" (decisions.md).

Golden rule: every value is known at the month-end close of the decision month.
- Stock and market features use bars up to and including the decision month.
- Macro figures go through their publication lag (FRED_SERIES); daily yields use the last value
  strictly before the decision date.
- Ranks and percentiles are computed within each decision date, never across dates.

Feature sets (named like the course's, checked so every column is in exactly one set):
TO_PREDICT, PAST_RETURNS, TA, STOCK, CROSS_SECTION, MARKET, MACRO, DUMMIES, plus INFO (ids, prices).
"""

import itertools

from loguru import logger
import numpy as np
import pandas as pd
import talib
import typer

from sp500_momentum.config import (
    AV_MANIFEST,
    AV_MONTHLY_DIR,
    FEATURES_TABLE,
    FRED_DIR,
    FRED_SERIES,
    MARKET_SERIES,
    MONTHLY_PANEL,
    REMOVED_SECTORS,
    SECTOR_ETF,
    SECTOR_ETF_FALLBACK,
    WIKIPEDIA_DIR,
    YAHOO_DAILY_DIR,
    YAHOO_SUSPECT,
)
from sp500_momentum.sources.yahoo import file_name

app = typer.Typer(help="Build the feature table.")


@app.callback()
def _main():
    """Build the feature table."""


BAR_COLS = ["open", "high", "low", "close", "volume", "dollar_vol"]

# ---------------------------------------------------------------------------------------------
# 1. Monthly bars
# ---------------------------------------------------------------------------------------------


def _contiguous(g: pd.DataFrame) -> pd.DataFrame:
    g = g.reindex(pd.period_range(g.index.min(), g.index.max(), freq="M"))
    g.index.name = "month"
    return g


def bars_from_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Yahoo daily rows -> monthly bars, adjusted for dividends and splits.

    Yahoo's `close` and `volume` are already split-adjusted, so close * volume is the dollar
    volume. Prices are scaled by adj_close / close (the dividend factor), and volume is put in the
    same adjusted units (volume * close / adj_close), so volume indicators stay consistent.
    """
    d = daily.sort_values("date")
    f = d["adj_close"] / d["close"]
    x = pd.DataFrame(
        {
            "month": d["date"].dt.to_period("M"),
            "open": d["open"] * f,
            "high": d["high"] * f,
            "low": d["low"] * f,
            "close": d["adj_close"],
            "volume": d["volume"] / f,
            "dollar_vol": d["close"] * d["volume"],
        }
    )
    g = x.groupby("month").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        dollar_vol=("dollar_vol", "sum"),
    )
    return _contiguous(g)


def bars_from_av(av: pd.DataFrame, removed_date) -> pd.DataFrame:
    """Alpha Vantage monthly rows -> the same bars, cut after the removal month.

    Alpha Vantage's open/high/low/close and volume are raw (not split-adjusted), so they're
    scaled by adjusted close / close, and volume by its inverse.
    """
    a = av.sort_values("timestamp").copy()
    a["month"] = pd.to_datetime(a["timestamp"]).dt.to_period("M")
    a = a[a["month"] <= pd.Timestamp(removed_date).to_period("M")]
    f = a["adjusted close"] / a["close"]
    g = (
        pd.DataFrame(
            {
                "month": a["month"],
                "open": a["open"] * f,
                "high": a["high"] * f,
                "low": a["low"] * f,
                "close": a["adjusted close"],
                "volume": a["volume"] / f,
                "dollar_vol": a["close"] * a["volume"],
            }
        )
        .groupby("month")
        .last()
    )
    return _contiguous(g)


# ---------------------------------------------------------------------------------------------
# 2. TA-Lib indicators on monthly bars (the course's 41 functions -> 55 columns)
# ---------------------------------------------------------------------------------------------


def ta_features(b: pd.DataFrame) -> pd.DataFrame:
    """TA-Lib indicators per month. Raw price or volume levels are made comparable across
    stocks: price-like outputs are divided by the close, cumulative volume lines (OBV, A/D) become
    their 12-month change over 12 months of volume."""
    ok = b.dropna(subset=["open", "high", "low", "close", "volume"])
    out = pd.DataFrame(index=b.index)
    if len(ok) < 2:
        return out
    o, h, lo, c, v = (
        ok[k].to_numpy(dtype="float64") for k in ["open", "high", "low", "close", "volume"]
    )
    r = {}
    # momentum
    r["adx"] = talib.ADX(h, lo, c)
    r["adxr"] = talib.ADXR(h, lo, c)
    r["apo"] = talib.APO(c) / c
    r["aroon_down"], r["aroon_up"] = talib.AROON(h, lo)
    r["aroonosc"] = talib.AROONOSC(h, lo)
    r["bop"] = talib.BOP(o, h, lo, c)
    r["cci"] = talib.CCI(h, lo, c)
    r["cmo"] = talib.CMO(c)
    r["dx"] = talib.DX(h, lo, c)
    for name, fn in [("macd", talib.MACD), ("macdext", talib.MACDEXT), ("macdfix", talib.MACDFIX)]:
        m, s, hist = fn(c)
        r[name], r[f"{name}_signal"], r[f"{name}_hist"] = m / c, s / c, hist / c
    r["mfi"] = talib.MFI(h, lo, c, v)
    r["minus_dm"] = talib.MINUS_DM(h, lo) / c
    r["mom"] = talib.MOM(c) / c
    r["plus_di"] = talib.PLUS_DI(h, lo, c)
    r["plus_dm"] = talib.PLUS_DM(h, lo) / c
    r["ppo"] = talib.PPO(c)
    r["roc"] = talib.ROC(c)
    r["rocp"] = talib.ROCP(c)
    r["rocr"] = talib.ROCR(c)
    r["rocr100"] = talib.ROCR100(c)
    r["rsi"] = talib.RSI(c)
    r["stoch_k"], r["stoch_d"] = talib.STOCH(h, lo, c)
    r["stochf_k"], r["stochf_d"] = talib.STOCHF(h, lo, c)
    r["stochrsi_k"], r["stochrsi_d"] = talib.STOCHRSI(c)
    r["trix"] = talib.TRIX(c)
    r["ultosc"] = talib.ULTOSC(h, lo, c)
    r["willr"] = talib.WILLR(h, lo, c)
    # volume
    vol12 = pd.Series(v).rolling(12).sum().to_numpy()
    r["ad"] = (pd.Series(talib.AD(h, lo, c, v)).diff(12).to_numpy()) / vol12
    r["adosc"] = talib.ADOSC(h, lo, c, v) / pd.Series(v).rolling(10).mean().to_numpy()
    r["obv"] = (pd.Series(talib.OBV(c, v)).diff(12).to_numpy()) / vol12
    # volatility
    r["atr"] = talib.ATR(h, lo, c) / c
    r["natr"] = talib.NATR(h, lo, c)
    # cycle (Hilbert transform; needs ~5 years of bars)
    r["ht_dcperiod"] = talib.HT_DCPERIOD(c)
    r["ht_dcphase"] = talib.HT_DCPHASE(c)
    inphase, quad = talib.HT_PHASOR(c)
    r["ht_phasor_inphase"], r["ht_phasor_quadrature"] = inphase / c, quad / c
    r["ht_sine"], r["ht_leadsine"] = talib.HT_SINE(c)
    r["ht_trendmode"] = talib.HT_TRENDMODE(c)
    # price transforms, relative to the close
    r["avgprice"] = talib.AVGPRICE(o, h, lo, c) / c - 1
    r["medprice"] = talib.MEDPRICE(h, lo) / c - 1
    r["typprice"] = talib.TYPPRICE(h, lo, c) / c - 1
    r["wclprice"] = talib.WCLPRICE(h, lo, c) / c - 1
    ta = pd.DataFrame({f"ta_{k}": val for k, val in r.items()}, index=ok.index)
    ta = ta.replace([np.inf, -np.inf], np.nan)
    return out.join(ta)


# ---------------------------------------------------------------------------------------------
# 3. Stock features (own, from the stock's bars)
# ---------------------------------------------------------------------------------------------


def stock_features(b: pd.DataFrame, spy_ret: pd.Series) -> pd.DataFrame:
    """Risk, price position and volume features from one stock's monthly bars."""
    c, h, lo, dv = b["close"], b["high"], b["low"], b["dollar_vol"]
    r = c.pct_change(fill_method=None)
    m = spy_ret.reindex(b.index)
    vol_12m = r.rolling(12).std()
    ma10 = c.rolling(10).mean()
    f = pd.DataFrame(index=b.index)
    f["vol_3m"] = r.rolling(3).std()
    f["vol_12m"] = vol_12m
    f["downside_vol_12m"] = r.clip(upper=0).rolling(12).std()
    f["beta_36m"] = r.rolling(36, min_periods=24).cov(m) / m.rolling(36, min_periods=24).var()
    f["drawdown_12m"] = c / c.rolling(12).max() - 1
    f["dist_high_12m"] = c / h.rolling(12).max() - 1
    f["dist_low_12m"] = c / lo.rolling(12).min() - 1
    f["ma3_ratio"] = c / c.rolling(3).mean() - 1
    f["ma10_ratio"] = c / ma10 - 1
    f["above_ma10"] = (c > ma10).astype(float).where(ma10.notna())
    f["up_months_12m"] = (r > 0).astype(float).where(r.notna()).rolling(12).mean()
    f["ret_1m_z"] = r / vol_12m.shift(1)  # last month's move in units of its usual volatility
    f["range_1m"] = (h - lo) / c
    f["log_dollar_vol"] = np.log1p(dv)
    f["dollar_vol_ratio"] = dv / dv.shift(1).rolling(12).mean()  # volume spike vs the past year
    return f.replace([np.inf, -np.inf], np.nan)


# ---------------------------------------------------------------------------------------------
# 4. Market and 5. macro features (one value per decision month)
# ---------------------------------------------------------------------------------------------


def returns_over(close: pd.Series, windows=(1, 3, 6, 12)) -> pd.DataFrame:
    return pd.DataFrame({f"{w}m": close / close.shift(w) - 1 for w in windows})


def market_features(
    bars: dict[str, pd.DataFrame], fred: dict[str, pd.DataFrame], dates: pd.Series
):
    """SPY, Dow, gold, WTI growth; 10-year yield changes; VIX level and percentile."""
    months = pd.PeriodIndex(dates.dt.to_period("M"))
    out = pd.DataFrame(index=months)
    for name, t in MARKET_SERIES.items():
        rets = returns_over(bars[t]["close"])
        for col in rets:
            out[f"mkt_{name}_ret_{col}"] = rets[col].reindex(months).to_numpy()
    # Yield changes need month-ends before the first decision date too (the data starts in 2005),
    # so they're computed on every SPY month-end, then read at the decision months.
    # Each month is read "as of" its last bond-trading day, or the actual decision date in decision
    # months, and takes the last value strictly before that day (yields publish the next day).
    d10 = fred["DGS10"]["date"]
    asof = d10.groupby(d10.dt.to_period("M")).max()
    asof.loc[months] = dates.to_numpy()
    y10 = yield_before(fred["DGS10"], pd.Series(asof.sort_index().to_numpy()))
    for w in (1, 3, 12):
        out[f"mkt_dgs10_chg_{w}m"] = (y10 - y10.shift(w)).reindex(months).to_numpy()
    vix = bars["^VIX"]["close"]
    out["vix"] = vix.reindex(months).to_numpy()
    pct = vix.rolling(60, min_periods=24).apply(lambda s: (s <= s.iloc[-1]).mean(), raw=False)
    out["vix_pct_60m"] = pct.reindex(months).to_numpy()
    return out


def yield_before(series: pd.DataFrame, dates: pd.Series) -> pd.Series:
    """For each decision date, the last daily value strictly before it (published next day)."""
    s = series.set_index("date")["value"].sort_index()
    idx = s.index.searchsorted(pd.DatetimeIndex(dates), side="left") - 1
    vals = np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan)
    return pd.Series(vals, index=pd.PeriodIndex(dates.dt.to_period("M")))


def monthly_lagged(series: pd.DataFrame, months: pd.PeriodIndex, lag: int) -> pd.Series:
    """A monthly series (dated the 1st), carried forward over gaps (e.g. CPI Oct 2025), read
    `lag` months after its own month: at decision month t, the value for month t - lag."""
    s = series.set_index(series["date"].dt.to_period("M"))["value"].sort_index()
    s = s.reindex(
        pd.period_range(s.index.min(), max(s.index.max(), months.max()), freq="M")
    ).ffill()
    return s.reindex(months - lag)


def macro_features(fred: dict[str, pd.DataFrame], dates: pd.Series) -> pd.DataFrame:
    months = pd.PeriodIndex(dates.dt.to_period("M"))
    out = pd.DataFrame(index=months)
    cpi = fred["CPILFESL"].set_index(fred["CPILFESL"]["date"].dt.to_period("M"))["value"]
    cpi = cpi.reindex(pd.period_range(cpi.index.min(), cpi.index.max(), freq="M")).ffill()
    cpi_df = pd.DataFrame({"date": cpi.index.to_timestamp(), "value": cpi.to_numpy()})
    lag = FRED_SERIES["CPILFESL"]["lag_months"]
    level = monthly_lagged(cpi_df, months, lag)
    out["cpi_yoy"] = (level.to_numpy() / monthly_lagged(cpi_df, months, lag + 12).to_numpy()) - 1
    out["cpi_mom"] = (level.to_numpy() / monthly_lagged(cpi_df, months, lag + 1).to_numpy()) - 1
    out["fedfunds"] = monthly_lagged(
        fred["FEDFUNDS"], months, FRED_SERIES["FEDFUNDS"]["lag_months"]
    ).to_numpy()
    for sid in ("DGS1", "DGS5", "DGS10"):
        out[sid.lower()] = yield_before(fred[sid], dates).to_numpy()
    out["yield_slope_10_1"] = out["dgs10"] - out["dgs1"]
    g = fred["GDPPOT"].set_index("date")["value"].sort_index()
    yoy, qoq = g.pct_change(4), g.pct_change(1)
    starts = months.to_timestamp()
    pos = g.index.searchsorted(starts, side="right") - 1  # latest quarter starting on or before
    out["gdppot_yoy"] = np.where(pos >= 0, yoy.to_numpy()[np.clip(pos, 0, None)], np.nan)
    out["gdppot_qoq"] = np.where(pos >= 0, qoq.to_numpy()[np.clip(pos, 0, None)], np.nan)
    return out


# ---------------------------------------------------------------------------------------------
# 6. Cross-section features (within each decision date)
# ---------------------------------------------------------------------------------------------

RANKED = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_12_1m"]


def cross_section_features(df: pd.DataFrame, monthly_ret: pd.DataFrame) -> pd.DataFrame:
    """Ranks, relative strength, breadth, dispersion and how last month's winners just did.

    `monthly_ret`: month x ticker table of 1-month returns (all stocks, members or not), used to
    see how the previous month's top-10 did over the month that just ended.
    """
    g = df.groupby("date")
    for col in RANKED:
        df[f"rank_{col}"] = g[col].rank(pct=True)
    for col in ("ret_1m", "ret_12_1m"):
        df[f"sector_rank_{col}"] = df.groupby(["date", "sector"])[col].rank(pct=True)
    df["rs_spy_1m"] = df["ret_1m"] - df["mkt_spy_ret_1m"]
    df["rs_spy_12m"] = df["ret_12m"] - df["mkt_spy_ret_12m"]
    df["rs_sector_1m"] = df["ret_1m"] - df["sector_etf_ret_1m"]
    df["rs_sector_12m"] = df["ret_12m"] - df["sector_etf_ret_12m"]
    df["breadth_above_ma10"] = g["above_ma10"].transform("mean")
    df["dispersion_1m"] = g["ret_1m"].transform(lambda s: s.quantile(0.9) - s.quantile(0.1))
    # Last month's top-10 winners (by ret_1m at t-1): their return over month t, minus SPY's.
    months = sorted(df["month_p"].unique())
    track = {}
    for prev, cur in itertools.pairwise(months):
        top = df[df["month_p"] == prev].nlargest(10, "ret_1m")["ticker"]
        r = monthly_ret.reindex(columns=top).loc[cur] if cur in monthly_ret.index else pd.Series()
        spy = df.loc[df["month_p"] == cur, "mkt_spy_ret_1m"].iloc[0]
        track[cur] = r.mean() - spy if len(r.dropna()) else np.nan
    t = pd.Series(track).sort_index()
    df["winners_excess_1m"] = df["month_p"].map(t)
    df["winners_excess_12m"] = df["month_p"].map(t.rolling(12, min_periods=6).mean())
    first_seen = df.groupby("ticker")["date"].transform("min")
    start = df["date"].min()
    df["new_member_12m"] = (
        (first_seen > start) & (df["date"] - first_seen < pd.Timedelta(days=366))
    ).astype(float)
    return df


# ---------------------------------------------------------------------------------------------
# Feature sets
# ---------------------------------------------------------------------------------------------

INFO = [
    "date",
    "month",
    "ticker",
    "price_ticker",
    "source",
    "close_adj",
    "entry_px",
    "dollar_vol",
    "has_price",
    "sector",
]
PAST_RETURNS = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_12_1m"]


def feature_sets(columns) -> dict[str, list[str]]:
    cols = list(columns)
    to_predict = [
        c for c in cols if c.startswith(("fwd_", "spy_fwd_", "is_beat_spy_", "is_top_decile_"))
    ]
    sets = {
        "INFO": [c for c in INFO if c in cols],
        "TO_PREDICT": to_predict,
        "PAST_RETURNS": PAST_RETURNS,
        "TA": [c for c in cols if c.startswith("ta_")],
        "STOCK": [
            "vol_3m",
            "vol_12m",
            "downside_vol_12m",
            "beta_36m",
            "drawdown_12m",
            "dist_high_12m",
            "dist_low_12m",
            "ma3_ratio",
            "ma10_ratio",
            "above_ma10",
            "up_months_12m",
            "ret_1m_z",
            "range_1m",
            "log_dollar_vol",
            "dollar_vol_ratio",
        ],
        "CROSS_SECTION": [
            *[f"rank_{c}" for c in RANKED],
            "sector_rank_ret_1m",
            "sector_rank_ret_12_1m",
            "rs_spy_1m",
            "rs_spy_12m",
            "rs_sector_1m",
            "rs_sector_12m",
            "breadth_above_ma10",
            "dispersion_1m",
            "winners_excess_1m",
            "winners_excess_12m",
            "new_member_12m",
        ],
        "MARKET": [c for c in cols if c.startswith(("mkt_", "sector_etf_ret_"))]
        + ["vix", "vix_pct_60m"],
        "MACRO": [
            "cpi_yoy",
            "cpi_mom",
            "fedfunds",
            "dgs1",
            "dgs5",
            "dgs10",
            "yield_slope_10_1",
            "gdppot_yoy",
            "gdppot_qoq",
        ],
        "DUMMIES": [c for c in cols if c.startswith(("month_of_year_", "sector_is_"))],
    }
    return sets


def check_sets(columns, sets: dict[str, list[str]]):
    """Every column is in exactly one set, and every set member exists."""
    seen = [c for s in sets.values() for c in s]
    dup = sorted({c for c in seen if seen.count(c) > 1})
    missing = sorted(set(seen) - set(columns))
    unassigned = sorted(set(columns) - set(seen))
    if dup or missing or unassigned:
        raise ValueError(
            f"feature sets: duplicated {dup}, missing {missing}, unassigned {unassigned}"
        )


# ---------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------


def load_bars(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Monthly bars for every price series the panel uses, plus the market series and sector funds."""
    suspect = set(pd.read_csv(YAHOO_SUSPECT)["ticker"]) if YAHOO_SUSPECT.exists() else set()
    bars = {}
    yahoo_needed = set(panel.loc[panel["source"] == "yahoo", "price_ticker"].dropna())
    yahoo_needed |= set(MARKET_SERIES.values()) | set(SECTOR_ETF.values()) | {"^VIX", "SPY"}
    for t in sorted(yahoo_needed - suspect):
        path = YAHOO_DAILY_DIR / file_name(t)
        if path.exists():
            bars[t] = bars_from_daily(pd.read_parquet(path))
    if AV_MANIFEST.exists():
        man = pd.read_csv(AV_MANIFEST, parse_dates=["removed_date"])
        for _, r in man[man["status"] == "ok"].iterrows():
            av = pd.read_csv(AV_MONTHLY_DIR / f"{r['ticker']}.csv", parse_dates=["timestamp"])
            bars[r["ticker"]] = bars_from_av(av, r["removed_date"])
    return bars


def sectors() -> pd.Series:
    cur = pd.read_csv(WIKIPEDIA_DIR / "sp500_current.csv")[["ticker", "sector"]]
    rem = pd.read_csv(REMOVED_SECTORS)
    return pd.concat([cur, rem[~rem["ticker"].isin(cur["ticker"])]]).set_index("ticker")["sector"]


def sector_etf_returns(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """1/3/12-month returns per sector fund, with the fallback fund before it existed."""
    out = {}
    for etf in set(SECTOR_ETF.values()):
        r = returns_over(bars[etf]["close"], (1, 3, 12))
        fb = SECTOR_ETF_FALLBACK.get(etf)
        if fb:
            r = r.combine_first(returns_over(bars[fb]["close"], (1, 3, 12)))
        out[etf] = r
    return out


def build_features(panel: pd.DataFrame, bars: dict, fred: dict) -> pd.DataFrame:
    df = panel.copy()
    df["month_p"] = pd.PeriodIndex(df["month"], freq="M")
    dates = pd.Series(sorted(df["date"].unique()))
    spy_ret = bars["SPY"]["close"].pct_change(fill_method=None)

    # per-stock: TA + stock features, joined on (price_ticker, month)
    parts = []
    for t in df["price_ticker"].dropna().unique():
        if t not in bars:
            continue
        b = bars[t]
        f = ta_features(b).join(stock_features(b, spy_ret))
        f["price_ticker"] = t
        parts.append(f.reset_index().rename(columns={"month": "month_p"}))
    per_stock = pd.concat(parts, ignore_index=True)
    df = df.merge(per_stock, on=["price_ticker", "month_p"], how="left")

    # market + macro, one row per month
    mm = market_features(bars, fred, dates).join(macro_features(fred, dates))
    df = df.join(mm, on="month_p")

    # sector, the sector fund's returns
    df["sector"] = df["ticker"].map(sectors()).fillna("Unknown")
    etf_rets = sector_etf_returns(bars)
    for w in ("1m", "3m", "12m"):
        df[f"sector_etf_ret_{w}"] = np.nan
    for sector, etf in SECTOR_ETF.items():
        rows = df["sector"] == sector
        for w in ("1m", "3m", "12m"):
            df.loc[rows, f"sector_etf_ret_{w}"] = (
                df.loc[rows, "month_p"].map(etf_rets[etf][w]).to_numpy()
            )

    # cross-section (members with a price only, so ranks compare like with like)
    monthly_ret = pd.DataFrame(
        {t: b["close"].pct_change(fill_method=None) for t, b in bars.items()}
    )
    priced = df[df["has_price"]].copy()
    priced = cross_section_features(priced, monthly_ret)
    new_cols = [c for c in priced.columns if c not in df.columns]
    df = df.join(priced[new_cols])

    # dummies
    moy = df["date"].dt.month
    for m in range(1, 13):
        df[f"month_of_year_{m:02d}"] = (moy == m).astype("int8")
    for s in sorted(df["sector"].unique()):
        df[f"sector_is_{s.lower().replace(' ', '_')}"] = (df["sector"] == s).astype("int8")

    df = df.drop(columns=["month_p"])
    check_sets(df.columns, feature_sets(df.columns))
    return df


@app.command()
def build():
    """Rebuild data/processed/features.parquet from the monthly panel and the raw files."""
    panel = pd.read_parquet(MONTHLY_PANEL)
    bars = load_bars(panel)
    fred = {sid: pd.read_csv(FRED_DIR / f"{sid}.csv", parse_dates=["date"]) for sid in FRED_SERIES}
    df = build_features(panel, bars, fred)
    df.to_parquet(FEATURES_TABLE, index=False)
    sets = feature_sets(df.columns)
    counts = {k: len(v) for k, v in sets.items()}
    n_features = sum(v for k, v in counts.items() if k not in ("INFO", "TO_PREDICT"))
    priced = df[df["has_price"]]
    fill = (
        priced[[c for k, v in sets.items() if k not in ("INFO", "TO_PREDICT") for c in v]]
        .notna()
        .mean()
    )
    logger.success(f"{len(df):,} rows, {n_features} features {counts}")
    logger.info(
        f"Least-filled features (share of priced rows with a value):\n{fill.sort_values().head(12).round(3).to_string()}"
    )
    logger.info(f"Sectors:\n{df.drop_duplicates('ticker')['sector'].value_counts().to_string()}")


if __name__ == "__main__":
    app()
