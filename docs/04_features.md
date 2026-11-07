# Chapter 4: Features

## 1. Goal

Give each row of the monthly table (one stock, one month-end) the information a model can use to
guess whether the stock will beat SPY next month. Every value must be **known at that month-end's
close**, the golden rule from [Chapter 1](01_problem.md#7-the-rules-of-the-test).

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

**152 features in 7 groups**, plus the targets and identifiers:

| Group | Count | Examples | Why it's there |
| --- | --- | --- | --- |
| **Past returns** | 5 | Return over 1, 3, 6 and 12 months; 12 months skipping the latest one | The idea itself: these define a "winner" |
| **Technical indicators** | 52 | RSI, MACD, ADX, CCI, Stochastics, Aroon, money flow, on-balance volume, ATR, cycle indicators | Standard summaries of trend, momentum, volume and volatility, computed on monthly bars |
| **Stock risk and position** | 22 | Volatility, downside volatility, beta to SPY, drawdown from the 12-month and all-time high, distance to the 12-month high and low, price vs its 3- and 10-month average, share of up months, a volume spike measure, plus the seven added in Section 3.5 | Separates steady climbers from erratic jumps. Stocks near their highs, and sudden volume spikes (often takeover news), are known to behave differently |
| **Compared with other members** | 17 | Rank of each past return among all members, rank within the sector, return vs SPY and vs the sector fund, share of members in an uptrend, spread between the best and worst stocks, how last month's top 10 just did, months in the index | "Winner" is relative. Ranks stay comparable in bull and bear markets. How last month's winners just did shows whether momentum is "working" right now |
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
| Share of features filled: Yahoo stocks vs monthly-only stocks | **99.6% vs 99.8%**. A blank says nothing about where the data came from, or whether the company later leaves |
| Strongest link between any single feature and next month's result (2010–2022) | An average rank correlation of **0.021**. A leaked feature typically shows 0.1 or more |

### 3.5 Eight more features, after a review against the course material

A later review compared the features with those built in the course this project grew out of, and
with well-known findings from research on stock returns. Most of the course's features were already
here in monthly form. Eight measure something none of the others did:

| Feature | What it measures | Why it's useful |
| --- | --- | --- |
| Dividend yield (12 months) | Dividends paid over the past year ÷ price | Income stocks behave differently from growth stocks, and nothing else here sees dividends |
| 12-1 month return ÷ volatility | Momentum per unit of risk | A steady climb and a wild one with the same return are different bets |
| Drawdown from the all-time high | How far below its highest price since 2000 | A longer memory than the 12-month high |
| Months in the index (capped at 10 years) | Time since the latest addition | New members and long-standing ones are different kinds of company |
| Residual momentum | The 12-1 month return with the market's part removed | Research finds it steadier, and less prone to sudden crashes, than raw momentum |
| Idiosyncratic volatility | How much the stock moves on its own, not with the market | Stocks that swing a lot on their own tend to do worse |
| Best month of the past year | The single largest monthly gain | Separates one big jump (often takeover news) from a steady climb |
| Same calendar month, past 5 years | The stock's average return in next month's calendar month | A known seasonal pattern, unrelated to momentum |

They passed the same checks as the rest. They use only months up to the decision (a test cuts the data
and confirms earlier values don't change), are filled as often for monthly-only stocks as for the
others, and none reaches even 0.02 on its own.

Three columns were **removed** at the same time: three rescalings of the rate of change (divided by
100, plus 1, and plus 100) that are the same number in different units. They were dropped because
their formulas are identical, not because of how they performed. That's 147 − 3 + 8 = 152.

Two of the course's features were **not** added:
- **A stock-split flag.** The monthly prices for companies that left have no split information, so the
  flag would be missing exactly for them, the same leak as Section 3.1.
- **Day-of-week and ticker flags.** Every row is a month-end, and a flag per company would let a model
  memorise names instead of learning patterns.

Some of the new values are extreme but real. A few companies show dividend yields above 100% in one year:
Weyerhaeuser's 2010 special distribution, and spin-offs recorded as dividends. They're kept as they are;
the modelling step limits extreme values in a consistent way.

That last check is also a first, sober preview. **No single feature predicts next month's winners
strongly**, which is normal for stock picking. Last month's return, the plain rule's signal, is among
the strongest, but it points the wrong way: last month's winners did slightly worse the next month
(Chapter 5). Whether the features add up to something useful *together* is the question for the
models (Chapter 6).

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
| Eight features added after a review against the course and research | Each measures something no other feature does. More of the same kind would only add noise |
| Exact copies removed by formula | The same number in different units adds nothing. Removing them by formula, not by results, keeps the choice independent of the data |
| No split flag | It would exist only for the companies that stayed, revealing which ones left |
| Months in the index from the changes record only, for every company | Today's member list has exact join dates, but only for companies still in the index. Using it would make the feature sharper exactly for the survivors |

---

## 5. Caveats

- **Sector labels are each company's final sector, not its sector on each date.** The sector scheme
  itself changed: Real Estate was split out of Financials in September 2016, and Communication Services
  was created in September 2018 (Alphabet and Meta came from technology and consumer discretionary). So
  rows before those dates carry sectors that didn't exist yet. No free history of past sector labels
  exists, and a label carries no information about future returns, so this is accepted and stated
  rather than fixed. One label (The Trade Desk) could reasonably be either technology or communication
  services.
- **Months in the index is capped at 10 years.** The record of index changes is thin before about 2008,
  so a company with no "added" entry is treated as "10 years or more". That's fair to all companies
  alike, but it can't tell a 12-year member from a 40-year one.
- **Potential GDP is a projection that gets revised,** and only the latest version is available. It's
  the one economic figure with a mild, accepted look-ahead.
- **Some indicators need long warm-ups.** The slowest one (TRIX) is missing for about 5% of rows,
  mostly stocks that listed during the study.
- **The numbers are a preview.** The download of delisted companies is still running, so the early years
  are still missing most acquired companies.
