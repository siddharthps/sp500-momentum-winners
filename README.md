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

> Status: data, the monthly table, the features, the exploratory analysis, the baseline rule grid
> and the models (setup, tuning, comparison, one test) and their trading simulations are done;
> equity curves, risk over time, the SPY trend filter and the diagnosis of the picks are done too.
> The monthly run (next month's picks) is scheduled; notifications, a live dashboard and a cloud run
> are next. The
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
| 5. Monthly table | `uv run python -m sp500_momentum.monthly build` | Steps 1–4 | `data/processed/monthly_panel.parquet`, plus every price series in `data/interim/monthly_prices.parquet` (for backtests) |
| 6. Features | `uv run python -m sp500_momentum.features build` | Step 5 + monthly bars, FRED, `references/removed_sectors.csv` | `data/processed/features.parquet` (152 features in named sets) |
| 7. Models | `uv run python -m sp500_momentum.modeling.train run` | Step 6 | `reports/model_cv_results.csv`, `reports/model_comparison.csv`, `data/processed/model_scores.parquet`, `models/` (~1¾ h; `--n-iter 1` for a quick smoke run) |
| 8. Monthly run | `uv run python -m sp500_momentum.modeling.predict run` | Steps 1–3 (current members only), 5–6, the step 7 settings | `reports/picks/picks_<YYYY-MM>.csv` (the headline model's and the 6-month rule's top 10), `data/processed/live_picks.csv` (every pick so far), `models/live_headline.joblib` (~2 min; `--no-download` rebuilds from the files on disk; `--force` redoes a month) |
| Progress | `uv run python -m sp500_momentum.dataset av-status` | | |

Step 4 is rerun once a day (and step 5 after it) until the queue is empty (started 2 Nov 2026,
expected to finish ~12–14 Nov). It skips tickers already pulled and stops cleanly when the daily
quota runs out. Removed members whose yfinance data fails step 5's volume check (another security
reused the ticker) are added to its queue automatically.

On Windows, `scripts/register_av_task.ps1` schedules it daily at 21:00 (PC local time) with Task Scheduler.
Each run appends to `logs/av_pull.log`.

**Step 8, the monthly run,** is scheduled by `scripts/register_monthly_task.ps1` (task
`sp500-momentum-monthly-run`). It starts at 07:00 every day, but only does anything on a weekday when
last month's picks don't exist yet: in practice the first weekday of each month, with catch-up if
the PC was off. Each run appends to `logs/monthly_run.log`, and `scripts/monthly_run.ps1 -Force`
runs it by hand. It re-downloads the full history of today's members and the benchmarks (the
adjusted close is recomputed after every dividend, so appending new days would mix two adjustments).
It refits the headline model with its tuned settings (never re-tuned), and **stops without writing
anything** when:
- the latest month-end isn't the month's last trading day;
- SPY or more than 5% of members lack a price;
- a member has no sector (add it to `references/removed_sectors.csv`);
- the feature columns differ from the tuned model's.

The picks are a research output, not advice.

### Telegram notifications (optional)

The monthly picks go to a public channel,
[t.me/s/sp500_momentum_picks](https://t.me/s/sp500_momentum_picks) (readable in a browser, no
account needed; the first real post is on 1 Dec 2026). Failure alerts and the nightly Alpha Vantage summary go
to a private chat. Without these settings, every message is only logged, and nothing fails.

1. In Telegram, message **@BotFather**, send `/newbot`, and copy the **token** it gives you.
2. Send your new bot any message (this opens your private chat with it).
3. Create a **public channel**, add the bot as an **administrator** (so it can post), and post
   anything in it once.
4. Put the token in `.env`, run `uv run python -m sp500_momentum.notify find-chats` to list the chat
   IDs, and add them:

```
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHANNEL_ID=@your_channel_name
TELEGRAM_CHAT_ID=your_private_chat_id
```

5. Check with `uv run python -m sp500_momentum.notify test`; `--dry-run` prints instead of sending.

A failed message never fails the run that sends it, and the token is never logged. The monthly run's
`--dry-run-notify` prints its messages instead of sending them.

Step 3 takes about a minute. It saves one parquet file per ticker (unadjusted OHLC, adjusted close,
volume, dividends, splits), ending at the previous close. Reruns skip tickers already saved, and
`--refresh` downloads everything again. To test the setup without using API calls, run
`scripts/av_pull_daily.ps1 -MaxCalls 0`. That also records any downloaded file the manifest is
missing, for example after a run was killed (each ticker is recorded as soon as it's fetched).

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
| The rule grid, the strategy versions or their costs (`RULE_LOOKBACKS`, `RULE_TOP_NS`, `COST_PER_SIDE`, `RULE_CHECK_FROM`, `START_DOLLARS`, `BUFFER_MULTIPLE`, `INVERSE_VOL_FEATURE`, `TREND_MONTHS`, `backtest.py`, `diagnostics.py`) | `run_notebooks run 04`, `run 05` and `run 06` |
| The model setup or the models (`modeling/prep.py`, `models.py`, `evaluate.py`, `train.py`), or anything that changes the features | `modeling.train run` → `run_notebooks run` |
| Anything above, or the analysis or charts (`eda.py`, `plots.py`) | … → `run_notebooks run` (refreshes the notebooks and `reports/figures/`) |

Raw files are never edited by hand, so every output can be rebuilt from the downloads.

## Notebooks

The notebooks show each step's results. They call the package's functions and hold no logic of their
own. They're committed **with their outputs**, so the tables and charts can be read on GitHub without
the data:

| Notebook | What it shows |
|---|---|
| [`01_data`](notebooks/01_data.ipynb) | Membership, the survivorship gap, the Alpha Vantage progress, prices, FRED, the monthly table and the feature sets |
| [`02_features_eda`](notebooks/02_features_eda.ipynb) | The target, each feature's signal (2010–2022 only), its stability, duplicates, market regimes, and a preview of the plain rule |
| [`03_models`](notebooks/03_models.ipynb) | The folds, each model's tuned setting (2014–19), the comparison on 2020–22 where the headline is chosen, the single test (2023 on), the model rule columns and what the headline looks at. Reads the training step's outputs |
| [`04_simulation`](notebooks/04_simulation.ipynb) | Backtests. Part 1: the baseline grid (60 rules: look-back × top N × hold, staggered, 10 bps a side) vs SPY and equal weight, and the best rule chosen on decisions 2010–2022 and followed through the test years (decisions from 2023). Part 2: the models traded (1-month hold; equal or inverse-vol weights, with or without a 2N hold buffer) vs SPY and the rules, in dollars from $10,000, for 2020–2022 and the test years. Takes about two minutes |
| [`05_risk`](notebooks/05_risk.ipynb) | The paths: $10,000 month by month, falls from the peak, and rolling 12-month returns minus SPY's, for 2020–2022 and the test years, plus the rules from 2010. The SPY trend filter (out of the market when SPY is below its 10-month average, cash at the Fed Funds rate) applied to every strategy, with its average effect. Takes about two minutes |
| [`06_diagnostics`](notebooks/06_diagnostics.ipynb) | Why the headline model loses: what each strategy buys (volatility, beta, size, past returns as within-month percentiles), hit rates by market regime, sector and year with month-level margins of error, the worst picks, and hypotheses for future work. Descriptive only |

They're only ever run by this command, top to bottom in a fresh kernel, so the stored outputs always
match the code. They show summaries, never raw tables (full results are saved under `reports/`).
After running, the command checks every output and **fails** if:
- a cell prints more than 50 lines;
- anything was written to stderr (logs, progress bars, warnings);
- an output contains a local path, an e-mail address or the API key;
- a notebook is over 300 KB.

Charts are written to `reports/figures/`:

```bash
uv run python -m sp500_momentum.run_notebooks run        # all notebooks (after features build)
uv run python -m sp500_momentum.run_notebooks run 02     # just 02_features_eda
```

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
Actions: ruff check, ruff format --check, pytest) runs on every push and pull request. `main` is
protected: changes arrive only through pull requests, CI must pass, merges are squashed, and force-pushes
or deleting `main` are blocked.

## Project organization

```
├── docs               <- The project book: one chapter per step (MkDocs-ready)
├── data
│   ├── external       <- Data from third-party sources
│   ├── interim        <- Intermediate data (e.g. yfinance coverage of removed members)
│   ├── processed      <- Final modelling tables
│   └── raw            <- Downloads, one folder per source (never edited by hand)
├── models             <- Trained models and predictions
├── notebooks          <- 01_data, 02_features_eda, 03_models, 04_simulation, 05_risk, 06_diagnostics (executed, with outputs); later 00_run_all
├── references         <- Decision log, brainstorm and dated working journal
├── reports/figures    <- Generated charts (reports/picks: the monthly picks)
├── scripts            <- Task Scheduler setup: the daily Alpha Vantage run and the monthly run
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
    ├── eda.py         <- Exploratory analysis: summary tables, IC, stability, plain-rule preview
    ├── backtest.py    <- `pred*` rule columns, staggered-portfolio simulation with costs, the rule grid,
    │                     strategy versions (weighting, buffer, trend filter), dollar paths
    ├── diagnostics.py <- What the picks look like and where they win or lose (month-level margins)
    ├── plots.py       <- Chart style (validated palette) and the charts
    ├── run_notebooks.py <- Executes the notebooks in a fresh kernel and checks their outputs
    ├── nb.py          <- Notebook setup (output caps, quiet logs, chart style) and the output rules
    └── modeling/      <- prep.py: feature matrix, targets, time blocks with gaps, CV folds,
                          in-fold preparation; models.py: the candidates and search ranges;
                          evaluate.py: top-10 scoring; train.py: tuning, comparison, the test;
                          predict.py: the monthly run (fresh data, checks, refit, picks)
```

## Acknowledgements

Built as the final project for the Stock Markets Analytics Zoomcamp 2026 (DataTalksClub).
