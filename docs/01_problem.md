# Chapter 1: The problem and the idea

## 1. Goal

> **At the end of each month, if you buy the S&P 500 stocks that rose the most and hold them for a
> while, do you beat the S&P 500 itself?**

This chapter sets out the question, why it's harder to answer honestly than it looks, and the rules
the test follows.

---

## 2. The idea in plain words

Every month-end:

1. Take every company that was **in the S&P 500 on that date**.
2. Rank them by how much they rose (the **"winners"**).
3. Buy the top ones at the **next morning's open**.
4. Hold them for a few months, then sell.
5. Compare the result with simply holding **SPY**, an S&P 500 fund (dividends included).

Two ways of picking the stocks are compared:

| Picker | How it ranks the stocks |
| --- | --- |
| **The plain rule** (the baseline) | By last month's return. Buy the top 1, 5 or 10 |
| **A machine-learning model** | By the model's estimated chance that the stock beats SPY next month. Buy the top 1, 5 or 10 |

The model only earns its place if it beats the **plain rule**, not just SPY. "Buy what went up
recently" is a well-known and surprisingly hard benchmark, so beating it is the real test.

---

## 3. Why it's harder than it looks: survivorship bias

The obvious way to test the idea is to download today's 503 S&P 500 members and look back. That
gives a badly wrong answer. Today's list only contains the companies that **survived**. It leaves out
everything that was acquired, went bust or got dropped from the index along the way.

For a "buy the winners" strategy, two of those gaps matter most:

- **Takeovers.** A takeover bid is one of the most common reasons a stock is the month's top gainer.
  After the jump, the price sits near the deal price until the deal closes, so it barely moves while
  the market keeps going. Without acquired companies, the rule never picks a takeover target, and it
  looks better than it would really have been.
- **Crashes during the hold.** A stock bought as a winner can collapse and then get dropped from the
  index. Silicon Valley Bank fell **−99.7%** in March 2023. If it's missing from the data, the test
  never sees that loss.

So the project rebuilds **who was in the index on each date** (point-in-time membership), and finds
prices for the companies that later left. [Chapter 2](02_data_collection.md) covers how.

---

## 4. The rules of the test

| Rule | Choice | Why |
| --- | --- | --- |
| **Universe** | S&P 500 members as of each date | Avoids survivorship bias (Section 3) |
| **Period** | Jan 2010 → Oct 2026 (202 month-ends) | The public record of index changes is thin before ~2008 |
| **Decision time** | The last trading day of each month | One decision a month, matching the idea |
| **The golden rule** | Everything the strategy uses is known **at the month-end close**; it trades **at the next open** | No peeking at the future |
| **Model target** | Does the stock beat SPY over the next month? | Directly answers "does it beat the index?". About 49% of stocks do in a typical month, so it's a fair coin to start with |
| **Hold periods (plain rule)** | 1, 3, 6 and 12 months | Research on momentum finds the effect over roughly 3–12 months. 1 month tests the idea as first stated |
| **Benchmarks** | SPY, plus an equal-weight basket of all members | The second shows whether an edge is real stock picking or just a tilt towards smaller members |
| **Costs** | ~0.1% per buy and per sell | A monthly rule replaces most of its holdings every month |

---

## 5. What makes this question different

Most stock-prediction examples ask *"will this stock go up?"* for a handful of well-known companies,
one day at a time. This project asks a different question:

| | Typical setup | This project |
| --- | --- | --- |
| Stocks | A fixed list of today's giants | ~500 S&P 500 members **as of each date**, including ones that later left |
| Question | Will the stock go up? | Will it **beat the index**, ranked against ~500 others? |
| Decision | Every day | Once a month (built from 2.86M daily prices) |

"Will it go up?" is easy to get right in a rising market: most stocks rise. "Will it beat the index?"
removes the market's general direction and leaves only the stock picking.

---

## 6. Decisions and why

- **One row per stock per month-end, not per day.** The decision is monthly. Daily rows would
  overlap heavily, and "last month's winner" would turn into a daily rule.
- **The model predicts one month ahead only.** Testing a 12-month prediction on a ~4-year test period
  leaves only about 2 independent periods to judge it on. The plain rule fits nothing to the data, so
  it can be tested on every hold period over the full 2010–2026 span.
- **No 24-month holds.** That's past the range where momentum is known to work (over longer spans,
  winners tend to fall back). It would also need long gaps between the training and test periods,
  using up about 4 of the 16 years.

---

## 7. Caveats

- **Free data only.** Prices for some delisted companies can't be found anywhere free. That gap is
  measured and reported ([Chapter 3](03_monthly_table.md)), not hidden.
- **2010–2026 was mostly a rising market.** Any strategy that holds stocks looks good in it. That's why
  the comparison is against SPY and an equal-weight basket, not against zero.
