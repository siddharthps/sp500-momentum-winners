"""The live dashboard (#40): a Streamlit app on Hugging Face Spaces.

Reads the PUBLIC dataset only (no token, only public data), cached for six hours, so each
monthly run's new picks appear without a redeploy. For a local preview or the tests, point
DASHBOARD_DATA_DIR at a folder holding the same files.

    streamlit run dashboard/app.py
"""

import json
import os
from pathlib import Path

import logic
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

REPO = os.getenv("DASHBOARD_REPO", "siddharthps/sp500-momentum-winners")
FILES = [
    "live_picks.csv",
    "strategy_returns.parquet",
    "live_record.parquet",
    "monitoring.parquet",
    "meta.json",
]
GITHUB = "https://github.com/siddharthps/sp500-momentum-winners"
CHANNEL = "https://t.me/s/sp500_momentum_picks"


@st.cache_data(ttl=6 * 3600, show_spinner="Loading the latest data…")
def load() -> dict:
    local = os.getenv("DASHBOARD_DATA_DIR")
    paths = {}
    for name in FILES:
        if local:
            paths[name] = Path(local) / name
        else:
            from huggingface_hub import hf_hub_download

            paths[name] = Path(hf_hub_download(REPO, name, repo_type="dataset"))
    return {
        "picks": pd.read_csv(paths["live_picks.csv"]),
        "returns": pd.read_parquet(paths["strategy_returns.parquet"]),
        "live": pd.read_parquet(paths["live_record.parquet"]),
        "drift": pd.read_parquet(paths["monitoring.parquet"]),
        "meta": json.loads(Path(paths["meta.json"]).read_text(encoding="utf-8")),
    }


def money(v: float) -> str:
    return f"${v:,.0f}"


def paths_chart(paths: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, (label, colour) in logic.LINES.items():
        if col in paths and paths[col].notna().any():
            fig.add_scatter(
                x=paths.index,
                y=paths[col],
                name=label,
                mode="lines",
                line={"color": colour, "width": 2.2 if col != "spy" else 1.8},
                hovertemplate="%{x}: $%{y:,.0f}<extra>" + label + "</extra>",
            )
    fig.add_hline(y=logic.START_DOLLARS, line={"color": "#c3c2b7", "width": 1})
    fig.update_layout(
        yaxis={
            "type": "log",
            "tickprefix": "$",
            "showtickprefix": "all",
            "tickformat": ",.0f",
            "title": "value of $10,000 (log scale)",
        },
        legend={"orientation": "h", "y": -0.2},
        margin={"t": 10},
        hovermode="x unified",
        height=430,
    )
    return fig


st.set_page_config(page_title="S&P 500 momentum winners", page_icon="📈", layout="wide")
data = load()
meta = data["meta"]

st.title("S&P 500 momentum winners")
st.caption(
    f"Updated {meta['updated']} · latest month-end {meta['latest_decision']} · "
    f"data status: {meta['status']} · [code and book]({GITHUB}) · [Telegram channel]({CHANNEL})"
)
st.warning(
    "Research output, not investment advice. In backtests the model didn't beat the plain "
    "6-month rule, and neither clearly beat SPY per unit of risk."
)

overview, picks_tab, live_tab, backtest_tab, monitor_tab = st.tabs(
    ["Overview", "This month's picks", "Live record", "Backtest", "Model monitoring"]
)

with overview:
    st.markdown(
        f"""
**The idea.** At each month-end, rank the S&P 500's members *as they were on that date* (including
companies later taken over or dropped) and buy the top 10 at the next open. Two ways to rank:
- **{meta["headline"]}**: a model trained to predict how much each stock beats SPY next month;
- **the plain rule**: the 10 members that rose most over the past six months.

**What the backtests found.** The plain rule beat the model in every test. In the untouched test
years it made far more than SPY, but with much more risk, mostly through one market theme; per unit
of risk, nothing chosen in advance clearly beat SPY. The model turned out to be a bet on volatile,
beaten-down stocks.

**What this page shows.** Each month's picks as they're made, the live record once results are in,
the backtest, and checks that the model still sees the kind of market it was trained on.
"""
    )

with picks_tab:
    decision, picks = logic.latest_picks(data["picks"])
    trade = (pd.Timestamp(decision) + pd.offsets.BDay(1)).strftime("%A %d %B %Y")
    st.subheader(f"Picks at the {pd.Timestamp(decision):%d %B %Y} close")
    st.write(f"Buy at the next open ({trade}), equal weight, hold one month.")
    cols = st.columns(2)
    for col, s in zip(cols, ["model", "rule"]):
        t = picks[picks["strategy"] == s][["rank", "ticker", "sector", "score"]]
        col.markdown(f"**{logic.STRATEGY_NAMES[s]}**")
        col.dataframe(t, hide_index=True, width="stretch")
    st.caption(
        "Score: the model's predicted return vs SPY next month; for the rule, the 6-month return."
    )

with live_tab:
    live = data["live"]
    if live.empty:
        st.info(
            "No live results yet. The first picks made before their trade date are the ones at the "
            "30 November 2026 close; their month ends in December, so the first result appears in "
            "early January 2027."
        )
    else:
        st.dataframe(
            logic.live_summary(live).style.format(
                {
                    "average month vs SPY": "{:+.2%}",
                    "picks beating SPY": "{:.0%}",
                    "base rate": "{:.0%}",
                }
            ),
            width="stretch",
        )
        t = live.assign(excess=live["ret"] - live["spy"])
        fig = go.Figure()
        for i, s in enumerate(["model", "rule"]):
            g = t[t["strategy"] == s]
            fig.add_bar(
                x=g["decision"],
                y=g["excess"],
                name=logic.STRATEGY_NAMES[s],
                marker_color=logic.SLOTS[i],
            )
        fig.update_layout(
            yaxis={"tickformat": "+.0%", "title": "month's return minus SPY's"},
            barmode="group",
            height=360,
            margin={"t": 10},
        )
        st.plotly_chart(fig, width="stretch")

with backtest_tab:
    period = st.radio(
        "Period",
        ["Test years (untouched)", "2020–2022 (where the model was chosen)"],
        horizontal=True,
    )
    if period.startswith("Test"):
        w = logic.window(data["returns"], meta["test_from"])
    else:  # 2020-2022: from the validation block's first month to the month before the test
        last = (pd.Period(meta["test_from"], freq="M") - 1).strftime("%Y-%m")
        w = logic.window(data["returns"], meta["validation_from"], last)
    cols = [c for c in logic.LINES if c in w]
    st.plotly_chart(paths_chart(logic.value_paths(w[cols])), width="stretch")
    table = logic.summary(w[cols]).rename(index={k: v[0] for k, v in logic.LINES.items()})
    st.dataframe(
        table.style.format(
            {
                "$10,000 became": money,
                "yearly return": "{:+.1%}",
                "volatility": "{:.1%}",
                "worst fall": "{:.1%}",
                "months": "{:.0f}",
            }
        ),
        width="stretch",
    )
    st.caption(
        "After 10 bps a side. The chosen rule was picked on 2010–2022, so only the test "
        "years are clean for it. Full results and caveats are in the book."
    )

with monitor_tab:
    month, drift = logic.latest_drift(data["drift"], meta["drift_features"])
    st.subheader(f"Input drift, {month}")
    st.write(
        "For the model's ten most important stock-level inputs: how far this month's spread of "
        "values is from the training years' (Population Stability Index). Under 0.1 is stable, "
        "0.1–0.25 a moderate shift, over 0.25 a major one: the model is being asked about a market "
        "unlike the one it learned from."
    )
    fig = go.Figure(
        go.Bar(x=drift["psi"], y=drift["feature"], orientation="h", marker_color=logic.SLOTS[0])
    )
    for x, text in ((0.1, "moderate"), (0.25, "major")):
        fig.add_vline(
            x=x,
            line={"color": "#52514e", "dash": "dash", "width": 1},
            annotation_text=text,
            annotation_position="top",
        )
    fig.update_layout(
        yaxis={"autorange": "reversed", "automargin": True},
        xaxis={"title": "PSI vs 2010–2022"},
        height=400,
        margin={"t": 30, "l": 10},
    )
    st.plotly_chart(fig, width="stretch")
    if not data["live"].empty:
        st.subheader("Live hit rate vs base rate")
        st.dataframe(logic.live_summary(data["live"]), width="stretch")
    else:
        st.caption(
            "The live hit rate appears here once the first live month is over (January 2027)."
        )
