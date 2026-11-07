# Chapter 9: Limitations, lessons and next steps

## 1. Goal

Step back from the results. Why did the models lose to a plain rule, would a professional fund with
far more data have done better, what limits the conclusions, and what would be worth trying next?

> **Draft.** The reasoning here doesn't depend on the final numbers, but the counts and results it
> refers to are previews until the download of delisted companies is complete.

---

## 2. What the project found

In short ([Chapter 7](07_simulation.md) has the full results):

- **Buying recent winners mostly buys more risk.** In a market that rose for most of 2010–2026, more
  risk was paid for with more return, but not with more return per unit of risk.
- **The best plain rule, chosen on 2010–2022** (the top 5 by 6-month return, held 6 months), earned
  about three times SPY's return in the test years, and tied with it per unit of risk. Its gain came
  from one market theme, the AI and chip boom.
- **No model beat a random pick** on the years the models were compared on, and the chosen one
  trailed SPY and every plain rule in the test years.

---

## 3. Why the models lost to plain momentum

Several reasons add up. The features are only one of them, and probably not the main one.

**1. Next month's result is mostly noise.** About half of all members beat SPY in a typical month,
and the predictable part of that is tiny. A large study of US stocks (Gu, Kelly and Xiu, 2020) found
that even the best machine-learning methods explain well under 1% of the month-to-month variation in
individual stock returns. A flexible model with 152 inputs and a few tens of thousands of training rows will find
patterns that held in its training years by accident. The tuning showed exactly this: each model's
best setting looked promising, but its typical setting scored no better than chance
([Chapter 6](06_modelling.md)).

**2. The model learned a different, weaker bet.** The plain rule buys the period's winners. The
chosen model leaned on short-term trading indicators and the market's last month, and in practice
bought **volatile, beaten-down stocks**: a bet on rebounds, not on momentum. That bet loses most in
the months the market falls, and so it did.

**3. The inputs are mostly the same information, repackaged.** Nearly every feature is built from each
stock's own prices and trading volume, plus sector and economic data. Momentum is the strongest known
signal in that family, and the plain rule uses it directly. Momentum is also one of the model's
inputs, so when the model loses to that one input used alone, the other inputs added more noise
than signal.

**4. The models trade fast; momentum works slowly.** The models predict one month ahead, so they're
held one month and replace most of their picks each time: about 18 times the portfolio a year at the
top 10, against 11 for the 6-month rule held the same way. Momentum shows up over 3–12 months. This
explains part of the gap, not all of it: the models also lost to the 6-month rule held one month.

**5. The S&P 500 is the hardest place to find an edge.** These are the most-watched, most-traded
stocks in the world. Studies of machine learning in stock returns (for example Avramov, Cheng and
Metzker, 2023) find that much of the gain comes from the smallest and most distressed companies: in
that study, leaving out the smallest stocks alone cut the strategy's payoff by about 60%.

**6. The test years rewarded riding one trend.** 2023–2026 was dominated by the AI and chip boom. A
momentum rule is built to keep buying what has been rising, so it rode the boom. A model averaging
many weak signals has no reason to concentrate like that.

---

## 4. Would a large quant fund do better?

Partly, yes. Professional funds have advantages this project doesn't:

- **Data beyond prices:** company accounts (earnings, valuations, profitability) recorded *as they
  were known at the time*, analysts' forecast revisions, earnings surprises, short interest, options
  markets, and alternative data such as card spending, web traffic and news text. Value, quality and
  earnings revisions are well-documented signals that aren't built from prices. This project has
  none of them, which is its biggest single limitation.
- **Breadth:** thousands of stocks worldwide, bought *and* sold short, so a result doesn't depend on
  the market's direction.
- **Execution:** trading costs well below the 0.1% a side assumed here, and risk controls that keep
  each bet small.

But their edge doesn't come from a deeper model that finds a "holy grail":

- **Bigger models don't remove the noise.** In the study above, neural networks did best with three
  layers and got worse as more were added. More computing power mostly finds more convincing noise.
- **The edge is many small bets.** A hit rate of 51–52% is close to worthless on ten stocks a month.
  Across thousands of positions, refreshed often, the same small edge adds up. A concentrated,
  buy-only top 10 is the opposite: its result is dominated by luck and by a few stocks.
- **Edges fade once they're known.** A signal that works gets traded until it stops working, so the
  work never stops at one model.

---

## 5. Limitations

**Data**

- **Free data only.** Some companies that left the index have no free price history. The ones that
  can't be recovered are mostly **takeovers, buy-outs and bankruptcies**, the very fates survivorship
  bias hides. So the gap isn't random: it most likely flatters strategies a little, by leaving out
  takeover targets bought after their jump and some collapses during a hold.
- **Reused tickers.** An old symbol can now belong to a different company (Staples' old symbol,
  Tyco's, EMC's and others). Those series were rejected rather than spliced onto the old company,
  which adds to the gap above.
- **No company accounts.** No earnings, valuations or analyst data, as above.

**The test**

- **One test window of 45 months,** dominated by one market theme, in a mostly rising market. A
  different four years could tell a different story.
- **Many strategies were scored.** Of 121 simulated strategies, 12 edge SPY on the test years.
  Among so many related tries, a few are expected to by chance, which is why only the strategies
  declared in advance count.

**The trading assumptions**

- **A flat cost of 0.1% a side,** with no allowance for the price moving against a large order.
- **Fractional shares,** so every pick gets exactly its share of the money. Small real accounts would
  keep some leftover cash.
- **Buy only, concentrated.** The strategies hold 1 to 10 stocks per batch, and never sell short.

---

## 6. Lessons

- **Most of the work is in the data, not the model.** Rebuilding who was in the index on each date,
  and finding prices for the companies that left, changes the answer more than any choice of model.
- **Fix the rules before looking at results.** The test years, the main version of each strategy and
  the measures were set in advance. The model version that looked best on 2020–2022 turned out to be
  its worst on the test, which is why only the main version counts.
- **A simple benchmark is hard to beat.** "Buy what went up over six months" is decades old and
  public, and it still beat every model built here.
- **A negative result is a result.** The honest answer, "the models add nothing here", is worth more
  than a flattering one built on the test years.

---

## 7. Next steps

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

## 8. Caveats

- **This chapter interprets results; it doesn't add tests.** The reasons in Section 3 fit the
  evidence, but none of them was tested on its own.
- **The comparison with professional funds is general background,** drawn from published research
  and common practice, not from anything measured here.
