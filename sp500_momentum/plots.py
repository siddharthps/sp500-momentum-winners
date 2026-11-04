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

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sp500_momentum.config import FIGURES_DIR

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
}


def label(feature: str, same_as=()) -> str:
    """Readable name; unlisted features get their column name with the prefix tidied."""
    name = FEATURE_LABELS.get(feature) or feature.removeprefix("ta_").replace("_", " ")
    return f"{name}  (+{len(same_as)} identical)" if len(same_as) else name


def apply_style():
    mpl.rcParams.update(
        {
            # Inline (notebook) display only; save() writes the book's PNGs at its own, higher dpi.
            "figure.dpi": 80,
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


def save(fig, name: str):
    """Save to reports/figures/<name>.png at a size that keeps notebooks small."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=110, bbox_inches="tight")


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
    (log scale, direct end labels, optional vertical marker, e.g. where a selection ends)."""
    monthly = pd.DataFrame(
        {"rule": rets, "spy": bench["spy"], "equal_weight": bench["equal_weight"]}
    ).dropna()
    monthly.index = monthly.index.to_timestamp(how="end").normalize()
    fig = growth_chart(monthly, "rule", rule_label, title, subtitle)
    ax = fig.axes[0]
    if mark:
        x = pd.Timestamp(mark)
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
