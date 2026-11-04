# Decisions log

The full discussion lives in [Project_Ideas_Brainstorm.md](Project_Ideas_Brainstorm.md). This file
keeps only what was decided and why.

## 2 Nov 2026

**Idea H: monthly winners on the S&P 500.** Buy last month's top performers, hold for X months, and
compare against SPY. An ML model ranks all members each month. The plain rule is the baseline.

**Start in 2010.** Wikipedia's change history is thin before ~2008 (43 changes in the 2000s versus
220 in the 2010s).

**Data sources**

| Data | Source | Why |
|---|---|---|
| Point-in-time membership | Wikipedia: current list + "Historical components of the S&P 500" | One request each, and it's free |
| Prices, current members and removed members still trading | yfinance (daily, adjusted) | Free, full daily history |
| Prices, removed members yfinance lacks | Alpha Vantage `TIME_SERIES_MONTHLY_ADJUSTED` | Free tier has full **monthly** history only. Full daily history is premium |

**Survivorship gap (members removed 2010 to Oct 2026):** 320 removed and not in today's list. yfinance
covers 107 of them. 213 are missing: 138 acquired, 44 market cap, 21 spin-offs, 3 failed banks, 4 ticker
changes, 3 other. Acquisitions matter most for this idea, because takeover jumps are a common reason
a stock is the month's top gainer.

**Alpha Vantage checks**

- Adjusted close includes dividends and splits (KO matched yfinance within 0.1%, 2005–2026).
- It has bought-out and failed names: TWTR, PXD, CMA, HOLX, SIVB.
- Some old tickers return the company that reused the symbol later (e.g. STI), and some return
  nothing (LEH, BBBY, FRC). Every pull is checked against the removal date (`validate()`).
- yfinance has the same reuse trap: `FB` now returns a different security.

**yfinance daily download (`yahoo-daily`)**

- **Universe: 623 tickers.** That's the 503 current members, 107 removed members yfinance covers, and
  13 benchmark series (SPY, the 11 SPDR sector ETFs and ^VIX).
- **Dates:** from 1 Jan 2007 (a 3-year warm-up for the 12- and 24-month features and the 200-day
  averages) to yesterday's close. Today's half-finished bar is never saved.
- **Columns:** unadjusted OHLC, adjusted close, volume, dividends and splits. The trade happens at the
  next open, so the adjusted open is rebuilt as `open × adj_close / close`.
- **Storage:** one parquet file per ticker in `data/raw/yahoo/daily/`, plus `_manifest.csv`.
  Reruns skip tickers that already have a file. `--refresh` downloads everything again.
- **First run:** all 623 `ok`, 2.84M daily rows, all ending 30 Oct 2026.

**Delisted prices: cutoff rule, no cross-check**

- After a failure, Alpha Vantage keeps reporting over-the-counter penny prices (SBNY +3,102% in
  Dec 2023). So each delisted stock's prices **stop after the month that contains its removal
  date**. A position still held is valued at that last price, then treated as cash.
- Keeping the removal month (not stopping before it) keeps the crash in. SIVB's March 2023 close is
  0.905, while February's was 288.11.
- **No AV vs yfinance cross-check.** The prices compared so far match (KO within 0.1%; WBD, AVB and
  EA exactly). Remaining errors would show up as outliers when the monthly table is checked.

**Hold periods and evaluation**

- **Rule baseline:** hold X = 1, 3, 6 and 12 months, run over the **full 2010–2026 period** with no
  split. The rule fits nothing, so it needs no test set.
- **Look-back grid:** "winner" is defined over 1, 3, 6 or 12 months, plus 12 months skipping the
  latest one. Every cell of the grid gets reported. The best one is also checked on 2022 onwards.
- **Simulation details:** staggered portfolios (1/X of the money enters each month), about 10 bps
  cost per side, and top 1 (the baseline) next to top 5 and top 10.
- **ML model: 1-month target only**, with the time split. A ~4-year test set leaves only ~24 usable
  months for a 12-month target (~2 independent periods), too few to judge.
- **24 months dropped.** It's past the range where momentum holds (winners tend to reverse), and its
  train/test gaps would use up ~4 of the 16 years.

**Monthly table (`sp500_momentum.monthly build`)**

- **Shape:** one row per member per month-end (2010-01 to 2026-10), in
  `data/processed/monthly_panel.parquet`. Rebuilt from the raw files each run.
- **Trade price:** the next trading day's adjusted open. Alpha Vantage names only have monthly data,
  so they use the month-end close.
- **Wikipedia repairs:** date-windowed renames in `RENAMES` (tickers get reused, so a flat alias map
  is wrong), synthetic adds in `MISSING_ADDS`, and stray characters stripped from tickers.
- **Wrong-security check:** a yfinance series with a median daily dollar volume under $10M over its
  member months is dropped, and the removed names go to the AV queue instead (CPWR, EP, GENZ, KG,
  SII, SUN).
- **Accepted gap:** about 550 member-months that neither source can fill, mostly old companies
  whose ticker a current member now uses (DOW, SNDK, DELL, CEG). They're measured, not fixed.

**Project plan (settled one question at a time, Session 5)**

| Area | Decision |
|---|---|
| Row | One per member per month-end. The 2.85M daily rows underneath cover >1M |
| Split | Train 2010–19, validation 2020–22, test 2023–26, 1-month gaps |
| Timing | Build now on current data. Rerun everything after the AV pull (~12 Nov) |
| Macro | Class FRED set + VIX (level, percentile) + yield-curve slope, each lagged to its publication date |
| Market growth features | US-focused: SPY, Dow, sector ETF, gold, WTI, 10-year yield |
| TA-Lib | ~55 indicators at month-end (running totals as changes or ranks). No candle patterns |
| Own features | Core ~20: ranks, relative strength, quality of the move, volatility and beta, 52-week position, breadth |
| Sectors, removed members | Filled in by hand (yfinance sector, then a name match, then "unknown"). An all-"unknown" sector would leak the future |
| Target | `is_beat_spy_1m` (top decile as a second target, for analysis) |
| Models | Decision tree, random forest, logistic regression, XGBoost |
| Tuning | Time-series CV (expanding yearly folds inside 2010–22). Test used once |
| Score | Precision of the monthly top-N picks against the ~49% base rate. Excess return alongside |
| Picks | Top 1, 5 and 10 reported. Headline: top 10 |
| Benchmarks | SPY + an equal-weight basket of all members |
| Simulation | Vector (`sim1_` style) + exact with reinvestment (CAGR, Sharpe, max drawdown, rolling) |
| Extra strategy | Only buy when SPY is above its 200-day average |
| Notebooks | `00_run_all`, `01_data`, `02_features_eda`, `03_models`, `04_simulation`, each calling the `.py` modules |
| Data hosting | Hugging Face dataset ("from file" mode) |
| Automation | Monthly Task Scheduler run (incremental update → rebuild → score → picks) + a `--from-file` switch |
| Extras | After the core (~mid-Nov). Telegram bot first if time allows |

**FRED and market downloads**

- **FRED:** six series (the class's set) from FRED's CSV endpoint, not `pandas_datareader`
  (unmaintained). Publication lags live in `FRED_SERIES`: 1 month for core CPI and Fed Funds, and
  the last value before the decision date for daily yields.
- **Market series:** `^DJI`, `GC=F` and `CL=F` were added to the yfinance downloads (A5). Downloads now keep
  rows strictly before the end date, because futures let today's half-finished bar through.

**Alpha Vantage schedule (3 Nov)**

- The daily pull runs at **21:00 PC time** (it was 09:00), with catch-up after boot. The PC was off at
  09:00, and the free tier's 25-call limit looks like a rolling 24 hours (only 9 of 23 calls got
  through on 3 Nov). Estimated finish: ~12–14 Nov.
- The quota message quotes the API key, so `av-pull` now writes `***` in its place in the log.

**Documentation (3 Nov)**

- **The book:** numbered Markdown chapters in `docs/`, MkDocs-ready (CCDS's own docs tool), with no build step.
  Chapters 01 problem, 02 data collection, 03 monthly table, 04 features, 05 EDA, 06 modelling,
  07 simulation and results, 08 automation, 09 limitations. Appendices: data dictionary, decisions, journal.
- **Chapter shape:** goal → what was done → what came out → decisions and why → caveats. The README is
  the front page and links to the chapters.
- **Rules (your review):** written for a reader who never took the course; no mention of the course or the
  grading rubric; no links to `references/` except in the last appendix ("the full working record");
  the why, not the how (no reproduce sections, commands or file paths, which stay in the README).
- **Timing:** written as we go (01–03 drafted on 3 Nov). The numbers get refreshed after the AV pull ends.

**Features (3 Nov)**

- **Monthly bars for every stock.** All features, TA-Lib included, come from monthly open/high/low/
  close/volume bars. Daily-only features would be blank exactly for the later-delisted (monthly-only)
  companies and leak their fate. (This replaced my first recommendation, "blank + flag", which had that leak.)
- **Prices from 2000**, for the warm-up of the long monthly indicators. The unfinished current month is
  never a decision date.
- **147 features in named sets:** PAST_RETURNS 5, TA 55, STOCK 15, CROSS_SECTION 16, MARKET 24, MACRO 9,
  DUMMIES 23. Price-level indicators are divided by the price, so they're scale-free.
- **Sectors for removed members** were labelled by hand (`references/removed_sectors.csv`). They agree 90% with
  Yahoo, against a 95% baseline. Sector funds that didn't exist yet fall back (XLRE → XLF, XLC → SPY).
- **Checked:** macro values come from already-published dates; fill rate is the same by source (99.6% vs 99.9%);
  the largest single-feature IC is 0.014 (no leak).

**Planning and workflow (3 Nov)**

- **Guiding rule:** the professional way over the easier one. The ~30 h budget is a soft guide.
- **Tracker:** GitHub Issues + 11 milestones (one per phase, with due dates) + a project board. The
  finished work is recorded as closed issues #1–#8, linked to their commits.
- **Workflow:** a branch per issue, a PR with `Closes #n`, squash merge.
- **Checks:** GitHub Actions CI (ruff check, ruff format --check, pytest) on every push and PR, plus a
  pre-commit hook (ruff, a large-file block, a private-key check). Merge only when CI is green.
- **Rerun chain:** documented in the README ("if you change X, rerun from Y").
- **Public early, to protect `main` (3 Nov):** a free private repo can't use branch protection, so the repo
  went public before the planned "near completion". The full history was scanned first: no key, data or
  logs. Ruleset "Protect main": PR required, CI `checks` required on an up-to-date branch, no force-push,
  no deletion, no bypass. Squash-only, branches auto-deleted.
- **Commit email:** new commits use the GitHub noreply address. The 13 earlier commits keep the original
  address. Rewriting them wouldn't hide it, because GitHub keeps PR #24's ref permanently.

**Exploratory analysis (3 Nov)**

- **Notebooks are committed executed, with outputs** (readers see results without the data). They're only
  ever run by `run_notebooks run` (fresh kernel), with metadata cleared, small charts, and a 500 KB cap;
  ruff lints them.
- **Charts:** a palette validated with the dataviz validator (blue/orange/aqua, all pairs pass). Aqua is
  below 3:1 contrast, so it always gets direct labels plus a table. One axis, and every chart is reviewed by eye.
- **Research period:** feature signal, stability, correlations and regimes use decisions up to 2022 only
  (`RESEARCH_END`). The test years 2023–26 stay unseen.
- **Logic lives in the package** (`eda.py`, `plots.py`, tested). Notebooks only call it.
- **What notebooks may print, enforced by the runner:** summaries only (`nb.setup()` caps tables at 20 rows;
  full results go to `reports/`). A run fails on a cell output over 50 lines, anything on stderr, a local
  path, e-mail or key in the outputs, or a notebook over 300 KB.

**Baseline rule grid (3 Nov, #11)**

- **60 rules, all reported:** look-back 1/3/6/12 m and 12-1 m × top 1/5/10 × hold 1/3/6/12 m, over the full
  period (returns earned Feb 2010 to Oct 2026). Each rule is a `pred_mom_<look-back>_top<N>` column.
- **Simulation:** staggered slots (1/X of the money reinvested monthly, buy-and-hold inside a slot, the
  slots averaged monthly). Trades at the next open. 10 bps per side on the traded weight, so a kept stock
  pays only the difference. Index leavers stay held; delisted names go to cash at their last price.
  Rebalancing between slots isn't charged.
- **Prices beyond membership:** `monthly build` now also writes every usable price series
  (`monthly_prices.parquet`), because a held stock can leave the index.
- **Scoring:** Sharpe ratio net of the Fed Funds rate (evaluation only, so no publication lag). The
  t-statistic of the monthly excess over SPY is shown, noting the 60 tries.
- **The best cell is chosen on 2010–2022 and followed through the test years (2023 on)**:
  `RULE_CHECK_FROM = SPLIT["test"][0]`. Choosing on the full period and then "checking" a sub-period of
  it would be circular. Using the models' test window means every strategy is judged on the same
  untouched months. The older "2022+" wording predates the A2 split. It was briefly built with a 2022
  cut, then aligned on principle, not on the result: the 2023 cut is the *less* flattering one for the rule.
- **The split stays 2010–19 / 2020–22 / 2023–26 (your question, 3 Nov).** In months that's about 60/18/22,
  not 70/15/15. With time-series CV over 2010–22 it's about 78/22 development vs test, close to the usual
  80/20. A 70/15/15 split would leave a ~30-month test, too few to judge a monthly strategy. The
  boundaries are calendar years fixed before any result.
- **Benchmarks are gross:** SPY's fee is in its price; the equal-weight basket is a yardstick.
- **Bug fixed along the way:** a ticker with both a (wrong-security) yfinance series and an Alpha
  Vantage series would have had both merged, and then both dropped. Alpha Vantage now wins, and only the
  yfinance copy of a suspect ticker is dropped. Not yet hit, because no suspect has arrived from AV.
- **Preview result:** 53 of 60 rules beat SPY on return, 6 on Sharpe, and none on worst fall. The best is
  top 5 by 6-month return, held 6 months, both over the full period and chosen on 2010–22. In 2023–26 it
  made 60% a year vs SPY's 21%, but with 43% volatility vs 12%, a worst fall of −27% vs −8%, and a
  **lower Sharpe (1.21 vs 1.29)**. Driven by AI and memory-chip stocks.

**Feature review against the course, Weeks 1–4 (3 Nov)**

- **Add 8 features with new information, drop 3 exact copies (#29, before modelling):**
  - from the course: 12-month dividend yield, risk-adjusted momentum (`ret_12_1m / vol_12m`), months in the index, drawdown from the all-time high;
  - from research: residual momentum, idiosyncratic volatility, the maximum monthly return over 12 months, same-month seasonality (5 years);
  - drop `ta_rocp`, `ta_rocr` and `ta_rocr100`, affine copies of `ta_roc`, dropped by formula, not by performance. 147 → 152.
- **No split flag:** Alpha Vantage's monthly data has no split column, so the flag would be blank exactly for the delisted names.
- **Not added from the course:** candle patterns (A6), non-US markets (A5), weekday, week-of-month and ticker dummies (rows are month-ends).
- **Sector labels** are today's GICS applied back to 2010. Communication Services (2018) and Real Estate (2016) are anachronistic before then. That's a caveat, not a fix: no free point-in-time GICS exists, and the labels carry no future returns.
- **Flagged moves** (>+100% or <−75% in a month) get a manual review in #20, once the list is final.
- **Blanks in the models (#12):** XGBoost keeps NaN. Tree, RF and LogReg get the training-fold median plus a "was missing" flag, fitted inside each CV fold. Never 0-filled (the course's way), because 0 is a real value for returns and betas.
- **Model now, not after the data:** one fit takes 1–11 s, and full tuning about 30–45 min. The missing data is in the training years (13,350 member-months) and barely in the test years (107).

**Alpha Vantage pull survives a killed run (3 Nov, #30)**

- The 21:00 run was killed from outside (`0xC000013A`) after saving 6 files, before writing the manifest, which used to be written only at the end.
- Now the manifest is written after every ticker, and on start any saved file the manifest lacks is added, validated with the same rule. `--max-calls 0` does only that, with no calls.
- The 6 were recovered with no calls. Tried 23, 192 left. The task registration is unchanged.

**Alpha Vantage budget stays at 23 (3 Nov, your call)**

- I recommended raising the nightly budget to 25: about 18 more calls over the remaining nights, roughly one night sooner. You chose to keep the 2-call buffer for a manual check. Finish stays around 12–14 Nov.

**Eight more features built (3 Nov, #29)**

- 152 features (TA 52, STOCK 22, CROSS_SECTION 17). Dividend yield uses each dividend over the same-time close in both sources. Months in the index uses only the changes table, capped at 120.
- **Extreme values stay in the table.** For LogReg, every feature is clipped to its training-fold 1st/99th percentile inside each CV fold (#12). Examples: dividend yields up to 167% from special payouts and spin-offs, risk-adjusted momentum up to 98.

**Model setup (4 Nov, #12), settled one question at a time, all as recommended**

- **CV layout, option A:** expanding yearly folds inside the train block, scoring 2014–2019 (6 folds). 2020–22 is held out to compare the tuned models. The chosen model is refit on 2010–22 and tested once on 2023+.
  - Option B (CV across all of 2010–22) was rejected: it loses the independent 2020–22 check.
- **Gap:** every training window drops its last decision month before the scored block. So the validation model trains to Nov 2019 and the test model to Nov 2022.
- **Models: the plan's four plus four (this changes B2):**
  - the four: tree, RF, LogReg, XGBoost classifier;
  - **XGBoost ranker** (learning to rank within each month);
  - **XGBoost regressor** on excess return;
  - **MLP** (small, 1–3 layers, averaged over random starts, after Gu, Kelly & Xiu 2020);
  - an **average** of the models' within-month rankings.
  - The course used tree, RF, LogReg and an NN; XGBoost was already our addition.
  - Other NN types were considered and skipped: ResNet-MLP and FT-Transformer, TabNet and SAINT (PyTorch, no consistent gain), TabPFN (made for ≤10k rows), sequence models (too little data, mostly relearn momentum), autoencoder pricing models (a project of their own).
- **Ranker label:** the excess-return decile 0–9 within each month.
- **Regressor target:** `fwd_excess_1m`, clipped to the training fold's 1st/99th percentile, with pseudo-Huber loss (set in #13).
- **Within-month percentile features:** a second copy of the 96 stock-level features. Market, macro and flag columns stay raw. Whether to use it is a tuning choice per model. It's stateless (same-month rows only), so it's computed once.
- **Preparation per model family**, fitted on training rows only:
  - XGBoost models: native blanks;
  - tree and RF: median plus "was missing" flags;
  - LogReg and MLP: clip to the 1st/99th percentile, then median plus flags, then scaling.
- **Editor folders** (`.vscode/`, `.idea/`) are git-ignored: personal settings, public repo.
- **`xgboost-cpu`, not `xgboost`:** the full package pulls ~300 MB of NVIDIA GPU libraries on Linux (CI). We never use a GPU; the CPU build has the same code and API.

**Tooling:** Cookiecutter Data Science v2.3.0 layout, uv, Python 3.12, pytest, ruff. No Makefile
(Windows), so each step is a command in `sp500_momentum.dataset`.

**Repo:** public since 3 Nov 2026 (it was private until then). `main` is protected (see Planning and workflow).
