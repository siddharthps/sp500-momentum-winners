"""Charts for the notebooks and the project book (static PNGs in reports/figures).

One style for every chart:
- Categorical colours come from a validated palette in a FIXED order (never cycled), and a colour
  follows the series everywhere (the plain rule is always blue, SPY always orange, ...). The first
  three slots were checked with the colour validator on 3 Nov 2026 (all pairs: CVD dE 9.2,
  normal-vision dE 24.0). Aqua is below 3:1 contrast on the surface, so every chart that uses it
  carries direct labels, and the notebooks show the same numbers as a table.
- One y-axis per chart, solid hairline grid, thin marks, selective direct labels, no chart junk.
- Sign (positive / negative) uses the diverging pair blue vs red.
"""

import io

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sp500_momentum.backtest import TREND, parse_strategy
from sp500_momentum.config import FIGURES_DIR, START_DOLLARS

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a"]  # blue, orange, aqua: validated all-pairs
POS, NEG = "#2a78d6", "#e34948"  # diverging poles (blue / red)
MID = "#f0efec"  # diverging midpoint: neutral gray, reads as "no difference"
DIVERGING = mpl.colors.LinearSegmentedColormap.from_list("blue_red", [NEG, MID, POS])

LOOKBACK_LABELS = {
    "ret_1m": "1 month",
    "ret_3m": "3 months",
    "ret_6m": "6 months",
    "ret_12m": "12 months",
    "ret_12_1m": "12 months, skip latest",
}

# Colour follows the series, never its position in a given chart.
SERIES_COLOR = {"plain rule": SLOTS[0], "spy": SLOTS[1], "equal_weight": SLOTS[2]}

# Readable names for charts (tables keep the column names). Unlisted features fall back to their name.
FEATURE_LABELS = {
    "ret_1m": "Last month's return",
    "ret_3m": "3-month return",
    "ret_6m": "6-month return",
    "ret_12m": "12-month return",
    "ret_12_1m": "12-month return, skipping last month",
    "rs_spy_1m": "Last month vs SPY",
    "rs_sector_1m": "Last month vs sector fund",
    "rank_ret_1m": "Rank of last month's return",
    "sector_rank_ret_1m": "Rank of last month's return in sector",
    "ret_1m_z": "Last month's move ÷ usual volatility",
    "ma3_ratio": "Price vs its 3-month average",
    "ma10_ratio": "Price vs its 10-month average",
    "ta_medprice": "Mid-price of the month vs close",
    "ta_wclprice": "Weighted close vs close",
    "ta_typprice": "Typical price vs close",
    "ta_avgprice": "Average price vs close",
    "ta_bop": "Balance of power",
    "ta_macd_hist": "MACD histogram",
    "ta_macdfix_hist": "MACD histogram (fixed)",
    "ta_ad": "Accumulation/distribution, 12-month change",
    "ta_adosc": "Chaikin A/D oscillator",
    "ta_trix": "TRIX",
    "ta_rsi": "RSI",
    "beta_36m": "Beta to SPY (36 months)",
    "sector_etf_ret_12m": "Sector fund, 12-month return",
    "log_dollar_vol": "Dollar volume (log)",
    "vol_12m": "Volatility (12 months)",
    "dist_high_12m": "Distance to 12-month high",
    "ta_ht_phasor_quadrature": "Cycle phasor, quadrature (Hilbert)",
    "ta_ht_phasor_inphase": "Cycle phasor, in-phase (Hilbert)",
    "ta_macdext_signal": "MACD signal line (extended)",
    "ta_dx": "Directional movement index",
    "ta_adx": "Average directional index",
    "ta_ultosc": "Ultimate oscillator",
    "ta_cci": "Commodity channel index",
    "ta_willr": "Williams %R",
    "ta_mfi": "Money flow index",
    "ta_obv": "On-balance volume, 12-month change",
    "ta_natr": "Average true range ÷ price",
    "vol_3m": "Volatility (3 months)",
    "downside_vol_12m": "Downside volatility (12 months)",
    "drawdown_12m": "Drawdown from 12-month peak",
    "dist_low_12m": "Distance to 12-month low",
    "dollar_vol_ratio": "Volume spike vs past year",
    "up_months_12m": "Share of up months (12)",
    "range_1m": "Range of the month ÷ price",
    "div_yield_12m": "Dividend yield (12 months)",
    "mom_12_1m_per_vol": "12-1 month return ÷ volatility",
    "drawdown_ath": "Drawdown from all-time high",
    "resid_mom_12_1m": "Residual momentum (12-1, market removed)",
    "ivol_36m": "Idiosyncratic volatility (36 months)",
    "max_ret_12m": "Best month of the past year",
    "seasonality_5y": "Same calendar month, past 5 years",
    "months_in_index": "Months in the index (capped at 120)",
    "ta_ppo": "Percentage price oscillator",
    "ta_atr": "Average true range (in dollars)",
    "ta_minus_dm": "Downward directional movement",
    "ta_macd": "MACD (in dollars)",
    "ta_macdfix": "MACD, fixed periods (in dollars)",
    "ta_stochrsi_d": "Stochastic RSI (smoothed)",
    "mkt_spy_ret_1m": "SPY, last month's return",
    "mkt_dji_ret_1m": "Dow, last month's return",
    "vix": "VIX",
}


def label(feature: str, same_as=()) -> str:
    """Readable name; unlisted features get their column name with the prefix tidied."""
    name = FEATURE_LABELS.get(feature) or feature.removeprefix("ta_").replace("_", " ")
    return f"{name}  (+{len(same_as)} identical)" if len(same_as) else name


def apply_style():
    mpl.rcParams.update(
        {
            # Inline (notebook) display only; save() writes the book's PNGs at its own, higher dpi.
            "figure.dpi": INLINE_DPI,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
            "font.size": 10,
            "text.color": INK,
            "axes.labelcolor": INK_2,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK_2,
            "ytick.labelcolor": INK_2,
            "lines.linewidth": 2,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",  # "semibold" isn't in every font and prints a warning
            "axes.titlelocation": "left",
            "axes.titlepad": 12,
            "legend.frameon": False,
        }
    )


INLINE_DPI = 80  # notebook display; the book's PNGs use BOOK_DPI
BOOK_DPI = 110


def _palette_png(fig, dpi: int) -> bytes:
    """The figure as a 256-colour PNG. Charts have a few flat colours plus their smoothed edges,
    so this looks the same as full colour at about a third of the bytes (it keeps the committed
    notebooks and figures small: every rerun stores new copies in git)."""
    from PIL import Image

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    pal = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = io.BytesIO()
    pal.save(out, format="PNG", optimize=True)
    return out.getvalue()


def save(fig, name: str):
    """Save to reports/figures/<name>.png and, in a notebook, show it: both as palette PNGs, so
    notebooks and the repo stay small. The figure is closed afterwards (shown once)."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    (FIGURES_DIR / f"{name}.png").write_bytes(_palette_png(fig, BOOK_DPI))
    try:
        from IPython import get_ipython
        from IPython.display import Image as IPyImage
        from IPython.display import display
    except ImportError:  # plain Python: nothing to show
        get_ipython = None
    if get_ipython is not None and get_ipython() is not None:
        display(IPyImage(data=_palette_png(fig, INLINE_DPI), format="png"))
    plt.close(fig)


def _subtitle(ax, text: str):
    ax.annotate(
        text,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(0, 4),
        textcoords="offset points",
        color=INK_2,
        fontsize=9,
        va="bottom",
    )


def coverage_chart(cov_year: pd.DataFrame):
    """Share of members with a price, by year (one series)."""
    fig, ax = plt.subplots(figsize=(8, 3.6))
    s = cov_year["priced_share"] * 100
    ax.plot(s.index, s.values, color=SLOTS[0], marker="o", markersize=5)
    ax.set_ylim(0, 105)
    ax.set_ylabel("% of members priced")
    ax.set_title("Members with a price, by year", pad=22)
    _subtitle(ax, "Missing early rows are mostly companies still on the Alpha Vantage list")
    for x in (s.index[0], s.index[-1]):
        ax.annotate(
            f"{s[x]:.0f}%",
            (x, s[x]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            color=INK,
            fontsize=9,
        )
    fig.tight_layout()
    return fig


def beat_rate_chart(by_year: pd.DataFrame):
    """Share of member-months that beat SPY the next month, by year (one series, bars)."""
    fig, ax = plt.subplots(figsize=(8, 3.6))
    s = by_year["beat_rate"] * 100
    ax.bar(s.index, s.values, color=SLOTS[0], width=0.6)
    ax.axhline(50, color=AXIS, linewidth=1)
    ax.set_xticks(list(s.index)[::2])  # whole years (matplotlib would show 2012.5)
    ax.set_ylim(0, 70)
    ax.set_ylabel("% of members beating SPY")
    ax.set_title("How often a member beats SPY the next month", pad=22)
    _subtitle(ax, "Line at 50%. Mostly above it until 2016, mostly below since")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def excess_hist_chart(df: pd.DataFrame, hold: int = 1, clip: float = 0.5):
    """Distribution of next-month excess returns over SPY (one series)."""
    s = df[f"fwd_excess_{hold}m"].dropna().clip(-clip, clip) * 100
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.hist(s, bins=100, color=SLOTS[0], edgecolor=SURFACE, linewidth=0.4)
    ax.axvline(0, color=INK_2, linewidth=1)
    ax.set_xlabel(f"{hold}-month return minus SPY's (%), clipped at ±{clip * 100:.0f}%")
    ax.set_ylabel("member-months")
    ax.set_title("Next-month excess returns are centred just below zero, with long tails", pad=12)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def ic_chart(ic: pd.DataFrame, n: int = 20):
    """Top-n distinct signals by |mean IC|, signed bars (diverging blue / red).

    `ic` should come from eda.distinct_signals, so a signal shared by several columns shows once."""
    top = ic.head(n).iloc[::-1]
    names = [label(i, top.loc[i].get("same_as", ())) for i in top.index]
    colors = [POS if v > 0 else NEG for v in top["ic_mean"]]
    fig, ax = plt.subplots(figsize=(8, 0.28 * n + 1.4))
    ax.barh(names, top["ic_mean"], color=colors, height=0.65)
    ax.axvline(0, color=INK_2, linewidth=1)
    ax.set_xlabel("mean monthly rank correlation with next-month excess return (IC)")
    ax.set_title(f"The {n} features with the strongest signal, 2010–2022", pad=22)
    _subtitle(ax, "Blue: higher value, better next month. Red: higher value, worse")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def ic_stability_chart(by_period: pd.DataFrame):
    """Mean IC per sub-period for a few features (dot plot; periods are 3 categorical series)."""
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(by_period) + 1.6))
    y = range(len(by_period))
    for i, col in enumerate(by_period.columns):
        ax.scatter(
            by_period[col],
            y,
            color=SLOTS[i],
            s=46,
            label=col,
            zorder=3,
            edgecolors=SURFACE,
            linewidths=1.5,
        )
    ax.set_yticks(list(y), [label(i) for i in by_period.index])
    ax.axvline(0, color=INK_2, linewidth=1)
    ax.set_xlabel("mean monthly IC")
    ax.set_title("Does the signal keep its sign over time?", pad=22)
    _subtitle(ax, "Each dot is one sub-period; a feature whose dots straddle zero is unreliable")
    # legend below the axis title, clear of the dots and of the title block
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncols=3,
        borderaxespad=0,
        handletextpad=0.3,
    )
    ax.grid(axis="y", visible=False)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def growth_chart(
    monthly: pd.DataFrame,
    rule_col: str = "top_10",
    rule_label: str = "Top 10 last-month winners",
    title: str = "Preview: buying last month's top 10 vs SPY",
    subtitle: str = "No costs, monthly rebalance; early years still miss most acquired companies",
):
    """Growth of $1: the plain rule vs SPY vs equal-weight members (log scale, direct end labels)."""
    series = {
        rule_label: (monthly[rule_col], SERIES_COLOR["plain rule"]),
        "SPY": (monthly["spy"], SERIES_COLOR["spy"]),
        "Equal-weight members": (monthly["equal_weight"], SERIES_COLOR["equal_weight"]),
    }
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ends = []
    for name, (r, color) in series.items():
        g = (1 + r.fillna(0)).cumprod()
        ax.plot(g.index, g.values, color=color, label=name)
        ends.append((g.iloc[-1], name, g.index[-1]))
    ax.set_yscale("log")
    # End labels, nudged apart in log space so close finishes don't overlap.
    ends.sort()
    placed = []
    for val, name, x in ends:
        y = np.log10(val)
        if placed and y - placed[-1] < 0.08:  # ~20% apart on the log axis, so labels don't touch
            y = placed[-1] + 0.08
        placed.append(y)
        ax.annotate(
            f"${val:.1f}",
            xy=(x, val),
            xytext=(x + pd.Timedelta(days=60), 10**y),
            textcoords="data",
            va="center",
            ha="left",
            color=INK,
            fontsize=9,
        )
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"${v:g}"))
    ax.set_ylabel("growth of $1 (log scale)")
    ax.set_title(title, pad=22)
    _subtitle(ax, subtitle)
    ax.legend(loc="upper left")
    ax.margins(x=0.02)
    fig.tight_layout()
    return fig


def model_cv_chart(best: pd.DataFrame, years: list[int], base_rate: float):
    """Each model's best setting: mean top-10 precision over the CV years, with the worst and best
    single year as a range (one series, so one colour), and the CV base rate as a line."""
    b = best.sort_values("precision")
    cols = [f"precision_{y}" for y in years]
    lo, hi = b[cols].min(axis=1) * 100, b[cols].max(axis=1) * 100
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(b) + 1.6))
    y = range(len(b))
    ax.hlines(y, lo, hi, color=SLOTS[0], linewidth=2, alpha=0.35)
    ax.scatter(b["precision"] * 100, y, color=SLOTS[0], s=46, zorder=3, edgecolors=SURFACE)
    ax.axvline(base_rate * 100, color=INK_2, linewidth=1, linestyle="--")
    ax.annotate(
        "base rate",
        xy=(base_rate * 100, 1),
        xycoords=("data", "axes fraction"),
        xytext=(4, -2),
        textcoords="offset points",
        va="top",
        color=INK_2,
        fontsize=8.5,
    )
    ax.set_yticks(list(y), b["label"])
    ax.set_xlabel("% of each month's top 10 that beat SPY")
    ax.set_title(f"Tuning: each model's best setting, {years[0]}–{years[-1]}", pad=22)
    _subtitle(ax, "Dot: average over the six years. Line: its worst and best single year")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def model_compare_chart(table: pd.DataFrame, period: str, title: str, subtitle: str):
    """Top-10 precision per candidate in one period: models blue, plain rules orange, the
    period's base rate as a line. Values are printed at the bar ends."""
    t = table[table["period"] == period].sort_values("precision")
    is_rule = t["model"].str.startswith("rule_")
    colors = [SLOTS[1] if r else SLOTS[0] for r in is_rule]
    names = [f"{lab} (headline)" if h else lab for lab, h in zip(t["label"], t["headline"])]
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(t) + 1.6))
    ax.barh(names, t["precision"] * 100, color=colors, height=0.62)
    base = t["base_rate"].mean() * 100
    ax.axvline(base, color=INK_2, linewidth=1, linestyle="--")
    for i, v in enumerate(t["precision"] * 100):
        ax.annotate(
            f"{v:.1f}%",
            (v, i),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=INK,
        )
    ax.set_xlim(min(base, (t["precision"] * 100).min()) - 6, (t["precision"] * 100).max() + 5)
    ax.set_xlabel(f"% of each month's top 10 that beat SPY (dashed: base rate {base:.1f}%)")
    ax.set_title(title, pad=22)
    _subtitle(ax, subtitle)
    handles = [
        mpl.patches.Patch(color=SLOTS[0], label="model"),
        mpl.patches.Patch(color=SLOTS[1], label="plain rule"),
    ]
    ax.legend(handles=handles, loc="lower right")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def importance_chart(imp: pd.Series, title: str, n: int = 15, subtitle: str | None = None):
    """The n most important features of a fitted model (one series), as % of the total."""
    top = imp.sort_values(ascending=False).head(n).iloc[::-1] / imp.sum() * 100
    fig, ax = plt.subplots(figsize=(8, 0.3 * n + 1.4))
    ax.barh([label(i) for i in top.index], top.values, color=SLOTS[0], height=0.62)
    ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(decimals=1))
    ax.set_xlabel("share of the model's total importance")
    ax.set_title(title, pad=22 if subtitle else 12)
    if subtitle:
        _subtitle(ax, subtitle)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


VERSION_LABELS = {
    "equal": "equal weight",
    "equal_buffer": "equal weight + buffer",
    "inv_vol": "inverse vol",
    "inv_vol_buffer": "inverse vol + buffer",
}
RULE_STRATEGY_LABELS = {"mom_1m": "Rule: last month's", "mom_6m": "Rule: 6-month"}
BENCHMARK_LABELS = {"spy": "SPY", "equal_weight": "All members, equal weight"}


def strategy_label(name: str, model_labels: dict[str, str], chosen: str | None = None) -> str:
    """'XGBoost, by how much: top 10, inverse vol + buffer' for a `run_strategies` column;
    benchmarks and the chosen grid rule (`chosen_rule`, described by `chosen`) by name."""
    if name in BENCHMARK_LABELS:
        return BENCHMARK_LABELS[name]
    if name == "chosen_rule":
        return f"Chosen rule: {chosen}" if chosen else "Chosen rule"
    p = parse_strategy(name)
    who = RULE_STRATEGY_LABELS.get(p["strategy"]) or model_labels.get(p["strategy"], p["strategy"])
    return f"{who} top {p['top_n']}, {VERSION_LABELS[p['version']]}"


def strategy_value_chart(
    tables: dict[str, pd.DataFrame],
    labels: dict[str, str],
    kinds: dict[str, str],
    title: str,
    subtitle: str,
):
    """What START_DOLLARS became for each strategy, one panel per period (small multiples, same
    rows, ordered by the last panel): models blue, rules orange, the all-members basket aqua,
    SPY's end value as a dashed line in each panel. `labels` and `kinds` ('model', 'rule',
    'benchmark') are keyed by the tables' index; values are printed at the bar ends."""
    names = [n for n in labels if n != "spy"]
    order = list(tables.values())[-1].loc[names, "end_value"].sort_values().index
    color = {"model": SLOTS[0], "rule": SLOTS[1], "benchmark": SLOTS[2]}
    fig, axes = plt.subplots(
        1, len(tables), figsize=(11, 0.42 * len(order) + 1.9), sharey=True, squeeze=False
    )
    for ax, (period, table) in zip(axes[0], tables.items()):
        t = table.loc[order, "end_value"]
        # bars start at the starting amount: length = gain (right) or loss (left)
        ax.barh(
            [labels[n] for n in order],
            t.values - START_DOLLARS,
            left=START_DOLLARS,
            color=[color[kinds[n]] for n in order],
            height=0.62,
        )
        spy = table.loc["spy", "end_value"]
        ax.axvline(spy, color=INK_2, linewidth=1, linestyle="--")
        ax.axvline(START_DOLLARS, color=INK_2, linewidth=1)
        for i, v in enumerate(t.values):
            gain = v >= START_DOLLARS
            ax.annotate(
                f"${v:,.0f}",
                (v, i),
                xytext=(4 if gain else -4, 0),
                textcoords="offset points",
                va="center",
                ha="left" if gain else "right",
                fontsize=8.5,
                color=INK,
            )
        lo, hi = min(START_DOLLARS, t.min()), max(spy, t.max())
        pad = (hi - lo) * 0.2
        ax.set_xlim(lo - (pad if t.min() < START_DOLLARS else pad / 4), hi + pad)
        ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"))
        ax.set_xlabel(f"dashed: SPY, ${spy:,.0f}")
        ax.set_title(period, fontsize=10, pad=6, loc="left")
        ax.grid(axis="y", visible=False)
    handles = [
        mpl.patches.Patch(color=color[k], label=lab)
        for k, lab in [("model", "model"), ("rule", "plain rule"), ("benchmark", "all members")]
    ]
    axes[0][-1].legend(handles=handles, loc="lower right")
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.93, subtitle, ha="left", color=INK_2, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return fig


def paths_chart(
    panels: dict[str, pd.DataFrame],
    lines: dict[str, tuple[str, str]],
    title: str,
    subtitle: str,
    kind: str,
    mark: str | None = None,
):
    """Monthly paths, one panel per period (shared y-axis only for drawdowns and excess).

    `panels`: {period title: DataFrame of monthly values, Period index, one column per line}.
    `lines`: {column: (strategy label, colour)}; a column ending in `_trend` is drawn dashed in
    its strategy's colour. `kind`: 'value' (dollars, log scale), 'drawdown' (% below the peak) or
    'excess' (% vs SPY, zero line). `mark`: a decision date for a vertical line (e.g. the test)."""
    fig, axes = plt.subplots(
        1,
        len(panels),
        figsize=(11 if len(panels) > 1 else 9, 4.6),
        squeeze=False,
        sharey=kind != "value",
    )
    for ax, (period, frame) in zip(axes[0], panels.items()):
        x = frame.index.to_timestamp(how="end").normalize()
        for col in frame:
            label, color = lines[col.removesuffix(TREND)]
            dashed = col.endswith(TREND)
            ax.plot(
                x,
                frame[col].to_numpy(),
                color=color,
                linewidth=1.2 if dashed else 1.8,
                linestyle="--" if dashed else "-",
                label=None if dashed else label,
            )
        years = (x.max() - x.min()).days / 365.25
        if years > 6:  # explicit ticks: the automatic date locator warns on short ranges
            ax.xaxis.set_major_locator(mpl.dates.YearLocator(base=2 if years > 10 else 1))
            ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%Y"))
        else:
            ax.xaxis.set_major_locator(mpl.dates.MonthLocator(bymonth=(1, 7)))
            ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%b %Y"))
        if kind == "value":
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(mpl.ticker.LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
            ax.yaxis.set_major_formatter(
                mpl.ticker.FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k")
            )
            ax.yaxis.set_minor_formatter(mpl.ticker.NullFormatter())
            ax.axhline(START_DOLLARS, color=AXIS, linewidth=1, zorder=0)
        else:
            ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0, decimals=0))
            ax.axhline(0, color=INK_2, linewidth=1, zorder=0)
        if mark:
            m = pd.Period(mark, freq="M").to_timestamp(how="end").normalize()
            if x.min() <= m <= x.max():
                ax.axvline(m, color=AXIS, linewidth=1, linestyle="--", zorder=0)
        ax.set_title(period, fontsize=10, pad=6, loc="left")
        ax.margins(x=0.01)
    handles = [
        mpl.lines.Line2D([], [], color=c, linewidth=1.8, label=lab) for lab, c in lines.values()
    ]
    handles.append(
        mpl.lines.Line2D(
            [],
            [],
            color=INK_2,
            linewidth=1.2,
            linestyle="--",
            label="dashed: with the trend filter",
        )
    )
    # one legend under the panels, so it never covers a line
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), fontsize=8.5, frameon=False)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.905, subtitle, ha="left", color=INK_2, fontsize=9)
    fig.tight_layout(rect=(0, 0.07, 1, 0.9))
    return fig


def exposure_chart(table: pd.DataFrame, names: dict[str, str], title: str, subtitle: str):
    """Average within-month percentile of each exposure among each strategy's picks, one panel
    per period (rows: exposures; one bar per strategy). 50 = the average member (line)."""
    periods = list(dict.fromkeys(table.index.get_level_values("period")))
    fig, axes = plt.subplots(
        1, len(periods), figsize=(11, 0.55 * table.shape[1] + 2.0), sharey=True, squeeze=False
    )
    y = np.arange(table.shape[1])
    h = 0.8 / len(names)
    for ax, period in zip(axes[0], periods):
        for i, (s, label) in enumerate(names.items()):
            v = table.loc[(period, s)].to_numpy()
            ax.barh(
                y + (len(names) - 1 - i) * h - 0.4 + h / 2,
                v,
                height=h * 0.9,
                color=SLOTS[i],
                label=label,
            )
            for yy, vv in zip(y + (len(names) - 1 - i) * h - 0.4 + h / 2, v):
                ax.annotate(
                    f"{vv:.0f}",
                    (vv, yy),
                    xytext=(3, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=8,
                    color=INK,
                )
        ax.axvline(50, color=INK_2, linewidth=1, linestyle="--")
        ax.set_xlim(0, 105)
        ax.set_yticks(y, table.columns)
        ax.invert_yaxis()
        ax.set_xlabel("percentile among that month's members (dashed: the average member)")
        ax.set_title(period, fontsize=10, pad=6, loc="left")
        ax.grid(axis="y", visible=False)
    fig.legend(
        *axes[0][0].get_legend_handles_labels(),
        loc="lower center",
        ncol=len(names),
        fontsize=8.5,
        frameon=False,
    )
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.9, subtitle, ha="left", color=INK_2, fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.88))
    return fig


def lift_chart(tables: dict[str, pd.DataFrame], names: dict[str, str], title: str, subtitle: str):
    """Hit rate minus the base rate, with a 95% margin (±1.96 month-level standard errors), per
    slice and strategy; one panel per period. `tables`: {strategy: slice_table output}."""
    first = next(iter(tables.values()))
    periods = list(dict.fromkeys(first.index.get_level_values(0)))
    slices = list(dict.fromkeys(first.index.get_level_values(1)))
    fig, axes = plt.subplots(
        1,
        len(periods),
        figsize=(11, 0.5 * len(slices) + 2.0),
        sharey=True,
        sharex=True,
        squeeze=False,
    )
    y = np.arange(len(slices))
    off = np.linspace(-0.15, 0.15, len(tables))
    for ax, period in zip(axes[0], periods):
        for i, (s, t) in enumerate(tables.items()):
            sub = t.loc[period].reindex(slices)
            ax.errorbar(
                sub["lift"] * 100,
                y + off[i],
                xerr=1.96 * sub["hit_se"] * 100,
                fmt="o",
                color=SLOTS[i],
                ecolor=SLOTS[i],
                elinewidth=1.2,
                capsize=0,
                markersize=5,
                label=names[s],
            )
        ax.axvline(0, color=INK_2, linewidth=1)
        ax.set_yticks(y, slices)
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(
            mpl.ticker.FuncFormatter(lambda v, _: f"{v:+.0f} pts" if round(v) else "0")
        )
        ax.set_xlabel("share of picks beating SPY minus all members' share (95% margin)")
        ax.set_title(period, fontsize=10, pad=6, loc="left")
        ax.grid(axis="y", visible=False)
    fig.legend(
        *axes[0][0].get_legend_handles_labels(),
        loc="lower center",
        ncol=len(tables),
        fontsize=8.5,
        frameon=False,
    )
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.9, subtitle, ha="left", color=INK_2, fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.88))
    return fig


def cell_label(lookback: str, top_n: int, hold: int) -> str:
    """'Top 5 by 6-month return, held 6 months'."""
    lb = LOOKBACK_LABELS[lookback].replace(" months", "-month").replace(" month", "-month")
    held = f"{hold} month" + ("s" if hold > 1 else "")
    return f"Top {top_n} by {lb} return, held {held}"


def grid_heatmap(table: pd.DataFrame, title: str, subtitle: str):
    """Sharpe ratio minus SPY's for every grid cell: one panel per basket size, look-back down,
    hold across. Diverging blue (better than SPY) / red (worse), gray at zero, values printed."""
    spy = table.loc["spy", "sharpe"]
    cells = table.dropna(subset=["top_n"]).copy()
    cells["diff"] = cells["sharpe"] - spy
    top_ns = sorted(cells["top_n"].unique())
    holds = sorted(cells["hold"].unique())
    lookbacks = [lb for lb in LOOKBACK_LABELS if lb in set(cells["lookback"])]
    lim = max(0.05, float(cells["diff"].abs().max()))
    norm = mpl.colors.TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim)
    fig, axes = plt.subplots(1, len(top_ns), figsize=(9.5, 3.6), sharey=True)
    for ax, n in zip(np.atleast_1d(axes), top_ns):
        grid = cells[cells["top_n"] == n].pivot_table(
            index="lookback", columns="hold", values="diff"
        )
        grid = grid.reindex(index=lookbacks, columns=holds)
        ax.imshow(grid.values, cmap=DIVERGING, norm=norm, aspect="auto")
        for (i, j), v in np.ndenumerate(grid.values):
            dark = abs(v) > 0.6 * lim  # strong cells get light text so the value stays legible
            text = "0.00" if abs(v) < 0.005 else f"{v:+.2f}"  # no "-0.00"
            ax.text(
                j, i, text, ha="center", va="center", fontsize=9, color=SURFACE if dark else INK
            )
        ax.set_xticks(range(len(holds)), [f"{int(h)}" for h in holds])
        ax.set_xlabel("hold (months)")
        ax.set_title(f"Top {int(n)}", fontsize=10, pad=6)
        ax.grid(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_visible(False)
        ax.tick_params(length=0)
    first = np.atleast_1d(axes)[0]
    first.set_yticks(range(len(lookbacks)), [LOOKBACK_LABELS[lb] for lb in lookbacks])
    first.set_ylabel("winner over the past")
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.905, subtitle, ha="left", color=INK_2, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    return fig


def rule_growth_chart(
    rets: pd.Series,
    bench: pd.DataFrame,
    rule_label: str,
    title: str,
    subtitle: str,
    mark: str | None = None,
    mark_label: str = "",
):
    """Growth of $1 for one rule vs SPY vs equal-weight members, months as a Period index
    (log scale, direct end labels, optional vertical marker, e.g. where a selection ends).
    `mark` is a decision date: the line is drawn at that month's end, where the returns of
    decisions from that date on start."""
    monthly = pd.DataFrame(
        {"rule": rets, "spy": bench["spy"], "equal_weight": bench["equal_weight"]}
    ).dropna()
    monthly.index = monthly.index.to_timestamp(how="end").normalize()
    fig = growth_chart(monthly, "rule", rule_label, title, subtitle)
    ax = fig.axes[0]
    if mark:
        x = pd.Period(mark, freq="M").to_timestamp(how="end").normalize()
        ax.axvline(x, color=AXIS, linewidth=1, linestyle="--", zorder=0)
        ax.annotate(
            mark_label,
            xy=(x, 1),
            xycoords=("data", "axes fraction"),
            xytext=(4, -4),
            textcoords="offset points",
            va="top",
            ha="left",
            color=INK_2,
            fontsize=8.5,
        )
    fig.tight_layout()
    return fig
