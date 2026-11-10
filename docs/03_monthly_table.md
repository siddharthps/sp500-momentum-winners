# Chapter 3: Building the monthly table

## 1. Goal

Turn the raw downloads into **one table with one row per S&P 500 member per month-end**. Each row
holds the stock's prices, its past returns and what happened next. Later chapters add more columns to
this table and train the models on it.

---

## 2. What was done

| Step | What happens |
| --- | --- |
| 1 | Pick the decision dates: the last trading day of each month, Jan 2010 → Oct 2026 (202 dates) |
| 2 | Rebuild the members on each date from the list of index changes |
| 3 | Repair the gaps in that list (renames, a missing addition, typos) |
| 4 | Turn daily prices into monthly ones: the month-end close and the next morning's open |
| 5 | Throw out price data that belongs to a different company (a volume check) |
| 6 | Work out past returns and future returns, and compare them with SPY |

The table is rebuilt from scratch whenever new data arrives, so the results always reflect
everything collected so far.

---

## 3. What came out

### 3.1 Membership on each date

Start from today's 503 members and walk the list of changes **backwards in time**. Undoing a change
means taking the added company out and putting the removed one back. A change counts from its own
date, so a stock added on a month-end counts as a member that day.

After the repairs below, every month-end has **499–504 members**. That's right for the S&P 500,
which has slightly more lines than 500 companies because a few have two share classes (e.g.
Alphabet's GOOGL and GOOG).

### 3.2 Repairs to the record of changes

Walking backwards only works if the record is complete. It isn't quite:

| Problem | Example | Effect if left alone | Fix |
| --- | --- | --- | --- |
| **Rename never recorded** | Facebook joined as `FB` in Dec 2013. The rename to `META` has no entry | Meta would count as a member from 2010, two years before it was even listed | Treat the 2013 addition as `META`. The same applies to Aptiv, Capri, Corpay, Everest Group, Under Armour, EchoStar and Alphabet's class C |
| **Ticker reused over time** | `Q` was Qwest (to 2011), then QuintilesIMS (2017), and is Qnity today | A simple "Q means IQVIA" rule would give Qnity the wrong prices | Each rename applies **only within its own dates** |
| **Addition never recorded** | Smurfit Westrock (`SW`) joined in 2024 with no entry | It would count back to 2010, priced with data from an older, unrelated "SW" | Add the missing entry |
| **Typos** | One entry reads `ALLE \|` / `JCP \|` | JCPenney was never looked up for prices | Strip stray characters from tickers |
| **Misleading reason** | Bemis was acquired, but the text reads like a ticker change | It wasn't fetched as an acquired company | Correct the reason by hand |
| **Rename recorded as a removal** | Discovery renamed itself Warner Bros. Discovery in 2022, recorded as "WBD added, DISCA removed" | Discovery (2010–2022) would look like a company that left, with no price | Treat it as a rename, priced from WBD's unbroken history |
| **The buyer kept the target's ticker** | ACE bought Chubb in 2016 and took its `CB` ticker; the sources file ACE's history under `CB` | The old Chubb would carry ACE's prices, and ACE would have none | Price each from its own history: ACE from `CB`, the old Chubb unpriced. The same for Tyco/Johnson Controls, Dow/DuPont and AGL/Nicor |

The kept-ticker cases slip past the volume check (Section 3.4), because both companies were large.
Each was confirmed from the series itself: whose dividends it pays, and whose price level it trades
at.

### 3.3 Monthly prices

Each row gets two prices:

- **The month-end close**, used to measure what the stock did up to the decision.
- **The price the strategy can actually trade at**: the next trading day's open, following the golden
  rule (decide on the close, trade the next morning). For the companies with only monthly prices
  (Chapter 2), the month-end close stands in for it.

Both are adjusted for dividends and splits, so returns compare fairly with SPY's.

### 3.4 Data from the wrong company

Some removed tickers passed the checks in Chapter 2, but their Yahoo data belongs to a **different,
tiny security** that took the ticker later. Compuware's showed almost no trading, and swings of +300%
and −75% within a month.

A real S&P 500 company trades far more than $10 million of shares a day. Any series whose typical daily
trading, over its months as a member, falls below that has its prices thrown out. Six were caught:
**Compuware, El Paso, Genzyme, King Pharmaceuticals, Smith International and Sunoco**, and sent to
Alpha Vantage instead. El Paso and Genzyme were found there, and Sunoco wasn't (its ticker is reused
there too). The other three are still in the queue.

### 3.5 What happened next (the targets)

For each hold period (1, 3, 6 and 12 months), every row records:

| Measure | Meaning |
| --- | --- |
| Future return | From the next open to the open at the end of the hold |
| SPY's return | Over exactly the same window |
| Excess return | The stock's return minus SPY's |
| **Beat SPY?** | Yes if the excess return is positive. **The model's target, for the 1-month hold** |
| Top 10%? | Yes if the stock was among the best tenth of members over the window |
| Cut short? | Yes if the stock's prices ended during the hold (see below) |

Past returns over 1, 3, 6 and 12 months, and over 12 months skipping the latest month, are recorded
too. These are the "winner" measures the plain rule ranks on.

**Stocks that disappear during the hold.** A delisted company's prices are kept to the end of the
month it left the index. An open position is valued at that last price, then held as cash. Keeping
the removal month matters: Silicon Valley Bank went from 288.11 at the end of February 2023 to 0.905
at the end of March, the month it left. Stopping in February would turn its **−99.7%** into no loss.

### 3.6 The result

| Item | Value (9 Nov 2026, preview) |
| --- | --- |
| Rows | **101,431** (one per member per month-end) |
| Month-ends | 202 (Jan 2010 → Oct 2026) |
| Distinct tickers | 819 |
| Members per month-end | 499–504 |
| Rows with a price | 92.9% |
| Share of rows that beat SPY the next month | 49% |

**Share of members with a price, by year:**

| 2010 | 2012 | 2014 | 2016 | 2018 | 2020 | 2022 | 2024 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 80% | 84% | 88% | 92% | 96% | 98% | 99% | 99.7% | 100% |

**Rows still without a price:** 7,193 (7%). About 4,150 are companies still on the Alpha Vantage
list. The other **~3,040 (3%) can't be filled from any free source**:

| Why there's no price | Member-months |
| --- | --- |
| Another company now uses the old ticker on Alpha Vantage | 1,820 |
| Alpha Vantage has no data | 504 |
| Alpha Vantage covers only part of the company's time in the index | 296 |
| The buyer kept the target's ticker (Section 3.2) | 261 |
| A current member now uses the ticker (the old SanDisk, Dell, Constellation, Qwest) | 161 |

Almost all are takeovers, buy-outs or failures in the early years: exactly what survivorship bias
leaves out. The final count comes once the download is complete.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Walk the changes backwards from today's list | Today's list is accurate. Errors can only come in from the changes, and those can be checked |
| Renames limited to their own dates | Tickers get reused (Q, UA, SUN). A permanent rule would silently give one company another's prices |
| A $10M daily trading check | It catches wrong-company data that starts *before* the removal date, which the date check misses |
| Kept-ticker cases fixed by choosing each row's price series, not by a rename | Both companies were members, so both lines stay. Only the price series each line uses changes. A company with no free history of its own stays unpriced, rather than carrying the buyer's prices |
| Keep a delisted stock's prices to the end of its removal month | Removes the penny prices that follow a failure, without hiding the crash itself |
| Trade at the next open, not the month-end close | The golden rule: decide on the close, trade the next morning |

---

## 5. Caveats

- **Until the Alpha Vantage list is finished, the early years are still missing many acquired
  companies.**
  Any results built on the table now are previews, still flattered by survivorship bias.
- **Companies with only monthly prices trade at the month-end close, not the next open.** That's a
  small timing difference for a minority of rows.
- **A few takeover targets are missing as lines, not just as prices.** The record of changes merges
  them into their buyer's line: the old Allergan (until Actavis bought it and took its name in 2015),
  21st Century Fox (2013–2019) and the old News Corp (2010–2013). No free source has their history,
  so adding them back would only add unpriced rows. They're stated here instead.
- **Six very large monthly moves are still flagged** (more than +100% or below −75% in a month). Each
  was checked one by one, and all are real:
  - **Apache (APA), March and April 2020:** one day of −54% in the oil crash, then a steady rebound.
  - **SanDisk, Intel and Dell in 2026:** steady climbs over 13–14 up days, with no split and heavy
    trading.
  - **Moderna, August 2026 (+156%):** one day of +177%, on 33 times its usual volume. A second price
    source agrees exactly.
