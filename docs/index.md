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
| 1 | [The problem and the idea](01_problem.md) | Final |
| 2 | [Data collection](02_data_collection.md) | Final |
| 3 | [Building the monthly table](03_monthly_table.md) | Final |
| 4 | [Features](04_features.md) | Final |
| 5 | [Exploratory analysis](05_eda.md) | Final |
| 6 | [Modelling](06_modelling.md) | Final (setup and results) |
| 7 | [Trading simulation](07_simulation.md) | Final (Parts 1–4: the baseline rule, the models traded, paths and the trend filter, why the model loses) |
| 8 | [Automation](08_automation.md) | Final (the monthly run, notifications, snapshots, the dashboard, the whole workflow, the run in the cloud) |
| 9 | [Results](09_results.md) | Final (the two questions answered, with the key numbers) |
| 10 | [Limitations, lessons and next steps](10_lessons.md) | Final (why the models lost, what a professional fund would do differently, limitations, next steps) |

## Appendices

| | Appendix | Status |
| --- | --- | --- |
| A | [Data dictionary](appendix_a_data_dictionary.md): every column of the final table | Final |
| B | [The full working record](appendix_b_working_record.md): for readers who want the whole process | Live |

## Running the project

| Guide | What's in it | Status |
| --- | --- | --- |
| [Running the project](running.md) | Setup, every pipeline step and command, the data snapshots, Docker, the dashboard, notifications, what to rerun after a change, the notebooks and the development workflow | Live |

> **The numbers are final:** the whole project was rebuilt on 16 Nov 2026, once every delisted
> company's prices had been collected.
