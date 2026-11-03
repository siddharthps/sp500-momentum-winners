# CLAUDE.md

Final project for the Stock Markets Analytics Zoomcamp 2026. **Deadline: Fri 20 Nov 2026,
23:59 Dublin time.** Time budget is about 30 hours (~3 h/day). A solid pass is the goal; extras are a bonus.

## The idea (idea H)

Each month-end, rank point-in-time S&P 500 members, buy last month's winners (the baseline rule) or
the top-N by an ML model's probability, hold X months, and backtest against SPY. Target: beats SPY
over X months. One row per stock per month-end (~150k rows), built from ~3M daily rows.
The golden rule: every feature is known at the month-end close, and the trade happens at the next open.

Background and the full design draft (feature groups, targets, modelling flow):
`C:\Users\Siddharth\Downloads\Stock-Markets-Analytics-Zoomcamp-2026\Final Project\Project_Ideas_Brainstorm.md`
(Section 7 = field design, Section 8 = discussion log). Ideation notes go there; decisions also go,
in short form, in `references/decisions.md` here.

## Data facts already established (don't re-test)

- Membership comes from Wikipedia: the current list plus **"Historical components of the S&P 500"**
  (the changes table moved off the main page). The study starts in **2010**.
- yfinance has no history for most delisted members (213 of the 320 removed since 2010).
  Some old tickers now point to different securities (`FB`), and some return 1-row stubs.
- Alpha Vantage key = **free tier: 25 calls a day, 1 a second**. Daily `outputsize=full` is premium,
  but **monthly adjusted is free with full history**, and it includes dividends (it matches yfinance).
  Some symbols return the company that reused the ticker later (STI), so validate against the removal date.
- **Don't spend Alpha Vantage calls ad hoc.** The scheduled task `sp500-momentum-av-pull` uses 23
  a day at 09:00 (`scripts/av_pull_daily.ps1`, log in `logs/av_pull.log`) until the queue is empty
  (~12 Nov 2026). Unregister the task once it's done.

## Commands

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format
uv run python -m sp500_momentum.dataset membership | coverage | av-pull | av-status
```

## Conventions

- Cookiecutter Data Science layout. One module per source in `sp500_momentum/sources/`. Don't name
  a module after a package it imports (hence `yahoo.py`, not `yfinance.py`).
- Raw data in `data/raw/<source>/` is never edited by hand. `data/` and `.env` are git-ignored.
- Tests are offline (no network).
- Windows + Git Bash/PowerShell. There's no `make`; steps are typer commands.
- The class's flow carries over (named feature sets, time split, `pred*` rules, tree/RF/LogReg,
  precision on test, `sim1_`-style simulation). Reuse it where possible, because time is short.
- The repo is private on GitHub (`siddharthps/sp500-momentum-winners`) and goes public near completion.
