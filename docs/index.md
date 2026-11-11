# S&P 500 momentum winners: the project book

At each month-end, does buying the S&P 500's recent winners beat simply holding the index (SPY)?
And can a machine-learning model pick better than "buy what went up"? This book follows the project
step by step, from the data to the answer: what each step does, why, and what came out.

Start with [Chapter 1](01_problem.md) for the setup in plain words, or go straight to the answers in
[Chapter 9](09_results.md). [Running the project](running.md) has every command.

Most chapters have the same shape:

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
| 7 | [Trading simulation](07_simulation.md) | Draft (Parts 1–4: the baseline rule, the models traded, paths and the trend filter, why the model loses) |
| 8 | [Automation](08_automation.md) | Draft (Parts 1–5: the monthly run, notifications, snapshots, the dashboard, the whole workflow) |
| 9 | [Results](09_results.md) | Draft (the two questions answered, with the key numbers; refreshed after the final run) |
| 10 | [Limitations, lessons and next steps](10_lessons.md) | Draft (why the models lost, what a professional fund would do differently, limitations, next steps) |

## Appendices

| | Appendix | Status |
| --- | --- | --- |
| A | [Data dictionary](appendix_a_data_dictionary.md): every column of the final table | Draft (column list refreshed after the final run) |
| B | [The full working record](appendix_b_working_record.md): for readers who want the whole process | Live |

## Running the project

| Guide | What's in it | Status |
| --- | --- | --- |
| [Running the project](running.md) | Setup, every pipeline step and command, the data snapshots, Docker, the dashboard, notifications, what to rerun after a change, the notebooks and the development workflow | Live |

> **The numbers are previews.** The download of delisted companies is still running (until about
> 13 Nov). Every count and result is refreshed once it's done.
