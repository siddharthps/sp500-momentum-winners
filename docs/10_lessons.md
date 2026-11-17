# Chapter 10: Limitations, lessons and next steps

## 1. Goal

[Chapter 9](09_results.md) gave the results. This chapter asks what they mean: why the models lost
to a plain rule, what a professional fund would do differently, what limits the conclusions, and
what would be worth trying next.

---

## 2. Why the models lost to the plain rule

"Lost" here means the model chosen in advance: it lost to every plain rule and to SPY in both
periods. Two models not chosen did better per unit of risk than the 6-month rule on the test years,
but nothing seen before the test pointed to them
([Chapter 9, §3.6](09_results.md#36-the-bottom-line)). Several reasons add up. The features are only
one of them, and probably not the main one.

**1. Next month's result is mostly noise.** Research on US stocks finds that even the best
machine-learning methods explain well under 1% of the month-to-month variation in individual
returns. A flexible model with 147 inputs will find patterns that held in its training years by
accident. The results show it: on 2020–2022 only two of the eight models beat a random pick (the
headline 51.9% and the decision tree 51.4%, against 49.9%). On the test years the headline did
worse than a random pick (43.6% against 45.1%). The neural network (51.6%) and logistic
regression, both below a random pick on 2020–2022, led the models instead ([Chapter 6,
§3.7–3.8](06_modelling.md#37-the-comparison-on-20202022-two-models-beat-a-random-pick)).

**2. The model never bet on winners.** It leaned mostly on the market's mood, so what it bought
changed with the market. On 2020–2022 it bought volatile, beaten-down stocks, in effect a bet on a
rebound. On the test years its picks looked like an average member, with no clear bet. In neither
period did it buy recent winners: its picks' past 6-month return ranked 18, then 52, out of 100,
against the rule's 99
([Chapter 9, §3.5](09_results.md#35-why-the-model-lost-it-never-bet-on-winners)).

**3. The inputs are mostly the same information, repackaged.** Nearly every feature comes from each
stock's own prices and volume, plus sector and economic data. Momentum is the best-documented signal
in that family and one of the model's inputs, so a model that loses to it used alone probably got
more noise than signal from the rest.

**4. The models trade fast; momentum works slowly.** Predicting one month ahead, the models turn
over about 18 times the portfolio a year at the top 10, against 11 for the 6-month rule held the
same way, while momentum shows up over 3–12 months. That's only part of the gap: the headline also
lost to the 6-month rule held one month ($12,107 against $29,150).

**5. The S&P 500 is the hardest place to find an edge.** These are the most-watched, most-traded
stocks in the world. Research finds that much of machine learning's gain in stock picking comes from
the smallest and most distressed companies: leaving them out considerably reduces the payoff.

**6. The test years rewarded riding one trend.** 2023–2026 was dominated by the AI and chip boom. A
momentum rule is built to keep buying what has been rising, so it rode the boom. A model averaging
many weak signals has no reason to concentrate like that.

---

## 3. What a professional fund would do differently

A large quant fund would likely do better, but not by building a deeper model. It would change three
things this project couldn't:

- **More kinds of data.** Company accounts (earnings, valuations, profitability) recorded *as they
  were known at the time*, analysts' forecast revisions, earnings surprises, short interest, options
  markets, and alternative data such as card spending or news text. Value, quality and earnings
  revisions are well-documented signals that aren't built from prices. This project has none of
  them: its biggest single limitation.
- **Many more bets.** A well-known rule of thumb in fund management says a strategy's risk-adjusted
  edge grows roughly with its skill per bet times the square root of the number of independent bets.
  A 51–52% hit rate is noise on ten stocks a month; across thousands of positions, bought *and* sold
  short, it can add up, and the result no longer rides on the market's direction.
- **Cheaper, controlled trading.** Costs well below the 0.1% a side assumed here, and risk limits
  that keep each bet small.

Two things wouldn't change:

- **Noise doesn't give way to bigger models.** In the largest study of machine learning on US stock
  returns, neural networks did best with three layers and got worse as more were added.
- **Edges fade once they're known.** Across 97 published ways of predicting stock returns, returns
  were about a quarter lower after each original study's data ended, and more than half lower after
  publication. A signal that works gets traded until it weakens, so the work never stops at one
  model.

---

## 4. Limitations

### 4.1 Data

- **No free price for some companies that left** (4.5% of member-months, mostly 2010–2015). By
  recorded reason, about six in ten are takeovers and one in five were dropped for their size
  ([Chapter 3, §3.6](03_monthly_table.md#36-the-result)). The gap isn't random: it likely flatters
  the strategies a little, by leaving out takeover targets bought after their jump and some falls
  during a hold.
- **Reused tickers.** An old symbol can now belong to a different company (SunTrust's, Staples',
  EMC's and others). Such a series is rejected, never spliced onto the old company, when it starts
  after the company left the index, or trades far too thinly for an S&P 500 member. On Alpha
  Vantage, it must also still be trading months after its company was taken over, because a thin
  series can be genuine. That last check came only in the final rebuild: until then four early
  members (El Paso, Genzyme, Millipore and LSI; 87 rows, up to April 2014) were priced from other
  securities ([Chapter 3, §3.4](03_monthly_table.md#34-data-from-the-wrong-company)). Rejected
  series add to the gap above.
- **Takeover targets whose buyer kept the ticker.** The sources file the buyer's history under the
  shared ticker, so each company is priced from its own history, or left unpriced where no free
  source has it. One target, the old Allergan, is missing even as a member.
- **Economic data as published, with one exception.** Potential GDP is read in the version
  published before each decision. Core inflation uses today's version, whose yearly seasonal
  adjustment shifts past months slightly ([Chapter 4, §5](04_features.md#5-caveats)).
- **Sector labels are each company's final sector,** not its sector on each date
  ([Chapter 4, §5](04_features.md#5-caveats)).
- **No company accounts.** No earnings, valuations or analyst data (Section 3).

### 4.2 The test

- **One test window of 45 months,** dominated by one market theme, in a mostly rising market. A
  different four years could tell a different story: with the cut a year earlier, SPY's poor 2022
  would make the chosen rule win on Sharpe too, which is why the cut was fixed in advance.
- **The chosen rule isn't tracked live.** The live record follows the model and the 6-month rule
  (top 10, held one month), so it compares only how stocks are picked. Tracking more rules would
  make it another place to pick a winner from
  ([Chapter 8, §3.2](08_automation.md#32-what-gets-published)). So the chosen rule's result rests on
  the backtest alone.

### 4.3 The trading assumptions

- **A flat cost of 0.1% a side.** Price impact, taxes and the money moved between a staggered
  portfolio's slots aren't charged ([Chapter 7, §5](07_simulation.md#5-caveats)).
- **Fractional shares,** so every pick gets exactly its share of the money. Small real accounts
  would keep some leftover cash.
- **Buy only, concentrated.** Each month's picks are 1, 5 or 10 stocks (a longer hold keeps
  several months' picks at once), and nothing is sold short.

---

## 5. Lessons

- **Most of the work is in the data, not the model, and it changes the answer.** Rebuilding who
  was in the index on each date, and finding prices for the companies that left, took most of the
  effort. Completing those prices (and fixing a few that belonged to the wrong company) moved the
  results: the plain rules that beat SPY per unit of risk fell from 7 of 60 to 3, and last month's
  top 10, held one month, went from edging SPY to trailing it. Survivorship bias, measured. Late
  fixes still mattered: a rebuild with only the correction of 87 early rows (under 0.1% of the
  table) changed five of the seven models' tuned settings. The fix was adopted because the data was
  wrong, not for its effect.
- **A simple benchmark is hard to beat.** "Buy what went up over six months" is decades old and
  public, and it still beat the model chosen in advance. Two models not chosen did better per unit
  of risk on the test years, but nothing seen before it pointed to them.
- **A negative result is a result.** The honest answer, "the model chosen in advance adds nothing
  here", is worth more than a flattering one built on the test years.

---

## 6. Next steps

Apart from the live record, which already runs, none of these was built or tested. The test years
have been used, so each would need new months or a separate earlier period.

1. **Keep the live record.** Each month the run refits the model with its settings fixed, picks
   stocks and records the outcome. Every new month is truly untouched data
   ([Chapter 8](08_automation.md)).
2. **Add company accounts,** recorded as they were known at the time, to test whether signals
   beyond prices help.
3. **A slower target,** such as beating SPY over 3, 6 or 12 months, which fits momentum's horizon.
4. **A broader portfolio, bought and sold short,** to see whether a small hit-rate edge shows up
   once the bet on the market is removed.
5. The ideas from [Chapter 7](07_simulation.md#314-ideas-for-future-work): take the market's
   direction out of the model, give it a risk-adjusted target, use it to filter the rule rather than
   replace it, and cap the rule's sector weights.

---

## 7. Caveats

- **This chapter interprets results; it doesn't add tests.** The reasons in Section 2 fit the
  evidence, but none of them was tested on its own.
- **The comparison with professional funds is general background,** drawn from published research
  (below) and common practice, not from anything measured here.

---

## 8. References

The research the book cites.

**Momentum** ([Chapter 1](01_problem.md), §2, §7 and §8; [Chapter 4](04_features.md), §3.5;
[Chapter 5](05_eda.md), §3.2):

- Asness, C. S., Moskowitz, T. J. and Pedersen, L. H. (2013). Value and momentum everywhere.
  *Journal of Finance*, 68(3), 929–985.
- Avramov, D., Chordia, T. and Goyal, A. (2006). Liquidity and autocorrelations in individual stock
  returns. *Journal of Finance*, 61(5), 2365–2394.
- Blitz, D., Huij, J. and Martens, M. (2011). Residual momentum. *Journal of Empirical Finance*,
  18(3), 506–521.
- Daniel, K. and Moskowitz, T. J. (2016). Momentum crashes. *Journal of Financial Economics*,
  122(2), 221–247.
- Hong, H. and Stein, J. C. (1999). A unified theory of underreaction, momentum trading, and
  overreaction in asset markets. *Journal of Finance*, 54(6), 2143–2184.
- Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of
  Finance*, 45(3), 881–898.
- Jegadeesh, N. and Titman, S. (1993). Returns to buying winners and selling losers: implications
  for stock market efficiency. *Journal of Finance*, 48(1), 65–91.
- Jegadeesh, N. and Titman, S. (2001). Profitability of momentum strategies: an evaluation of
  alternative explanations. *Journal of Finance*, 56(2), 699–720.
- Rouwenhorst, K. G. (1998). International momentum strategies. *Journal of Finance*, 53(1),
  267–284.

**Trend filters** ([Chapter 7](07_simulation.md), §3.8):

- Faber, M. T. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth
  Management*, Spring 2007.

**Machine learning and fund management** ([Chapter 6](06_modelling.md), §3.5; Sections 2 and 3
above):

- Avramov, D., Cheng, S. and Metzker, L. (2023). Machine learning vs. economic restrictions:
  evidence from stock return predictability. *Management Science*, 69(5), 2587–2619.
- Grinold, R. C. (1989). The fundamental law of active management. *Journal of Portfolio
  Management*, 15(3), 30–37.
- Gu, S., Kelly, B. and Xiu, D. (2020). Empirical asset pricing via machine learning. *Review of
  Financial Studies*, 33(5), 2223–2273.
- McLean, R. D. and Pontiff, J. (2016). Does academic research destroy stock return predictability?
  *Journal of Finance*, 71(1), 5–32.
