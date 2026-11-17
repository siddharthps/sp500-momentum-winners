# Running the project

Everything needed to reproduce the project: setup, every pipeline step and command, the monthly
run in the cloud, the data snapshots, Docker, the dashboard, notifications, what to rerun after a
change, the notebooks, development and the project's folders. The book's chapters explain *why*
each step exists; this page says *how* to run it.

**Contents:** [Setup](#setup) · [Data pipeline](#data-pipeline) ·
[The monthly run in the cloud](#the-monthly-run-in-the-cloud) ·
[Data snapshots](#data-snapshots-on-hugging-face) · [Docker](#docker) ·
[Live dashboard](#live-dashboard) · [Telegram notifications](#telegram-notifications-optional) ·
[Rerunning after a change](#rerunning-after-a-change) · [Notebooks](#notebooks) ·
[Development](#development) · [Project organization](#project-organization)

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
```

Settings go in `.env` (git-ignored), one `NAME=value` per line:

| Setting in `.env` | Needed for | Without it |
| --- | --- | --- |
| `ALPHAVANTAGE_API_KEY` | Step 4 (`av-pull`) only | Not needed with the private snapshot |
| `FRED_API_KEY` ([request it](https://fredaccount.stlouisfed.org/apikeys) after logging in) | Step 3b: potential GDP's published versions (one API request; the other FRED series use the keyless CSV endpoint) | `dataset fred` saves the other six series, then stops with an error |
| `HF_USER`, `HF_TOKEN` | The [data snapshots](#data-snapshots-on-hugging-face) | `hub` commands and `--from-file` stop |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_CHAT_ID` | [Notifications](#telegram-notifications-optional) | Messages are only logged |

## Data pipeline

| Step | Command | Reads | Writes |
| --- | --- | --- | --- |
| 1. Membership | `uv run python -m sp500_momentum.dataset membership` | Wikipedia: current list + "Historical components of the S&P 500" | `data/raw/wikipedia/` |
| 2. Coverage | `uv run python -m sp500_momentum.dataset coverage` | yfinance | `data/interim/removed_coverage.csv` |
| 3. Daily prices | `uv run python -m sp500_momentum.dataset yahoo-daily` | yfinance: current members, removed members it covers, SPY, sector ETFs, VIX, Dow, gold, WTI (from 2000) | `data/raw/yahoo/` |
| 3b. Macro | `uv run python -m sp500_momentum.dataset fred` | FRED: core CPI, Fed Funds, 1/5/10-year yields, potential GDP (from 2005), plus every published version of potential GDP (one API request, `FRED_API_KEY`) | `data/raw/fred/` (`GDPPOT_vintages.csv` for the versions) |
| 4. Delisted prices | `uv run python -m sp500_momentum.dataset av-pull` | Alpha Vantage (free tier, ~23 tickers/day, resumable) | `data/raw/alphavantage/` |
| 5. Monthly table | `uv run python -m sp500_momentum.monthly build` | Steps 1–4 | `data/processed/monthly_panel.parquet`; every price series in `data/interim/monthly_prices.parquet` (for backtests); the wrong-security lists `data/interim/yahoo_suspect.csv` and `av_suspect.csv` |
| 6. Features | `uv run python -m sp500_momentum.features build` | Step 5 + monthly bars, FRED, `references/removed_sectors.csv` | `data/processed/features.parquet` (147 features in named sets) |
| 7. Models | `uv run python -m sp500_momentum.modeling.train run` | Step 6 | `reports/model_cv_results.csv`, `reports/model_comparison.csv`, `data/processed/model_scores.parquet`, `models/` (~1¾ h) |
| 8. Monthly run | `uv run python -m sp500_momentum.modeling.predict run` | Steps 1, 2, 3 (today's members and benchmarks only: `--active-only`), 3b, 5–6, the step 7 settings | `reports/picks/picks_<YYYY-MM>.csv` (the headline model's and the 6-month rule's top 10), `data/processed/live_picks.csv` (every pick so far), `models/live_headline.joblib` (~2 min) |
| Is the monthly run due? | `uv run python -m sp500_momentum.modeling.predict due` | The running record (from the private snapshot) | Prints `due=true` or `due=false` |
| Everything (5–7, notebooks, snapshots) | `uv run python -m sp500_momentum.pipeline rebuild-all [--tag <name>]` | The data on disk | The final rebuild, timed and stopping at the first failure (~2 h with retraining) |
| Alpha Vantage progress | `uv run python -m sp500_momentum.dataset av-status` | The queue and the manifest | Tried, left, days to go |

Their options:

| Command | Option | What it does |
| --- | --- | --- |
| `dataset yahoo-daily` | `--refresh` | Downloads every ticker again (by default, tickers already saved are skipped) |
| | `--active-only` | Downloads today's members and the benchmarks again, in full; removed members' files stay (the monthly run uses it) |
| `dataset av-pull` | `--max-calls N` | At most N calls (default 23); `0` makes no calls |
| `modeling.train run` | `--n-iter 1` | One try per model: a quick smoke run |
| | `--models tree,logreg` | Only these models |
| `modeling.predict run` | `--no-download` | Rebuilds from the files on disk |
| | `--force` | Redoes a month already done |
| | `--from-file` | Starts from the private snapshot (with `--no-download`: no sources at all) |
| | `--dry-run-notify` | Prints the Telegram messages instead of sending them |
| | `--no-publish` | Skips the upload to both Hugging Face datasets |
| `modeling.predict due` | `--no-from-hub` | Reads the local running record instead |
| `pipeline rebuild-all` | `--tag X` | Tags the published snapshots (optional) |
| | `--no-retrain`, `--no-notebooks`, `--no-publish` | Skips the model search, the notebooks or the upload |
| | `--dry-run` | Lists the steps and the checks to do by hand |
| `hub push` | `--target` (`private`, `public` or `both`), `--tag X`, `--status` | Which dataset, a tag, the status shown on the card |
| `hub pull` | `--revision X` | A tag or commit (default: the latest) |
| `notify test` | `--dry-run` | Prints instead of sending |
| `run_notebooks run` | `[prefix]` | Only the notebooks whose name starts with it |

**Step 3** takes about a minute and saves one parquet file per ticker (unadjusted OHLC, adjusted
close, volume, dividends, splits), ending at the previous close.

**Step 4** ran once a day until the queue was empty (2–13 Nov 2026; 216 tickers); the daily task
was unregistered on 16 Nov. If a ticker ever joins the queue, run `av-pull` by hand: it skips
tickers already pulled, stops cleanly when the daily quota runs out, and records each ticker as
soon as it's fetched. `av-pull --max-calls 0` makes no calls: it shows the progress and records any
downloaded file the manifest is missing (for example after a run was killed). After new files
arrive, rerun step 5.

Step 5 checks each series' trading volume:

- a removed member whose Yahoo series fails (another security reused the ticker) joins the Alpha
    Vantage queue automatically (`data/interim/yahoo_suspect.csv`);
- an Alpha Vantage series that fails and still trades more than 95 days after a takeover is
    dropped as another security (`data/interim/av_suspect.csv`), and isn't queued again.

The retired scheduler, for reference: `scripts/register_av_task.ps1` registered the task
`sp500-momentum-av-pull` (21:00 PC time daily, appending to `logs/av_pull.log`).

**Step 8, the monthly run,** runs in the cloud (see
[The monthly run in the cloud](#the-monthly-run-in-the-cloud)): a Cloudflare Worker starts
[`monthly.yml`](../.github/workflows/monthly.yml) at 03:17 UTC every day, with GitHub's own schedule
at 04:17 UTC on weekdays as a backup. Each run asks `predict due` whether last month's picks are in
the running record, and runs `predict run --from-file` only if they aren't.

It downloads the full history of today's members and the benchmarks again (the adjusted close is
recomputed after every dividend, so appending new days would mix two adjustments), then refits the
headline model with its tuned settings (never re-tuned). It **makes no picks, publishes nothing and
alerts the private chat** when:

- the latest month-end is in a month that isn't over, or isn't the month's last trading day;
- SPY, or more than 5% of members, lack a month-end price;
- a member has no sector (add it to `references/removed_sectors.csv`);
- the feature columns differ from the tuned model's.

What it downloaded and rebuilt stays on disk. A month already in the record is skipped unless
`--force`.

**On a PC instead** (retired on 11 Nov 2026): `scripts/register_monthly_task.ps1` registers the
Task Scheduler task `sp500-momentum-monthly-run` (07:00 PC time daily, logging to
`logs/monthly_run.log`), and `scripts/monthly_run.ps1 -Force` runs it by hand. **Never run both:**
the PC script decides "done" from its own picks file, so it can't see a cloud run, and both would
post the picks.

The picks are a research output, not advice.

## The monthly run in the cloud

[`monthly.yml`](../.github/workflows/monthly.yml) runs on GitHub's servers, so the live record
doesn't depend on a PC being on. Two triggers start it, because GitHub's own schedule can run
hours late or be dropped under load (its docs; ~7 h late on 12–13 Nov 2026):

- **A Cloudflare Worker** ([`cloudflare/`](../cloudflare/wrangler.toml)) at 03:17 UTC every day:
  it re-enables the workflow (GitHub disables scheduled workflows in a public repository after 60
  days without repository activity) and dispatches it with `dry_run=false` and `respect_due=true`.
- **GitHub's schedule** at 04:17 UTC on weekdays, as a backup. Runs go one at a time, so whichever
  runs second finds the month done, or tries again if the first failed.

Each run:

1. `predict due` downloads only the running record (`data/processed/live_picks.csv`) from the
   private snapshot and prints `due=true` if last month's picks aren't in it (weekdays, by the
   runner's UTC clock).
2. If due: `predict run --from-file` pulls the private snapshot, downloads fresh data (Wikipedia,
   Yahoo with paced retries, FRED with retries), rebuilds, checks, makes the picks, posts them to
   Telegram and pushes both Hugging Face datasets. Nothing is committed to the repository.
3. The month's picks are kept as a run artifact for 90 days; a failed scheduled or
   Worker-triggered run alerts the private Telegram chat. A failure of the Worker itself (an
   expired token) shows only in its Cloudflare logs; GitHub's backup still runs.
4. A run after the next open (a missed night caught up later) still records its picks, but they're
   left out of the live result.

**Secrets.** GitHub (repository → Settings → Secrets and variables → Actions): `HF_USER`,
`HF_TOKEN` (write), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_CHAT_ID` and
`FRED_API_KEY` (without it the download step fails: no picks are posted, and the failure alert
still goes out). Cloudflare (the Worker): `GITHUB_TOKEN`, a fine-grained token for this repository
only, with Actions read and write, expiring 16 Nov 2027. No Alpha Vantage key is needed: the
delisted companies' prices come with the snapshot.

**The Worker** (Node, with wrangler pinned in `cloudflare/package.json`):

```bash
cd cloudflare
npm ci                                   # the pinned wrangler
npm test                                 # the Worker's offline tests
npx wrangler login                       # once, in a browser
npx wrangler deploy                      # publishes the Worker and its daily trigger
npx wrangler secret put GITHUB_TOKEN     # then the token (the Worker must exist first)
```

On a new Cloudflare account, the first deploy can't attach the daily trigger ("You need a
workers.dev subdomain"): open **Workers & Pages** in the Cloudflare dashboard once, then deploy
again. The Worker itself stays private (`workers_dev = false`). If its token lapses, GitHub's backup
schedule still starts the run, but less reliably on time, and only until GitHub switches scheduled
workflows off after 60 days without repository activity.

**By hand** (Actions tab → Monthly run → Run workflow, or the command line). A manual run is a dry
run by default (messages printed, nothing published); `force` redoes last month's picks:

```bash
gh workflow run monthly.yml -f dry_run=true -f force=true   # a full test that changes nothing
gh run watch                                                 # follow it
```

## Data snapshots on Hugging Face

Two datasets, because Yahoo Finance and Alpha Vantage prices are licensed and their terms forbid
redistribution:

| Dataset | Access | Contents |
| --- | --- | --- |
| [`sp500-momentum-data`](https://huggingface.co/datasets/siddharthps/sp500-momentum-data) | **private** (by token) | Everything: raw downloads, interim and processed tables, trained models. Used by `--from-file` and the cloud run |
| [`sp500-momentum-winners`](https://huggingface.co/datasets/siddharthps/sp500-momentum-winners) | **public** | What this project computed: features and the member table **without raw price columns**, model scores, the live picks, result tables, with a card naming every source. The dashboard reads this one |

```bash
# upload (refuses if a secret from .env is in any file)
uv run python -m sp500_momentum.hub push --target both
# the private snapshot -> data/, models/ (the latest version)
uv run python -m sp500_momentum.hub pull
# the data this book reports
uv run python -m sp500_momentum.hub pull --revision final-2026-11b
# a full try from the snapshot: no sources, nothing sent or published
uv run python -m sp500_momentum.modeling.predict run --from-file --no-download \
    --dry-run-notify --no-publish
```

Settings in `.env`: `HF_USER` (the account) and `HF_TOKEN` (a write token). Without
`--dry-run-notify` and `--no-publish`, `predict run` is a real monthly run: it posts the picks and
uploads both datasets, so never run it alongside the cloud one.

The data this book reports is tagged `final-2026-11b` (`final-2026-11` is the earlier rebuild,
before two data fixes); the latest version moves with each monthly upload. With access to the
private snapshot, `hub pull` replaces steps 1–4 (with 3b) and 7, so `monthly build` onwards runs
without any download or API key (the tuned settings in `reports/` are in the repository). Without
it, the public tables are enough to follow the analysis. Prices can be rebuilt with your own access
through steps 1–4.

## Docker

The [`Dockerfile`](../Dockerfile) builds the pipeline from uv's lock file (Python 3.12, TA-Lib from
its prebuilt wheel). It holds no data, models or secrets: mount them, or pull the private snapshot
with a token at run time. The Docker workflow (not a required check) builds it and runs the tests
inside it on every pull request that can change it (the build, the dependencies, the code, tests,
notebooks, or the files the pipeline reads; docs-only changes skip it). Each such merge to `main`
publishes it to GitHub Container Registry.

```bash
# the image (or build it: docker build -t sp500-momentum .)
docker pull ghcr.io/siddharthps/sp500-momentum-winners:latest
# the final rebuild's steps (dry run)
docker run --rm ghcr.io/siddharthps/sp500-momentum-winners
# the monthly run on your mounted data, sending and publishing nothing
docker run --rm --env-file .env -v "$PWD/data:/app/data" -v "$PWD/models:/app/models" \
    -v "$PWD/reports:/app/reports" ghcr.io/siddharthps/sp500-momentum-winners \
    sp500_momentum.modeling.predict run --dry-run-notify --no-publish
```

Any project module runs as `docker run <image> <module> [args]`. Without `--dry-run-notify` and
`--no-publish`, the monthly run above would be a real one (never alongside the cloud one). The image
is about 2.9 GB, mostly the scientific stack. A vulnerability scan (Trivy) reports high and
critical findings in the build log. The base image's Debian packages are updated at build time, so
most of what remains has no fix published yet.

## Live dashboard

**[sp500-momentum-winners.streamlit.app](https://sp500-momentum-winners.streamlit.app/)**: a
Streamlit app ([`dashboard/`](../dashboard/README.md)), hosted free on Streamlit Community Cloud
from this repository's `main` branch. It may take ~30 s to wake if nobody has visited for a while.
It has five tabs: the overview, this month's picks, the live record, the backtest, and model
monitoring (input drift). It reads only the public dataset, so it holds no token. It rereads the
public dataset every six hours, so a new month shows within six hours.
`uv run streamlit run dashboard/app.py` runs it locally.

## Telegram notifications (optional)

The monthly picks go to a public channel,
[t.me/s/sp500_momentum_picks](https://t.me/s/sp500_momentum_picks) (readable in a browser, no
account needed; the first real post is on 1 Dec 2026). Failure alerts and the Alpha Vantage summary
after each `av-pull` go to a private chat. Without these settings, every message is only logged,
and nothing fails.

1. In Telegram, message **@BotFather**, send `/newbot`, and copy the **token** it gives you.
2. Send your new bot any message (this opens your private chat with it).
3. Create a **public channel**, add the bot as an **administrator** (so it can post), and post
   anything in it once.
4. Put the token in `.env`, run `uv run python -m sp500_momentum.notify find-chats` to list the chat
   IDs, and add them:

    ```text
    TELEGRAM_BOT_TOKEN=123456:ABC...
    TELEGRAM_CHANNEL_ID=@your_channel_name
    TELEGRAM_CHAT_ID=your_private_chat_id
    ```

5. Check with `uv run python -m sp500_momentum.notify test`; `--dry-run` prints instead of sending.

A failed message never fails the run that sends it, and the token is never logged. The monthly run's
`--dry-run-notify` prints its messages instead of sending them.

## Rerunning after a change

Each step reads only the outputs of the steps before it:

```text
membership ─► coverage ─► yahoo-daily ─┐
                  │                    ├─► monthly build ─► features build ─► models ─► notebooks
                  └─► av-pull (by hand)┘        │                                           │
fred ──────────────────────────────────────────┼──────────────► (features build)        hub push
                                                ├─► yahoo_suspect.csv ─► av-pull queue
                                                └─► av_suspect.csv (Alpha Vantage series dropped)
```

If something earlier changes, rerun from the first affected step, then everything after it:

| What changed | Rerun from |
| --- | --- |
| Wikipedia refreshed (`membership`) | `coverage` → `yahoo-daily` → `av-pull` (if the queue grew) → `monthly build` → … |
| A removal reason (`REASON_OVERRIDES`) | `coverage` → `av-pull` (if the queue grew) → `monthly build` → … |
| A rename or missing addition (`RENAMES`, `MISSING_ADDS`) | `monthly build` → … |
| A price override for a takeover where the buyer kept the ticker (`PRICE_OVERRIDES`) | `monthly build` → … |
| `PRICE_START`, or price data re-downloaded | `yahoo-daily --refresh` → `monthly build` → … |
| New Alpha Vantage data (`av-pull`) | `monthly build` → `features build` → … |
| Volume threshold (`MIN_MEMBER_DOLLAR_VOLUME`) | `monthly build` (rewrites the suspect list, which changes the AV queue) → … |
| The wrong-security test for Alpha Vantage (`AV_MAX_DAYS_AFTER_TAKEOVER`, `TRADING_DAYS_PER_MONTH`) | `monthly build` → … |
| Hold periods, the delisting cutoff or the targets (`monthly.py`) | `monthly build` → … |
| A FRED series or its publication lag (`FRED_SERIES`) | `fred` → `features build` → … |
| A revised series read point-in-time (`FRED_VINTAGES`) | `fred` → `features build` → … |
| Sectors (`references/removed_sectors.csv`, `SECTOR_ETF`) or any feature (`features.py`) | `features build` → … |
| The rule grid, the strategy versions or their costs (`RULE_LOOKBACKS`, `RULE_TOP_NS`, `COST_PER_SIDE`, `RULE_CHECK_FROM`, `START_DOLLARS`, `BUFFER_MULTIPLE`, `INVERSE_VOL_FEATURE`, `TREND_MONTHS`, `backtest.py`, `diagnostics.py`) | `run_notebooks run` (00 and 03–06 all use the simulation code), then `hub push --target public` (the dashboard's tables) |
| The model setup or the models (`modeling/prep.py`, `models.py`, `evaluate.py`, `train.py`), or anything that changes the features | `modeling.train run` → `run_notebooks run` |
| Anything above, or the analysis or charts (`eda.py`, `plots.py`) | … → `run_notebooks run` (refreshes the notebooks and `reports/figures/`) |

Then `hub push --target both`, so the snapshots and the dashboard match.

Raw files are never edited by hand, so every output can be rebuilt from the downloads.

## Notebooks

The notebooks show each step's results. They call the package's functions and hold no logic of
their own. They're committed **with their outputs**, so the tables and charts can be read on GitHub
without the data:

| Notebook | What it shows |
| --- | --- |
| [`00_run_all`](../notebooks/00_run_all.ipynb) | **The whole workflow end to end**, one call per step: data (regime `local`, `hub` or `download`), transform, predict (refit with the tuned settings and the monthly run's checks), simulate (both strategies, the chosen rule and SPY on 2020–2022 and the test years), the latest trades, and how it runs unattended. The same functions as the monthly run, with no side effects (no message, no publishing, no live record). About two minutes |
| [`01_data`](../notebooks/01_data.ipynb) | Membership, the survivorship gap, what the Alpha Vantage pull found, prices, FRED, the monthly table and the feature sets |
| [`02_features_eda`](../notebooks/02_features_eda.ipynb) | The target, the signal of the 87 features that vary between stocks (2010–2022 only), its stability, exact duplicates, when last month's winners do well (market regimes), and a first look at the plain rule |
| [`03_models`](../notebooks/03_models.ipynb) | The folds, each model's tuned setting (2014–19), the comparison on 2020–22 where the headline is chosen, the single test (2023 on), the model rule columns and what the headline looks at. Reads the training step's outputs |
| [`04_simulation`](../notebooks/04_simulation.ipynb) | Backtests. Part 1: the baseline grid (60 rules: look-back × top N × hold, staggered, 10 bps a side) vs SPY and equal weight, and the best rule chosen on decisions 2010–2022 and followed through the test years. Part 2: the models traded (1-month hold; equal or inverse-vol weights, with or without a 2N hold buffer) vs SPY and the rules, in dollars from $10,000, for 2020–2022 and the test years, every model for reference, and a simpler $100-per-pick cross-check. About two minutes |
| [`05_risk`](../notebooks/05_risk.ipynb) | The paths: $10,000 month by month, falls from the peak, and rolling 12-month returns minus SPY's, for 2020–2022 and the test years, plus the rules from 2010. The SPY trend filter applied to every strategy, with its average effect. About two minutes |
| [`06_diagnostics`](../notebooks/06_diagnostics.ipynb) | Why the headline model loses: what each strategy buys, hit rates by market regime, sector and year with month-level margins of error, the worst picks, and hypotheses for future work. Descriptive only |

Run them only with:

```bash
uv run python -m sp500_momentum.run_notebooks run        # all notebooks (after features build)
uv run python -m sp500_momentum.run_notebooks run 02     # just 02_features_eda
```

This runs them top to bottom in a fresh kernel, so the stored outputs always match the code, and
writes the charts to `reports/figures/`. The notebooks show summaries, never raw tables (full
results are saved under `reports/`). After running, the command checks every output and **fails**
if:

- a cell prints more than 50 lines;
- anything was written to stderr (logs, progress bars, warnings);
- an output contains a local path, an e-mail address or any key or token from `.env`;
- a notebook is over 300 KB.

## Development

```bash
uv sync                        # installs dev tools too (pytest, ruff, pre-commit)
uv run pre-commit install      # once: ruff + safety checks on every commit
uv run pytest                  # tests (offline)
uv run ruff check              # lint
uv run ruff format             # format
uv run mkdocs serve            # preview the book at http://127.0.0.1:8000
uv run mkdocs build --strict   # the book build CI runs (fails on a broken chart or link, or a
                               # link to a missing section)
```

**Workflow.** Work is tracked as GitHub issues, grouped into milestones (one per phase) and shown on
the project board. Each issue gets its own branch (`<issue>-<short-name>`, e.g. `10-eda`) and is
merged into `main` through a pull request whose description says `Closes #<issue>`. CI (GitHub
Actions: ruff check, ruff format --check, pytest, the book build) runs on every pull request and
every push to `main`. `main` is protected: changes arrive only through pull requests, CI must pass
on an up-to-date branch, and force-pushes or deleting `main` are blocked. Pull requests are
squash-merged.

**The docs agent.** A Claude Code subagent, `docs-editor` (`.claude/agents/docs-editor.md`),
maintains this book and the README, one page per run: in *edit mode* it makes a given change, and
in *review mode* it returns ranked suggestions and changes nothing. A guard hook
(`.claude/hooks/docs_guard.py`, tested in `tests/test_docs_guard.py`) lets it write only `docs/`,
`README.md` and `code_issues.local.md`, and run only read-only git and the book build. It reads the
code but can't change it: clear code defects it finds go to `code_issues.local.md` at the repo
root, a git-ignored local file, to become issues. It leaves its changes uncommitted.

## Project organization

```text
├── docs               <- The project book (one chapter per step) and this guide (MkDocs)
├── data
│   ├── external       <- Data from third-party sources
│   ├── interim        <- Intermediate data (e.g. yfinance coverage of removed members, the
│   │                     wrong-security lists)
│   ├── processed      <- Final modelling tables
│   └── raw            <- Downloads, one folder per source (never edited by hand)
├── models             <- Trained models (each tuned model and the live refit)
├── notebooks          <- 00_run_all (the whole workflow), 01_data … 06_diagnostics (executed,
│                         with outputs)
├── references         <- Decision log, brainstorm and dated working journal, and the removed
│                         members' sectors (removed_sectors.csv)
├── reports            <- Result tables (*.csv), charts (figures/), the monthly picks (picks/)
├── scripts            <- Task Scheduler setup (retired: the Alpha Vantage pull and the PC monthly
│                         run) and the book's build hook (mkdocs_hooks.py)
├── cloudflare         <- The Worker that starts the monthly run (wrangler, offline tests)
├── .claude            <- The docs agent and its guard hook
├── logs               <- Run logs (git-ignored)
├── tests              <- pytest tests (offline, no network)
├── dashboard          <- The Streamlit dashboard (reads only the public dataset)
├── mkdocs.yml         <- The book website's build
├── Dockerfile         <- The pipeline image (built from the lock file; no data or secrets)
├── .github/workflows  <- CI (lint, format, tests, book), Docker build and publish, the book site,
│                         the monthly run
├── .pre-commit-config.yaml <- Checks run on every commit (ruff, large files, private keys)
└── sp500_momentum     <- Source code
    ├── config.py      <- Paths, study settings, membership repairs, price overrides, FRED lags
    ├── dataset.py     <- Command-line download steps (see above)
    ├── sources/       <- One module per data source: wikipedia, yahoo, alphavantage, fred
    ├── membership.py  <- Point-in-time membership and repairs to Wikipedia's changes
    ├── monthly.py     <- The monthly member table: prices, past and forward returns
    ├── features.py    <- Features from monthly bars (TA-Lib, risk, ranks, market, macro) and
    │                     feature sets
    ├── eda.py         <- Exploratory analysis: summary tables, IC, stability, plain-rule preview
    ├── backtest.py    <- `pred*` rule columns, staggered-portfolio simulation with costs, the rule
    │                     grid, strategy versions (weighting, buffer, trend filter), dollar paths
    ├── diagnostics.py <- What the picks look like and where they win or lose (month-level margins)
    ├── monitoring.py  <- Input drift (PSI), the live record, strategy returns for the dashboard
    ├── pipeline.py    <- The whole workflow as five calls (the run-all notebook), and rebuild-all
    ├── retries.py     <- Retries with longer waits (Wikipedia, FRED)
    ├── notify.py      <- Telegram: picks to the public channel, alerts to a private chat
    ├── hub.py         <- Hugging Face: the private snapshot, the public derived dataset
    ├── plots.py       <- Chart style (validated palette) and the charts
    ├── run_notebooks.py <- Executes the notebooks in a fresh kernel and checks their outputs
    ├── nb.py          <- Notebook setup (output caps, quiet logs, chart style) and the output rules
    └── modeling/      <- prep.py: feature matrix, targets, time blocks with gaps, CV folds,
                          in-fold preparation; models.py: the candidates and search ranges;
                          evaluate.py: top-10 scoring; train.py: tuning, comparison, the test;
                          predict.py: the monthly run (fresh data, checks, refit, picks)
```
