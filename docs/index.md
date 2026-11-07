# S&P 500 momentum winners: the project book

This book explains the project one step at a time, in the order the work was done. It covers the
*why* of each step: what question it answers, what came out, and the choices made along the way. How
to run the project is in the [README](../README.md).

## The short version

**The question.** At each month-end, buy the S&P 500 stocks that rose the most and hold them for a
while. Does that beat simply holding the index (SPY)? And can a machine-learning model pick better
than "buy what went up"?

**How it was tested.** Using the companies that were in the index *at each date*, including the ones
that later left. Each strategy buys at the next morning's open, pays trading costs, and is compared
with SPY on return per unit of risk. Every choice was made on 2010–2022, and every strategy is judged
on the same untouched years, from 2023 on. [Chapter 1](01_problem.md) explains the setup in plain
words, with a worked example.

**What came out** (preview numbers, see the note at the end of this page):

- **Buying recent winners mostly buys more risk.** Of 60 versions of the plain rule over 2010–2026, 53
  earned more per year than SPY, but only 7 earned more per unit of risk, and every one had a deeper
  worst fall.
- **The best rule, chosen on 2010–2022, tripled SPY's return in the test years**: buying the top 5 by
  6-month return and holding each 6 months turned $10,000 into about $59,000, against about $20,000
  for SPY. But per unit of risk it only tied, with a worst fall of −27% against SPY's −8%. Most of
  the gain came from a handful of AI and chip stocks.
- **The machine-learning models did worse.** None picked winners more often than chance in the years
  they were compared on, and the chosen one turned $10,000 into about $11,600 in the test years.
- **Bottom line:** on this data the models add nothing that a plain 6-month momentum rule doesn't do
  better, and no strategy chosen in advance clearly beats SPY per unit of risk. Chapter 9 discusses
  why.

Each chapter has the same shape:

1. **Goal**: the question the step answers.
2. **What was done**: the path, in plain steps.
3. **What came out**: the numbers.
4. **Decisions and why**: the choices made along the way.
5. **Caveats**: what to keep in mind.

## Chapters

| # | Chapter | Status |
| --- | --- | --- |
| 1 | [The problem and the idea](01_problem.md) | Draft |
| 2 | [Data collection](02_data_collection.md) | Draft |
| 3 | [Building the monthly table](03_monthly_table.md) | Draft |
| 4 | [Features](04_features.md) | Draft |
| 5 | [Exploratory analysis](05_eda.md) | Draft |
| 6 | [Modelling](06_modelling.md) | Draft (setup and results; preview numbers) |
| 7 | [Trading simulation and results](07_simulation.md) | Draft (Parts 1–4: the baseline rule, the models traded, paths and the trend filter, why the model loses) |
| 8 | [Automation](08_automation.md) | Draft (Parts 1–5: the monthly run, notifications, snapshots, the dashboard, the whole workflow) |
| 9 | [Limitations, lessons and next steps](09_lessons.md) | Draft (why the models lost, limitations, next steps; numbers refreshed after the final run) |

## Appendices

| | Appendix | Status |
| --- | --- | --- |
| A | Data dictionary: every column of the final table | To do |
| B | [The full working record](appendix_b_working_record.md): for readers who want the whole process | Live |

> **Numbers in the draft chapters are as of 3 Nov 2026.** The download of delisted companies is still
> running (until about 12–14 Nov). Every count and result gets refreshed once it's done.
