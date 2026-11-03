# sp500-momentum-winners

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>
<a href="https://github.com/siddharthps/sp500-momentum-winners/actions/workflows/ci.yml">
    <img src="https://github.com/siddharthps/sp500-momentum-winners/actions/workflows/ci.yml/badge.svg" alt="CI" />
</a>

**Idea:** at the end of each month, buy the S&P 500 stocks that rose the most, hold them for X months,
and find the best X. The plain rule is the baseline. An ML model ranks all members each month, and the
results are backtested against SPY. The test uses **point-in-time membership** (who was in the index
*on each date*), including companies that were later acquired, failed or dropped, so the results
aren't flattered by survivorship bias.

> Status: data, the monthly table and the features are done; exploratory analysis is next. The
> Alpha Vantage download of delisted companies runs until ~12–14 Nov 2026. Progress is tracked in
> [issues](https://github.com/siddharthps/sp500-momentum-winners/issues), by
> [milestone](https://github.com/siddharthps/sp500-momentum-winners/milestones), and on the
> [project board](https://github.com/users/siddharthps/projects/1).

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
| 3. Daily prices | `uv run python -m sp500_momentum.dataset yahoo-daily` | yfinance: current members, removed members it covers, SPY, sector ETFs, VIX, Dow, gold, WTI (from 2000) | `data/raw/yahoo/` |
| 3b. Macro | `uv run python -m sp500_momentum.dataset fred` | FRED: core CPI, Fed Funds, 1/5/10-year yields, potential GDP (from 2005) | `data/raw/fred/` |
| 4. Delisted prices | `uv run python -m sp500_momentum.dataset av-pull` | Alpha Vantage (free tier, ~23 tickers/day, resumable) | `data/raw/alphavantage/` |
| 5. Monthly table | `uv run python -m sp500_momentum.monthly build` | Steps 1–4 | `data/processed/monthly_panel.parquet` |
| 6. Features | `uv run python -m sp500_momentum.features build` | Step 5 + monthly bars, FRED, `references/removed_sectors.csv` | `data/processed/features.parquet` (147 features in named sets) |
| Progress | `uv run python -m sp500_momentum.dataset av-status` | | |

Step 4 is rerun once a day (and step 5 after it) until the queue is empty (started 2 Nov 2026,
expected to finish ~12–14 Nov). It skips tickers already pulled and stops cleanly when the daily
quota runs out. Removed members whose yfinance data fails step 5's volume check (another security
reused the ticker) are added to its queue automatically.

On Windows, `scripts/register_av_task.ps1` schedules it daily at 21:00 (PC local time) with Task Scheduler.
Each run appends to `logs/av_pull.log`.

Step 3 takes about a minute. It saves one parquet file per ticker (unadjusted OHLC, adjusted close,
volume, dividends, splits), ending at the previous close. Reruns skip tickers already saved, and
`--refresh` downloads everything again. To test the setup without using API calls, run
`scripts/av_pull_daily.ps1 -MaxCalls 0`.

### Rerunning after a change

Each step reads only the outputs of the steps before it:

```
membership ─► coverage ─► yahoo-daily ─┐
                  │                    ├─► monthly build ─► features build ─► models ─► simulation
                  └─► av-pull (daily) ─┘        │
fred ──────────────────────────────────────────┼──────────────► (features build)
                                                └─► yahoo_suspect.csv ─► av-pull queue
```

If something earlier changes, rerun from the first affected step, then everything after it:

| What changed | Rerun from |
|---|---|
| Wikipedia refreshed, or a membership repair in `config.py` (`RENAMES`, `MISSING_ADDS`, `REASON_OVERRIDES`) | `coverage` → `yahoo-daily` → `monthly build` → `features build` → models |
| `PRICE_START`, or price data re-downloaded | `yahoo-daily --refresh` → `monthly build` → … |
| New Alpha Vantage data (every night until ~12–14 Nov) | `monthly build` → `features build` → … |
| Volume threshold (`MIN_MEMBER_DOLLAR_VOLUME`) | `monthly build` (rewrites the suspect list, which changes the AV queue) → … |
| Hold periods, the delisting cutoff or the targets (`monthly.py`) | `monthly build` → … |
| A FRED series or its publication lag (`FRED_SERIES`) | `fred` → `features build` → … |
| Sectors (`references/removed_sectors.csv`, `SECTOR_ETF`) or any feature (`features.py`) | `features build` → … |

Raw files are never edited by hand, so every output can be rebuilt from the downloads.

## Development

```bash
uv sync                        # installs dev tools too (pytest, ruff, pre-commit)
uv run pre-commit install      # once: ruff + safety checks on every commit
uv run pytest                  # tests (offline)
uv run ruff check              # lint
uv run ruff format             # format
```

**Workflow.** Work is tracked as GitHub issues, grouped into milestones (one per phase) and shown on
the project board. Each issue gets its own branch (`<issue>-<short-name>`, e.g. `10-eda`) and is
merged into `main` through a pull request whose description says `Closes #<issue>`. CI (GitHub
Actions: ruff check, ruff format --check, pytest) runs on every push and pull request, and a pull
request is merged only when CI is green.

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
├── references         <- Decision log, brainstorm and dated working journal
├── reports/figures    <- Generated charts
├── scripts            <- Task Scheduler setup and the daily Alpha Vantage run
├── logs               <- Run logs (git-ignored)
├── tests              <- pytest tests (offline, no network)
├── mkdocs.yml         <- Optional website build for docs/
├── .github/workflows  <- CI: lint, formatting and tests on every push and pull request
├── .pre-commit-config.yaml <- Checks run on every commit (ruff, large files, private keys)
└── sp500_momentum     <- Source code
    ├── config.py      <- Paths, study settings, membership repairs, FRED lags
    ├── dataset.py     <- Command-line download steps (see above)
    ├── sources/       <- One module per data source: wikipedia, yahoo, alphavantage, fred
    ├── membership.py  <- Point-in-time membership and repairs to Wikipedia's changes
    ├── monthly.py     <- The monthly member table: prices, past and forward returns
    ├── features.py    <- Features from monthly bars (TA-Lib, risk, ranks, market, macro) and feature sets
    ├── modeling/      <- train.py, predict.py (to do)
    └── plots.py       <- Charts (to do)
```

## Acknowledgements

Built as the final project for the Stock Markets Analytics Zoomcamp 2026 (DataTalksClub).
