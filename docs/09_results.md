# Chapter 9: Results

## 1. Goal

Answer the two questions from [Chapter 1](01_problem.md): does buying the S&P 500's recent winners beat
simply holding SPY, and can a machine-learning model pick better than "buy what went up"?

Two kinds of strategy are compared throughout:

- **The plain rule:** each month-end, buy the members that rose the most over a recent period (for
  example the top 10 by 6-month return). No model, just recent winners.
- **The model:** each month-end, buy the members a machine-learning model rates most likely to beat
  SPY next month ([Chapter 6](06_modelling.md)).

---

## 2. How every strategy was judged

- **The index as it was on each date,** including the companies that later left it.
- **Decide on the month-end close, trade at the next open,** paying 0.1% on every buy and sell.
- **Every choice made on 2010–2022.** Every strategy is then judged on the same untouched test years:
  decisions from January 2023, 45 months.
- **Risk counts.** The Sharpe ratio (return above cash per unit of volatility) and the worst fall sit
  next to the return.

---

## 3. What came out

### 3.1 Buying recent winners buys more risk

Of 60 versions of the plain rule (how far back "winner" is measured, how many stocks are bought, how
long they're held), over 2010–2026:

| Each version's result, compared with SPY's | Versions, of 60 |
| --- | --- |
| Earned a higher return a year than SPY | 52 |
| Earned more per unit of risk than SPY (a higher Sharpe ratio) | 3 |
| Had a deeper worst fall than SPY | 60 |

In a market that rose for most of these years, more risk was paid for with more return, but not with
more return per unit of risk. Measuring "winner" over 6 months, buying 5 or 10 stocks and holding
longer worked best; buying the single best stock each month worked worst.
([Chapter 7, §3.1–3.2](07_simulation.md#31-more-return-but-more-risk))

### 3.2 The best rule, chosen in advance, tripled SPY's return but only tied it on risk

The rule with the best Sharpe ratio on 2010–2022 buys the **top 5 by 6-month return and holds them
6 months**. Followed through the test years:

| Test years | The rule | SPY |
| --- | --- | --- |
| What $10,000 became | **$59,209** | $19,650 |
| Yearly return | 60.7% | 19.7% |
| Volatility | 43.1% | 11.8% |
| Sharpe ratio | 1.21 | 1.21 |
| Worst fall | −27% | −8% |

![The best rule up to 2022, and what it did after](../reports/figures/baseline_best_rule.png)

Most of the gain came from a handful of AI and memory-chip stocks (NVIDIA, Western Digital, Palantir,
Seagate, GE Vernova, SanDisk, Micron), and most of it arrived in one burst in late 2025 and 2026: a
market theme the rule caught, not a steady edge.
([Chapter 7, §3.3](07_simulation.md#33-chosen-on-20102022-followed-through-the-test-years))

### 3.3 The models looked promising, then did worse than the plain rules

On 2020–2022, where the models were compared, four of them picked winners more often than a random
pick would have, the headline among them, and so did both plain rules. On the test years, nobody had
looked at, all four fell back: the headline model, chosen before the test was read, did no better
than a random pick.

| Test years, top 10 held one month unless stated | What $10,000 became |
| --- | --- |
| The rule chosen in advance (top 5, held 6 months) | $59,209 |
| 6-month rule | $29,150 |
| SPY | $19,650 |
| Last month's winners | $18,987 |
| All members, equal weight | $15,599 |
| **Headline model** | **$12,583** |

![What $10,000 became](../reports/figures/strategies_value.png)

Of 121 simulated strategies, only 3 edged SPY's Sharpe ratio on the test years: the 6-month rule's
single best stock and the chosen rule, which ties. No model did.
([Chapter 6](06_modelling.md), [Chapter 7, §3.5–3.7](07_simulation.md#35-the-headline-model-loses-to-the-plain-rules-and-to-spy))

### 3.4 A market-trend filter helped once, and hurt overall

Selling everything whenever SPY closed a month below its 10-month average helped in 2020–2022, which
included a long decline: it raised the Sharpe ratio of about 70% of the strategies. Everywhere else
it hurt. It kept missing the rebounds (SPY rose 3.5% on average in the months after it got out,
against 0.8% in the others), so on the test years it improved only 3–7% of the strategies, and over
2010–2026 filtered SPY earned 7.8% a year against 14.3%.
([Chapter 7, §3.9](07_simulation.md#39-the-filter-helped-in-one-long-decline-and-hurt-everywhere-else))

### 3.5 Why the model lost: it never bet on winners

To see what each strategy really bought, every pick was ranked against all the members that month,
from 0 (the lowest) to 100 (the highest), on two measures, and the ranks were averaged over each
period:

| What the picks looked like | How volatile (0–100) | Return over the past 6 months (0–100) |
| --- | --- | --- |
| The model's picks, 2020–2022 | 73: more volatile than most | 29: among the weaker |
| The model's picks, test years | 46: about average | 44: about average |
| The 6-month rule's picks, test years | 85: among the most volatile | 99: the very best |

The rule bought the recent winners. The model never did, and its bet changed with the market: on
2020–2022 it leaned towards volatile, beaten-down stocks, betting they'd bounce back; on the test
years it leaned towards calmer stocks (utilities were 15% of its picks, against 6% of members), a
defensive tilt that lagged a mostly rising market. A model that reads mostly the market's mood
(Chapter 6) chooses a different kind of stock as the mood changes.
([Chapter 7, §3.11–3.12](07_simulation.md#311-part-4-why-the-model-loses))

### 3.6 The bottom line

**On this data, the models add nothing that a plain 6-month momentum rule doesn't do better, and no
strategy chosen in advance clearly beats SPY per unit of risk.** The one test still to come is the
live record: picks made each month before their results are known
([Chapter 8](08_automation.md)). [Chapter 10](10_lessons.md) asks why the models lost and what that
means.

---

## 4. Caveats

- **Some early takeovers have no free price at all ([Chapter 3](03_monthly_table.md)).** Takeover
  targets are often recent winners, so the rules' numbers may still be slightly flattered.
- **The test years are few:** 45 months, dominated by one market theme. A different four years could
  tell a different story.
- **Costs are a flat 0.1% a side;** taxes and the price impact of large orders aren't modelled
  ([Chapter 7](07_simulation.md)).
- **The chosen rule isn't tracked live.** The live record follows the model and its plain twin (the
  6-month top 10, held one month), which differ only in how stocks are picked
  ([Chapter 8](08_automation.md)). So the chosen rule's result rests on the backtest alone.
