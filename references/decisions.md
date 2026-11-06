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

**Models trained and tuned (4 Nov, #13)**

- **Random search** (scikit-learn's `ParameterSampler`, seed 0): 30 tries per model, 20 for the MLP. It covers wide ranges better than a grid, and gives the same tries on every rerun.
- **Selection score:** the mean of the six yearly top-10 precisions minus 0.5 × their standard deviation. A setting has to hold up every year.
- **One headline, chosen on 2020–22** by the same score, before the test was read. Every candidate is still tested and simulated, for reference only.
- **Top-N rules, not probability thresholds:** the strategy buys a fixed number of stocks, so a threshold (the course's `pred` > 0.5 style) would buy a varying number, or none.
- **No class weights:** about half of member-months beat SPY.
- **MLP:** averaged over 5 seeds, with early stopping on the latest 15% of training rows (in time order).
- **LogReg:** L2 penalty with lbfgs. saga took ~8 min a try, and L1 is unstable with near-duplicate features.
- **Test-period numbers are never logged** by the training command; they're shown once, in notebook 03. Trained models are saved in `models/` (git-ignored).
- **Result (preview):** every model was below the base rate on 2020–22, and both plain rules were above it. The headline is the XGBoost regressor (49.2% vs 49.9%). On the test it scored 45.1% vs a 45.2% base rate, and its picks trailed SPY by 0.8% a month. The 6-month rule made 52.9%, at +1.5% a month. The decision tree was top on the test (54.0%), but it wasn't chosen and won't be: it was below the base rate on 2020–22.

**Model simulations (4 Nov, #14), settled one question at a time, all as recommended, before any results**

- **No $100 vector (sim1_) version.** The exact staggered simulator from #11 already reinvests. It charges costs only on the traded weight, so a stock kept from last month isn't sold and rebought (it's only trimmed back to its target weight).
- **Dollar amounts:** "$10,000 invested" next to CAGR, and fees in dollars (your question).
- **Weighting:** equal weight is the main version. Inverse volatility (∝ 1 / 3-month volatility, known at month-end) is one pre-declared variant.
  - Confidence weighting was rejected: it would amplify a signal that's close to noise.
  - Rank weighting was rejected for the same reason.
  - Market-cap weighting was rejected: no shares outstanding for the delisted names, and it would tilt towards the index giants.
  - Optimised weights were rejected: unstable on noisy return forecasts.
- **Hold buffer, 2N:** buy the top N, but keep a holding while it ranks within the top 2N. A sold name is replaced by the best-ranked name not already held.
  - Your question: a momentum strategy shouldn't churn stocks that stay strong.
  - Picks kept from one month to the next (2014–22, top 10): 4% for the 1-month rule, 54% for the 6-month rule, 27% for the headline model, 32% for the tree.
  - It's a variant for every 1-month-hold strategy. The grid's longer holds are unchanged.
- **Periods:** 2020–22 and the test only. 2014–19 is left out because its scores come from the folds the settings were chosen on.
- **Presentation:**
  - Main result: the headline at top 10 in 4 versions (weighting × buffer), against SPY, equal weight, the rule chosen on 2010–22, and the 1-month rules with the same top N.
  - Reference: all 8 candidates at top 10. Every cell goes to `reports/`.
- **Issues:** #14 is now "Model simulations: costs, buffer, weighting". #15 is "Equity curves, rolling returns and the SPY trend filter".
- **Every window is set by decision date (this changes #11's check window by one month).** The grid used to count returns earned from Jan 2023 as "test". But the Dec 2022 decision that earns January belongs to 2022, and the headline model was chosen partly on it.
  - Now every strategy's test is the returns from decisions in `SPLIT["test"]` (earned Feb 2023 on). 2020–22 is the decisions 2020–22 (earned Feb 2020 – Jan 2023).
  - Decided before the numbers were seen. Its effect: SPY's test Sharpe went from 1.29 to 1.21 (January 2023 was strong for SPY). The chosen rule is unchanged and now ties SPY on Sharpe (1.21 vs 1.21) instead of losing.
- **Result (preview):**
  - The headline at top 10 turned $10,000 into $11,858 on 2020–22 (SPY $13,146) and $11,640 on the test years (SPY $19,650; Sharpe 0.12 vs 1.21). That's below every plain rule shown, in both periods.
  - Its best version on 2020–22 (inverse vol + buffer) was its worst on the test.
  - The buffer cut the models' trading by about 3 portfolio-turns a year, and lifted the 6-month top-10 rule in both periods. Inverse vol helped on 2020–22 and hurt on the test.
  - 12 of 121 strategies edge SPY's test Sharpe, mostly single-stock ones. Of those declared in advance, only the chosen rule does, and that's a tie.

**Equity curves, risk over time and the SPY trend filter (4 Nov, #15), settled before any results**

- **A new notebook, `05_risk`** (recommended; you asked why the 300 KB cap exists). The cap keeps git history small: notebooks are committed with their outputs, and each rerun stores new images. It also forces summaries over dumps. 04 is at 278 KB, and its question ("how much did each make?") differs from 05's ("what was the path like, and does a market switch help?"). 05 recomputes its own strategies through the package, so it doesn't depend on 04 having run.
- **Trend signal: the 10-month average** (recommended): SPY's month-end adjusted close against the mean of its last 10 month-end closes, read at each decision. 10 months ≈ 200 trading days. It's Faber's (2007) monthly version of the classic 200-day rule. The length is a published convention, never tuned here (you asked what's special about 10: nothing, and that's the point).
- **Cash earns the Fed Funds rate** (recommended), the same risk-free rate as in every Sharpe ratio.
- **"Off" sells everything** (recommended): the whole portfolio goes to cash at the next open, every slot sold, costs charged. On re-entry every slot buys that month's picks.
- **All 121 strategies get a filtered version, plus filtered SPY (your call; I had recommended four).** The notebook reports the filter's *average* effect across all of them, and the pre-declared main versions in full. No filtered strategy is picked from the 121.
- **Curves:** two panels (2020–22 and the test years, each from $10,000, the shared months only), plus a separate "rules only, 2010 on" chart with and without the filter. You asked how 2010-on and 2020-on strategies are told apart: never on one chart, and every title states its window. The chosen rule is in-sample before 2023, which is noted wherever it appears before then.
- **Risk over time:** rolling 12-month return minus SPY's, and drawdown from the previous peak, both in the same two panels.
- **Bug fixed: the worst fall ignored a loss in the first month.** It was measured from the end of the first month, not from the starting amount. Grid and test-window numbers in the text were unchanged. The 2020–22 window starts with the February 2020 crash, so 92 drawdowns there deepened (the headline: −48% → −55%).
- **Palette PNGs (just done, a refactor within `plots`):** every chart is saved and shown as a 256-colour PNG, which looks the same at about a third of the bytes. Notebook 05 went from 505 to 195 KB, and 04 from 278 to 152 KB. The 300 KB check is unchanged. Pillow is now a declared dependency.
- **Result (preview):**
  - The filter lowered the Sharpe ratio of SPY and of every pre-declared strategy, in every period. Over 2010–26, filtered SPY made 7.8% a year against 14.3% (Sharpe 0.58 vs 0.88).
  - It was out at 31 of 201 decisions, and SPY averaged +3.5% in those months against +0.8% otherwise: it missed the rebounds.
  - It shortened long falls (the headline's 2020–22 worst fall: −55% → −28%), but deepened the rules' worst falls since 2010.
  - **The filter is not adopted.**

**Deeper analysis of the predictions (4 Nov, #16), settled one question at a time, all as recommended**

- **Descriptive only.** Every breakdown shows its sample size and a margin of error. Improvement ideas are written up as hypotheses with their reasoning, and are not built or tested on the test years (no untouched data is left to test them honestly).
- **Strategies:** the headline model and the 6-month rule, both top 10, held 1 month, main version (equal weight, no buffer). Like for like.
- **Breakdowns:**
  - regime: SPY above/below its 10-month average, VIX above/below its 2010–22 median (fixed in advance), and SPY's up vs down months;
  - sector;
  - year.

  Calendar month is left out (6–7 observations each). Always included: the wrong picks, and what the picks look like against the average member (within-month percentiles of volatility, size, beta and past return).
- **Margins of error are computed across months, not picks:** ten picks in one month move together, so counting them as ten independent tries would overstate the certainty.
- **Periods:** 2020–22 and the test years, separately.
- **A new notebook, `06_diagnostics`**; chapter 7 Part 4.
- **Findings (preview):**
  - The headline model buys volatile, beaten-down stocks (volatility in the 83rd–90th percentile, 6-month return in the 20th–24th): a rebound bet, not momentum.
  - In SPY's down months its picks beat SPY 33% / 39% of the time vs 53% / 51% for all members (about −3 and −2.6 standard errors). 16% of its picks left the index within a year (2% of members).
  - The 6-month rule is a winning market bet in the test years (+13.5 points in up months), with 46% of its picks in technology.
- **Hypotheses, not tested:** remove market exposure; a risk-adjusted target; the model as a filter on the rule; sector caps on the rule.

**Extras (5 Nov), your choice from my assessment**

- **Three extras, each its own issue in the Automation milestone:** the Telegram bot (#38), a live dashboard on Hugging Face Spaces with model monitoring (#40), and the monthly run on GitHub Actions (#39). Built in that order, after the core step each one needs. If time runs short they're dropped from the bottom, and never at the cost of #20 or the write-up.
- **Docker was left out** (it was ranked lowest): reproducibility is already covered by uv's lock file and CI.
- Every published pick says it's a research output, not advice, and what the backtest found.

**The monthly run (5 Nov, #17), settled one question at a time, all as recommended**

- **Both strategies' picks are published, labelled:** the headline model's top 10 and the 6-month rule's top 10. This starts a live head-to-head.
- **The headline is refitted monthly with fixed settings** on every month with a known result, using the backtest's one-month gap. It's never re-tuned.
  - Proven equal to the backtest: run as of Jan 2023, it reproduces the test fit's scores for all 497 members exactly, with the same top 10.
- **Schedule:** the first weekday of each month at 07:00 PC time, with catch-up. The task (registered with your approval) starts daily at 07:00 but exits at once unless it's a weekday and last month's picks are missing. PowerShell's task tools have no monthly trigger.
- **Prices for active tickers are re-downloaded in full, never appended:** the adjusted close is recomputed backwards after every dividend or split.
- **Checks that stop the run and write nothing:**
  - the latest decision isn't the month's last trading day (Good Friday, Memorial Day and Thanksgiving allowed for);
  - SPY lacks a close, or under 95% of members are priced;
  - a member has no sector;
  - the feature columns differ from the tuned model's.
- **Found on the first run:** Kenvue (KVUE) had left today's list, so its sector became "Unknown" and created a 153rd feature column. KVUE was added to `references/removed_sectors.csv`, and the run now stops on any missing sector.
- **The first picks file (decisions at the end of Oct 2026) was made on 5 Nov,** after the open it would trade at. Nothing leaks, but it wasn't tradeable. `made_at` records this. The first truly live month is the run on 1 Dec 2026.
- **Notebooks stay on the 4 Nov data snapshot until #20 (your call, as recommended).** The run refreshed `data/` (20 more delisted names, Kenvue's sector). #20 reruns everything once, on the complete data.

**Telegram notifications (5 Nov, #38), settled one question at a time, all as recommended**

- **Events:** the monthly run's picks and any failure; the nightly Alpha Vantage summary until the queue is empty (it ends with a reminder to unregister the task). Manual `--max-calls 0` checks stay silent.
- **Recipients, split by audience:** the picks go to a public channel, and failures plus the AV summaries go to a private chat.
  - You asked what there'd be to show if everything went to you only. The picks are already public in `reports/picks/`; a channel makes them viewable at `t.me/s/<name>` without an account and timestamps them independently.
  - That changed my first recommendation (a private chat only) to the split.
- **The live record in each message from Jan 2027:** last month's picks, from the next open to the month-end close, against SPY, and how many beat it. Only tradeable picks count (made before the next 08:30 Central open), so the Oct 2026 file is left out.
- **Defaults:**
  - plain `requests` (send-only, no bot framework or server);
  - a failed message never fails the run;
  - the token is never logged (errors by type only, since a request error's text holds the URL, and the URL holds the token);
  - `--dry-run`, a `find-chats` setup helper, and the token added to the notebook runner's secret scan.
- `append_record` tolerates a record written before a column existed (`price_ticker` was added for the live result).

**Hugging Face datasets (5 Nov, #18), settled one question at a time, all as recommended**

- **A private dataset with everything, plus a public dataset of derived tables.** Yahoo and Alpha Vantage prices are licensed for personal use, and their terms forbid redistribution.
  - Private (`sp500-momentum-data`): raw, interim, processed and models. It's reached by token from `--from-file`, the dashboard and the cloud run.
  - Public (`sp500-momentum-winners`): features and the member table without `close_adj`, `entry_px`, `dollar_vol` and `source`; model scores; live picks; report tables; and a card naming every source. Its licence is CC BY-SA 4.0, following Wikipedia's membership data.
- **A preview snapshot now, the final one in #20,** tagged (e.g. `final-2026-11`) as the version the write-up quotes.
- **Every upload scans the files for any secret from `.env` and refuses if one is found** (file names only are reported). The first scan: 704 files, none.
- **`predict run --from-file`** starts from the private snapshot; with `--no-download` it uses no data source at all.

**The live dashboard (5 Nov, #40), settled one question at a time, all as recommended**

- **Streamlit, hosted on Streamlit Community Cloud** (free, deployed from GitHub `main`, entry point `dashboard/app.py`). It reads the **public** dataset only, so the page holds no token, and it shows only public data.
  - The plan was HF Spaces, but deploying found that Spaces no longer offer a Streamlit type, and that Docker/Gradio Spaces on free hardware now need PRO (~$9/month).
  - Probed with throwaway Spaces, deleted at once: only static Spaces are free.
  - You chose Community Cloud (as recommended) over PRO or a static page. The code was unchanged; the Dockerfile and `hub deploy` were removed.
- **The ruff `include` list lacked `dashboard/`,** so lint and format silently skipped it (the same trap as `tests/` on 3 Nov). Fixed, and a comment now says every new code folder goes there.
- **Found while building drift: `ta_natr` is exactly 100 × `ta_atr`** (both are divided by the price, by design), so the "(in dollars)" labels added in #13 were wrong.
  - The labels are corrected now (the figure refreshes in #20).
  - Dropping `ta_natr` is added to #20's checklist, under the same rule as ROCP/ROCR.
- **The monthly run pushes both datasets after the picks.** The page re-reads within a day (cached). A failed push alerts the private chat and never fails the run.
- **Pages:**
  1. the overview, with the finding and "not advice";
  2. this month's picks;
  3. the live record (empty until Jan 2027, and saying so);
  4. backtest paths and the strategy table;
  5. model monitoring: the live hit rate against the base rate, plus input drift (PSI of the headline's most important features, this month against 2010–22).

  The "why the model loses" page was left out; the exposure analysis stays in notebook 06 and chapter 7.
- **Small precomputed public tables** (strategy returns, the live record, monitoring), so the page never downloads the 77 MB feature table. The page logic is plain pandas, tested in CI, with a Streamlit smoke test.

**Checked against the course's project criteria (5 Nov, evening; the criteria page read, not recalled)**

- About 29–30 of 36 points as things stood, and 33–35 with the gaps closed. Two **mandatory** items were open:
  - the run-all notebook (#19);
  - "vector simulations", dropped in #14.
- **The vector simulation is added back as a labelled cross-check (#47; recommended, your call):** `sim1_` / `sim2_` per prediction, $100 per pick, compared with the exact simulator. This reverses part of the #14 decision for deliverable completeness; no result changes.
- **Docker is re-added (#48; recommended),** after the core items and before #39: containerization is a scored bonus.
- #22 now lists the README items the criteria name: a data-sources section with the 20+ new features, the dataset size (3.67 M daily rows), and the decision rule in plain terms.
- **Order until #20:** #19 → #47 → #26 → #20 prep → #22 (the parts without numbers) → #48 → #39.

**The run-all notebook (6 Nov, #19)**

- **`notebooks/00_run_all.ipynb`:** data → transform → predict → simulate → the latest trades, one call per step into `sp500_momentum/pipeline.py`, which reuses the monthly run's own functions.
- **The committed copy runs on local files** (your choice, as recommended): offline and deterministic. `hub` and `download` are one setting away.
- **No side effects:** no Telegram, no Hugging Face push, no live record. The full search sits behind `RETRAIN` (off).
- The monthly run's checks are applied as is (including the 95% priced threshold).

**The vector simulation cross-check (6 Nov, #47), all as recommended**

- **The course's method, mapped monthly** (from its Week 4 notes, read, not recalled):
  - $100 per pick at the next open;
  - 0.1% on the buy and 0.1% on the sell for every pick, kept stocks included;
  - per-row `simN_gross` / `simN_fees` / `simN_net`;
  - capital = $100 × hold × picks per decision month (75th percentile);
  - CAGR = the growth of that fixed capital, annualised over the months it was in use.
- **Three strategies:** `sim1_` the headline (top 10, 1 month), `sim2_` the 6-month rule (top 10, 1 month), and `sim3_` the chosen rule (top 5, 6 months: overlapping positions, capital $3,000).
- **The results go into notebook 04 and chapter 7 in #20** (your choice): rerunning 04 now would shift its numbers away from chapter 7. The code and tests ship now.
- **Cross-check (preview, test years, 45 months):**

  | Strategy | Vector CAGR | Exact CAGR |
  |---|---|---|
  | Headline | 5.6% | 3.6% |
  | 6-month rule | 24.5% | 33.0% |
  | Chosen rule | 42.1% | 60.7% |

  - **The same ranking.** The levels differ as the method predicts: no compounding and fees on every pick (lower for the rules); volatility drag in the exact one (the headline's simple sum is higher).
- **A bug in my first draft:** the window counted the Oct 2026 decisions, whose month isn't over (46 months instead of 45). Now the span runs from the first decision to the end of the last completed hold; a test covers it.

**The book as a website (6 Nov, #26), both as recommended**

- **A build hook (`scripts/mkdocs_hooks.py`):** the charts in `reports/figures/` are added to the site as `figures/`, chart paths are rewritten, and links outside `docs/` go to the file on GitHub. The chapters' Markdown is unchanged, so GitHub rendering is untouched.
  - Not chosen: saving charts into `docs/` (it breaks the template layout and every path) or a third-party plugin (a dependency for a small job).
- **Published on GitHub Pages** (https://siddharthps.github.io/sp500-momentum-winners/) by `.github/workflows/pages.yml` on merges to `main` that touch the book. Pages was enabled with build type "workflow" through the API.
- **`mkdocs build --strict` runs in CI:** a broken chart or link fails the PR.
- The `scripts/` folder is added to ruff's include list (the trap from 3 and 5 Nov).
- Material for MkDocs announces its end of life in May 2027 (successor: Zensical). No effect on this project.

**Preparing the final rebuild (6 Nov, #20 prep)**

- **Flagged price moves (>+100% or <−75% in a month): all 6 reviewed and all real, so no fixes.**
  - APA, Mar 2020 (−84%): one day was −54% (the oil collapse of 9 Mar 2020). APA, Apr 2020 (+226%): a steady rebound.
  - SanDisk Jan 2026, Intel Apr 2026, Dell May 2026: steady climbs over 13–14 up days, no split, heavy volume.
  - Moderna Aug 2026 (+156%): one day was +177%, on 199 M shares against a usual 6 M (33×), with follow-through over the next days.
  - **Second source (your approval, one Alpha Vantage call from that day's two spare):** AV agrees with Yahoo exactly (close $140.34, +156%; volume within 1.6%). The call was saved to a scratch folder only, not the pipeline.
- **DISCA → WBD rename (a config entry; applied when #20 rebuilds):** Discovery's class A had 145 member-months (2010–Mar 2022) with no price.
  - Alpha Vantage's WBD series runs from 2005 without a break and tracks DISCK at a 0.98 monthly correlation before 2022.
  - Discovery acquired WarnerMedia and renamed itself (the same entity; DISCA → WBD 1:1), so this is a true rename, not a different company. A test covers the membership walk.
- **`ta_natr` is dropped inside #20, not before:** any rebuild before the retrain would otherwise trip the monthly run's column check (by design).
- **`pipeline rebuild-all`:** monthly table → features → models → notebooks → snapshots (tagged), timed, stopping at the first failure. `--dry-run` prints the checks to do by hand before (AV done and unregistered, `ta_natr`, the vector section, `DATA_STATUS`) and after (numbers, the book, the dashboard).

**Tooling:** Cookiecutter Data Science v2.3.0 layout, uv, Python 3.12, pytest, ruff. No Makefile
(Windows), so each step is a command in `sp500_momentum.dataset`.

**Repo:** public since 3 Nov 2026 (it was private until then). `main` is protected (see Planning and workflow).
