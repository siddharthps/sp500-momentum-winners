# CLAUDE.md

Course final project (Stock Markets Analytics Zoomcamp 2026). **Deadline: Fri 20 Nov 2026, 23:59 Dublin.**
**Do things the professional, industry-standard way, not the quickest way.** ~30 h is a soft guide,
not a cap. Extras (bot, Docker, dashboard) still come after the core is done.

## The project

Each month-end, rank the point-in-time S&P 500 members and buy the top N, either by last month's
return (the baseline rule) or by an ML model's probability of beating SPY next month. Hold them, and
backtest against SPY. One row per member per month-end (2010 →), built from the daily prices.
**Golden rule:** every feature is known at the month-end close; the trade happens at the next open.

The agreed plan (split, features, models, simulation, deliverables) is in `references/decisions.md`.
Follow it. **Ask first** before changing the plan, spending API calls, or touching the scheduled task.
**Just do it** for bug fixes, tests, and refactors within a module, and say so afterwards.

**Done means:** `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass; the monthly
table and features rebuild; the journal entry and the step's chapter are written; the issue's "Done
when" boxes are ticked; the PR is merged with CI green.

## Working rules

- **Work through the tracker.** Every task is a GitHub issue in a milestone, shown on the project board
  (https://github.com/users/siddharthps/projects/1). Use `gh` (installed at
  `C:\Program Files\GitHub CLI\gh.exe`, not on PATH in the Bash tool).
  - Start a task on a branch named `<issue>-<short-name>` from an up-to-date `main`. Never commit to `main`.
  - Tick the issue's "Done when" boxes as items are finished, and set its board status (Todo → In
    Progress → Done).
  - Open a PR whose body says `Closes #<issue>`, and squash-merge it once CI is green.
  - **`main` is protected** (ruleset "Protect main"): a PR is required, the CI check `checks` must pass
    on an up-to-date branch, and force-pushes, deletion and bypasses are blocked. Merged branches are
    deleted automatically. If a push to `main` is rejected (GH013), that's the ruleset working.
  - New work found along the way gets its own issue, not a silent addition.
- **Pre-commit** runs ruff and safety checks on every commit. If it changes files, re-add them and
  commit again. Never skip it with `--no-verify`.
- **"If you change X, rerun from Y"** is in the README ("Rerunning after a change"). Follow it after
  changing any earlier step.
- **Journal every step.** Add a dated "Session N" entry to Section 8 of
  `references/Project_Ideas_Brainstorm.md` (plain style, including traps found and fixes). Put settled
  points in its Section 9 table and in `references/decisions.md`.
- **Write the book as you go.** After each step, write or update its chapter in `docs/` and its row in
  `docs/index.md`. Chapter shape: goal → what was done → what came out → decisions and why → caveats.
  - No mention of the course or the grading rubric.
  - No links to `references/`, except in the last appendix.
  - Explain the why, not the how: no commands, file paths or module names (the README has those).
- Keep the README's commands current.

## Traps (don't re-learn these)

- **Never spend Alpha Vantage calls ad hoc** (free tier: 25 per rolling ~24 h). The Task Scheduler job
  `sp500-momentum-av-pull` pulls daily at 21:00 PC time; its log is `logs/av_pull.log`. Unregister it
  once the queue is empty (~12–14 Nov).
- **Tickers get reused.** An old symbol can return a different company (FB, STI, CPWR). Always check a
  series against the removal date and trading volume. Membership repairs live in `config.py`.
- **Features come from monthly bars for every stock.** Never add a daily-only feature: it would be
  blank exactly for the later-delisted (Alpha Vantage) names and leak their fate.
- **Look-ahead checks for every feature:**
  - It uses data up to the month-end close only.
  - Macro values go through their `FRED_SERIES` publication lag.
  - Ranks and percentiles are computed within each date, never across dates.
- **Results:**
  - Label every result a *preview* until the AV pull is finished.
  - Never choose settings by looking at the test period (2023–26). Tune with time-series CV inside 2010–22.
- **Rebuild order:** after new raw data (the AV pull, any download), rerun `monthly build` before
  anything downstream.
- **Secrets:** never print, log or commit the Alpha Vantage key or `.env`.
- **Editing on Windows:** change code with the Edit/Write tools. Shell heredocs with Python patches
  break on `\n` inside strings (this happened 3 times).
- Raw data in `data/raw/` is never edited by hand.

## Commands

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format
uv run python -m sp500_momentum.dataset membership | coverage | yahoo-daily | fred | av-pull | av-status
uv run python -m sp500_momentum.monthly build
uv run python -m sp500_momentum.features build     # after monthly build
```

## Conventions

- Cookiecutter Data Science layout. One module per data source in `sp500_momentum/sources/`. Never
  name a module after a package it imports (`yahoo.py`, not `yfinance.py`).
- Steps are typer commands (Windows, no `make`). Tests are offline. `data/` and `.env` are git-ignored.
- Reuse the course's flow where it fits (named feature sets, `pred*` rules, `sim1_`-style simulation).
- The GitHub repo `siddharthps/sp500-momentum-winners` is **public** (since 3 Nov 2026). Everything
  pushed is visible: never commit data, secrets, logs or personal details. Commits use the GitHub
  noreply email (repo-local git config).
