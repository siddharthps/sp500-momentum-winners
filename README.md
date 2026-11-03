# sp500-momentum-winners

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

Final project for the Stock Markets Analytics Zoomcamp 2026.

**Idea:** at the end of each month, buy the S&P 500 stocks that rose the most, hold them for X months,
and find the best X. The plain rule is the baseline. An ML model ranks all members each month, and the
results are backtested against SPY. The test uses **point-in-time membership** (who was in the index
*on each date*), including companies that were later acquired, failed or dropped, so the results
aren't flattered by survivorship bias.

> Status: data collection in progress. See [references/decisions.md](references/decisions.md).

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
| 3. Delisted prices | `uv run python -m sp500_momentum.dataset av-pull` | Alpha Vantage (free tier, ~23 tickers/day, resumable) | `data/raw/alphavantage/` |
| Progress | `uv run python -m sp500_momentum.dataset av-status` | | |

Step 3 is rerun once a day until the queue is empty (~9 days for members removed since 2010).
It skips tickers already pulled and stops cleanly when the daily quota runs out.

## Development

```bash
uv run pytest          # tests
uv run ruff check      # lint
uv run ruff format     # format
```

## Project organization

```
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
