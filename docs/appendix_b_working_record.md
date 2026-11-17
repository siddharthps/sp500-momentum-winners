# Appendix B: The full working record

The chapters are the edited story: what was done and why. The proof behind them, and every
discussion, dead end and fix in the order it happened, is kept alongside the code in two records.
They're working notes, written as the work happened: they use issue numbers (such as #85) and code
names, and a later entry sometimes corrects an earlier one.

| Record | What's in it |
| --- | --- |
| [Decision log](../references/decisions.md) | The decisions, dated, each with its reason, and the evidence for the ones the chapters only summarise (for example the per-case checks of the takeover price fixes, and of the four wrong-security price series) |
| [Brainstorm and journal](../references/Project_Ideas_Brainstorm.md) | How the question was chosen from several candidate ideas (Section 5); the first design of the table (Section 7); a dated entry for every working session, with the traps found and fixed (Section 8, "Discussion Log"); and a table of settled decisions, with the parked ideas and open questions (Section 9) |

The book's results come from notebooks, each saved with its outputs, and from the result tables
they write:

| Notebook | What it produces | Chapters |
| --- | --- | --- |
| [Data](../notebooks/01_data.ipynb) | Membership, the survivorship gap, the downloads, the monthly and feature tables | 1, 2, 3, 4 |
| [Features and exploratory analysis](../notebooks/02_features_eda.ipynb) | The target, the signal of the 87 features that vary between stocks, its stability | 1, 4, 5 |
| [Models](../notebooks/03_models.ipynb) | Tuning, the comparison on 2020–2022, the one test | 6, 9, 10 |
| [Simulation](../notebooks/04_simulation.ipynb) | The 60-rule grid, the chosen rule, the models traded, a simpler $100-per-pick cross-check | 7, 9, 10 |
| [Risk](../notebooks/05_risk.ipynb) | The paths over time and the market-trend filter | 7, 9 |
| [Diagnostics](../notebooks/06_diagnostics.ipynb) | What each strategy buys, and where it wins and loses | 7, 9, 10 |
| [The whole workflow](../notebooks/00_run_all.ipynb) | Every step end to end through the monthly run's own functions, with nothing sent or published | 8 |

| Result table | What it holds |
| --- | --- |
| [The rule grid](../reports/baseline_grid_2010_2026.csv) | All 60 versions of the plain rule, plus SPY and equal weight, 2010–2026 |
| [Feature signal](../reports/feature_signal_2010_2022.csv) | The information coefficient of the 87 features that vary between stocks on the same date (how well each ranks next month's winners, within each month), 2010–2022 |
| [Model tuning](../reports/model_cv_results.csv) | Every setting each tuned model tried (30 each, 20 for the neural network), and its score |
| [Model comparison](../reports/model_comparison.csv) | Each model and both plain rules on the tuning years (2014–2019), the comparison years (2020–2022) and the test years |
| [Strategies](../reports/strategies_2020_2026.csv) | The models and both plain rules held one month (top 1, 5 and 10; each weighting, with and without the buffer), the chosen rule, SPY and equal weight, on 2020–2022 and the test years |
| [Strategies with the trend filter](../reports/strategies_trend_2020_2026.csv) | The same, with and without the filter |
