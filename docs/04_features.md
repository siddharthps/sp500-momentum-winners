# Chapter 4: Features

## 1. Goal

Give each row of the monthly table (one stock, one month-end) what a model needs to guess whether,
and by how much, the stock will beat SPY next month. Every value must be **known at that
month-end's close**: the golden rule from [Chapter 1](01_problem.md#7-the-rules-of-the-test).

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

- **Many companies that later left the index have only monthly prices:** 135 in the table
  (Chapter 2's 136 usable from Alpha Vantage, less DowDuPont, priced from its daily history under
  its later ticker). Daily measures, like a 14-day RSI or the share of up days, can't be worked out
  for them.
- **Leaving those values blank would leak the future.** "No daily data" happens exactly for
  companies that are later delisted, mostly acquired. A model would soon learn that a blank means
  "this company is about to disappear".
- **So every stock is treated the same way:** daily prices are rolled up into monthly bars, and
  every feature is computed from those bars. The cost: day-level detail, such as the biggest
  single-day jump in a month, is replaced by monthly versions.

### 3.2 The feature sets

**147 features in 7 groups**, plus the targets and identifiers:

| Group | Count | Examples | Why it's there |
| --- | --- | --- | --- |
| **Past returns** | 5 | Return over 1, 3, 6 and 12 months; 12 months skipping the latest one | The idea itself: these define a "winner" |
| **Technical indicators** | 47 | RSI, MACD, ADX, CCI, Stochastics, Aroon, money flow, on-balance volume, ATR, cycle indicators | Standard summaries of trend, momentum, volume and volatility, computed on monthly bars |
| **Stock risk and position** | 22 | Volatility, downside volatility, beta to SPY, drawdown from the 12-month high, distance to the 12-month high and low, price vs its 3- and 10-month average, share of up months, a volume spike measure, plus the seven added in Section 3.5 | Separates steady climbers from erratic jumps. Stocks near their highs, and sudden volume spikes (often takeover news), are known to behave differently |
| **Compared with other members** | 17 | Rank of each past return among all members, rank within the sector, return vs SPY and vs the sector fund, share of members in an uptrend, spread between the best and worst stocks, how last month's top 10 just did, months in the index | "Winner" is relative. Ranks stay comparable in bull and bear markets. How last month's winners just did shows whether momentum is "working" right now |
| **Market** | 24 | Return of SPY, the Dow, gold and oil over 1, 3, 6 and 12 months; change in the 10-year yield; the stock's sector fund over 1, 3 and 12 months; VIX level and its percentile over the past 5 years | The market's mood. Momentum strategies are known to crash in sharp rebounds after a fall |
| **Economy** | 9 | Core inflation (yearly and monthly), Fed Funds rate, 1/5/10-year yields, the yield-curve slope, potential GDP growth | The interest-rate and inflation regime, which shifts which stocks lead |
| **Flags** | 23 | Month of the year (12), sector (11) | Seasonal effects (e.g. January reversals) and sector identity |

**Raw price and volume levels are made comparable.** Some indicators come out in dollars or shares
(on-balance volume, the accumulation/distribution line, MACD, momentum, ATR, and the average and
typical prices), and a $500 stock and a $20 stock can't be compared on those.

- Price-like values are divided by the stock's price.
- Running volume totals become their 12-month change relative to 12 months of volume.
- A check confirms that the same stock at 50 times the share price gets exactly the same indicator
  values.

**Eight columns were dropped as copies:** three rescalings of the rate of change and five
indicators that are exact functions of others. All went for their formulas, not their performance,
and a check now fails if any indicator becomes a rescaled copy of another.

| Dropped | Why it's a copy |
| --- | --- |
| Rescaled rate of change | Divided by 100, plus 1, and plus 100 |
| Chande Momentum Oscillator | The RSI rescaled |
| Fast stochastics' %D | It *is* slow %K |
| ATR in percent | The ATR ÷ price times 100 |
| Typical and weighted-close prices | Once divided by the close, fixed fractions of the median price |

### 3.3 Sectors for companies that left

The current member list has each company's sector; for the 321 companies that left the index since
2010, the membership data records none.

- **317 were labelled by hand** with their last sector, in the same 11-sector scheme as today's
  members.
- **The other four don't need one.** Three were renamed and keep their sector under the new ticker.
  MasterBrand joined and left within December 2022, so it was never a member at a month-end.

The labels were then compared with Yahoo Finance's own sector field for the ~100 companies Yahoo
still lists:

| Comparison | Agreement |
| --- | --- |
| Today's members: official sector vs Yahoo (a baseline for how much the two schemes differ) | 95% |
| Companies that left: hand labels vs Yahoo | 90% |

Three of the disagreements were Yahoo describing the *wrong company*: the tiny securities that
later reused those tickers (Chapter 3). Yahoo calls Compuware a utility, for example. The rest are
differences between the two sector schemes.

### 3.4 Checks for look-ahead

| Check | Result |
| --- | --- |
| Inflation used for the August 2026 decision | **July's** figure. August's wasn't published until mid-September |
| 10-year yield used on 30 Oct 2026 | **29 Oct's** value. A day's yield is published the next day |
| Fed Funds rate used on 30 Oct 2026 | **September's** figure. October's comes out in November |
| Share of features filled: Yahoo stocks vs monthly-only stocks | **99.6% vs 99.0%**. The gap is in the slowest indicators (TRIX, the cycle measures, the 36-month risk measures), which need years of history (below) |
| Strongest link between any single feature and next month's result (2010–2022) | An average rank correlation of **0.023**. That's the size of a weak real signal (Chapter 5); a feature that leaked next month's result would stand far above it |

- **The fill gap comes from history length.** Monthly-only companies more often have a short
  history or rows in the early years, and both are known at the decision. Leaving out each stock's
  first five years in the table and the table's first year, both sources are at least 99.97%
  filled. So a blank says how long a stock has traded, not whether it later leaves.
- **No single feature predicts next month's winners strongly**, which is normal for stock picking.
  The last check is also a first, sober look at the results. Last month's return (the 1-month plain
  rule's signal) is among the strongest, but it points the wrong way: last month's winners did
  slightly worse the next month (Chapter 5).
- **Whether the features add up to something useful *together*** is the question for the models
  (Chapter 6).

### 3.5 Eight features from research and common practice

The features were compared with those commonly built for stock-picking models, and with well-known
findings from research on stock returns. Most were already here in monthly form. These eight
measure something none of the others does; more of the same kind would only add noise:

| Feature | What it measures | Why it's useful |
| --- | --- | --- |
| Dividend yield (12 months) | Dividends paid over the past year ÷ price | Income stocks behave differently from growth stocks, and nothing else here sees dividends |
| 12-1 month return ÷ volatility | Momentum per unit of risk | A steady climb and a wild one with the same return are different bets |
| Drawdown from the all-time high | How far below its highest price since 2000 | A longer memory than the 12-month high |
| Months in the index (capped at 10 years) | Time since the latest addition | New members and long-standing ones are different kinds of company |
| Residual momentum | The 12-1 month return with the market's part removed | Research finds it more consistent over time than raw momentum, and more profitable after risk |
| Idiosyncratic volatility | How much the stock moves on its own, not with the market | Stocks that swing a lot on their own tend to do worse |
| Best month of the past year | The single largest monthly gain | Separates one big jump (often takeover news) from a steady climb |
| Same calendar month, past 5 years | The stock's average return in next month's calendar month | A known seasonal pattern, unrelated to momentum |

- **They passed the same checks as the rest.** They use only months up to the decision (a test cuts
  the data and confirms earlier values don't change), and none reaches even 0.02 on its own.
- **The three that need three to five years of history** (residual momentum, idiosyncratic
  volatility and the 5-year seasonal average) are blank a little more often for monthly-only
  stocks: 95–97% filled against 98–99%, for the warm-up reason in Section 3.4.
- **Some values are extreme but real, and kept as they are.** A few companies show dividend yields
  above 100% in one year: Weyerhaeuser's 2010 special distribution, and spin-offs recorded as
  dividends. The modelling step limits extreme values in a consistent way.

Two common features were **not** added:

- **A stock-split flag.** The monthly prices for companies that left have no split information, so
  the flag would be missing exactly for them, the same leak as Section 3.1.
- **Day-of-week and ticker flags.** Every row is a month-end, and a flag per company would let a
  model memorise names instead of learning patterns.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Prices from 2000, though decisions start in 2010 | The slowest monthly indicators need years of history: MACD about 3, the cycle indicators about 5, TRIX about 7 |
| Technical indicators kept, candlestick patterns dropped | A one-day candle pattern says little about the next month. Patterns would add ~60 columns that are zero almost every month |
| Ranks computed within each date only | Ranking across dates would mix in later information |
| Sectors labelled by hand, never "unknown" | An "unknown" sector would mean "this company left the index later", the same leak as Section 3.1 |
| Sector funds that didn't exist yet are replaced | Real Estate uses the financials fund before its own started (2015; REITs were part of Financials until 2016), and Communication Services uses SPY before 2018 |
| Months in the index from the changes record only, for every company | Today's member list has exact join dates, but only for companies still in the index. Using it would make the feature sharper exactly for the survivors |

---

## 5. Caveats

- **Sector labels are each company's final sector, not its sector on each date.** The scheme itself
  changed: Real Estate was split out of Financials in September 2016, and Communication Services
  was created in September 2018 (Alphabet and Meta came from technology, Netflix from consumer
  discretionary). So rows before those dates carry sectors that didn't exist yet. This is accepted
  and stated rather than fixed: no free history of past sector labels exists, and every company is
  labelled in the same scheme, so a label doesn't reveal which companies later leave. One label
  (The Trade Desk) could reasonably be either technology or communication services.
- **Months in the index is capped at 10 years.** The record of index changes is thin before about
  2008, so a company with no "added" entry is treated as "10 years or more". That's fair to all
  companies alike, but it can't tell a 12-year member from a 40-year one.
- **Core inflation uses today's version.** Its seasonal adjustment is recalculated each year, so
  past months shift slightly: a mild, accepted look-ahead. Potential GDP, revised by far more, is
  read in the version published before each decision (its 2023 growth: 1.8% as published then,
  2.6% in today's version).
- **Some indicators need long warm-ups.** The slowest one (TRIX) is missing for about 6% of rows,
  mostly stocks that listed during the study.
