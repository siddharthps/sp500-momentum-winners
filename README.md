# sp500-momentum-winners

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" alt="Cookiecutter Data Science template" />
</a>
<a href="https://github.com/siddharthps/sp500-momentum-winners/actions/workflows/ci.yml">
    <img src="https://github.com/siddharthps/sp500-momentum-winners/actions/workflows/ci.yml/badge.svg" alt="CI" />
</a>

**At the end of each month, if you buy the S&P 500 stocks that rose the most and hold them for a
while, do you beat the S&P 500 itself? And can a machine-learning model pick better than "buy what
went up"?**

"Momentum" (recent winners keep winning for a while) is one of the best-documented patterns in stock
returns, and it's easy to test badly: looking back with today's index members leaves out every
company that was acquired, went bust or was dropped. So this project rebuilds **who was in the index
on each date** since 2010, finds prices for the companies that later left, and tests two kinds of
strategy against SPY, after trading costs:

- **The plain rule:** buy the members that rose the most over the past 1–12 months (60 versions, all
  reported).
- **The model:** buy the members a machine-learning model, trained on 152 features, rates most likely
  to beat SPY next month.

Every choice is made on 2010–2022, and every strategy is then judged once on the decisions from
January 2023.

## The result so far (preview)

> **Preview numbers:** the download of delisted companies is still running (until ~13 Nov 2026), and
> everything is rerun once it's complete.

What $10,000 became over the test years (decisions Jan 2023 – Sept 2026, 45 months, after costs):

| Strategy | Value | Sharpe ratio | Worst fall |
| --- | --- | --- | --- |
| SPY | $19,650 | 1.21 | −8% |
| **The rule chosen on 2010–2022:** top 5 by 6-month return, each held 6 months | **$59,209** | 1.21 | −27% |
| **The headline model:** top 10 by predicted return above SPY, held 1 month | $11,640 | 0.12 | −31% |

**The models add nothing that a plain 6-month momentum rule doesn't do better, and no strategy chosen
in advance clearly beats SPY per unit of risk.** The rule tripled SPY's return, but through far more
risk and a handful of AI and chip stocks; per unit of risk it tied.
[Chapter 9](docs/09_results.md) has the results and [Chapter 10](docs/10_lessons.md) explains why.

## The decision rule, in plain terms

At each month-end close, using only what was known then:

1. Take every company in the S&P 500 on that date that has a month-end price.
2. **The model:** score each one with the headline model, a gradient-boosting model that predicts
   its return above SPY over the next month, and take the **10 highest scores**. **The plain rule,
   published next to it:** the 10 highest 6-month returns.
3. Buy them in equal amounts at the next trading day's open, and hold for one month. Then repeat.

**Nothing is bought** when the month's data can't be trusted (an incomplete month, missing prices or
sectors, or features unlike the model's). The picks are a research output, not advice.

## Links

| | |
| --- | --- |
| **The project book** | [siddharthps.github.io/sp500-momentum-winners](https://siddharthps.github.io/sp500-momentum-winners/): each step as a chapter, in plain words |
| **Running the project** | [The full guide](docs/running.md): setup, every pipeline step, snapshots, Docker, notebooks, development |
| **Live dashboard** | [sp500-momentum-winners.streamlit.app](https://sp500-momentum-winners.streamlit.app/): this month's picks, the live record, the backtest, model monitoring |
| **Monthly picks on Telegram** | [t.me/s/sp500_momentum_picks](https://t.me/s/sp500_momentum_picks) (readable in a browser) |
| **Public dataset** | [huggingface.co/datasets/siddharthps/sp500-momentum-winners](https://huggingface.co/datasets/siddharthps/sp500-momentum-winners): the features and results, without the vendors' raw prices |
| **Docker image** | `ghcr.io/siddharthps/sp500-momentum-winners` |
| **Progress** | [issues](https://github.com/siddharthps/sp500-momentum-winners/issues), [milestones](https://github.com/siddharthps/sp500-momentum-winners/milestones), the [project board](https://github.com/users/siddharthps/projects/1); decisions in [references/decisions.md](references/decisions.md) |

## Data sources

| Source | What it gives |
| --- | --- |
| **Wikipedia:** the current S&P 500 list and its record of index changes | Who was in the index on each date (819 companies over 202 month-ends), with repairs for renames and missing entries |
| **Yahoo Finance** (yfinance) | Daily prices from 2000 for current members, the departed companies it still covers, SPY, the sector funds, the Dow, VIX, gold and oil (628 series) |
| **Alpha Vantage** (free tier) | Monthly prices for departed companies Yahoo no longer has, or whose symbol now belongs to another company (the download is still running) |
| **FRED** (St. Louis Fed) | Core inflation, the Fed Funds rate, 1/5/10-year Treasury yields and potential GDP, each used only after its publication date |

The result is **one row per member per month-end: 101,431 rows** from January 2010, each with 152
features and the targets. [Appendix A](docs/appendix_a_data_dictionary.md) defines every column.

## How to run

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12. To read the results without running
anything, use the book, or the [notebooks](notebooks/), which are committed with their outputs.

```bash
uv sync                                                    # Python 3.12 and every dependency, from the lock file
uv run pytest                                              # the tests (offline, no data needed)
uv run python -m sp500_momentum.pipeline rebuild-all --dry-run   # the whole workflow's steps, in order
docker run --rm ghcr.io/siddharthps/sp500-momentum-winners # or the same, in Docker
```

To rebuild everything from the sources, add an Alpha Vantage key to `.env` and follow the pipeline:
membership → coverage → daily prices → FRED → delisted prices → monthly table → features → models →
notebooks. With access to the private data snapshot, one download replaces the first five steps.
**[The full guide](docs/running.md)** has every command, what to rerun after a change, the snapshots,
Docker, the dashboard, notifications and the development workflow.

## Acknowledgements

Built as the final project for the Stock Markets Analytics Zoomcamp 2026 (DataTalksClub).
