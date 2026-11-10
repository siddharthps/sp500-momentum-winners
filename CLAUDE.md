# CLAUDE.md

Course final project (Stock Markets Analytics Zoomcamp 2026). **Deadline: Fri 20 Nov 2026, 23:59 Dublin.**
**Do things the professional, industry-standard way, not the quickest way.** ~30 h is a soft guide,
not a cap. The extras (Telegram bot, Docker, dashboard, book site) are built; the last one (the
cloud run, #39) must never cost the final rebuild (#20) or the write-up (#22).

## The project

Each month-end, rank the point-in-time S&P 500 members and buy the top N, either by last month's
return (the baseline rule) or by an ML model's probability of beating SPY next month. Hold them, and
backtest against SPY. One row per member per month-end (2010 →), built from the daily prices.
**Golden rule:** every feature is known at the month-end close; the trade happens at the next open.

The agreed plan (split, features, models, simulation, deliverables) is in `references/decisions.md`.
Follow it. **Ask first** before changing the plan, spending API calls, or touching the scheduled task.
**Just do it** for bug fixes, tests, and refactors within a module, and say so afterwards.

**Done means:** `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` and
`uv run mkdocs build --strict` pass (and the Docker build, if the Dockerfile or dependencies
changed); the monthly table and features rebuild; `run_notebooks run` passes its output checks; the
journal entry and the step's chapter are written; the issue's "Done when" boxes are ticked; the PR
is merged with CI green (both the CI and Docker workflows).

## Working rules

- **Work through the tracker.** Every task is a GitHub issue in a milestone, shown on the project board
  (https://github.com/users/siddharthps/projects/1). Use `gh` (installed at
  `C:\Program Files\GitHub CLI\gh.exe`, not on PATH in the Bash tool).
  - Start a task on a branch named `<issue>-<short-name>` from an up-to-date `main`. Never commit to `main`.
  - Tick the issue's "Done when" boxes as items are finished, and set its board status (Todo → In
    Progress → Done).
  - Open a PR whose body says `Closes #<issue>`, and squash-merge it once CI is green.
    **Wait for CI by PR number in its own step** (right after `gh pr create`, `gh pr checks
    --watch` returns "no checks" at once), and set the board to Done only once the PR is MERGED.
  - GitHub's API sometimes errors mid-batch (GraphQL errors, 502). A failed write may still have
    happened: list the actual state before retrying, so nothing is duplicated.
  - **`main` is protected** (ruleset "Protect main"): a PR is required, the CI check `checks` must pass
    on an up-to-date branch, and force-pushes, deletion and bypasses are blocked. Merged branches are
    deleted automatically. If a push to `main` is rejected (GH013), that's the ruleset working.
  - New work found along the way gets its own issue, not a silent addition.
- **Pre-commit** runs ruff and safety checks on every commit. If it changes files, re-add them and
  commit again. Never skip it with `--no-verify`.
- **"If you change X, rerun from Y"** is in the README ("Rerunning after a change"). Follow it after
  changing any earlier step.
- **Check every claim before writing it.** No finding goes into a chart title, notebook text,
  chapter or summary until it has been checked against the actual output. (A drafted subtitle said
  the opposite of the data once; it was caught in review.) Research cited in the book is looked up
  before it ships, never quoted from memory (a recalled "shallow beats deep" needed refining on
  7 Nov). Counts that appear in two chapters must agree.
- **Journal every step.** Add a dated "Session N" entry to Section 8 of
  `references/Project_Ideas_Brainstorm.md` (plain style, including traps found and fixes). Put settled
  points in its Section 9 table and in `references/decisions.md`.
- **Write the book as you go.** After each step, write or update its chapter in `docs/` and its row in
  `docs/index.md`. Chapter shape: goal → what was done → what came out → decisions and why → caveats.
  - No mention of the course or the grading rubric.
  - No links to `references/`, except in the last appendix.
  - Explain the why, not the how: no commands, file paths or module names (the README has those).
- Keep the README's commands current.

## Now: the chapter-by-chapter review (temporary, from 7 Nov; remove when it ends)

- **One chapter at a time, in order. Never move on to the next chapter until the user says go.**
  For each chapter: summarise it in plain words, check it against the code and the data, list
  suggestions (errors first), and ask which to apply (one prompt). Apply them, build the book, and
  commit locally, one commit per chapter. **Don't push** until the user asks.
- **State (9 Nov):** Chapters 1 and 2 are approved and merged. **Chapter 3's review has started.**
  Checking it against the data found #59, the takeovers where the buyer kept the target's ticker,
  fixed in its own PR. Chapter 3's own suggestions haven't been offered yet:
  - stale counts (the share priced and the by-year row, now from the 9 Nov rebuild);
  - the six wrong-company series' Alpha Vantage outcomes;
  - "about 550 member-months can't be filled", now far more once the Alpha Vantage failures count;
  - the DISCA → WBD repair;
  - the flagged-price review.
- **The ask behind it:** the published book didn't make the setup clear to a first-time reader. Read
  each chapter as that reader would, not as its author.
- **For #20's refresh, beyond rerunning the notebooks:**
  - the README's result table and sizes;
  - Appendix A (drop `ta_natr`);
  - Chapter 9's numbers;
  - the contents page's short version.

## Traps (don't re-learn these)

- **Never spend Alpha Vantage calls ad hoc** (free tier: 25 per rolling ~24 h). The Task Scheduler job
  `sp500-momentum-av-pull` pulls daily at 21:00 PC time; its log is `logs/av_pull.log`. Unregister it
  once the queue is empty (~12–14 Nov). Each ticker is recorded in the manifest as soon as it's
  fetched. If a run is killed (log stops after the header, task result `0xC000013A`), the next run,
  or `av-pull --max-calls 0` now, records the saved files without any calls.
- **The monthly run** (task `sp500-momentum-monthly-run`, daily at 07:00, a no-op unless last
  month's picks are missing on a weekday; log `logs/monthly_run.log`) refits the headline with its
  tuned settings, never re-tunes. It stops on purpose when a newly removed member has no sector:
  add it to `references/removed_sectors.csv` (KVUE, the first time). Its refit must keep matching
  the backtest (run as of Jan 2023 it reproduces the test fit's scores exactly).
- **Tickers get reused.** An old symbol can return a different company (FB, STI, CPWR). Always check a
  series against the removal date and trading volume. Membership repairs live in `config.py`.
  When a buyer keeps the target's ticker (ACE/CB, Tyco/JCI, Dow/DD, AGL/GAS), the source files the
  *buyer's* history under it for years before the deal, and the volume check can't see it. Check
  whose dividends and price level the series has, then fix it with `PRICE_OVERRIDES` (#59), not a
  rename.
- **Features come from monthly bars for every stock.** Never add a daily-only feature: it would be
  blank exactly for the later-delisted (Alpha Vantage) names and leak their fate.
- **Look-ahead checks for every feature:**
  - It uses data up to the month-end close only.
  - Macro values go through their `FRED_SERIES` publication lag.
  - Ranks and percentiles are computed within each date, never across dates.
- **Results:**
  - Label every result a *preview* until the AV pull is finished.
  - Never choose settings by looking at the test period (2023–26). Tune with time-series CV inside 2010–22.
  - **One test window for every strategy.** Rules and models are chosen on 2010–22 only and scored on
    `SPLIT["test"]` (2023 on). Any cut-off or check window comes from `SPLIT`, never a new date.
  - **Windows are set by decision date.** Returns are labelled by the month earned (decision + 1), so
    convert with `backtest.earned_months`. SPLIT's end dates are inclusive and table windows are
    `[start, end)`: a period ends where the next one starts. (A Dec 2022 decision counted as "test"
    once scored a strategy on a month it was chosen on.)
  - **Judge a method by its reasoning, never by its result.** Fix splits, cut-offs and metrics before
    looking at outcomes. Never change one because the conclusion would look better (a 2022 cut made the
    baseline win on Sharpe; the agreed 2023 cut makes it lose).
- **Models:** never log or print test-period (2023+) results during development; they're shown
  once, in notebook 03. The headline is chosen on 2020–22 before the test is read. Time every model
  with `--n-iter 1` before a full search (a slow solver once cost ~8 min a try).
- **Backtests:** a held stock can leave the index, so simulate from `MONTHLY_PRICES` (every price
  series), not from the member panel. Any new simulation must reproduce the table's `fwd_ret_1m` with a
  1-month hold and no costs before its results are trusted. Strategy versions (weighting, the 2N
  buffer, the trend filter) are declared before results and none are added after; the headline is
  the main version only (its best 2020–22 version was its worst on the test).
- **Rebuild order:** after new raw data (the AV pull, any download), rerun `monthly build` before
  anything downstream.
- **Until #20, `data/` is newer than the notebooks.** The monthly run (5 Nov) rebuilt `data/` with
  more delisted names and Kenvue's sector, while notebooks 01–06 and the chapters show the 4 Nov
  snapshot (agreed). Don't rerun notebooks or retrain before #20: the numbers would drift from the
  book. #20 reruns everything once on the complete data.
- **Secrets:** never print, log or commit the Alpha Vantage key, the Telegram or Hugging Face
  tokens, or `.env`. Verify a token by asking its service who it belongs to, never by printing it.
  Request errors can carry the token in their URL: report them by type only.
- **Ruff only checks the folders in `pyproject.toml`'s `include`.** `tests/` (3 Nov) and
  `dashboard/` (5 Nov) were both silently skipped at first. Add every new code folder.
- **Docker:** `.dockerignore` keeps data, models, logs, `.env`, `CLAUDE.local.md` and `.claude/`
  out of the image, which is published publicly (GHCR): keep it that way. Secrets are passed at
  run time (`--env-file`), never as build arguments. Running third-party scanner images locally
  with Docker-engine access is blocked by the safety check; the Trivy scan runs in CI instead.
  **pip is removed on purpose** (from the project's dependencies and the image): it vendors
  setuptools 70.3.0 (CVE-2025-47273), and uv manages everything. Don't add it back. Upgrading a
  package doesn't fix a *vendored* copy; check `*/_vendor/vendor.txt`. Local builds need Docker
  Desktop running. The Docker workflow is path-filtered (not a required check): when a new file
  or folder starts feeding the pipeline, add it to both `paths:` lists in `docker.yml`.
- **Pin new third-party GitHub Actions to commit SHAs** (version in a comment), and look every
  version up (`gh api repos/<owner>/<repo>/releases`), never recall it: a pin written from memory
  (`trivy-action@0.28.0`) didn't exist, and that action's tags had been re-created. (Trivy is pinned
  to a SHA; `astral-sh/setup-uv` and the `docker/*` actions are still on tags.)
- **The book site** (GitHub Pages, `.github/workflows/pages.yml`) builds `docs/` with
  `scripts/mkdocs_hooks.py`: chapters keep GitHub-style paths (`../reports/figures/x.png`,
  `../references/...`) and the hook adapts them. Keep writing chapters that way; `--strict` in CI
  fails on any broken chart or link.
- **The dashboard** (`dashboard/`, Streamlit Community Cloud from `main`) can't import the package:
  its calculations live in `dashboard/logic.py`, tested against the package where they overlap.
  It reads only the public HF dataset. HF Spaces now need PRO for Streamlit/Docker (only static
  Spaces are free).
- **Hugging Face:** raw vendor prices (`close_adj`, `entry_px`, `dollar_vol`) go only to the
  **private** dataset; the public one gets derived tables (`hub.without_prices`). `hub push` scans
  for secrets and refuses; keep it that way.
- **Notebooks are committed with outputs**, so:
  - Run them only with `run_notebooks run` (a fresh kernel). Never edit outputs by hand.
  - Start every notebook with `nb.setup()`. It caps tables at 20 rows, keeps logs to warnings only,
    and applies the chart style.
  - **Show summaries, never raw data:** aggregates, rates, `.head(n)`. Full results go to files in
    `reports/`. One table or chart per question, each with a sentence saying what it shows.
  - Keep logic in the package (`eda.py`, `backtest.py`, `diagnostics.py`, `plots.py`), not in cells.
  - Breakdowns (by sector, regime, year) are descriptive: margins of error across months, never
    turned into a strategy tested on the same years.
  - Feature analysis uses decisions up to `RESEARCH_END` only.
  - **The runner fails** on: a cell output over 50 lines; anything on stderr; a local path, e-mail or
    the AV key in any output; a notebook over 300 KB. Fix the cause, never loosen the check.
- **Charts:** follow the dataviz skill. Colours come from `plots.SLOTS` in fixed order (validated
  with the skill's validator; Node is at `C:\Program Files\nodejs\node.exe`), one y-axis, and every
  chart gets looked at before it ships. Bars start at a real baseline (zero, or the starting amount
  for gains and losses), never at an axis edge. If a notebook nears the 300 KB limit, combine charts
  into small multiples rather than loosening the check. Show every chart through `plots.save` (it
  writes and displays 256-colour PNGs, about a third the bytes, and closes the figure); smoothed
  multi-line charts are what make PNGs large. Date axes use explicit locators (the automatic one
  warns on short ranges, which fails the runner).
- **Editing on Windows:** change code with the Edit/Write tools. Shell heredocs with Python patches
  break on `\n` inside strings (this happened 3 times). PowerShell also mangles quotes in inline
  `python -c` scripts, and a multi-line `.Replace()` silently misses on CRLF files: write a scratch
  script or use Edit. Never name a scratch script after a standard module (`numbers.py` broke numpy's
  import).
- Raw data in `data/raw/` is never edited by hand.

## Commands

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format
uv run python -m sp500_momentum.dataset membership | coverage | yahoo-daily | fred | av-pull | av-status
uv run python -m sp500_momentum.monthly build
uv run python -m sp500_momentum.features build     # after monthly build
uv run python -m sp500_momentum.modeling.train run # after features build; ~1¾ h (--n-iter 1: smoke run)
uv run python -m sp500_momentum.modeling.predict run  # the monthly run (~2 min; --no-download, --force,
                                                      # --from-file, --dry-run-notify, --no-publish)
uv run python -m sp500_momentum.hub push --target private|public|both [--tag X] | pull   # HF datasets
uv run python -m sp500_momentum.notify test [--dry-run] | find-chats                    # Telegram
uv run streamlit run dashboard/app.py               # the dashboard locally (live: sp500-momentum-winners.streamlit.app)
uv run mkdocs build --strict                        # the book (CI runs it; published to GitHub Pages from main)
uv run python -m sp500_momentum.pipeline rebuild-all --tag final-2026-11 [--dry-run]   # #20's rebuild
docker build --target test -t sp500-momentum:test . && docker run --rm sp500-momentum:test   # tests in the image
uv run python -m sp500_momentum.run_notebooks run  # after features build (and train); refreshes figures
uv run python -m sp500_momentum.run_notebooks run 04  # just one notebook (04: rule grid + model strategies, ~2 min)
```

## Conventions

- Cookiecutter Data Science layout. One module per data source in `sp500_momentum/sources/`. Never
  name a module after a package it imports (`yahoo.py`, not `yfinance.py`).
- Steps are typer commands (Windows, no `make`). Tests are offline. `data/` and `.env` are git-ignored.
- Reuse the course's flow where it fits (named feature sets, `pred*` rules, `sim1_`-style simulation).
- The GitHub repo `siddharthps/sp500-momentum-winners` is **public** (since 3 Nov 2026). Everything
  pushed is visible: never commit data, secrets, logs or personal details. Commits use the GitHub
  noreply email (repo-local git config).
