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
2. Rank them by how much they rose over a past stretch (the **"winners"**).
3. Buy the top ones at the **next morning's open**.
4. Hold them for a fixed number of months, then sell.
5. Compare the result with simply holding **SPY**, an S&P 500 fund (dividends included).

Two ways of picking the stocks are compared:

| Picker | How it ranks the stocks | Holds for |
| --- | --- | --- |
| **The plain rule** (the baseline) | By its return over the past 1, 3, 6 or 12 months (each one tested). Buy the top 1, 5 or 10 | 1, 3, 6 or 12 months |
| **A machine-learning model** | By the model's estimate of how likely the stock is to beat SPY next month, using many inputs, past returns among them. Buy the top 1, 5 or 10 | 1 month, because it predicts one month ahead |

The model only earns its place if it beats the **plain rule**, not just SPY. "Buy what went up
recently" is a well-known and surprisingly hard benchmark, so beating it is the real test.

---

## 3. How a hold works: a worked example

Take one rule: **buy the top 5, hold each for 6 months**, starting with $6,000.

It doesn't mean "buy 5 stocks in January and do nothing until July". The result would then depend on
the luck of the starting month: a January start and a March start can give very different answers.
It doesn't mean adding new money every month either, which would make the comparison with SPY
unequal. Instead, the money is split into **six equal slots**, one per month of the hold:

| Date | What happens |
| --- | --- |
| Early January | Slot 1 buys December's top 5, equal amounts each |
| Early February | Slot 2 buys January's top 5, even if some are already held by slot 1. Slot 1 keeps holding |
| March to June | Slots 3 to 6 do the same, one new batch a month |
| Early July | Slot 1 has held for six months: it sells and buys June's top 5. Slot 2 follows in August, and so on |

From then on there are always **six overlapping batches** (up to 30 stocks, fewer when a stock
appears in more than one). Each month **a sixth of the money changes hands**, and every stock is held
exactly six months. This is the standard way to test a longer hold. In effect it averages over all
six possible starting months.

A few details fill the picture in:

- **No new money is added, and none sits idle.** In the first months, before all six slots exist,
  the money is spread over the slots that do (all of it in January's five). After that, each slot is
  a sixth of the portfolio's *current* value, so gains are reinvested: if $6,000 has grown to $7,200,
  the slot refreshed that month gets $1,200.
- **SPY gets the same starting money and is simply held**, dividends reinvested.
- **With a 1-month hold, there's one slot:** sell everything and buy the new top 5 every month.
- **Fractional shares are assumed.** The test works in percentages, not share counts, so $240 in a
  $7,000 stock is simply that stock's move on $240. Most brokers offer fractional shares today. Without
  them, small accounts would hold some leftover cash and couldn't buy the priciest stocks at all; the
  effect fades as the account grows. Because everything is a percentage, the starting amount doesn't
  change any result. The charts start at $10,000 for easy reading.

---

## 4. How the two are compared

Both sides are turned into **monthly returns** over the same months, and compared on four
measures:

| Measure | What it says |
| --- | --- |
| **Yearly return** | How fast the money grew, on average per year |
| **Volatility** | How much the monthly returns swing: the usual measure of risk |
| **Sharpe ratio** | Return earned above cash (the Fed Funds rate), per unit of volatility. The fairest single score: a riskier strategy should earn more |
| **Worst fall** | The largest drop from a previous high, as an investor would have lived through it |

A strategy that earns more than SPY only by taking more risk hasn't really beaten it. That's why the
**Sharpe ratio**, not the final balance, is the main yardstick.

---

## 5. Keeping the test honest: choose on the past, judge on untouched years

Every combination of the plain rule could simply be run over all the years and compared, and the
project does exactly that, as a description. The trouble starts when **the best one is picked and its
result is quoted**. With dozens of related rules, some look good by luck, and the best of the list
mixes a real edge with that luck. It's like choosing the fund with the best ten-year record and
expecting the same again.

So the years are split, and **every strategy is judged on the same untouched years**:

| Period | Decisions | Used for | Like |
| --- | --- | --- | --- |
| **Training** | 2010–2019 | The models learn their patterns here. Their settings are tuned on six successive years, each time training only on the years before | Studying |
| **Validation** | 2020–2022 | Comparing the tuned models and choosing the headline one | A practice exam |
| **Test** | January 2023 onwards | One final check, **never used for any choice** | The real exam |

The plain rule fits nothing, so it needs no training. But choosing the best of many rules is a kind of
fitting, so its best version is chosen on 2010–2022 alone and then followed through the same test
years as the models.

**This is where the machine learning comes in.** The plain rule ranks stocks on one number, the past
return. A model ranks them on many inputs at once (past returns, volatility, trading patterns,
sector, interest rates and other economic data, all known at the month-end) and learns from the
training years which combinations came before a stock beat SPY. A flexible model can memorise its
training years almost perfectly, so how it does there means nothing. The validation years catch that
kind of overfitting, and the test years catch any left in the choices made on validation.

The cut is always by time, never at random: a model must never learn from March 2024 and be tested on
February 2024. [Chapter 6](06_modelling.md) has the details.

---

---

## 6. Why it's harder than it looks: survivorship bias

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

## 7. The rules of the test

| Rule | Choice | Why |
| --- | --- | --- |
| **Universe** | S&P 500 members as of each date | Avoids survivorship bias (Section 6) |
| **Period** | Jan 2010 → Oct 2026 (202 month-ends) | The public record of index changes is thin before ~2008 |
| **Decision time** | The last trading day of each month | One decision a month, matching the idea |
| **The golden rule** | Everything the strategy uses is known **at the month-end close**; it trades **at the next open** | No peeking at the future |
| **Model target** | Does the stock beat SPY over the next month? | Directly answers "does it beat the index?". About 49% of stocks do in a typical month, so it's a fair coin to start with |
| **Hold periods (plain rule)** | 1, 3, 6 and 12 months | Research on momentum finds the effect over roughly 3–12 months. 1 month tests the idea as first stated |
| **Benchmarks** | SPY, plus an equal-weight basket of all members | The second shows whether an edge is real stock picking or just a tilt towards smaller members |
| **Costs** | ~0.1% per buy and per sell | A monthly rule replaces most of its holdings every month |

---

## 8. What makes this question different

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

## 9. Decisions and why

- **One row per stock per month-end, not per day.** The decision is monthly. Daily rows would
  overlap heavily, and "last month's winner" would turn into a daily rule.
- **The model predicts one month ahead only.** Testing a 12-month prediction on a ~4-year test period
  leaves only about 2 independent periods to judge it on. The plain rule fits nothing to the data, so
  it can be tested on every hold period over the full 2010–2026 span.
- **No 24-month holds.** That's past the range where momentum is known to work (over longer spans,
  winners tend to fall back). It would also need long gaps between the training and test periods,
  using up about 4 of the 16 years.

---

## 10. Caveats

- **Free data only.** Prices for some delisted companies can't be found anywhere free. That gap is
  measured and reported ([Chapter 3](03_monthly_table.md)), not hidden.
- **2010–2026 was mostly a rising market.** Any strategy that holds stocks looks good in it. That's why
  the comparison is against SPY and an equal-weight basket, not against zero.
