# sp500-momentum-winners

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

**Idea:** at the end of each month, buy the S&P 500 stocks that rose the most, hold them for X months,
and find the best X. The plain rule is the baseline. An ML model ranks all members each month, and the
results are backtested against SPY. The test uses **point-in-time membership** (who was in the index
*on each date*), including companies that were later acquired, failed or dropped, so the results
aren't flattered by survivorship bias.

> Status: data collection and the monthly table are done; features are next. The Alpha Vantage
> download of delisted companies runs until ~12–14 Nov 2026.

**The project book:** [docs/](docs/index.md) explains each step as a chapter (problem, data
collection, the monthly table, features, modelling, results, automation). Decisions are in
[references/decisions.md](references/decisions.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
```

Copy your Alpha Vantage key into `.env` (git-ignored):

```
ALPHAVANTAGE_API_KEY=your_key_here
```

## Data pipeline

| Step | Command | Source | Output |
|---|---|---|---|
| 1. Membership | `uv run python -m sp500_momentum.dataset membership` | Wikipedia: current list + "Historical components of the S&P 500" | `data/raw/wikipedia/` |
| 2. Coverage | `uv run python -m sp500_momentum.dataset coverage` | yfinance | `data/interim/removed_coverage.csv` |
| 3. Daily prices | `uv run python -m sp500_momentum.dataset yahoo-daily` | yfinance: current members, removed members it covers, SPY, sector ETFs, VIX (from 2007) | `data/raw/yahoo/` |
| 3b. Macro | `uv run python -m sp500_momentum.dataset fred` | FRED: core CPI, Fed Funds, 1/5/10-year yields, potential GDP (from 2005) | `data/raw/fred/` |
| 4. Delisted prices | `uv run python -m sp500_momentum.dataset av-pull` | Alpha Vantage (free tier, ~23 tickers/day, resumable) | `data/raw/alphavantage/` |
| 5. Monthly table | `uv run python -m sp500_momentum.monthly build` | Steps 1–4 | `data/processed/monthly_panel.parquet` |
| Progress | `uv run python -m sp500_momentum.dataset av-status` | | |

Step 4 is rerun once a day (and step 5 after it) until the queue is empty (~9 days for members removed since 2010).
It skips tickers already pulled and stops cleanly when the daily quota runs out.

On Windows, `scripts/register_av_task.ps1` schedules it daily at 21:00 (PC local time) with Task Scheduler.
Each run appends to `logs/av_pull.log`.

Step 3 takes about a minute. It saves one parquet file per ticker (unadjusted OHLC, adjusted close,
volume, dividends, splits), ending at the previous close. Reruns skip tickers already saved, and
`--refresh` downloads everything again. To test the setup without using API calls, run
`scripts/av_pull_daily.ps1 -MaxCalls 0`.

## Development

```bash
uv run pytest          # tests
uv run ruff check      # lint
uv run ruff format     # format
```

## Project organization

```
├── docs               <- The project book: one chapter per step (MkDocs-ready)
├── data
│   ├── external       <- Data from third-party sources
│   ├── interim        <- Intermediate data (e.g. yfinance coverage of removed members)
│   ├── processed      <- Final modelling tables
│   └── raw            <- Downloads, one folder per source (never edited by hand)
├── models             <- Trained models and predictions
├── notebooks          <- Exploration and the orchestrating notebook
├── references         <- Decisions, data dictionary, notes
├── reports/figures    <- Generated charts
├── tests              <- pytest tests (offline, no network)
└── sp500_momentum     <- Source code
    ├── config.py      <- Paths and study settings (start date, API budget)
    ├── dataset.py     <- Command-line data steps (see above)
    ├── sources/       <- One module per data source: wikipedia, yahoo, alphavantage
    ├── features.py    <- Monthly feature table (to do)
    ├── modeling/      <- train.py, predict.py (to do)
    └── plots.py       <- Charts (to do)
```

## Acknowledgements

Built as the final project for the Stock Markets Analytics Zoomcamp 2026 (DataTalksClub).
