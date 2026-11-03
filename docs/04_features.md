# Chapter 4: Features

## 1. Goal

Give each row of the monthly table (one stock, one month-end) the information a model can use to
guess whether the stock will beat SPY next month. Every value must be **known at that month-end's
close**, the golden rule from [Chapter 1](01_problem.md#4-the-rules-of-the-test).

---

## 2. What was done

| Step | What happens |
| --- | --- |
| 1 | Turn every stock's prices into **monthly bars** (open, high, low, close and volume for each month) |
| 2 | Work out technical indicators, risk measures and volume measures from those bars |
| 3 | Add what the whole market, interest rates and inflation were doing |
| 4 | Compare each stock with all the other members on the same date (ranks, relative strength) |
| 5 | Give every company a sector, and add month and sector flags |
| 6 | Group the columns into named sets, and check for look-ahead |

---

## 3. What came out

### 3.1 Why everything is built from monthly bars

About 200 of the companies that later left the index only have monthly prices (Chapter 2). Daily
measures, like a 14-day RSI or the share of up days, can't be worked out for them.

Leaving those values blank would have been worse than it sounds. **"No daily data" happens exactly
for companies that are later delisted**, mostly acquired. A model would soon learn that a blank
means "this company is about to disappear", which is information from the future.

So every stock is treated the same way. Daily prices are rolled up into monthly bars, and every
feature is computed from those bars. The cost is that day-level detail, such as the biggest
single-day jump in a month, is replaced by monthly versions.

### 3.2 The feature sets

**147 features in 7 groups**, plus the targets and identifiers:

| Group | Count | Examples | Why it's there |
| --- | --- | --- | --- |
| **Past returns** | 5 | Return over 1, 3, 6 and 12 months; 12 months skipping the latest one | The idea itself: these define a "winner" |
| **Technical indicators** | 55 | RSI, MACD, ADX, CCI, Stochastics, Aroon, money flow, on-balance volume, ATR, cycle indicators | Standard summaries of trend, momentum, volume and volatility, computed on monthly bars |
| **Stock risk and position** | 15 | Volatility, downside volatility, beta to SPY, drawdown from the 12-month high, distance to the 12-month high and low, price vs its 3- and 10-month average, share of up months, a volume spike measure | Separates steady climbers from erratic jumps. Stocks near their highs, and sudden volume spikes (often takeover news), are known to behave differently |
| **Compared with other members** | 16 | Rank of each past return among all members, rank within the sector, return vs SPY and vs the sector fund, share of members in an uptrend, spread between the best and worst stocks, how last month's top 10 just did | "Winner" is relative. Ranks stay comparable in bull and bear markets. How last month's winners just did shows whether momentum is "working" right now |
| **Market** | 24 | Return of SPY, the Dow, gold and oil over 1, 3, 6 and 12 months; change in the 10-year yield; the stock's sector fund over 1, 3 and 12 months; VIX level and where it sits in its 5-year range | The market's mood. Momentum strategies are known to crash in sharp rebounds after a fall |
| **Economy** | 9 | Core inflation (yearly and monthly), Fed Funds rate, 1/5/10-year yields, the yield-curve slope, potential GDP growth | The interest-rate and inflation regime, which shifts which stocks lead |
| **Flags** | 23 | Month of the year (12), sector (11) | Seasonal effects (e.g. January reversals) and sector identity |

**Raw price and volume levels are made comparable.** Some indicators come out in dollars or shares:
on-balance volume, the accumulation/distribution line, MACD, momentum, ATR, and the average and
typical prices. A $500 stock and a $20 stock can't be compared on those. Price-like values are
divided by the stock's price, and running volume totals become their 12-month change relative to
12 months of volume. A check confirms that the same stock at 50 times the share price gets exactly
the same indicator values.

### 3.3 Sectors for companies that left

The current member list has each company's sector. For the 316 companies that left the index since
2010, none is recorded anywhere in the membership data. Each was labelled by hand with its last
sector, using the same 11-sector scheme as today's members.

The labels were then compared with Yahoo Finance's own sector field for the ~100 companies Yahoo
still lists:

| Comparison | Agreement |
| --- | --- |
| Today's members: official sector vs Yahoo (a baseline for how much the two schemes differ) | 95% |
| Companies that left: hand labels vs Yahoo | 90% |

Three of the disagreements were actually Yahoo describing the *wrong company*: the tiny securities
that later reused those tickers (Chapter 3). For example, Yahoo calls Compuware a utility. The rest
are differences between the two sector schemes.

### 3.4 Checks for look-ahead

| Check | Result |
| --- | --- |
| Inflation used for the August 2026 decision | **July's** figure. August's wasn't published until mid-September |
| 10-year yield used on 30 Oct 2026 | **29 Oct's** value. A day's yield is published the next day |
| Fed Funds rate used on 30 Oct 2026 | **September's** figure. October's comes out in November |
| Share of features filled: Yahoo stocks vs monthly-only stocks | **99.6% vs 99.9%**. A blank says nothing about where the data came from, or whether the company later leaves |
| Strongest link between any single feature and next month's result | An average rank correlation of **0.014**. A leaked feature typically shows 0.1 or more |

That last check is also a first, sober preview. **No single feature predicts next month's winners
strongly**, which is normal for stock picking. Last month's return, the plain rule's signal, isn't
among the ten strongest. Whether the features add up to something useful *together* is the
question for the models (Chapter 6).

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Monthly bars for every stock, no daily-only features | Blank daily features would reveal which companies are later delisted (Section 3.1) |
| Prices from 2000, though decisions start in 2010 | The slowest monthly indicators need years of history. MACD needs about 3, the cycle indicators about 5 |
| Technical indicators kept, candlestick patterns dropped | A one-day candle pattern says little about the next month. Patterns would add ~60 mostly empty columns |
| Market series: SPY, Dow, the sector fund, gold, oil, the 10-year yield | This is a US stock picker. Foreign indexes and crypto would add little |
| Economic figures used only after publication | The golden rule. A common shortcut uses each month's figure about two weeks too early |
| Ranks computed within each date only | Comparing a stock with other members on the *same* date keeps bull and bear months comparable, and can't mix in later information |
| Sectors labelled by hand, never "unknown" | An "unknown" sector would mean "this company left the index later", the same leak as Section 3.1 |
| Sector funds that didn't exist yet are replaced | Real Estate uses the financials fund before its own started (2015), and Communication Services uses SPY before 2018 |

---

## 5. Caveats

- **Sector labels are each company's final sector, not its sector on each date.** For example, Alphabet
  was classed as technology before 2018. A sector rarely changes, and the change doesn't carry
  information about future returns, so the effect should be small. One label (The Trade Desk) could
  reasonably be either technology or communication services.
- **Potential GDP is a projection that gets revised,** and only the latest version is available. It's
  the one economic figure with a mild, accepted look-ahead.
- **Some indicators need long warm-ups.** The slowest one (TRIX) is missing for about 5% of rows,
  mostly stocks that listed during the study.
- **The numbers are a preview.** The download of delisted companies is still running, so the early years
  are still missing most acquired companies.
