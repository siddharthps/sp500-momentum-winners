# Chapter 10: Limitations, lessons and next steps

## 1. Goal

[Chapter 9](09_results.md) gave the results. This chapter asks what they mean: why the models lost
to a plain rule, what a professional fund would do differently, what limits the conclusions, and
what would be worth trying next.

> **All numbers here are previews.** The download of delisted companies is still running; the
> reasoning doesn't depend on the final numbers.

---

## 2. Why the models lost to plain momentum

Several reasons add up. The features are only one of them, and probably not the main one.

**1. Next month's result is mostly noise.** A large study of US stocks (Gu, Kelly and Xiu, 2020)
found that even the best machine-learning methods explain well under 1% of the month-to-month
variation in individual returns. A flexible model with 152 inputs will find patterns that held in its
training years by accident. The tuning showed exactly this: each model's best setting looked
promising, its typical setting no better than chance ([Chapter 6](06_modelling.md)).

**2. The model learned a different, weaker bet.** The plain rule buys the period's winners. The
chosen model leaned on short-term trading indicators and the market's last month, and in practice
bought **volatile, beaten-down stocks**: a bet on rebounds, not on momentum. That bet loses most in
the months the market falls, and so it did.

**3. The inputs are mostly the same information, repackaged.** Nearly every feature comes from each
stock's own prices and volume, plus sector and economic data. Momentum is the strongest known signal
in that family and one of the model's inputs, so when the model loses to it used alone, the other
inputs added more noise than signal.

**4. The models trade fast; momentum works slowly.** Predicting one month ahead, the models turn over
about 18 times the portfolio a year at the top 10, against 11 for the 6-month rule held the same way,
while momentum shows up over 3–12 months. That's only part of the gap: the models also lost to the
6-month rule held one month.

**5. The S&P 500 is the hardest place to find an edge.** These are the most-watched, most-traded
stocks in the world. Studies of machine learning in stock returns (for example Avramov, Cheng and
Metzker, 2023) find that much of the gain comes from the smallest and most distressed companies: in
that study, leaving out the smallest stocks alone cut the strategy's payoff by about 60%.

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
- **Many more bets.** Grinold's fundamental law of active management says a strategy's risk-adjusted
  edge grows roughly with its skill per bet times the square root of the number of independent bets.
  A 51–52% hit rate is noise on ten stocks a month; across thousands of positions, bought *and* sold
  short, it can add up, and the result no longer rides on the market's direction.
- **Cheaper, controlled trading.** Costs well below the 0.1% a side assumed here, and risk limits that
  keep each bet small.

Two things wouldn't change:

- **Noise doesn't give way to bigger models.** In Gu, Kelly and Xiu's study, neural networks did best
  with three layers and got worse as more were added.
- **Edges fade once they're known.** Across 97 published return predictors, McLean and Pontiff (2016)
  found portfolio returns 26% lower after each original study's sample ended, and 58% lower after
  publication. A signal that works gets traded until it weakens, so the work never stops at one
  model.

---

## 4. Limitations

### 4.1 Data

- **Free data only.** Some companies that left the index have no free price history. The ones that
  can't be recovered are mostly **takeovers, buy-outs and bankruptcies**, the very fates survivorship
  bias hides. So the gap isn't random: it most likely flatters strategies a little, by leaving out
  takeover targets bought after their jump and some collapses during a hold.
- **Reused tickers.** An old symbol can now belong to a different company (Staples' old symbol,
  SunTrust's, EMC's and others). Those series were rejected rather than spliced onto the old company,
  which adds to the gap above.
- **Takeover targets whose buyer kept the ticker.** The sources file the buyer's history under the
  shared ticker, so each company is priced from its own history, or left unpriced where no free source
  has it. A few targets are missing even as members (the old Allergan, 21st Century Fox, the old News
  Corp).
- **No company accounts.** No earnings, valuations or analyst data, as above.

### 4.2 The test

- **One test window of 45 months,** dominated by one market theme, in a mostly rising market. A
  different four years could tell a different story.
- **Many strategies were scored.** Of 121 simulated strategies, 12 edge SPY on the test years.
  Among so many related tries, a few are expected to by chance, which is why only the strategies
  declared in advance count.

### 4.3 The trading assumptions

- **A flat cost of 0.1% a side,** with no allowance for the price moving against a large order.
- **Fractional shares,** so every pick gets exactly its share of the money. Small real accounts would
  keep some leftover cash.
- **Buy only, concentrated.** The strategies hold 1 to 10 stocks per batch, and never sell short.

---

## 5. Lessons

- **Most of the work is in the data, not the model.** Rebuilding who was in the index on each date,
  and finding prices for the companies that left, took most of the effort. Without it, every result
  would be flattered by survivorship bias.
- **Fix the rules before looking at results.** The test years, the main version of each strategy and
  the measures were set in advance. The model version that looked best on 2020–2022 turned out to be
  its worst on the test, which is why only the main version counts.
- **A simple benchmark is hard to beat.** "Buy what went up over six months" is decades old and
  public, and it still beat every model built here.
- **A negative result is a result.** The honest answer, "the models add nothing here", is worth more
  than a flattering one built on the test years.

---

## 6. Next steps

None of these was built or tested. The test years have been used, so each would need new months:

1. **Keep the live record.** The monthly run picks stocks every month with frozen settings and
   records the outcome. Every new month is truly untouched data
   ([Chapter 8](08_automation.md)).
2. **Add company accounts,** recorded as they were known at the time, to test whether signals beyond
   prices help.
3. **A slower target,** such as beating SPY over 3, 6 or 12 months, which fits momentum's horizon.
4. **A broader portfolio, bought and sold short,** to see whether a small hit-rate edge shows up once
   the bet on the market is removed.
5. The ideas from [Chapter 7](07_simulation.md#315-ideas-for-future-work): take the market's
   direction out of the model, give it a risk-adjusted target, use it to filter the rule rather than
   replace it, and cap the rule's sector weights.

---

## 7. Caveats

- **This chapter interprets results; it doesn't add tests.** The reasons in Section 2 fit the
  evidence, but none of them was tested on its own.
- **The comparison with professional funds is general background,** drawn from published research
  and common practice, not from anything measured here.
