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
**Compuware, El Paso, Genzyme, King Pharmaceuticals, Smith International and Sunoco**. They're now on
the Alpha Vantage list instead.

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

**Stocks that disappear during the hold.** A delisted company's prices are kept up to the end of the
month it left the index, then they stop. A position still open is valued at that last price and held
as cash for the rest of the hold.

The removal month itself must be kept. Silicon Valley Bank left the index on 15 Mar 2023. Its February
month-end price was 288.11, its March one 0.905. Stopping before March would turn a −99.7% loss into
no loss at all. With this rule, a stock bought at the end of January 2023 and held 3 months shows
**−99.7%**, as it should.

### 3.6 The result

| Item | Value (3 Nov 2026) |
| --- | --- |
| Rows | **101,431** (one per member per month-end) |
| Month-ends | 202 (Jan 2010 → Oct 2026) |
| Distinct tickers | 819 |
| Members per month-end | 499–504 |
| Rows with a price | 86.7% |
| Share of rows that beat SPY the next month | 49% |

**Share of members with a price, by year:**

| 2010 | 2012 | 2014 | 2016 | 2018 | 2020 | 2022 | 2024 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 69% | 73% | 77% | 83% | 88% | 93% | 97% | 99.5% | 100% |

Almost all of the missing early rows are companies still on the Alpha Vantage list. About **550
member-months can't be filled from any free source**. These are mostly old companies whose ticker a
current member now uses, so no source keeps the old history: Dow Chemical before 2017, the old
SanDisk, Dell before its 2013 buyout, and Constellation Energy before 2012. That gap is measured and
reported, not hidden.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Walk the changes backwards from today's list | Today's list is accurate. Errors can only come in from the changes, and those can be checked |
| Renames limited to their own dates | Tickers get reused (Q, UA, SUN). A permanent rule would silently give one company another's prices |
| A $10M daily trading check | It catches wrong-company data that starts *before* the removal date, which the date check misses |
| Keep a delisted stock's prices to the end of its removal month | Removes the penny prices that follow a failure, without hiding the crash itself |
| Trade at the next open, not the month-end close | The golden rule: decide on the close, trade the next morning |

---

## 5. Caveats

- **Until the Alpha Vantage list is finished, the early years are missing most acquired companies.**
  Any results built on the table now are previews, still flattered by survivorship bias.
- **Companies with only monthly prices trade at the month-end close, not the next open.** That's a
  small timing difference for a minority of rows.
- **Six very large monthly moves are still flagged.** All look real: Apache (APA) in the 2020 oil crash,
  and SanDisk, Intel, Dell and Moderna in 2026, all on heavy trading.
