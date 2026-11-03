# Chapter 2: Data collection

## 1. Goal

Collect everything the project needs, from free sources:

1. **Who was in the S&P 500 on each date** (point-in-time membership).
2. **Daily prices** for every member, including the companies that later left the index.
3. **Market and economic series**: SPY, sector funds, the VIX "fear index", the Dow, gold, oil,
   interest rates and inflation.

---

## 2. What was done

| Step | What was collected | Source |
| --- | --- | --- |
| 1 | Today's 503 members, plus a list of 414 index changes (1976 → Oct 2026) | Wikipedia |
| 2 | Which of the 320 members removed since 2010 still have price history on Yahoo Finance | Yahoo Finance |
| 3 | Daily prices from 2007 for members, removed members Yahoo has, and market series | Yahoo Finance |
| 4 | Monthly prices for the removed members Yahoo lacks | Alpha Vantage (free tier) |
| 5 | Core inflation, the Fed Funds rate, 1/5/10-year Treasury yields, potential GDP | FRED (St. Louis Fed) |

---

## 3. What came out

### 3.1 Membership (Wikipedia)

- The current list comes from Wikipedia's *List of S&P 500 companies*. The history of changes is on a
  separate page, *Historical components of the S&P 500*.
- The record is sparse before 2008: 2 changes in the 1970s, 8 in the 1990s, 43 in the 2000s, then
  **220 in the 2010s** and 141 in the 2020s. That's why the study starts in **2010** (361 changes since).
- Each removal comes with a free-text reason. These were sorted into buckets (acquired, market cap,
  spin-off, failed, ticker change) with keyword rules.

### 3.2 The survivorship gap

320 companies left the index between 2010 and Oct 2026 and aren't members today. Yahoo Finance has
usable history for only about a third of them:

| Why it was removed | Total | On Yahoo | Missing |
| --- | --- | --- | --- |
| Acquired or merged | 149 | 5 | **144** |
| Market cap / index rules | 126 | 81 | 45 |
| Spin-off or restructuring | 33 | 13 | 20 |
| Failed (SVB, Signature Bank, First Republic) | 3 | 0 | 3 |
| Ticker change | 4 | 1 | 3 |
| Other | 5 | 2 | 3 |
| **Total** | **320** | **102** | **218** |

Companies dropped for market cap mostly still trade on smaller indexes, so Yahoo has them.
**Acquired companies are almost all missing.** That's the gap that matters most for this question
([Chapter 1](01_problem.md#3-why-its-harder-than-it-looks-survivorship-bias)).

"Usable" means more than one row of data, starting before the removal date. Two cases count as missing:
- a 1-row "stub" (Yahoo keeps only the last price of some recent delistings);
- data that starts after the removal (another company reused the ticker).

### 3.3 Filling the gap: Alpha Vantage

Alpha Vantage's free tier allows only **25 requests a day**. Full daily history is a paid feature, but
**monthly prices are free, with full history and dividends included**. Monthly prices are enough for
monthly returns, which is what the strategy trades on.

- **Checked against Yahoo:** Coca-Cola's dividend-adjusted prices matched within 0.1% from 2005 to
  2026. The last prices of Warner Bros. Discovery, AvalonBay and Electronic Arts matched Yahoo exactly.
- **It has the hard cases:** Twitter, Pioneer Natural Resources, Hologic and Silicon Valley Bank,
  including the March 2023 crash (288.11 → 0.905).
- **It's collected a little every day.** Each evening an automatic run fetches the next ~23 companies,
  most important first: failed banks, then acquisitions, then the rest. It stops when the daily limit
  is reached. At that pace the full list takes about two weeks. **Status on 3 Nov:** 17 companies
  fetched (16 with data; First Republic has none), 198 to go, finishing around 12–14 Nov.

### 3.4 Daily prices (Yahoo Finance)

| Group | Series |
| --- | --- |
| Current members | 503 |
| Removed members Yahoo covers | 108 |
| Market series | 16 |
| **Total** | **627 series, 2,861,374 daily rows** |

The 16 market series are SPY, the 11 sector funds (technology, financials, energy, …), VIX, the Dow
Jones, gold and WTI oil.

- **From Jan 2007.** That's a 3-year warm-up before the first decision in 2010, so 12-month measures and
  200-day averages exist from the start.
- **To the previous day's close**, so a half-finished trading day is never stored.
- **Prices are kept both raw and dividend-adjusted.** Dividends and splits stay visible, and the
  price at the next morning's open can be adjusted the same way as the close.

### 3.5 Economic data (FRED)

Six standard US series, from 2005:

| Series | What it is | How often | Used from |
| --- | --- | --- | --- |
| Core CPI | Inflation, excluding food and energy | Monthly | 1 month after the month it describes |
| Fed Funds rate | The Federal Reserve's policy rate | Monthly | 1 month after |
| 1-, 5- and 10-year Treasury yields | Interest rates on government bonds | Daily | The last value before the decision date |
| Potential GDP | The economy's long-run growth capacity (a projection) | Quarterly | Its own quarter |

**Why "used from" matters.** Inflation for July is published in mid-August. A common shortcut copies
each month's figure onto every day of that month. That lets a model "see" the number about two weeks
before anyone could. Here, a figure is only used once it would have been public.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Start in 2010 | The record of index changes is thin before ~2008 |
| Yahoo first, Alpha Vantage only for the gaps | Yahoo is free and daily. The free Alpha Vantage tier allows 25 requests a day |
| Monthly prices from Alpha Vantage, not daily | Full daily history is a paid feature. Monthly prices are enough for monthly returns |
| Fetch failed banks and acquisitions first | Those are the gaps that would flatter a "buy the winners" test most |
| No large-scale price cross-check of Alpha Vantage | Every price compared so far matched. Any remaining errors would stand out as outliers later |
| US-focused market series: SPY, Dow, sector funds, gold, oil, 10-year yield | This is a US stock picker. Foreign indexes, Brent oil and Bitcoin would add little |
| Use each economic figure only after its publication date | Keeps the golden rule: nothing the strategy uses can come from the future |

---

## 5. Caveats and traps found

These are the problems found while collecting the data, and how each was handled:

- **Reused tickers.** An old ticker can point to a different company today. On Yahoo, `FB` is no longer
  Meta's history. On Alpha Vantage, `STI` returns a company that took the ticker years after SunTrust
  left. Every download is checked against the removal date. [Chapter 3](03_monthly_table.md) adds a
  second check, on trading volume, for the cases this one misses.
- **Prices after a failure.** After a bank fails, Alpha Vantage keeps reporting over-the-counter penny
  prices. Signature Bank went from $0.05 to $1.60 in December 2023 (+3,102%). Each delisted company's
  prices stop after the month it left the index (Chapter 3).
- **Half-finished trading days.** Gold and oil futures trade overnight, so Yahoo returned today's
  unfinished prices. Only completed days are kept.
- **Missing inflation figure.** Core CPI has no October 2025 value (the 2025 government shutdown). The
  previous month's value is carried forward.
- **Oil below zero.** Oil futures closed at −$37.63 on 20 Apr 2020. That's real, not a data error. Only
  the month-end value is used, and it was a normal $18.84.
- **The daily limit is stricter than it looks.** Alpha Vantage's 25 requests seem to count over a rolling
  24 hours, not per calendar day. Only 9 got through on the first scheduled day. The automatic run
  moved to the evening, which pushed the finish date back by a day or two.
