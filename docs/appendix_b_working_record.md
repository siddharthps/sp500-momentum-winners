# Appendix B: The full working record

The chapters are the edited story: what was done and why. The proof behind them, and every
discussion, dead end and fix in the order it happened, is kept alongside the code:

| Record | What's in it |
| --- | --- |
| [Decision log](../references/decisions.md) | Every decision and the reason behind it, by date, with the evidence for the ones the chapters only summarise (for example the per-case checks of the takeover price fixes) |
| [Brainstorm and journal](../references/Project_Ideas_Brainstorm.md) | How the question was chosen from several candidate ideas, the first design of the table, a dated journal of every working session with the traps found and fixed (Section 8), and a table of settled decisions (Section 9) |

The numbers in the book come from notebooks, each saved with its outputs, and from the result tables
they write:

| Notebook | What it produces | Chapters |
| --- | --- | --- |
| [Data](../notebooks/01_data.ipynb) | Membership, the survivorship gap, the downloads, the monthly and feature tables | 2, 3, 4 |
| [Features and exploratory analysis](../notebooks/02_features_eda.ipynb) | The target, each feature's signal, its stability | 4, 5 |
| [Models](../notebooks/03_models.ipynb) | Tuning, the comparison on 2020–2022, the one test | 6 |
| [Simulation](../notebooks/04_simulation.ipynb) | The 60-rule grid, the chosen rule, the models traded | 7, 9 |
| [Risk](../notebooks/05_risk.ipynb) | The paths over time and the market-trend filter | 7, 9 |
| [Diagnostics](../notebooks/06_diagnostics.ipynb) | What each strategy buys, and where it wins and loses | 7, 9 |
| [The whole workflow](../notebooks/00_run_all.ipynb) | Every step end to end, as the monthly run does it | 8 |

| Result table | What it holds |
| --- | --- |
| [The rule grid](../reports/baseline_grid_2010_2026.csv) | All 60 versions of the plain rule, 2010–2026 |
| [Feature signal](../reports/feature_signal_2010_2022.csv) | Each feature's information coefficient, 2010–2022 |
| [Model tuning](../reports/model_cv_results.csv) | Every setting each model tried, and its score |
| [Model comparison](../reports/model_comparison.csv) | Each model and plain rule on the tuning years, 2020–2022 and the test years |
| [Strategies](../reports/strategies_2020_2026.csv) | Every simulated strategy on 2020–2022 and the test years |
| [Strategies with the trend filter](../reports/strategies_trend_2020_2026.csv) | The same, with and without the filter |
