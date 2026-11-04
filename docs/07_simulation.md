# Chapter 7: Trading simulation and results

> **This draft covers Part 1, the baseline rule.** The model-based strategies, the simulation with
> reinvestment and the market-trend filter are added in later parts.

## 1. Goal

Before asking a model to pick stocks, test the plain idea properly: at each month-end, buy the
members that rose the most, hold them, and compare with SPY. Three questions:

1. Does any version of "buy the winners" beat SPY after trading costs, and **on a risk-adjusted
   basis**, not just on raw return?
2. Which version works best: how far back to measure "winner", how many stocks to buy, and how long to
   hold them?
3. If the best version is chosen from many, is it real, or just the luckiest of the lot?

The answer is the **bar the models have to clear**. A model that can't beat the plain rule adds
nothing.

> **All numbers here are previews.** The download of delisted companies is still running, so the early
> years still miss most acquired companies. Everything gets rerun once it's complete.

---

## 2. What was done

| Choice | Values | Count |
| --- | --- | --- |
| "Winner" measured over the past | 1, 3, 6, 12 months, or 12 months skipping the latest | 5 |
| Stocks bought | top 1, 5 or 10, equal amounts | 3 |
| Hold | 1, 3, 6 or 12 months | 4 |

That's **60 rules**, all run over the whole period (February 2010 to October 2026) and **all reported**.
Reporting only the good ones would hide how many were tried.

How each rule is traded:

- **The trade happens at the next open** after the month-end, so a rule never trades at a price it
  couldn't have had.
- **Staggered portfolios.** With a 6-month hold, the money is split into six parts, and each month one
  part sells its stocks and buys that month's picks. The result then doesn't depend on which month
  the test happens to start in.
- **Costs of 0.1% on every buy and every sell.** A stock kept from one month's picks to the next is
  only traded by the difference, as a real portfolio would be.
- **Companies that leave the index stay held** until their part of the portfolio is due to sell. A
  company that's delisted is valued at its last price and then held as cash.
- **Two yardsticks:** SPY, and an equal-weight basket of every member, rebalanced monthly.
- **The Sharpe ratio subtracts the risk-free rate** (the Fed Funds rate) from the return before dividing
  by volatility.

The rule fits nothing to the data, so it needs no training period. But picking the best of 60 *is* a
kind of fitting. So the best rule is also **chosen on 2010–2022 alone and then followed through 2023–2026**.
Those are the same test years the models are scored on, never used to choose anything, so the
baseline and the models are compared on exactly the same months.

---

## 3. What came out

### 3.1 More return, but more risk

| Yardstick, 2010–2026 | Yearly return | Volatility | Sharpe ratio | Worst fall |
| --- | --- | --- | --- | --- |
| SPY | 14.3% | 14.8% | 0.88 | −23% |
| Equal-weight members | 13.8% | 16.1% | 0.79 | −30% |

Of the 60 rules:

- **53 earn a higher yearly return than SPY.**
- **Only 6 have a better Sharpe ratio.**
- **All 60 have a deeper worst fall.**

Buying recent winners mostly buys more risk. In a market that rose for most of 2010–2026, more risk
was paid for with more return, but not with more return *per unit of risk*.

![Sharpe ratio minus SPY's, every rule](../reports/figures/baseline_grid_sharpe.png)

### 3.2 Which version works best

| Grid dimension | Best | Worst | Why |
| --- | --- | --- | --- |
| "Winner" over | **6 months** (best median return, Sharpe and worst fall) | Last month alone | Last month's winners tend to fall back the month after (the short-term reversal seen in the feature analysis) |
| Stocks bought | 5 or 10 | **1** (a median worst fall of −56%) | A single stock's swings swamp everything else |
| Hold | 12 months | 1 month | Holding longer costs less: about 1.4% a year in trading costs with a 1-month hold, 0.2% with 12 months |

The best rule over the whole period buys the **top 5 by 6-month return and holds them 6 months**: 28.2%
a year, a Sharpe ratio of 0.96 against SPY's 0.88, and a worst fall of −27%. The best **top-10** rule
(3-month winners, held 12 months) has a Sharpe ratio of 0.90, close to a tie with SPY.

Even the best rule isn't clearly better than chance. Its average monthly return over SPY has a
t-statistic of 2.8, and 11 of the 60 rules clear 2. That's convincing for one rule chosen in advance,
but less so for the best of 60 related ones. None clears 3.

### 3.3 Chosen on 2010–2022, followed through the test years

The rule with the best Sharpe ratio on **2010–2022** returns turns out to be the same one: the top 5
by 6-month return, held 6 months.

| | Yearly return | Volatility | Sharpe ratio | Worst fall |
| --- | --- | --- | --- | --- |
| **2010–2022** (chosen here) | | | | |
| The rule | 20.0% | 22.8% | 0.89 | −26% |
| SPY | 12.5% | 15.6% | 0.79 | −23% |
| **2023–Oct 2026** (test years, never used to choose) | | | | |
| The rule | 60.0% | 42.6% | 1.21 | −27% |
| SPY | 20.9% | 11.9% | 1.29 | −8% |
| Equal-weight members | 14.2% | 12.9% | 0.75 | −11% |

![The best rule up to 2022, and what it did after](../reports/figures/baseline_best_rule.png)

In the test years the rule **earned almost three times SPY's yearly return**, and ranked 4th of the 60
rules. But **per unit of risk it did slightly worse than SPY**: 43% volatility against 12%, and a worst
fall of −27% against −8%. The gain came from a handful of stocks riding the AI and memory-chip boom
(NVIDIA, Western Digital, Palantir, Seagate, GE Vernova, SanDisk, Micron), each picked at many
month-ends. That's a strong market theme the rule happened to catch, not a steady, broad edge.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Every one of the 60 rules reported | Showing only the winners would hide how many were tried, and so how likely the best is to be luck |
| Staggered portfolios for holds longer than a month | One portfolio started in one month would make the result depend on that month |
| Costs on every buy and sell, netted for stocks kept | Monthly rules trade a lot. Without costs, the 1-month rules look about 1.4 points a year better than they are |
| Trade at the next open | Every rule only uses prices it could have had |
| Sharpe ratio net of the Fed Funds rate | Risky strategies should be compared on what they earn above cash |
| Best rule chosen on 2010–2022, then followed through 2023–2026 | A best-of-60 judged on the same years it was chosen on is flattered by the choice. These are the models' test years too, so every strategy is judged on the same untouched months |
| Top 10 kept as the headline for the models | Top 1 is far too volatile. Top 10 is close to SPY on a risk-adjusted basis, a fair bar for a model to beat |

---

## 5. Caveats

- **Previews only.** The early years still miss most acquired companies, and takeover targets are
  often among the recent winners. The numbers will change once the download finishes.
- **The test years are few.** Under four years, dominated by one market theme. One strong stretch
  can't settle whether the edge is lasting, and a single bad year for SPY would change the comparison.
  (With the cut a year earlier, SPY's poor 2022 makes the rule look better on Sharpe too. That's why
  the cut is fixed to the models' test window, not chosen by result.)
- **Rebalancing between the parts of a staggered portfolio isn't charged.** That trading is small next
  to the monthly picks, but it isn't zero.
- **The equal-weight yardstick has no costs,** so it's slightly flattered compared with the rules.
- **Taxes, short-term price impact and the bid-ask spread on small trades are not modelled.** The 0.1% per
  side is meant to cover the spread and commissions of a liquid large-cap stock.
