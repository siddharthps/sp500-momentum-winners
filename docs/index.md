# S&P 500 momentum winners: the project book

At each month-end, does buying the S&P 500's recent winners beat simply holding SPY, a fund that
tracks the index? And can a machine-learning model pick better than "buy what went up"? This book
follows the project step by step, from the data to the answer: what each step does, why, and what
came out.

Start with [Chapter 1](01_problem.md) for the setup in plain words, or go straight to the answers in
[Chapter 9](09_results.md).

> **The numbers are final.** They come from the last full rebuild (16 Nov 2026). It was made after
> every company that left the index without usable Yahoo Finance prices had been tried on Alpha
> Vantage, and after two data fixes: four price series that belonged to other securities were
> dropped, and potential GDP is now read as published at the time. Some early takeovers have no
> free price anywhere: 4.5% of member-months ([Chapter 3](03_monthly_table.md#36-the-result)).

Chapters 2–8 share one shape: **goal** (the question the step answers), **what was done** (the
path, in plain steps), **what came out** (the numbers), **decisions and why** (the choices made
along the way) and **caveats** (what to keep in mind).

## Chapters

| # | Chapter | What it covers |
| --- | --- | --- |
| 1 | [The problem and the idea](01_problem.md) | The two questions, survivorship bias, how a hold works, the rules of the test |
| 2 | [Data collection](02_data_collection.md) | Who was in the index, prices for the companies that left, the economic series |
| 3 | [Building the monthly table](03_monthly_table.md) | Membership on each date, its repairs, monthly prices, the targets |
| 4 | [Features](04_features.md) | The feature sets, sectors for companies that left, the look-ahead checks |
| 5 | [Exploratory analysis](05_eda.md) | How hard SPY is to beat, how weak and unsteady each feature's signal is, a first look at the plain rule |
| 6 | [Modelling](06_modelling.md) | The setup, the eight models and their tuning, the 2020–2022 comparison, the one test |
| 7 | [Trading simulation](07_simulation.md) | In four parts: the plain rule, the models traded, the paths and a market-trend filter, why the model loses |
| 8 | [Automation](08_automation.md) | The monthly run, what it publishes and where (Telegram, the dashboard, the datasets), running it yourself (a notebook, a container), the run in the cloud |
| 9 | [Results](09_results.md) | The two questions answered, with the key numbers |
| 10 | [Limitations, lessons and next steps](10_lessons.md) | Why the models lost, what a professional fund would do differently, limitations, lessons, next steps |

## Appendices and the running guide

| | Page | What's in it |
| --- | --- | --- |
| A | [Data dictionary](appendix_a_data_dictionary.md) | Every column of the final table |
| B | [The full working record](appendix_b_working_record.md) | For readers who want the whole process: the decision log, the journal, and the notebooks and result tables behind each chapter |
| | [Running the project](running.md) | Setup, every pipeline step and command, the monthly run in the cloud, the data snapshots, Docker, the dashboard, notifications, what to rerun after a change, the notebooks, development and the project's folders |

The chapters and Appendix A are final. Appendix B's records and the running guide are kept up to
date as the project runs.
