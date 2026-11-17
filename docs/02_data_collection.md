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
| 1 | Today's 503 members, plus a list of 415 index changes (1976 → Oct 2026) | Wikipedia |
| 2 | Which of the 321 members removed since 2010 still have price history on Yahoo Finance | Yahoo Finance |
| 3 | Daily prices from 2000 for members, removed members Yahoo has, and market series | Yahoo Finance |
| 4 | Monthly prices for the removed members Yahoo lacks | Alpha Vantage (free tier) |
| 5 | Core inflation, the Fed Funds rate, 1/5/10-year Treasury yields, potential GDP | FRED (St. Louis Fed) |

---

## 3. What came out

### 3.1 Membership (Wikipedia)

- **Two pages.** Today's list is Wikipedia's *List of S&P 500 companies*. The changes are on
  *Historical components of the S&P 500*.
- **The record is sparse before 2008:**

  | Decade | 1970s | 1990s | 2000s | 2010s | 2020s |
  | --- | --- | --- | --- | --- | --- |
  | Changes recorded | 2 | 8 | 43 | **220** | 142 |

  The 2010s average about 22 a year. The index didn't stand still before then, so the earlier record
  is incomplete. That's why the study starts in **2010** (362 changes since).
- **The removal reasons are approximate.** Each change has one free-text reason, which often
  describes the company added, not the one removed. Keyword rules sort them into buckets: acquired,
  market cap, spin-off, failed, ticker change.

### 3.2 The survivorship gap

321 companies left the index between 2010 and Oct 2026 and aren't members today. Yahoo Finance has
usable history for only about a third of them. A series is usable if it passes two checks:

1. **It starts before the removal date and has more than one row.** This rules out a 1-row "stub"
   (Yahoo keeps only the last price of some recent delistings). It also rules out data that starts
   after the removal (another company reused the ticker). 108 series pass, and all are downloaded.
2. **It trades like an S&P 500 company.** A later check ([Chapter 3](03_monthly_table.md)) compares
   its trading volume with a member's. It finds 6 more that belong to a much smaller company using
   the old ticker, 5 of them for acquired companies. That leaves **102**.

| Recorded reason (approximate) | Total | Yahoo has a series | Usable after the volume check | Missing |
| --- | --- | --- | --- | --- |
| Acquired or merged | 150 | 10 | 5 | **145** |
| Market cap / index rules | 126 | 82 | 81 | 45 |
| Spin-off or restructuring | 33 | 13 | 13 | 20 |
| Failed (SVB, Signature Bank, First Republic) | 3 | 0 | 0 | 3 |
| Ticker change | 4 | 1 | 1 | 3 |
| Other | 5 | 2 | 2 | 3 |
| **Total** | **321** | **108** | **102** | **219** |

- **Companies dropped for market cap** mostly still trade on smaller indexes, so Yahoo has them.
- **Acquired companies are almost all missing.** That's the gap that matters most for this question
  ([Chapter 1](01_problem.md#3-why-its-harder-than-it-looks-survivorship-bias)). The five
  "acquired" companies that pass both checks were in fact dropped for their size on the day of
  another company's deal. Every true takeover Yahoo had a series for failed the volume check.
- **The three missing ticker changes aren't real gaps.** Each company kept trading under its new
  symbol (Kraft Foods as Mondelez, Willis Towers Watson as WTW, Ceridian as Dayforce), and its
  history continues there.

### 3.3 Filling the gap: Alpha Vantage

Alpha Vantage's free tier allows only **25 requests a day**. Full daily history is paid, but
**monthly prices are free, with full history and dividends included**. They're enough: the strategy
trades on monthly returns.

- **Checked against Yahoo:** Coca-Cola's dividend-adjusted prices matched within 0.1% from 2005 to
  2026. The last prices of Warner Bros. Discovery, AvalonBay and Electronic Arts matched Yahoo
  exactly.
- **It has the hard cases:** Twitter, Pioneer Natural Resources, Hologic and Silicon Valley Bank,
  including the March 2023 crash (288.11 → 0.905).
- **It was collected a little every day.** Each day from 2 to 13 Nov 2026 (in the evening from
  3 Nov), an automatic run fetched the next ~23 companies, stopping at the daily limit. The most
  important came first: failed banks, then acquisitions, then the rest.
- **All 216 were tried.** 140 return prices, 43 return a different company that now uses the old
  ticker, and 33 have no data at all. A later check ([Chapter 3](03_monthly_table.md)) finds four
  of the 140 are other securities too, so 136 are used.
- **Most of the 80 failures are takeovers (51).** The rest are mostly companies dropped for their
  size (17) and spin-offs (9).
- **The gap is concentrated in the early years.** 36 of the 61 companies removed in 2010–2013 have
  no free history, against 5 of the 89 removed since 2022. Those are exactly the companies
  survivorship bias leaves out.

### 3.4 Daily prices (Yahoo Finance)

| Group | Series |
| --- | --- |
| Current members | 503 |
| Removed members Yahoo has a series for (6 later rejected, Section 3.2) | 108 |
| Market series | 16 |
| Kenvue (left the index on 30 Oct 2026): a leftover file, unused; its prices come from Alpha Vantage | 1 |
| **Total** | **628 series, 3,673,295 daily rows** |

The 16 market series are SPY, the 11 sector funds (technology, financials, energy, …), VIX, the Dow
Jones, gold and WTI oil.

- **From January 2000**, ten years before the first decision in 2010. Every feature is built from
  monthly bars (Chapter 4), and the slowest monthly indicator (TRIX) needs about seven years of
  history before it gives a value.
- **To the previous day's close**, so a half-finished trading day is never stored.
- **Both raw and dividend-adjusted prices are kept.** Dividends and splits stay visible, and the
  next morning's open can be adjusted the same way as the close.

### 3.5 Economic data (FRED)

Six standard US series, from 2005:

| Series | What it is | How often | Used from |
| --- | --- | --- | --- |
| Core CPI | Inflation, excluding food and energy | Monthly | 1 month after the month it describes |
| Fed Funds rate | The Federal Reserve's policy rate | Monthly | 1 month after |
| 1-, 5- and 10-year Treasury yields | Interest rates on government bonds | Daily | The last value before the decision date |
| Potential GDP | The economy's long-run growth capacity (a projection) | Quarterly | Its own quarter, in the version published before the decision |

- **Why "used from" matters.** Inflation for July is published in mid-August. A common shortcut
  copies each month's figure onto every day of that month, which lets a model "see" the number about
  two weeks before anyone could. Here, a figure is only used once it would have been public.
- **Revisions.** FRED serves today's revised values, but it also archives each past version.
  Potential GDP, a projection revised often and by a lot, is read in the version published before
  each decision.
- **Core CPI uses today's version.** Only its seasonal adjustment is recalculated each year, a
  small difference ([Chapter 4](04_features.md)).

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Yahoo first, Alpha Vantage only for the gaps | Yahoo is free and daily. The free Alpha Vantage tier allows 25 requests a day |
| Fetch failed banks and acquisitions first | Those are the gaps that would flatter a "buy the winners" test most |
| No large-scale price cross-check of Alpha Vantage | Every price compared matched. Any remaining errors would stand out as outliers later |
| US-focused market series: SPY, Dow, sector funds, gold, oil, 10-year yield | This is a US stock picker. Foreign indexes, Brent oil and Bitcoin would add little |

---

## 5. Caveats and traps found

The problems found while collecting the data, and how each was handled:

- **Reused tickers.** An old ticker can point to a different company today. On Yahoo, `FB` is no
  longer Meta's history. On Alpha Vantage, `STI` returns a company that took the ticker years after
  SunTrust left. Every download is checked against the removal date, and
  [Chapter 3](03_monthly_table.md) adds a volume check for the cases this one misses.
- **Prices after a failure.** After a bank fails, Alpha Vantage keeps reporting over-the-counter
  penny prices: Signature Bank went from $0.05 to $1.60 in December 2023 (+3,102%). Each delisted
  company's prices stop after the month it left the index (Chapter 3).
- **Half-finished trading days.** Gold and oil futures trade overnight, so Yahoo returned today's
  unfinished prices. Only completed days are kept.
- **Missing inflation figure.** Core CPI has no October 2025 value (the 2025 government shutdown).
  The previous month's value is carried forward.
- **Oil below zero.** Oil futures closed at −$37.63 on 20 Apr 2020. That's real, not a data error.
  Only the month-end value is used, and it was a normal $18.84.
- **The download's limits.** Alpha Vantage's limit seems to run over a rolling 24 hours. A run cut
  off halfway loses at most one request.
- **A gap remains.** 80 of the 216 have no free history, mostly early takeovers.
  [Chapter 3](03_monthly_table.md) counts it: 4.5% of member-months have no price.
