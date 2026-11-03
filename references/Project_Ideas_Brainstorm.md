# Final Project: Idea Brainstorm

Working notes for choosing the final project. The sessions are **idea generation only, no code**. Each discussion goes into the log in Section 8. Once something is decided, it moves to Section 9. Section 7 holds the draft dataset design for idea H.

Sources used: the course's final project brief and rubric (re-checked 2 Nov 2026 after it was updated with the 2026 dates) and the course's Week 1–4 material and summaries, including Homework 4. Week 5 hadn't started when this was written.

*This file was moved into this repo's `references/` on 2 Nov 2026. Older entries were written while it lived in the course repo.*

> **Deadline: Fri 20 Nov 2026, 23:59:59 Dublin time** (attempt 1). The README says the project is meant to be done within about 2 weeks after Homework 5.

---

## 1. What the Project Has to Be

Build an **end-to-end algo-trading strategy**:

1. Pick data sources (APIs, scraping, files).
2. Combine them into **one table**.
3. Transform the data, create features and prepare it for ML.
4. Train one or more models to **predict future returns**.
5. Turn the predictions into a **trading strategy** and simulate it.
6. **Automate** the whole thing.

Deliverables: README, research notebooks, `.py` scripts for each step, a workflow/command list, `requirements.txt` or Pipfile, and optionally a Dockerfile. **No data files on GitHub.** Data goes on a drive, or must be fully downloadable from the APIs.

---

## 2. The Rubric as a Planning Tool

Maximum **36 points**. To pass you need the **6 bold (minimum) points** and you have to present your own results.

**Peer review:** the projects are marked by other students. To get points for your own project, you have to **review 3 other projects**, and each review earns 3 extra points. The 2026 review window isn't in the README yet. In 2025 it opened on the submission deadline and ran for about 9 days. So the README has to be clear enough for a peer to mark it without help.

| Area | Max | Minimum point (bold) | Extra points, and whether the **idea choice** affects them |
|---|---|---|---|
| Problem description | 4 | Brief README | **New problem definition** (idea-dependent). Clear context and end goal. Clear step-by-step write-up |
| Data sources | 4 | Lecture sources and features | **New data source** that isn't yfinance or FRED (idea-dependent). **>1M records** (idea-dependent). 20+ new described features |
| Transformations + EDA | 3 | One combined table, feature sets defined | 5+ new transformed features. EDA of the target and its correlations |
| Modelling | 5 | Decision tree or random forest | 2+ lecture models. Custom decision rules. Hyperparameter tuning. New models (XGBoost, LSTM, …) |
| Trading simulation | 8 | Vector simulation for 1 strategy | 2+ strategies. Exact day-by-day simulation with reinvestment. Sharpe, drawdown and comparison with a benchmark. Risk management. A new strategy type. **Beat a realistic benchmark** (idea-dependent). Deep error analysis |
| Automation | 5 | Scripts + one notebook that runs the workflow | Dependencies managed. Cron re-run. Two run modes (from a file / live download). Incremental loading |
| Bonus | 7 | — | Well-designed code. **Broker API** (idea-dependent). Monitoring (dashboard / Telegram bot). Docker. Cloud. Reviewer's choice (1–2) |

**Takeaway:** most points come from *how well* the project is built, whatever the idea. About **five points depend directly on which idea we pick**: new problem, new data source, >1M rows, broker API and beating the benchmark. The idea should make these easy to get.

> Note: the "new problem" point says *not just the current setup of a week-long strategy for the largest stocks*. The class universe already mixed US, European and Indian large caps on a 30-day horizon, so an idea has to be **clearly different** from that to earn this point.

---

## 3. What We Already Have from Weeks 1–4

| Piece | What the class built | Reusable? |
|---|---|---|
| Data sources | yfinance (stocks, indexes, ETFs, gold, oil, Bitcoin, VIX), FRED (CPI, Fed Funds, Treasury yields, GDP), scraping (Trading Economics, companiesmarketcap, IPO lists), Eurostat yield curve | Yes. Covers the minimum data point |
| Features | ~55 TA-Lib indicators, 61 candlestick patterns, growth windows (1–365 days) for the stock and the markets, macro, calendar and ticker dummies | Yes. Needs 20+ *new* ones on top |
| Dataset | 33 large caps, 2000–2026, **~202k rows**, 301 features (208 after dropping ticker / month-week dummies) | Pattern yes. Too small for the >1M point |
| Target | 30-trading-day growth > 0 (or > 2.2% in HW Q3) | Will change with the new problem |
| Models | Hand-written rules, decision tree, random forest, logistic regression, neural network, probability thresholds | Yes |
| Simulation | $100 per "buy" signal, 30-day hold, 0.2% fees per round trip, capital = 30 × 75th-percentile daily trades, approximate CAGR | Starting point only |
| **Not covered yet** | Exact simulation with reinvestment, Sharpe / drawdown, buy-and-hold benchmark, scripts, cron, Docker, broker APIs | All rubric points still open |

---

## 4. Lessons from Weeks 1–4 That Should Shape the Idea

1. **The edge is thin.** 57% of test stock-days went up anyway. The best models reached 60–63% precision.
2. **Simple momentum is hard to beat.** "Buy what went up last month" (pred1) made ~11.9% CAGR, about the same as the best tree.
3. **The benchmark bar is high.** No buy-and-hold benchmark was run in class. A rough check: the S&P 500 went from about 3,600–4,100 (Sep 2022) to about 7,700 (Sep 2026). That's roughly **17–21% a year**, price only. The best class strategy made ~12–13%. CAGR on "capital needed" isn't measured the same way, but the "exceptional profitability" point means beating something like this. We should plan for that from the start.
4. **The macro regime drives everything.** Inflation and interest rates were the first splits in every tree. Models trained on 2000–2022 became very cautious in the 2022–2026 high-rate regime.
5. **Busy days were the best days.** When the random forest liked many stocks at once, it was catching a market-wide upswing (71% hit rate on days with 11+ signals). Capping the number of trades per day destroyed returns.
6. **"Two models must agree" made things worse.** Each model's good trades were the ones the other model didn't pick.
7. **Results are fragile.** The random seed alone moved CAGR by about ±1.5 points. Fixed thresholds broke as soon as the target changed. The scikit-learn version changed the results too.
8. **Hygiene to get right this time:** pick settings on validation, not test. Lag monthly macro data by its publication date. Don't score models on rescaled data by mistake. Pin library versions.

---

## 5. Candidate Ideas (Shortlist)

**Filtered on 2 Nov 2026 against these constraints:**

| Constraint | Value | What it rules out |
|---|---|---|
| Time | **10 days × 3 hrs ≈ 30 hours** in total | Anything with a fragile scrape or a brand-new data pipeline to build |
| Market | Any | Nothing |
| Goal | **A solid pass is the MVP.** Extra points are a bonus | Ideas where the minimum points are already hard to reach |
| Broker / exchange account | **No, for now** | Ideas that need an account just to get the data. The broker bonus point is dropped |
| Paid data | **Alpha Vantage key** only | Ideas that need paid data. The free Alpha Vantage tier allows about **25 calls a day** (to check which plan the key is on), so it suits a few dozen tickers or one-off pulls, not 500 stocks |
| Compute | Local, plus Colab / cloud if needed | Nothing |

Three ideas are left: **H** (the lead), **D** (the safe fallback) and **A** (the alternative). The ideas that were removed, and why, are listed at the end of this section.

### A. Crypto, hourly or 4-hourly

- **Pitch:** predict whether the top 10–20 coins rise over the next 24 hours, by more than fees.
- **Data:** exchange OHLCV via the Binance public API or CCXT, funding rates, open interest, Fear & Greed index (alternative.me), possibly on-chain metrics.
- **Why it's interesting:** markets trade 24/7. Long-short is natural on perpetual futures. 20 coins × 6 years × 8,760 hours ≈ **1M rows**. Exchanges have testnets for paper trading.
- **Benchmark:** Bitcoin buy-and-hold. Week 2 had Bitcoin **down 33%** over the past year, so a long-short strategy could plausibly beat it.
- **Risks:** very noisy, fees bite harder at short horizons, sharp regime changes. Exchange access varies by country.
- **Fit with the constraints (2 Nov):** stays in. Price history needs **no account**: Binance publishes free bulk files (data.binance.vision), and its public API needs no key. The testnet would need an account, so drop the broker point. The extra cost is that most of the class code assumes one row per stock per *day*. Moving to hourly rows means rewriting the features, the split and the simulation, probably **8–10 of the 30 hours**. To cut that, use 4-hourly or daily bars and keep only the parts that need no account (prices, Fear & Greed). Funding rates and open interest are optional.

### D. Sector / ETF rotation, weekly or monthly

- **Pitch:** rank 11 sector ETFs (plus factor or country ETFs) by expected return against SPY. Go long the top ones and short the bottom ones.
- **Why it's interesting:** a natural long-short "new strategy". The S&P 500 benchmark is built in. Directly uses the "macro regime matters" lesson.
- **Risks:** a small dataset (well under 1M rows), so it's easy to overfit, and the >1M point is lost unless it's extended.
- **Fit with the constraints (2 Nov):** stays in as the **safe fallback**. It's the cheapest to build: about 20–30 ETFs from yfinance, FRED macro, and no scraping. It's also small enough for the free Alpha Vantage tier, which could serve as the "new data source" (e.g. its economic or sentiment endpoints, to check). It gives up about 1–2 points (>1M rows, maybe the new data source), but the class code carries over almost as is, which leaves the most time for the simulation and automation points.

### H. Monthly winner on the S&P 500 (your idea, 18 Oct)

- **Pitch:** at the end of each month, find the S&P 500 stock that rose the most that month. Buy it at the start of the next month and hold it for **X months**. Find the best X.
- **What it is:** a form of **momentum investing**: buy recent winners because they tend to keep winning. It's one of the most studied effects in finance, so there's plenty to compare against.
- **What past research says.** These are points to test, not settled answers:
  - Stocks that won over the **past 3–12 months** have tended to keep beating the market for the **next 3–12 months** (Jegadeesh & Titman, 1993). This is the classic momentum effect.
  - Stocks that won over the **past 1 month** have tended to **fall back** the following month (short-term reversal). That's why the classic version looks at the past 12 months and **skips the most recent month**. The effect is weaker in large caps today, so it's worth checking on our data.
  - Over **3–5 years**, past winners have tended to **lag** (long-term reversal, De Bondt & Thaler, 1985). Your yearly version (hold for 2+ years) falls between these two effects. That's a good reason to test it directly.
  - Momentum strategies have occasional **sharp crashes**, usually when beaten-down stocks rebound hard (e.g. spring 2009).
- **Main pitfalls:**
  - **Survivorship bias, the biggest risk.** Today's S&P 500 list holds only the companies that survived and the winners that were added later. Running the test on today's list makes almost any "buy winners" rule look good. We need **point-in-time membership**, meaning who was in the index *on each date*. Wikipedia's list of S&P 500 changes can be scraped for this. Prices of delisted companies are hard to get from yfinance, so that limit has to be documented.
  - **One stock is a concentrated bet.** The result may hinge on a handful of picks (an NVIDIA-type winner). Compare the top 1 with the top 3, 5 and 10.
  - **Few decisions.** One pick a month gives only about 300 picks in 25 years. That's a small sample, and luck plays a big part.
  - **One-off jumps.** A month's top performer is often a single-event story, like a takeover bid (the price jumps, then goes flat) or an earnings surprise.
- **Turning it into an ML project.** The rubric needs a model that predicts returns:
  - The plain rule is the **baseline strategy**.
  - **Option 1:** a model predicts *which* of the month's top-N winners will keep beating SPY over the next X months. Possible features: what drove the rise (earnings or not), volume surge, volatility, sector, distance to the 52-week high, market regime, and 3-, 6- and 12-month momentum.
  - **Option 2:** for all ~500 stocks, predict the next-X-month return relative to SPY and buy the top-ranked ones. Last month's return becomes just one of the features.
- **Settings to explore:** lookback (1, 3, 6 or 12 months, with or without skipping the latest month) × number of stocks (1, 3, 5, 10) × hold X (1–24 months) × equal or probability weighting. Pick the settings on the validation period only, so we don't overfit the grid.
- **Rubric fit:** long-term trading is one of the rubric's own examples of a new problem. Daily data for ~500 stocks × 25 years ≈ **3M rows**. The point-in-time membership scrape is a new data source. SPY is the natural benchmark. Monthly orders are easy to place through a paper-trading API (Alpaca). Overlapping holdings (a new buy each month, each held X months) suit the exact-simulation point.
- **Fit with the constraints (2 Nov):** stays in as the **lead idea, with a reduced scope**. The broker point is dropped (no account). The two slow parts have to be time-boxed:
  - **Membership scrape:** the Wikipedia changes table only. Cap it at about **3 hours**, and start in 2010 if the older history is patchy.
  - **Delisted companies:** **measure the gap** (count how many past members yfinance has no prices for) and document it, instead of fixing it. Alpha Vantage's listing-status endpoint lists delisted tickers in a single call, which helps with the count. Whether the free tier gives their full price history needs checking.
  - **Features:** start with the groups that are cheap to build from daily prices (1–6, 9, 12 in Section 7.3). Leave the fundamentals (group 13) out.

### Quick comparison

The broker column was dropped (no account for now). "Reuse of class code" matters most with only 30 hours.

| Idea | New problem | New data source | >1M rows | Clear benchmark | Reuse of class code | Rough build time | Role |
|---|---|---|---|---|---|---|---|
| **H. Monthly winner (S&P 500)** | ✓ | ✓ membership scrape | ✓ (daily) | ✓ SPY | Medium: daily → month-end rows | ~25–30 h | **Lead** |
| D. Sector / ETF rotation | ✓ | ~ (Alpha Vantage?) | ✗ | ✓ SPY | High | ~18–22 h | **Safe fallback** |
| A. Crypto, 4-hourly / hourly | ✓ | ✓ Binance files | ✓ (hourly) | ✓ BTC | Low–Medium: new time grid | ~28–32 h | Alternative |

All three can reach the 6 minimum points comfortably. They differ in how many extra points they leave time for.

### Ideas removed on 2 Nov (and why)

| Idea | Why it was removed |
|---|---|
| B. India, broad universe | NSE bhavcopy and FII/DII scraping is fragile, and survivorship bias would need the same membership work as H, in a market with less free history. Too much risk for 30 hours |
| C. US intraday / hourly | Free intraday history needs an Alpaca or Polygon account (ruled out). yfinance hourly only goes back ~2 years, and the free Alpha Vantage tier is too slow to pull it for many stocks |
| E. Earnings events | Needs earnings history for ~500 stocks. On the free Alpha Vantage tier (~25 calls a day) that alone takes weeks. The event table is small too (~30k) |
| F. Alt-data overlay | Not a project on its own. Text and timestamp cleaning doesn't fit in 30 hours. Moved to the parking lot as a possible add-on to H or D |
| G. Sports betting / macro allocation | Betting reuses almost none of the class code. Macro allocation is a smaller version of D |

---

## 6. Building Blocks That Fit Any Idea

A pick-and-mix list to come back to once the main idea is chosen.

- **New features:** rank against peers on the same day, relative strength against the index, distance to the 52-week high and low, volatility regime (VIX percentile), macro lagged to its publication date, days to the next earnings date or holiday, unusual volume, FX moves.
- **Models:** XGBoost / LightGBM, walk-forward retraining, probability calibration, maybe an LSTM for the "new model" point.
- **Strategies:** long-short, probability-weighted sizing, stop-loss / take-profit, trade only in certain volatility or rate regimes (Strategy D from HW4 worked a little), near-52-week-low filter, max N concurrent positions.
- **Simulation upgrades:** exact day-by-day simulation with compounding, Sharpe ratio, max drawdown, rolling returns, and a buy-and-hold benchmark from day one.
- **Automation:** one script per step plus an orchestrating notebook, pinned versions, scheduled re-runs (Windows Task Scheduler, WSL cron or GitHub Actions), "from file" vs "live download" modes, incremental loading into Parquet / DuckDB / SQLite on a drive or bucket.
- **Bonus:** Docker, a small cloud deployment, a Telegram bot for daily trades, a Streamlit dashboard.

---

## 7. Idea H: How the Fields Would Be Built (Draft)

### 7.1 The shape of the table

- **One row per stock per month-end** (the decision date). Each month includes every stock that was **in the S&P 500 on that date**.
- About 500 stocks × 12 months × ~25 years ≈ **150k rows** in the modelling table.
- It's built from a **daily price table** of 500+ stocks × 25 years, about **3M+ rows**, which covers the >1M point.
- **Golden rule:** every field must be known by the **close on the last trading day of the month**. The trade happens at the **next day's open**.

**Why include every member, not just the top winners?** "Buy last month's best" is the same as "sort all members by 1-month return and take the top N". With every member as a row, the plain rule and the ML model are scored on the same table, and the model can find good stocks the rule misses. A table of only each month's top 20 winners would have about 6,000 rows, too few to train on.

### 7.2 What we predict (TO_PREDICT)

| Field | Meaning |
|---|---|
| `fwd_ret_Xm` | Return from the next day's open to the open X months later, for X = 1, 3, 6, 12, 24 |
| `fwd_excess_Xm` | The same, minus SPY's return over the same window |
| `is_beat_spy_Xm` | 1 if `fwd_excess_Xm` > 0. **The main target** |
| `is_top_decile_Xm` | 1 if the stock lands in the top 10% of members over the window. A stricter target, like the "> 2.2%" target in HW4 Q3 |

Stocks that leave the index or get delisted during the hold stay in, valued at their last available price and flagged. Dropping them would bring survivorship bias back in.

### 7.3 Features (NUMERIC and DUMMIES)

| # | Group | Example fields | Why it matters |
|---|---|---|---|
| 1 | Past returns | 1-, 3-, 6- and 12-month returns, plus the 12-month return **skipping the latest month** | The core of the idea. Tests the 1-month vs 12-month question directly |
| 2 | Ranks | Each return above as a percentile among all members that month, and within the stock's sector | The idea is about being *the best*, which is relative. Ranks also stay comparable in bull and bear markets |
| 3 | Relative strength | Return against SPY and against the stock's sector ETF (XLK, XLF, …) | Separates "the stock won" from "its whole sector won" |
| 4 | Quality of the move | Share of up days in the month, biggest single-day gain ÷ the month's gain, gap-up days, this month's volume ÷ the 12-month average, earnings report in the month (flag) | Separates steady climbs from one-day jumps such as takeover bids or earnings surprises. **Likely the key to "which winners keep winning"** |
| 5 | Risk | Volatility over 1 and 12 months, beta against SPY, max drawdown over 12 months, downside volatility | Big winners are often high-risk stocks. Also needed for position sizing and stop-losses |
| 6 | Price position | Distance to the 52-week high and low, above the 50- and 200-day averages, new all-time high (flag) | Stocks near their highs have tended to keep their momentum |
| 7 | Size and liquidity | Average daily dollar volume, price level, market cap where available | Momentum behaves differently in mega caps and smaller members |
| 8 | Index membership | Months since joining the S&P 500, recently added (flag), sector dummies | Captures the effect of new additions and of crowding into one sector |
| 9 | Market regime | SPY 12-month return, SPY above its 200-day average, VIX level and percentile, 10-year yield, yield-curve slope, core inflation (lagged to its publication date), Fed Funds rate | The Week 3–4 lesson: the macro regime drove the models. Momentum crashes tend to come in sharp rebounds after bear markets |
| 10 | Breadth and dispersion (built from our own table) | Share of members above their 200-day average, gap between the top and bottom deciles' returns | Momentum has tended to pay more when winners and losers are far apart |
| 11 | Strategy track record | How past winners did over the last 3, 6 and 12 months | The edge comes and goes in phases ("momentum of momentum") |
| 12 | Calendar | Month of year (dummies), earnings-season flag | Momentum has historically reversed in January |
| 13 | Fundamentals (stretch) | EPS growth, earnings surprise, P/E | Helps explain *why* a stock rose. Historical, point-in-time fundamentals are hard to get free: yfinance covers only about 4 years |

That's **60+ fields before dummies**, which easily covers the "20+ new features" and "5+ new transformations" points. Ranks, ratios, flags and binned variables (e.g. VIX buckets) all count as transformations.

### 7.4 Where each piece comes from

| Data | Source |
|---|---|
| Daily prices and volume | yfinance |
| S&P 500 membership over time, sectors | Wikipedia: the current list plus the table of changes, scraped. **The new data source** |
| SPY, sector ETFs, VIX | yfinance |
| Macro | FRED |
| Earnings dates | yfinance (recent years only) or scraping. Stretch goal |

### 7.5 Problems to plan for

- **Delisted and renamed companies.** yfinance often has no data for companies that were bought out or went bust, and tickers change (FB → META). Options: (a) accept it and **measure** the gap, by counting how many past members have no prices; (b) start later (e.g. 2010), where coverage is better; (c) a low-cost paid source with delisted history. To decide later.
- **Gaps in Wikipedia's change history**, especially further back. Needs checking.
- **Overlapping targets.** With X = 12, targets in consecutive months share 11 months, so the rows aren't independent. Train, validation and test need a **gap of X months between them**, or the test period leaks into training.
- **Total return.** Use dividend-adjusted prices so the stocks compare fairly with SPY's total return.

### 7.6 What the class built: field counts (from the Week 2 and Week 4 notebooks)

| Feature set | Count | What's in it |
|---|---|---|
| GROWTH | **54** | Price ratio over 1, 3, 7, 30, 90 and 365 days, for the stock itself and for 8 markets (DAX, S&P 500, Dow, India ETF, gold, WTI, Brent, Bitcoin): 9 × 6 |
| TECHNICAL_INDICATORS | **55** | TA-Lib momentum, volume, volatility, cycle and price indicators (RSI, MACD, CCI, ADX, OBV, ATR, …) |
| TECHNICAL_PATTERNS | **61** | TA-Lib candlestick patterns, each flagged on the day it appears |
| CUSTOM_NUMERICAL | **8** | SMA10, SMA20, SMA10 > SMA20 flag, daily range ÷ close, 30-day volatility, log volume, dividend paid flag, split flag |
| MACRO | **8** | Potential GDP growth (year and quarter), core CPI (year and month), Fed Funds, 1-, 5- and 10-year Treasury yields |
| **NUMERICAL total** | **186** | |
| DUMMIES | **115** | Month 12, weekday 7, ticker 33, region 3, month + week-of-month 60 |
| **All features** | **301** | 208 after HW4 Q1 dropped the ticker and month-week dummies |
| TO_PREDICT | 2 | `growth_future_30d` (ratio) and `is_positive_growth_30d_future` (yes/no) |

Week 3 used 239 of these (184 numeric + 55 dummies). Module 4 added the dividend and split flags and the month-week dummies.

**How the class modelled with them:**

1. **Defined feature sets** as named lists: GROWTH, TECHNICAL_INDICATORS, TECHNICAL_PATTERNS, CUSTOM_NUMERICAL, MACRO, CATEGORICAL → DUMMIES, TO_PREDICT, TO_DROP. A check confirmed that no column was left unassigned.
2. **Cleaned the data:** infinities and blanks set to 0.
3. **Split by time** into 70% train, 15% validation and 15% test.
4. **Hand-written rules** as `pred0`–`pred4` (e.g. "stock rose over the last 30 days").
5. **Models:** decision tree (depth search), random forest (depth × number of trees), logistic regression, neural network. All were trained on train + validation, with **precision on test** as the main score.
6. **Probability thresholds:** "buy if probability ≥ 0.55" and similar rules, as `pred8`–`pred11`.
7. **Simulation `sim1_`:** $100 on every "buy", held for 30 days, 0.2% fees. Capital = 30 × the 75th percentile of trades per day. CAGR over the test period.

### 7.7 Can we do the same for idea H? Yes, with a few changes

The **whole flow carries over**: the named feature sets, time split, `pred` rules, the same models, `sim1_` and the comparison table. The changes come from switching from "one row per stock per day" to "one row per stock per month-end, ranked against ~500 others".

**Fields: what to reuse, change or drop**

| Class feature set | For idea H | Why |
|---|---|---|
| GROWTH (54) | **Reuse the method**, change the windows to 21, 63, 126 and 252 trading days (1, 3, 6, 12 months) plus 12-months-skip-1. Add SPY and the stock's sector ETF to the market list | Month-scale windows fit a monthly decision. The 1–7 day windows matter less |
| TECHNICAL_INDICATORS (55) | **Reuse**: compute on daily data, keep the value on the month's last trading day | Same TA-Lib code. **But** some (OBV, A/D, average and median price) are raw levels that can't be compared across 500 stocks. Use their *change* or *rank* instead |
| TECHNICAL_PATTERNS (61) | **Drop, or squash into a few counts** (e.g. bullish vs bearish patterns in the month) | A one-day candle on the last day of the month says little about the next 6–12 months. Saves 61 noisy columns (HW4 Q1 lesson: fewer, better features) |
| CUSTOM_NUMERICAL (8) | **Reuse** volatility, log volume, the moving-average flag, dividend and split flags | Still meaningful at month-end |
| MACRO (8) | **Reuse, plus VIX properly.** In class, VIX got renamed `Close_y` in the merge and was then dropped, so it never reached the models. Lag monthly data by its publication date | The macro regime was the strongest signal in class |
| DUMMIES (115) | **Month (12) + sector (11) only.** Drop weekday (always month-end), ticker (500+ columns, and HW4 Q1 showed dropping tickers helped) and month-week | Sector replaces ticker as the "identity" signal |
| *New* (Section 7.3) | Ranks, relative strength, quality of the move, risk, 52-week position, index membership, breadth and dispersion, strategy track record | These carry the idea itself. The class had no cross-stock comparison at all |

**Rough count:** about 35 growth + 55 indicators + 5 pattern counts + 8 custom + 10 macro + 40 new + 23 dummies ≈ **175 features**. That's a similar scale to the class's 208–301, on about 150k rows (class: 202k).

**Modelling: what changes**

| Step | Class | Idea H |
|---|---|---|
| Target | Stock up after 30 days | Stock **beats SPY** after X months |
| Split | 70 / 15 / 15 by date | Same, plus a **gap of X months** between the sets (overlapping targets) |
| Manual rules | `pred0`–`pred4` | `pred0` = **your rule** (top 1 by last month's return). `pred1` = top 10 by last month. `pred2` = top 10 by 12-months-skip-1 (classic momentum) |
| Models | Tree, RF, LogReg, NN | Tree, RF, plus **XGBoost / LightGBM** for the "new model" point |
| Turning probability into "buy" | Fixed threshold (≥ 0.55) | **Top N by probability each month.** It fits the idea, and HW4 showed fixed thresholds break easily. Compare with a threshold rule as a second strategy |
| Main score | Precision on all buys | **Precision of the top-N picks** per month, and their average return against SPY |
| Simulation | $100 per signal, capital estimated from the 75th percentile of trades per day | $100 per pick, N picks a month, held X months. **Capital is exactly N × X × $100**, so there's no estimate, and CAGR is cleaner. Then an exact simulation with reinvestment for the extra point |

---

## 8. Discussion Log

### Session 1 — Sunday, 18 Oct 2026 (idea generation, no code)

- Set up this file.
- Reviewed the project brief and rubric, and the Week 1–4 summaries, to see what was already built in class and what lessons carry over.
- Drafted a starter menu of ideas (Section 5) to react to.
- **Your initial idea (now idea H):** each month, buy the S&P 500's best performer from the previous month and hold it for X months. Find the best X later. You noted that a **yearly** version (buy last year's best stock, hold for at least 2 years) is known to beat the market.
- **Discussion:**
  - This is **momentum investing**. Research supports holding 3–12-month winners for 3–12 months. It also warns that **1-month winners tend to fall back** in the short term, and that winners tend to **lag over 3–5 years**. So both the monthly lookback and the 2-year hold are worth testing, not assuming.
  - The biggest risk is **survivorship bias**: we must use who was in the S&P 500 at each date, not today's list.
  - A plain rule isn't an ML project yet. The rule becomes the baseline, and a model either **picks which winners keep winning** or **ranks all ~500 stocks**.
- **Your answers:**
  - The yearly result you'd seen was most likely tested on **membership as it stood each year**, not today's list.
  - A **small group** (top 3–10) is fine, but only if it shows a real edge over the single top stock.
- **How to build the fields** (full draft in Section 7):
  - **One row per stock per month-end**, covering every S&P 500 member on that date: about 150k rows, built from about 3M daily rows.
  - The targets are **X-month returns against SPY**.
  - **13 feature groups**. The most promising for this idea is **"quality of the move"**: was last month's gain a steady climb or a one-day jump?
  - Every field must be known by the month-end close, and the trade happens at the next open.
- **You asked:** how many fields did the class create, how did it model with them, and can we do the same? (Full answer in Sections 7.6–7.7.)
  - **Class:** 186 numeric features (54 growth, 55 indicators, 61 candles, 8 custom, 8 macro) + 115 dummies = **301**.
  - The class modelled with rules, a tree, a random forest, logistic regression and a neural network, scored by precision on test, then ran the `sim1_` $100-per-signal simulation.
  - **Idea H can follow the same flow.** Reuse the growth method (with monthly windows), TA-Lib indicators and macro data. Drop the candlestick patterns and the ticker and weekday dummies. Add the cross-stock fields (ranks, quality of the move, etc.). That's about **175 features on ~150k rows**.
  - Main modelling change: **buy the top N by probability each month** instead of using a fixed threshold. Capital becomes exactly N × X × $100.
  - Found in passing: **VIX never reached the class models.** It was renamed `Close_y` in the merge and then dropped.
### Session 2 — Monday, 2 Nov 2026 (review, no code)

- Re-read the updated project brief and checked the Week 1–4 material against this file.
- **README changes:**
  - **2026 deadline: Fri 20 Nov 2026, 23:59:59 Dublin time.** That's 18 days from today, and Week 5 / Homework 5 hasn't started yet. Open question 1 is answered.
  - The README says the project is meant to take about 2 weeks after Homework 5.
  - Peer review is now spelled out: review 3 projects, 3 extra points for each one. Added to Section 2.
  - The rubric itself hasn't changed (still 36 points, 6 minimum), so Section 2 still holds.
- **Weeks 1–4:** nothing has changed since 18 Oct. The numbers in Sections 3, 4 and 7.6 still match the summaries (57% baseline, 60–63% precision, ~11.9% CAGR for pred1, the `Close_y` VIX issue). Week 5 is empty, so Week 5 material (probably automation / deployment) isn't covered here yet.
- **What the deadline means for idea H:** with about 2.5 weeks, the slow parts are the **point-in-time membership scrape** and **delisted-company prices** (Section 7.5). We may need to keep their scope small (e.g. start in 2010 and measure the gap rather than fix it), so the time goes to the simulation and automation points.
- **Your constraints (answers to open questions 2–7):**
  - **Time:** 10 days × 3 hours ≈ **30 hours**. You're planning on 10 days, which is earlier than the README's 20 Nov date, so the plan has some buffer.
  - **Market:** any.
  - **Goal:** a solid pass is the MVP. Anything more is a bonus.
  - **Broker / paper-trading account:** no, for now.
  - **Paid data:** an Alpha Vantage key.
  - **Compute:** Colab or cloud is available if needed.
- **Section 5 filtered against these constraints:**
  - **Kept:** H (lead, reduced scope), D (safe fallback), A (alternative, without the testnet).
  - **Removed:** B (fragile scraping), C (needs an account for intraday data), E (earnings data too slow on the free Alpha Vantage tier), F (moved to the parking lot as an add-on), G (little reuse of class code).
  - **Alpha Vantage key:** stored in this repo's `.env` as `ALPHAVANTAGE_API_KEY` (git-ignored). Tested with one quote call: it works. Your plan level is still unknown. You also shared the Alpha Vantage MCP server (https://mcp.alphavantage.co/). It's useful for exploring the data in chat, but the project scripts will still call the REST API.
  - **Main finding:** with 30 hours, **how much class code carries over** matters more than the extra rubric points an idea opens up. All three remaining ideas clear the 6 minimum points. H opens up the most extra points but has the two slow data steps. D is the quickest to build.
- **Data check for idea H: delisted tickers, Alpha Vantage vs yfinance** (quick test in chat, nothing saved to the project):
  - **Test ticker: SIVB** (SVB Financial). An S&P 500 member that collapsed in March 2023. It's the worst case for survivorship bias: if a source has no prices for it, the backtest never sees a −99.7% month.
  - **yfinance 1.7.0: no data at all** for SIVB (or SIVBQ). The same goes for FRC, LEH, TWTR, ATVI, XLNX, CTXS and ABMD, so **8 out of 8** delisted members tried came back empty. The gap is real and systematic.
  - **Ticker reuse trap:** `FB` in yfinance now returns a *different* security (data from June 2025 only, ~$45), not Meta's history. A naive download by old ticker would pull in the wrong prices without any error. Point-in-time tickers need mapping to current ones (FB → META) and a check on the first date.
  - **Alpha Vantage: full SIVB history, 1999 → today**, including the crash (Feb 2023 close 288.11 → Mar 2023 close 0.905), then OTC prices afterwards. Its 2000 2-for-1 split shows up correctly in the adjusted close. Daily and monthly-adjusted both work.
  - **But the key is on the free tier:** 25 requests a day, at most 1 a second (the error message says so). With ~700+ point-in-time members, a full pull takes about **4 weeks** at 25 a day. Too slow to use for everything.
  - **What this suggests (to decide):** use **yfinance for current members** and **Alpha Vantage only for the delisted ones**. The listing-status call gives that list in one request. Even then, a few hundred delisted names would take 1–2 weeks of daily calls. So either start the daily pull right away as a background job, cap it to the delisted members after 2010, or measure the gap as planned. Not checked yet: whether Alpha Vantage's adjusted close includes dividends (SIVB paid none), and whether it has bought-out names like TWTR.
- **Follow-up: is the hybrid "yfinance + Alpha Vantage for delisted" plan viable?** (quick test in chat, scripts and CSVs in the session scratchpad only)
  - **The full removal list in one request: yes.** Wikipedia moved the changes table off the main S&P 500 page to its own page, **"Historical components of the S&P 500"**. It has 414 changes from 1976 to Oct 2026, but almost all are 2000+ (43 in the 2000s, 220 in the 2010s, 141 in the 2020s). So the history before ~2008 is thin, which backs **starting in 2010**.
  - **The gap, measured:** 360 removed tickers aren't in today's list. yfinance has usable history for 114 of them, mostly companies that moved down to smaller indexes and still trade. **246 need another source, or 210 for removals since 2010 and 149 since 2015.** Some yfinance "hits" are 1-row stubs (e.g. LEG, QRVO), where Yahoo keeps only the last print of a recently delisted stock, so they count as missing.
  - **Alpha Vantage on the free tier:**
    - **Full daily history is premium.** `TIME_SERIES_DAILY` with `outputsize=full` is refused, and free daily is the last 100 days only. **Monthly adjusted is free with full history.**
    - **Dividends are handled correctly:** KO's adjusted close matches yfinance within 0.1% from 2005 to 2026, including the 2012 split.
    - **Bought-out and recent names work:** TWTR (2013 → Oct 2022), PXD, CMA, HOLX and SIVB all returned full monthly history up to delisting.
    - **Failures:** LEH (2008) and BBBY return nothing. **STI returns the company that reused the ticker** (data from 2024 only), so the reuse trap exists here too. Every pull needs a check that its last date lines up with the removal date.
    - **Hit rate:** 5 of the 8 delisted names tried were good. 153 of the 210 post-2010 missing tickers appear in Alpha Vantage's delisted listing (a rough upper bound).
  - **Verdict: viable, with limits.**
    - The thing survivorship bias hurts most is the **target**: the forward return of the stocks we pick. Monthly adjusted prices are enough to compute `fwd_excess_Xm` and the month-scale return and rank features for delisted names.
    - Daily-based features (volatility, quality of the move, TA-Lib) wouldn't exist for those names. Options: leave them blank there, or build those features from monthly data for everyone.
    - **Cost:** ~210 calls at ~23 a day ≈ **9–10 days** for the 2010+ set, or ~7 days for 2015+. That only works if a daily pull job **starts now**. Such a job would also count towards the automation / incremental-load points.
    - Expect ~20–40% of names to stay missing (reused tickers, older failures). Measure and document that leftover gap.
- **Step back: how many names in total, and do the removal reasons matter?**
  - **Total universe:** 503 current members + 320 removed since 2010 ≈ **823 names** (≈ 750 for 2015+). A few "removals" are only ticker changes (CDAY → DAY, WLTW → WTW), not missing companies.
  - **Removals since 2010, by reason** (classified from Wikipedia's "Reason" column):

    | Reason | Total | yfinance OK | Missing |
    |---|---|---|---|
    | Acquired / merged | 150 | 14 | **136** |
    | Market cap / index rules | 126 | 82 | 44 |
    | Spin-off / restructure | 33 | 12 | 21 |
    | Bankrupt / failed (SIVB, SBNY, FRC) | 3 | 0 | 3 |
    | Other (mostly ticker changes) | 8 | 2 | 6 |
    | **Total** | **320** | **110** | **210** |

  - **Your point, that market-cap drops shouldn't affect momentum much, is partly right:**
    - **Partly true:** the strategy buys winners, and a stock is usually dropped after a long fall, so at that point it ranks near the bottom and would almost never be bought. Also, **yfinance already has 82 of the 126** (they still trade on smaller indexes), so only 44 are missing.
    - **But it still matters in two ways:**
      - (1) A stock picked as a winner can crash *during the hold* and then get dropped. Losing those cases hides exactly the "momentum crash" losses.
      - (2) Ranks, breadth and the "beat SPY" base rate are worked out across all members. With the losers gone, every month's group looks better than it really was.
  - **Acquisitions are the bigger issue for idea H** (136 missing):
    - A takeover bid is one of the most common reasons a stock is **the month's top gainer**. After the jump the price sits near the deal price until the deal closes, so it barely moves while SPY keeps going.
    - Without these names, the plain "buy last month's winner" rule **never picks a takeover target**. Its picks look cleaner, and it scores better than it would have in real life. It also removes the main example the "quality of the move" features are meant to catch.
  - **Implication for the pull:** order it by impact. Acquired + bankrupt first (139 calls ≈ 6 days at ~23 a day), then the 44 market-cap names if time allows. Spin-offs and ticker changes mostly need **mapping**, not new data.
- **Before coding: separate repo and code layout**
  - **Separate repo: create it now, before any code.** A later split (`git subtree split` / `git filter-repo`) would work, but three things make now better:
    - The Alpha Vantage pull runs daily for about a week with fixed paths. Moving the folder halfway through means re-pointing the schedule and the partly pulled data.
    - Peer reviewers get a clean history.
    - The project needs its own pinned environment and `.env` anyway.
  - **Suggested location:** a folder of its own with its own GitHub repo, outside the course repo. (Later the same day, this brainstorm file moved into the new repo's `references/` as well, next to the short `decisions.md`.)
  - **Layout: Cookiecutter Data Science v2, with changes:**
    - Split the download step by source: yfinance, Alpha Vantage (incremental and resumable, ~23 calls a day) and Wikipedia.
    - Add a `simulate.py` for the backtest.
    - Replace the Makefile with a Python command-line script (Windows has no `make`).
    - "From file" vs "live" data modes, so reviewers can run it without the 6-day pull.
    - One pinned environment tool.
  - **Open decisions:** repo name (ideas: `sp500-momentum-winners`, `monthly-winner-momentum`) and public or private; location; environment tool (uv, pip or conda); start year (2010 or 2015).
  - **First code, once decided:** the repo layout plus the resumable Alpha Vantage pull, so the slow step starts first.
- **Decided (2 Nov):**
  - Repo **`sp500-momentum-winners`** (this repo), private on GitHub until near completion.
  - uv with Python 3.12, Cookiecutter Data Science v2.3.0 layout, **start in 2010**.
  - **Built and committed:** the Wikipedia membership scrape, the yfinance coverage check (213 removed members missing, 209 queued for Alpha Vantage) and the resumable Alpha Vantage pull.
  - **First pull:** 8 tickers, 7 ok, FRC no data. About 9 more days to finish.
  - Decisions are kept short in `references/decisions.md`. Discussion stays here.
  - Daily Task Scheduler job `sp500-momentum-av-pull` set up (09:00, 23 calls). This file was moved into the repo's `references/` folder.

### Session 3 — Monday, 2 Nov 2026 (yfinance daily download, code)

- **Status check first:** the scaffold, the Wikipedia scrape, the coverage check and the Alpha Vantage pull were all in place. The scheduled task hadn't run on its own yet (first run: Tue 3 Nov, 09:00). The AV queue had 201 tickers left (~9 days, done ~11–12 Nov). Features, modelling and the backtest hadn't started.
- **Housekeeping:** open questions 6 (Alpha Vantage plan) and 11 (delisted companies) were already settled in Session 2, so they're now marked as answered in Section 9.
- **Built: the `yahoo-daily` step** (`uv run python -m sp500_momentum.dataset yahoo-daily`).
  - **Who gets downloaded (623 tickers):**
    - the 503 current members;
    - the 107 members removed since 2010 that yfinance still covers (`yahoo_ok` in `removed_coverage.csv`);
    - 13 benchmark and regime series: SPY, the 11 SPDR sector ETFs (XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY) and ^VIX, for feature groups 3 and 9 in Section 7.3.
  - **Date range: 1 Jan 2007 to yesterday's close.** It starts 3 years before the first decision date (2010), so the 12- and 24-month features, the 200-day averages and the 12-month beta all exist from the first month, and the 2008 crash is in the regime data. The end date is exclusive and set to today, so a half-finished trading day never gets saved.
  - **What's kept:** the unadjusted open, high, low and close, plus `adj_close`, volume, dividends and splits. The golden rule says we trade at the next open, so we need an **adjusted open**. It can be rebuilt as `open × adj_close / close`. Keeping the raw columns also keeps the dividends and splits visible, so they can be checked.
  - **Storage:** one parquet file per ticker in `data/raw/yahoo/daily/` (`^VIX` is saved as `_VIX.parquet`), plus `data/raw/yahoo/_manifest.csv` with each ticker's status, rows, first and last date, and dividend and split counts. Same pattern as the Alpha Vantage folder.
  - **Resumable:** a rerun skips tickers that already have a file. `--refresh` downloads everything again. Tickers that come back empty in a big batch get one retry in small batches. The manifest is always rebuilt from the files on disk.
  - **Checks per ticker** (`check_daily`): `no_data`, `stub` (1 row), `bad_prices` (zero or negative), `reused_ticker` (a removed member whose data starts after its removal date).
  - 3 offline tests were added (universe groups, column tidying, the checks). There are now 10 tests, all passing.
- **Result of the first run (about 50 seconds):**
  - **All 623 tickers are `ok`. That's 2,841,416 daily rows** (about 134 MB of parquet), which covers the "3M daily rows" estimate in Section 7.1. The Alpha Vantage monthly data for delisted names comes on top.
  - Every series ends on **Fri 30 Oct 2026**.
  - 134 tickers start after Jan 2007 because they listed later (IPOs and spin-offs). That's expected.
  - **Spot checks:**
    - AAPL's 7:1 (2014) and 4:1 (2020) splits are there.
    - SPY's total-return CAGR from 2010 to 2025 comes out at **13.9%**, which is plausible.
  - All 107 removed members still trade today, which is why yfinance has them. So these are mostly **market-cap drops**, not the acquisitions that matter most for the bias. Those still depend on the Alpha Vantage pull.
- **Known risks, not handled yet:**
  - **Hidden ticker reuse:** the `reused_ticker` check only catches data that *starts after* the removal. If a ticker passed to another company that already traded before the removal date, it wouldn't be caught. A price-jump check around the removal date would find that. It goes on the list for the monthly-table step.
  - **Ticker changes:** for these, the old and new tickers need mapping to one stock in the monthly table (e.g. CDAY → DAY).
- **Committed and pushed** (`0cfdfc5`).
- **Your question: is anything Alpha Vantage pulls also available on yfinance, and is it correct?** (checked from the saved files, plus yfinance calls only; no Alpha Vantage calls used)
  - **What the coverage step already guarantees:** a ticker only goes into the AV queue if yfinance has no usable history **under the same ticker**. Of the 213 missing:
    - 182 return **no rows at all**;
    - 5 are **1-row stubs** (WBD, AVB, EA, QRVO, LEG);
    - 26 have data that **starts after the removal date**. Either a different company reused the symbol (MMI, STI, EMC, SE, ...), or the same company relisted after bankruptcy without its old history (BTU, NE, SHLD).
    - 4 ticker changes are kept out of the queue, because they need mapping, not new data.
    - So no AV call goes to a name yfinance already covers under that ticker.
  - **Not checked:** whether yfinance has some of them under **another symbol** (a new ticker after a rename, or an OTC `…Q` symbol after bankruptcy). Only SIVBQ was tried, in Session 2, and it was empty. For acquired names the old ticker is usually the only one, so this gap is likely small.
  - **Are the 7 AV pulls correct?** `validate()` only checks dates, not prices, so a price check was run as well:
    - **Last price matches yfinance's stub exactly:** WBD 30.95, AVB 184.06, EA 209.70.
    - HOLX, CTRA and SIVB have nothing on yfinance to compare against. The AV data looks sane: no zero or negative prices, SIVB −99.7% in Mar 2023, SBNY −99.8%.
    - Earlier check (Session 2): KO's adjusted close matched yfinance within 0.1% over 2005–2026, dividends included.
  - **New finding, a trap for the monthly table:** after the failure, the AV data carries on with **OTC penny prices**. SBNY goes +350% in Nov 2023 and **+3,102% in Dec 2023** (0.05 → 1.60), and SIVB +111% in Jan 2024. These are noise after the removal date. The monthly table must **cut each delisted name's prices at its removal or delisting date** and value a position still held at that last price. Otherwise a held loser could turn into a fake 30× winner.
  - **Possible extra check (not done; it needs AV calls):** use the 2 spare calls a day (the budget is 25 and the task uses 23) on removed members that **both** sources cover, and compare monthly returns. About 18 overlap checks by 11 Nov, with no delay to the main queue.
- **Decided: no AV vs yfinance cross-check. The cutoff rule handles the risk.**
  - **Your call:** skip the overlap check, cut each delisted stock at its removal date, and value an open position at its last real price.
  - **Why it's enough:** the penny-price trap was the only real error we found, and the cutoff removes it. Where both sources have a price they match (KO within 0.1%; WBD, AVB and EA exactly). The 18 extra checks wouldn't change any decision, and the time goes to the build.
  - **One detail, so the cutoff doesn't hide losses:** with *monthly* data, cutting *before* the removal date would drop the crash. SIVB was removed on 15 Mar 2023. Its last month-end before that is Feb (288.11), but the March month-end is 0.905. Valuing at Feb would turn a −99.7% loss into no loss. So the rule is: **keep the month that contains the removal date, then stop.**
    - For SIVB that gives Mar 2023 (0.905). For SBNY, Mar 2023 (0.183).
    - For acquired names, AV's last row is the last trading day, which sits at the deal price.
    - After that month, the position is treated as cash, at 0% until the hold ends.
  - **What this leaves out:** AV's prices *before* removal are trusted on the strength of 4 matches. If one turns out wrong, it shows up as an outlier when the monthly table is checked.
- **Discussion: which hold periods (X)? (open question 10, proposal, not yet decided)**
  - **Suggested: X = 1, 3, 6, 12 for the rule. Drop 24.**
    - In the research, the momentum effect lasts about 3–12 months. Past ~2 years, winners tend to *reverse*. So 24 months tests a different effect.
    - It's also expensive. With 2010–2026 (~200 months), each split needs a 24-month gap (Section 7.5). Two gaps would use up 4 of the 16 years.
    - 1 month is worth keeping as the contrast: the research also finds a **short-term reversal**, where last month's biggest winner often gives some of it back the next month. That makes it a fair test of the original idea.
  - **Suggested: also vary the look-back** (how "winner" is defined: last 1, 3, 6 or 12 months, and 12 months skipping the latest one). That gives a small look-back × hold grid, the classic way momentum is reported. It's cheap once the monthly table exists, and it shows *which kind* of winner works.
  - **Suggested: the ML model gets one main horizon, not five.** 1 month by default: there's no overlap, no gap is needed, it has the most test months and it fits the class flow. Switch to the best X from the rule grid if 1 month clearly loses. The other horizons stay as extra targets for analysis only.
  - **Points the plan didn't cover yet:**
    - **(a) How to hold X months when a new signal comes every month.** Suggested: staggered portfolios. Each month, 1/X of the money goes into that month's picks and stays for X months. The result then doesn't depend on which month you started in. The plain alternative, rebalancing only every X months, gives one result per start month.
    - **(b) Trading costs.** A top-1 rule changes the whole portfolio every month. Charge e.g. 10 bps per side, so short holds aren't flattered.
    - **(c) Top-1 is noisy.** One stock a month means one takeover or crash decides the year. Report top-1 (the baseline) next to top-5 and top-10 from the start, since it costs nothing extra.
  - **Your challenge: why keep 12 months, if a ~4-year test set leaves so few data points?**
    - **For the ML test set, you're right.** Take 48 test months. Lose 12 to the gap after training, and 12 at the end, where the 12-month return isn't known yet. That leaves **~24 usable decision months, or only ~2 independent 12-month periods.** That's too few to judge anything. So 12 months (and even 6) is **not** used for the ML model.
    - **For the plain rule, it's fine,** because the rule learns nothing. "Buy last month's top N" has no fitted parameters, so it needs no train/test split and can run over **the full 2010–2026 period**. That's ~190 monthly start dates, or ~16 independent 12-month periods. Still modest, but enough to compare against SPY.
    - **The catch:** if we pick the "best X" from the full-period grid, that choice is fitted to the data. So report **every cell of the grid**, not just the winner. And check that the best X also wins in the later years (2022 onwards) on its own.
    - **Decided (you agreed):** the rule runs over the full period with X = 1, 3, 6, 12. The ML model uses 1 month only, with the time split. 12 months stays as a rule-only cell. Dropping it would be fine too if time runs short.
- **Next:** build the monthly table. Take month-end closes and next-day opens from the daily files, apply the point-in-time membership on each month-end, and join the Alpha Vantage monthly prices for delisted names. Then run the baseline rule against SPY. Open question 10 (which hold periods X to test) needs an answer before the targets are built.
### Session 4 — Monday, 2 Nov 2026 (monthly table, code)

- **Built: `uv run python -m sp500_momentum.monthly build`.** It writes `data/processed/monthly_panel.parquet`, with **one row per member per month-end**. It rebuilds from the raw files in about 12 seconds, so it gets rerun as the Alpha Vantage data arrives.
  - **Membership** (`membership.py`): start from today's list and walk Wikipedia's changes backwards. A change counts from its own date. Decision dates are the last trading day of each month (SPY's calendar), from Jan 2010 to Oct 2026: 202 month-ends.
  - **Prices per stock and month:**
    - `close_adj` is the month-end adjusted close. Features use it.
    - `entry_px` is the price we trade at. For yfinance names that's the **next trading day's adjusted open**, following the golden rule. Alpha Vantage only has monthly data, so for those names it's the month-end close.
    - Alpha Vantage names are cut after the month that contains their removal date (the Session 3 rule).
  - **Columns:**
    - Past returns: `ret_1m`, `ret_3m`, `ret_6m`, `ret_12m` and `ret_12_1m` (12 months, skipping the latest).
    - For X = 1, 3, 6, 12: `fwd_ret_Xm`, `fwd_trunc_Xm` (prices ended during the hold, so the position was valued at the last price, then cash), `spy_fwd_ret_Xm`, `fwd_excess_Xm`, `is_beat_spy_Xm` and `is_top_decile_Xm`.
    - Targets only exist where the exit price is known. The last 1-month target is the Aug 2026 decision.
- **Problems found while building, and the fixes:**
  - **Missing renames made stocks members too early.**
    - Wikipedia lists the *old* ticker being added (FB in Dec 2013) but has no row for the rename to META. Walking backwards, META was never taken out, so it counted as a member from 2010. In 2012–13 it was priced, on wrong rows.
    - The same happened with DLPH → APTV, KORS → CPRI, FLT → CPAY, RE → EG, UA-C/UA → UA/UAA, SATS → ECHO, and the 2014 GOOGL row (it was really GOOG, the class C).
    - **Fix:** a `RENAMES` list in `config.py` rewrites old → new, but **only inside a date window**, because tickers get reused. "Q" was Qwest until 2011, QuintilesIMS in 2017, and is Qnity now. The first version's flat `Q → IQV` alias would have given Qnity IQVIA's prices.
    - The old alias map was dropped. Pure rename rows (CDAY → DAY, WLTW → WTW, Q → IQV, KFT → MDLZ) become no-ops. One stock, under today's ticker.
  - **A missing add:** Smurfit Westrock (SW, joined 2024) has no "added" row. It was counted back to 2010 with the junk data of an older "SW". Fixed with a synthetic add in `MISSING_ADDS`.
  - **Stray characters in scraped tickers:** one Wikipedia row reads "ALLE |" / "JCP |", and another "ITT |". The coverage check had never tried JCP or ITT. `normalize_ticker` now drops anything that isn't a letter, digit or "-".
  - **Hidden ticker reuse, confirmed:** CPWR's and EP's yfinance data are a different security. Volume is near zero and prices jump around (CPWR +300% then −75% in a month). The coverage check passed them because the data starts *before* the removal date.
    - **Fix:** a liquidity check. If a yfinance series' median daily dollar volume over its member months is under **$10M**, it can't be an S&P 500 stock, so its prices are dropped.
    - It caught 6: **CPWR, EP, GENZ, KG, SII and SUN** (Sunoco; yfinance "SUN" is Sunoco LP).
    - The removed ones are written to `data/interim/yahoo_suspect.csv`, and `av-pull` now treats them as missing.
  - **Bemis (BMS)** was acquired by Amcor, but the reason text reads like a ticker change, so it was kept out of the AV queue. It's now in `REASON_OVERRIDES`.
  - With these fixes, the **AV queue went from 201 to 207** (+JCP, +BMS, +the 6 suspects; ITT turned out to be on yfinance). It still finishes ~11–12 Nov.
- **Result:**
  - **101,431 rows, 819 tickers, 499–504 members per month-end** (before the fixes it was up to 510).
  - **Share of members priced:** 68% in 2010, rising to 100% in 2026. The gap is almost all the AV queue: **14,253 of 14,803 unpriced member-months wait on it.** About 550 won't be filled:
    - Old companies whose ticker a current member reuses, so neither source has the old history: Dow Chemical (DOW, 92 months), SanDisk (SNDK, 76), Dell before its 2013 buyout (45), Constellation Energy (CEG, 26).
    - FRC has no data on Alpha Vantage. Qwest (Q) is missing for 2010–11.
    - These get measured and documented, not fixed.
  - **Spot checks:**
    - SIVB, Jan 2023 decision: −99.7% over 3 months, valued at the March crash price and flagged as cut short.
    - AAPL's 2020 rows line up with SPY.
    - The 1-month beat-SPY base rate is 49%.
    - The 6 flagged moves left look real: APA in the 2020 oil crash, and SNDK, INTC, DELL and MRNA in 2026, all with high volume.
  - 5 new offline tests (the membership walk, the repairs, ticker cleaning, cutoff and truncation, and the data-end rule). There are now 15, all passing.
- **Caution:** until the AV pull finishes, the early years are missing most acquired names. So **any baseline result run now is still survivorship-biased** and is a preview only.
- **Next:** the baseline rule grid (look-back × hold, top 1/5/10, staggered, ~10 bps), as a first version of `simulate.py`. Then features.

### Session 5 — Monday, 2 Nov 2026 (step back: compare with the class's Weeks 1–4, no code)

- **Why:** before writing more code, you wanted to see how the class built its dataset and project, and keep this project similar.
- **The class's pipeline, in four steps:**
  - **Week 1, sources:** yfinance (stocks, indexes, ETFs), FRED macro data, and scraping.
  - **Week 2, one table:** daily history for 33 stocks. Added:
    - growth features over 1, 3, 7, 30, 90 and 365 days, for the stock and for 8 markets;
    - about 55 TA-Lib indicators and 61 candlestick patterns;
    - macro data (monthly values copied onto each day);
    - dummies.
    - The targets are `growth_future_30d` and `is_positive_growth_30d_future`. The result was 240k rows × 203 columns, saved as one parquet file.
  - **Week 3, first models:**
    - named feature sets and a 70/15/15 time split;
    - a 57% baseline, and a correlation check;
    - hand-written rules `pred0`–`pred4`;
    - decision trees, scored on precision on test.
  - **Week 4, more models and the simulation:**
    - more models: random forest, logistic regression, a neural network;
    - probability thresholds (`pred8`–`pred11`);
    - `sim1_`: $100 per "buy", held 30 days, 0.2% fees. Capital = 30 × the 75th percentile of trades per day. Scored by CAGR.
    - HW4 lessons: fewer dummies helped the RF; fixed thresholds break when anything changes; "stock rose last month" was a tough benchmark; choosing settings on the test set flatters the results.
- **Same pipeline for idea H.** What changes (as planned in Section 7.7):
  - **One row per stock per month-end, not per day.** It's still built the class's way: from a daily table (our 2.85M yfinance rows), computing the features on daily data, then keeping the month-end value.
  - **Universe:** about 500 point-in-time members instead of 33 fixed stocks.
  - **Target:** beats SPY over the next month (ML), instead of "up in 30 days".
  - **Rules:** `pred0` = top 1 by last month's return (your idea).
  - **Probability → buy:** top N each month, not a fixed threshold.
  - **Simulation:** capital is exactly N × X × $100.
- **Where we are on that pipeline:**
  - Sources: done (yfinance, Wikipedia, Alpha Vantage). FRED isn't pulled yet.
  - One table: the skeleton is done (membership, prices, returns, targets). **None of the class-style features exist yet** (growth against markets, TA-Lib, macro, VIX, dummies, named feature sets).
  - EDA, models and the simulation: not started.
  - **No notebooks yet.** The class worked in notebooks, and the rubric wants notebooks + `.py` scripts + one notebook that runs the whole workflow.
- **Two things that came out of the comparison:**
  - **A minimum (bold) rubric point says "use the data sources and the features from the lectures".** So FRED macro data, TA-Lib indicators and growth-against-markets features are required, not optional.
  - **Proposal: one notebook per class week.** `01_data` (sources + one table), `02_features_eda`, `03_models`, `04_simulation`, plus a `run_all` notebook. Each one calls the `.py` functions. It matches the course layout, so reviewers can follow it.
- **The open questions, broken into 20 small ones and settled one at a time (your answers):**
  - **A. Table and data**
    - **A1, row:** one row per member per **month-end** (not daily). The 2.85M daily rows underneath cover the >1M point.
    - **A2, split:** **train 2010–19, validation 2020–22, test 2023–26**, with a 1-month gap between them.
    - **A3, timing:** **build everything now** on the current data. Rerun it all once the AV pull ends (~12 Nov). Until then, results are labelled "preview".
    - **A4, macro:** the class's FRED set (core CPI yearly and monthly, Fed Funds, 1/5/10-year yields, potential GDP), **plus VIX** (level and percentile) and the yield-curve slope. Every figure is **lagged to its publication date**.
    - **A5, markets for growth features:** **US-focused set**: SPY, Dow, the stock's sector ETF, gold, WTI, the 10-year yield. DAX, India, Brent and Bitcoin are dropped. *(This differs from my recommendation of keeping the class's 8. The "features from the lectures" point is still covered by the same growth-feature method, the FRED macro and TA-Lib.)*
    - **A6, TA-Lib:** **keep the ~55 indicators** at month-end, with raw running totals (OBV, A/D) turned into changes or ranks. **Drop the 61 candle patterns.** Note: Alpha Vantage-only names have monthly prices only, so their daily-based indicators will be blank.
    - **A7, own features:** a **core ~20**: ranks (among members and within sector), return against SPY and the sector ETF, quality of the move (share of up days, biggest-day share), volatility and beta, distance to the 52-week high and low, breadth.
    - **A8, sectors for removed members:** **fill them in by hand, once**. Use yfinance "sector" where it has the ticker, otherwise a keyword match on the name, and "unknown" for what's left. *(My first recommendation, "unknown" for all, was dropped. An "unknown" sector would really mean "gets removed later", which leaks the future.)*
  - **B. Modelling**
    - **B1, target:** **`is_beat_spy_1m`** (base rate ~49%). Top decile is kept as a second target for analysis.
    - **B2, models:** **decision tree, random forest, logistic regression, XGBoost.**
    - **B3, tuning:** **time-series cross-validation** inside 2010–22, with expanding-window folds: train on the years before, validate on the next year, 1-month gap. The test set (2023–26) is used **once**, at the end.
      - **Your follow-up: is the extra run time worth it?** (estimates, not measured; the features don't exist yet)
        - **Cost:** about 7 fits per setting instead of 1. With class-sized grids that's ~35–50 min against ~5–8 min. With trimmed grids (e.g. RF depth {4,6,8,10,13} × trees {50,100}) it's ~10–15 min against ~2. It's paid once per tuning run. The CV results are saved to a CSV (like the class's pre-calculated tuning tables), so the notebooks and the monthly run only load the chosen settings. About 30 extra lines of code.
        - **Gain:**
          - A single 2020–22 validation period is only 36 decisions (360 top-10 picks), so precision carries about ±2.6 points of noise, while settings differed by 1–3 points in class.
          - Those three years are unusual: the COVID crash, the 2020–21 rebound (momentum's classic weak spot) and the 2022 bear market.
          - HW4's forest chosen on validation fell to 3.7% CAGR on test.
          - CV over 2016–22 gives 84 months across seven different years, and about ±1.7 points of noise.
        - **No cost to model quality:** the final model is retrained on 2010–22 either way.
        - **Verdict: keep CV**, with trimmed grids and cached results.
    - **B4, main score:** **precision of each month's top-N picks** (the share that beat SPY), against the ~49% base rate. Average excess return is reported alongside.
  - **C. Strategy and simulation**
    - **C1, picks:** report top 1, 5 and 10. **Headline: top 10.**
    - **C2, benchmarks:** **SPY**, plus an **equal-weight basket of all members**.
    - **C3, simulation:** **both kinds.** The class's `sim1_`-style vector simulation, plus an exact simulation with reinvestment (equity curve, CAGR, Sharpe, max drawdown, rolling returns).
    - **C4, extra strategy:** **market filter**: only buy when SPY is above its 200-day average, otherwise hold cash.
  - **D. Deliverables and automation**
    - **D1, notebooks:** **one per class week**: `01_data`, `02_features_eda`, `03_models`, `04_simulation`, plus `00_run_all`. Each calls the `.py` functions.
    - **D2, data hosting:** a **Hugging Face dataset**, used by the "from file" mode.
    - **D3, automation:** a **monthly scheduled run** (Task Scheduler, on the first trading day of the month). It updates prices incrementally, rebuilds the table, scores with the saved model and saves next month's picks. Plus a `--from-file` switch.
    - **D4, extras:** **core first, then decide** (~mid-Nov). If time is left, the Telegram bot comes first.
### Session 6 — Monday, 2 Nov 2026 (FRED and market downloads, code)

- **Built: `uv run python -m sp500_momentum.dataset fred`** (new `sources/fred.py`). It downloads the class's six FRED series from 2005 into `data/raw/fred/<ID>.csv` (date, value). It's a full refresh each time: 6 small requests, under a second.
  - **Series:**
    - `CPILFESL`: core CPI, monthly, 2005-01 → 2026-09;
    - `FEDFUNDS`: monthly, → 2026-10;
    - `DGS1`, `DGS5`, `DGS10`: daily, → 30 Oct 2026, 5,462 rows each;
    - `GDPPOT`: quarterly CBO projection, runs to 2036.
  - **Not `pandas_datareader`**, which the class used. It's unmaintained. FRED's public CSV endpoint returns the same data without a key.
  - **Trap found:** FRED's endpoint **stalls (30-second timeout) on our custom User-Agent** but answers in 0.2 s with the default one. So `fred.py` doesn't send `HTTP_HEADERS`.
  - **Publication lags are written into `FRED_SERIES` in `config.py`, so no feature sees a figure before it was published (decision A4):**
    - core CPI and Fed Funds: 1 month (July's value is used from the end of August);
    - daily yields: the last value strictly before the decision date;
    - GDPPOT: 0. It's a projection, but FRED keeps only the latest one, so this is a mild, accepted look-ahead.
  - **Gap found: core CPI has no Oct 2025 value** (the 2025 government shutdown, the same gap the class noted). The features step will carry the previous value forward.
- **Market series (decision A5, US-focused):** `^DJI`, `GC=F` (gold) and `CL=F` (WTI) were added to `BENCHMARKS`. `yahoo-daily` downloaded just those 3 (it skips what's already saved). The 10-year yield comes from FRED. SPY and the sector ETFs were already there.
  - CL=F shows as `bad_prices` in the manifest because of the −$37.63 close on 20 Apr 2020. That's real, and April's month-end (18.84) is fine.
  - **Trap found:** futures trade overnight, so yfinance's `end` date let **today's half-finished bar** through for GC=F and CL=F. `download_daily` now keeps rows strictly before `end`. The two files were downloaded again, and all series now end on 30 Oct.
- **Totals:** 627 yfinance series, 2,861,374 daily rows, plus 6 FRED series. One test added (FRED CSV parsing, `.` and blank values). There are now 16, all passing.
- **Next:** the features step. Daily → month-end: growth against SPY, Dow, the sector ETF, gold, WTI and the 10-year yield; TA-Lib indicators; macro with the lags; VIX; ~20 own features; sectors for removed members. Then the named feature sets.
### Session 7 — Tuesday, 3 Nov 2026 (checking the scheduled Alpha Vantage run)

- **Your question: did the scheduled run work?** Yes, but late and only partly.
  - **The PC was off at 09:00.** It booted at 09:16, and the PC clock is Central time (-06:00). The task's "start when available" setting caught up at **09:19:43** and pulled **9 tickers, all `ok`**: DAY, K, IPG, WBA, HES, ANSS, JNPR, DFS, CTLT. Then Alpha Vantage refused more ("25 requests per day").
  - My first status check (09:19:53) landed while that run was still going, so the task looked like it had never run. A manual start at 09:20 then found the limit already used, and stopped cleanly.
  - The manifest went from 8 to 17 tried, and **198 are left**.
- **Why only 9 calls, not 23:** most likely **the free tier counts 25 calls over a rolling 24 hours**, not per calendar day. About 16 calls were made on the afternoon and evening of 2 Nov (tests in chat plus the first 8 pulls). This is inferred from the log, not documented by Alpha Vantage.
- **Changed (your choice): the task now runs at 21:00 only (PC time), not 09:00.** `scripts/register_av_task.ps1` was updated and the task re-registered. Catch-up after boot is still on. The first run is tonight. If the window really is rolling, tonight gets ~16 calls (this morning's 9 are still inside 24 hours), and from tomorrow ~23 a night. **Estimated finish: about 12–14 Nov**, still before the 20 Nov deadline.
- **Fixed: the API key was being written to the log.** Alpha Vantage's quota message quotes the key, and `av-pull` logged the message as is. The key is now replaced with `***`, and it was scrubbed from the existing `logs/av_pull.log`. `logs/` is git-ignored, so it never reached GitHub.
- Also noted: Task Scheduler's own history log is switched off on this PC, so `logs/av_pull.log` is the only record of the runs.
- ANSS came back `ok`, but its data runs to Nov 2026, well past its Jul 2025 removal (the old ticker still quotes). The cutoff rule from Session 3 (stop after the removal month) already handles this.
### Session 8 — Tuesday, 3 Nov 2026 (how to document the project, then chapters 01–03)

- **Your question: how do we document this simply but in depth, like chapters of a book? Are there rules, skills or a template (like CCDS) to follow?**
  - **CCDS:** it has a `docs/` folder and uses **MkDocs** as its docs tool. Our scaffold was generated with docs switched off, so there was no `docs/` yet.
  - **Diátaxis**, the standard framework for technical docs, sorts docs into tutorials, how-to guides, reference and explanation. Our book is mostly *explanation*, plus one *how-to* chapter (reproducing the project) and one *reference* (the data dictionary). We borrow that split, not the whole framework.
  - **Chapter template: the course's own summary files** (`Module_0X_..._Summary.md`): goal → what was done → what came out → takeaways → caveats. Reviewers took the same course, so it's familiar. Two sections are added to each chapter: **decisions and why**, and **how to reproduce**.
  - **Skills:** none specific. The `docs` skill is for documents on claude.ai, not repo files, and the rubric scores the repo. Style: plain language, short sentences, real numbers in tables, one chart per key point (the Google developer documentation style guide as a reference).
  - **Layers, so nothing is written twice:**
    - README = the front page (where most rubric points are judged);
    - `docs/` = the book;
    - notebooks = the evidence;
    - journal + `decisions.md` = the lab notebook, used as source material and linked as appendices.
- **Decided (one question at a time):**
  - **Format:** numbered Markdown chapters in `docs/`, plus an `mkdocs.yml`, so it can become a website later. GitHub renders the files as they are, with nothing to build.
  - **Chapters:**
    - 01 Problem and idea;
    - 02 Data collection;
    - 03 Building the monthly table;
    - 04 Features;
    - 05 Exploratory analysis;
    - 06 Modelling;
    - 07 Trading simulation and results;
    - 08 Automation and reproducing;
    - 09 Limitations and next steps.
    - Appendices: A data dictionary, B decision log, C journal.
  - **Timing:** write as we go. Draft 01–03 now from Sessions 1–7, write each later chapter right after its step, and do a final pass after the AV pull (~14 Nov) to refresh the numbers. Budget: ~30–40 min a chapter, 4–5 h in total.
- **Drafted:** `docs/index.md` and chapters 01–03, plus `mkdocs.yml`. The README now links to the book. The monthly table was rebuilt first so the chapters quote current numbers (86.7% of rows priced after this morning's 9 AV tickers).
- **Your review of the drafts: four rules for the book** (now also in `CLAUDE.md`):
  1. **No references to the course.** The book must make sense to someone who never took it. Chapter 1's "how this differs from the course" became "what makes this question different" (compared with a typical stock-prediction setup).
  2. **No mention of the grading rubric**, in any form.
  3. **No references to the files in `references/`** inside the chapters. They're tagged only in the last appendix, for readers who want the whole process. Appendices B (decisions) and C (journal) were merged into **Appendix B, "The full working record"**.
  4. **No "how to reproduce" sections.** The book explains the *why*. Commands, file paths and module names were removed, and the "how" stays in the README. Chapter 8 was renamed from "Automation and reproducing" to "Automation".
- All three chapters were rewritten to these rules, and a scan of `docs/` for course, rubric, references, commands and paths came back clean. Table separators were tidied to `| --- |`.
- **README (your choice):** the opening line "Final project for the Stock Markets Analytics Zoomcamp 2026" moved to a short **Acknowledgements** section at the end. The README now opens with the idea itself.
- **`CLAUDE.md` trimmed (your request: "lean and mean", so adding more doesn't confuse).**
  - **Taken out:**
    - numbers that go stale ("~150k rows" was already wrong at ~101k; ticker and row counts);
    - facts the code already documents (the FRED User-Agent trap in `fred.py`, the repair lists in `config.py`, the download details);
    - the section-by-section map of this file.
  - **Kept:**
    - the deadline and budget, the project in 4 lines, and the golden rule;
    - a pointer to `decisions.md` as the agreed plan ("follow it, ask before changing");
    - the working rules: the journal, and the book with its 3 writing rules;
    - two traps: Alpha Vantage calls, and reused tickers;
    - the commands and conventions.
  - It went from 71 lines to about 50.
- **Your question: what best practices are missing from `CLAUDE.md`?** Added, by your choice:
  - a **definition of done**: pytest and ruff pass, the table rebuilds, the journal and chapter are written;
  - an **ask-vs-act boundary**: ask before changing the plan, spending API calls or touching the task; bug fixes, tests and refactors just get done and reported;
  - a **look-ahead checklist** for features: data to the month-end close only, macro through its publication lag, ranks within each date;
  - **results honesty**: "preview" until the AV pull ends, never tune on 2023–26;
  - the **rebuild order** after new raw data;
  - **secrets**: never print, log or commit the key or `.env`;
  - the **Windows editing trap**: use the Edit/Write tools, because heredoc patches broke 3 times.
  - **Not added:** `@` imports (they would load the growing `decisions.md` into every session), coding-style rules (ruff covers them), per-folder files (the codebase is too small).
- **New: `CLAUDE.local.md`** (git-ignored), for personal preferences that shouldn't go public with the repo: commit only when asked, decisions one at a time, and PC time (Central) versus deadline time (Dublin). `CLAUDE.md` is now 69 lines.
- *(The discussion continues below.)*

---

## 9. Decisions and Parking Lot

### Decisions made

| Date | Decision | Why |
|---|---|---|
| 18 Oct 2026 | Use **point-in-time S&P 500 membership** (who was in the index on each date) | Avoids survivorship bias, the biggest risk for a "buy winners" strategy |
| 18 Oct 2026 | **Top 1 is the baseline.** Move to a top 3–10 basket only if it shows a real edge | Keeps the original idea as the reference point, and lets the data decide whether to spread the risk |
| 18 Oct 2026 | Lean towards **one row per member per month-end** (all stocks, not just the winners) | The rule and the ML model can then be compared on the same table, with enough rows to train on |
| 2 Nov 2026 | Budget: **~30 hours over 10 days**. A solid pass is the MVP, anything more is a bonus | Your time constraint. Scope decisions are made against it |
| 2 Nov 2026 | **No broker or exchange account for now.** The broker bonus point is dropped | Your call. Rules out ideas that need an account just to get the data |
| 2 Nov 2026 | Shortlist cut to **H (lead), D (fallback), A (alternative)**. B, C, E, F and G removed | They don't fit 30 hours, no account and the free Alpha Vantage tier (Section 5) |
| 2 Nov 2026 | **Idea H, start in 2010.** Prices: yfinance daily for current members and removed members it covers, Alpha Vantage monthly for the rest | Thin Wikipedia history before ~2008. The free Alpha Vantage tier has full history for monthly data only |
| 2 Nov 2026 | **Daily prices start in Jan 2007**, unadjusted OHLC + adjusted close + dividends and splits, one parquet file per ticker. SPY, the 11 sector ETFs and VIX are included | A 3-year warm-up for the long features. The unadjusted columns let us rebuild an adjusted next-day open |
| 2 Nov 2026 | **Delisted names: keep prices up to the month that contains the removal date, then stop.** An open position is valued at that last price, then held as cash. **No AV vs yfinance cross-check** | Removes the OTC penny-price noise (SBNY +3,102% in Dec 2023) without hiding the crash month. The prices compared so far all match |
| 2 Nov 2026 | **Hold periods:** rule baseline X = 1, 3, 6, 12 months over the full 2010–2026 period, as a look-back × hold grid with staggered portfolios, ~10 bps per side and top 1/5/10. **ML model: 1 month only**, with the time split. **24 months dropped** | The rule fits nothing, so it can use every month. A ~4-year test set leaves only ~2 independent 12-month periods for ML. 24 months is past the momentum range and needs long gaps |
| 2 Nov 2026 | **Project plan (20 small decisions, Session 5):** month-end rows; split 2010–19 / 2020–22 / 2023–26; build now, rerun after the AV pull; class FRED set + VIX, lagged; US-focused markets; TA-Lib indicators (no candle patterns); ~20 own features; sectors filled in by hand; target `is_beat_spy_1m`; Tree + RF + LogReg + XGBoost; time-series CV, test once; score = precision of the top-N picks; top 1/5/10 (headline 10); SPY + equal-weight benchmarks; vector + exact simulation; SPY > 200-day filter; notebooks per class week + `00_run_all`; Hugging Face data; monthly scheduled run; extras after the core | Mirrors the class's flow (Weeks 1–4) and the rubric's points. Fixes the class's caveats: look-ahead in macro, tuning on test, no benchmark |
| 2 Nov 2026 | **Monthly table repairs:** date-windowed `RENAMES`, `MISSING_ADDS`, ticker cleaning, and a $10M median dollar-volume check that drops yfinance series belonging to another security (those go to the AV queue) | Wikipedia misses renames, so stocks counted as members too early (META from 2010). Tickers get reused (Q, UA, SUN), so a flat alias map gives wrong prices |

### Parking lot (ideas to keep but not pursue now)

- **Alternative-data overlay (old idea F):** SEC EDGAR insider trades, Alpha Vantage news sentiment, Google Trends. A possible add-on to H or D if time is left over.
- **Broker API bonus point:** an Alpaca paper account (for H or D) or an exchange testnet (for A), if you change your mind about opening an account.

### Open questions

1. ~~What is the **2026 submission deadline**?~~ Answered (2 Nov): **20 Nov 2026, 23:59:59 Dublin time**. Still open: the 2026 peer-review window, and whether there will be a second attempt (2024 and 2025 both had one).
2. ~~How much time can go into the project?~~ Answered (2 Nov): 10 days × 3 hours ≈ 30 hours.
3. ~~Which market?~~ Answered (2 Nov): any.
4. ~~A solid pass, or as many points as possible?~~ Answered (2 Nov): a solid pass is the MVP, anything more is a bonus.
5. ~~Is a paper-trading account acceptable?~~ Answered (2 Nov): no, for now.
6. ~~Any paid data?~~ Answered (2 Nov): an Alpha Vantage key, on the **free tier** (25 calls a day, 1 a second). Monthly adjusted data has full history. Daily full history is premium.
7. ~~Compute?~~ Answered (2 Nov): Colab / cloud is available if needed.
8. ~~Was the yearly "winner beats the market" result tested on today's list or historical membership?~~ Answered: most likely historical membership. Still open: was it the single top stock or a group, and over which years?
9. ~~One stock per month or a basket?~~ Answered: top 1 as the baseline, a basket only if it shows a real edge.
10. ~~Which **hold periods (X)** should we test?~~ Answered (2 Nov): rule baseline X = 1, 3, 6, 12 over the full period. ML model 1 month only, with the time split. 24 months dropped (Section 8, Session 3).
11. ~~For delisted companies: accept the gap and measure it, start the data later (e.g. 2010), or pay for data with delisted history?~~ Answered (2 Nov): a mix. Start in 2010, fill the gap with free Alpha Vantage monthly data, and measure what's still missing.
