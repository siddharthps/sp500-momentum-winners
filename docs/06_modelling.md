# Chapter 6: Modelling

> **Part 1, the setup** (3.1–3.5): the models, and how they're trained and judged fairly. **Part 2,
> the results** (3.6–3.9). Chapter 7 trades them.

## 1. Goal

Build models that rank each month's members by their chance of beating SPY next month, so that buying
the top few beats the plain rule ([Chapter 1](01_problem.md)) and SPY. Every result depends on one
guarantee: **a model only learns from what was knowable before the period it's judged on.**

> **All numbers here are previews.** The download of delisted companies is still running.

---

## 2. What was done

| Step | What it decides |
| --- | --- |
| 1 | Which rows a model sees, and what it's asked to predict |
| 2 | How time is cut into training, validation and test periods, with gaps |
| 3 | How each model's settings are tuned without touching the later periods |
| 4 | How each kind of model's inputs are prepared, inside each training period only |
| 5 | Which models are compared |

---

## 3. What came out

### 3.1 The rows and the three questions

Of the monthly table's 101,431 rows, **88,137 can be used** (in the 4 Nov snapshot the models were
trained on): members with a price and a known next-month result. That's about 440 a month over 201
months, each with **152 features**. The same rows are asked three questions:

| Framing | Question | Used by |
| --- | --- | --- |
| Beat or not | Will this stock beat SPY next month? (yes/no) | Four classifiers and the neural network |
| By how much | What will its return be, minus SPY's? | One regression model |
| Better than the others | Where will it rank among this month's members? (graded 0–9 by tenth) | One ranking model |

The strategy only uses the *order* within each month, so all are judged the same way: how often, and
by how much, each month's top picks beat SPY.

### 3.2 Three periods, cut by time

| Period | Years | Rows | Months | Share beating SPY | Used for |
| --- | --- | --- | --- | --- | --- |
| Train | 2010–2019 | 48,137 | 120 | 50.6% | Learning and tuning |
| Validation | 2020–2022 | 17,443 | 36 | 50.0% | Comparing the tuned models |
| Test | 2023 – Sept 2026 | 22,557 | 45 | 45.2% | One final check, never used for any choice |

The cut is by time, never random: a random split would let a model learn from March 2024 and be
tested on February 2024. Every strategy, including the plain rule in Chapter 7, is judged on the same
test years.

**A one-month gap sits before every judged period.** A December row is labelled with January's
result, so a model judged on January mustn't train on it: the model judged on 2020–2022 trains on
decisions up to November 2019.

### 3.3 Tuning across successive years

Each model has settings to choose, such as tree depth or penalty strength. The signal moves between
periods ([Chapter 5](05_eda.md)), so settings are scored on **six successive years**, each time
training only on the years before:

| Fold | Trains on decisions | Scored on | Training rows | Scored rows |
| --- | --- | --- | --- | --- |
| 1 | Jan 2010 – Nov 2013 | 2014 | 16,991 | 4,672 |
| 2 | Jan 2010 – Nov 2014 | 2015 | 21,656 | 4,810 |
| 3 | Jan 2010 – Nov 2015 | 2016 | 26,449 | 5,060 |
| 4 | Jan 2010 – Nov 2016 | 2017 | 31,490 | 5,251 |
| 5 | Jan 2010 – Nov 2017 | 2018 | 36,726 | 5,404 |
| 6 | Jan 2010 – Nov 2018 | 2019 | 42,115 | 5,564 |

Each model tries **30 random settings** (20 for the slower neural network). The winner has the best
**average across the six years minus half its spread**, so steady beats brilliant-then-poor. The tuned
models are compared on 2020–2022, which no fold touched, and the best becomes the **headline**.
Finally every model is retrained up to November 2022 and checked once on 2023 onwards.

### 3.4 Preparing the inputs, inside each training period

Different kinds of model need different preparation:

| Models | Blank values | Extreme values | Scale |
| --- | --- | --- | --- |
| The three gradient-boosting models | Read as they are: the model learns which way to send a blank | Not a problem for trees | Not needed |
| Decision tree, random forest | Filled with the training period's median, plus a "was blank" marker | Not a problem for trees | Not needed |
| Logistic regression, neural network | Median, plus the marker | Limited to the training period's 1st–99th percentile | Standardised |

**Every value used for preparation is learned from the training rows alone**, never from the rows being
scored. A median computed over all years would let 2022 data shape a model judged on 2016.

Each model can also use the stock-level features as **percentiles among that month's members**
("top 10% by volatility this month"). They mean the same in calm and wild markets, have no extreme
values, and use only the same month's rows. The tuning decides, model by model, whether raw values or
percentiles do better. Market and economic features, the same for every stock in a month, stay as
they are.

### 3.5 The models

| Model | Why it's in the comparison |
| --- | --- |
| Decision tree | The simplest model; its rules can be read |
| Random forest | Many trees averaged: stable, and not fooled by near-duplicate features |
| Logistic regression | A straight-line benchmark: if it matches the others, the signal is simple |
| Gradient boosting, beat or not | Usually the strongest kind of model on tables like this |
| Gradient boosting, ranking | Trained directly on the order within each month, which is how picks are made |
| Gradient boosting, by how much | Uses the size of a stock's win, not just whether it won |
| Small neural network | Research on monthly US stock returns found shallow networks among the best methods |
| Average of all of them | Different models' errors partly cancel |

A model's **precision** is the share of its top 10 that beat SPY the next month. It's set against the
**base rate**, the share of all members that did: what a random pick scores.

### 3.6 Tuning: promising, but mostly by selection

On 2014–2019, six of the seven models' best settings beat the 50.0% base rate; logistic regression
only matched it.

| Model | Best setting's precision | Worst year | Median of its tries |
| --- | --- | --- | --- |
| Decision tree | 55.7% | 45.8% | 51.0% |
| Gradient boosting, beat or not | 55.6% | 47.5% | 48.8% |
| Random forest | 53.9% | 49.2% | 50.1% |
| Neural network | 53.1% | 46.7% | 51.0% |
| Gradient boosting, ranking | 52.5% | 50.0% | 50.3% |
| Gradient boosting, by how much | 52.2% | 45.8% | 49.9% |
| Logistic regression | 50.0% | 46.7% | 48.8% |

The last column is the warning: **the typical setting of every model scored about the base rate.** The
best of 20–30 tries is a few points higher, partly by luck of the draw; only untouched years can tell
how much is real.

### 3.7 The comparison on 2020–2022: no model beat a random pick

| | Precision | Average return vs SPY, per month |
| --- | --- | --- |
| Plain rule: 6-month top 10 | **53.1%** | +0.74% |
| Plain rule: last month's top 10 | 52.5% | +0.85% |
| Gradient boosting, by how much (**headline**) | 49.2% | +1.20% |
| Random forest | 48.6% | +0.15% |
| Neural network | 48.3% | 0.00% |
| Gradient boosting, beat or not | 47.8% | −0.69% |
| Decision tree | 47.8% | +0.42% |
| Gradient boosting, ranking | 47.5% | +1.28% |
| Average of the models | 47.2% | +0.07% |
| Logistic regression | 45.6% | +0.06% |
| *Base rate* | *49.9%* | |

**Every model's top 10 beat SPY less often than the base rate; both plain rules beat it.** The
headline was chosen by the same rule as the tuning (average across the years minus half the spread),
and the by-how-much model scored best: closest to the base rate and the steadiest. Fewer than half its
picks won, but the winners won by more, so it gained the second-most. Averaging the models didn't
help.

### 3.8 The test (2023 onwards): the same picture

Every model was retrained to November 2022 and scored once on 45 months nothing had been chosen on.

| | Precision | Average return vs SPY, per month |
| --- | --- | --- |
| Decision tree | 54.0% | +0.04% |
| Plain rule: 6-month top 10 | 52.9% | **+1.47%** |
| Average of the models | 50.7% | +0.05% |
| Logistic regression | 49.6% | +0.27% |
| Neural network | 47.1% | +0.59% |
| Plain rule: last month's top 10 | 46.4% | +0.45% |
| Gradient boosting, beat or not | 45.6% | −0.66% |
| Random forest | 45.6% | −0.12% |
| Gradient boosting, by how much (**headline**) | 45.1% | −0.83% |
| Gradient boosting, ranking | 42.9% | −1.92% |
| *Base rate* | *45.2%* | |

**The headline did no better than a random pick, and trailed SPY;** the 6-month rule did better on
both. The decision tree topped precision but gained almost nothing over SPY (often, by little). It had
been below the base rate on 2020–2022, so picking it now would be choosing on the test.

### 3.9 What the headline looks at

The by-how-much model spreads its attention thinly: its 15 most important inputs, of 152, carry about
a quarter of the total, mostly short-term technical indicators and the market's last month. As in
Chapter 5, no feature has a strong, steady signal, and the models found nothing stronger combined.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Blanks never filled with zero | Zero is a real value for a return or a beta; a filled blank would look like one |
| The ranking model learns grades 0–9 within each month | Grades keep the size of the win without letting one huge takeover month dominate |
| The by-how-much model's target is limited to its training period's 1st–99th percentile | A few +100% months would otherwise steer it |
| Random search over settings, 30 tries per model (20 for the neural network), fixed seed | Covers wide ranges more efficiently than a grid, and gives the same tries on every rerun |
| One headline, chosen on 2020–2022 before the test was read; every model still tested and simulated | Choosing after the test would turn the test into another tuning round. Showing the others keeps the choice honest, but they're never picked from |
| No reweighting of winners and losers | About half of member-months beat SPY, so the classes are already balanced |
| The neural network averaged over five starting seeds, stopping when its latest 15% of training months stop improving | One network's result depends on its random start; the stopping data is the most recent, as in real use |
| Logistic regression with a plain (L2) penalty | The sparse (L1) version took minutes per try and was unstable with near-duplicate features |

---

## 5. Caveats

- **The test years have a lower base rate.** Only 45% of member-months beat SPY in 2023–2026, against
  about 50% before, because a few very large companies carried the index. Precision of the top picks
  is judged against each period's own base rate for that reason.
- **Six tuning years is still a short history** for an effect that comes and goes. The average across
  folds reduces, but can't remove, the chance of settings that suit 2014–2019 by luck.
- **Precision is not profit.** It counts winners, not their size, and the "return vs SPY" above is the
  average of each month's picks before costs and without holding periods. Chapter 7 trades the
  models with both.
- **36 and 45 months are short.** A gap of three or four points in precision between two models can be
  chance. The conclusion rests on the pattern (every model below its base rate on 2020–2022; the
  headline at it on the test), not on any single gap.
- **Previews only.** The early years still miss many acquired companies
  ([Chapter 3](03_monthly_table.md)), and every model is retrained once the download finishes.
