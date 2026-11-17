# Chapter 6: Modelling

> **Part 1, the setup** (3.1–3.5): the models, and how they're trained and judged fairly. **Part 2,
> the results** (3.6–3.9). Chapter 7 trades them.

## 1. Goal

Build models that rank each month's members by their chance of beating SPY next month. Buying the
top few should then beat the plain rule ([Chapter 1](01_problem.md)) and SPY. Every result depends
on one guarantee: **a model only learns from what was knowable before the period it's judged on.**

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

**96,317 of the monthly table's 101,363 rows can be used:** members with a price and a known
next-month result. That's about 480 a month over 201 months, each with **147 features**. The same
rows are asked three questions:

| Framing | Question | Used by |
| --- | --- | --- |
| Beat or not | Will this stock beat SPY next month? (yes/no) | Four classifiers and the neural network |
| By how much | What will its return be, minus SPY's? | One regression model |
| Better than the others | Where will it rank among this month's members? (graded 0–9 by tenth, 9 = the best tenth) | One ranking model |

- **All three are judged the same way.** The strategy only uses the *order* within each month, so
  what counts is how often, and by how much, each month's top picks beat SPY.
- **Precision** is the share of a model's top 10 that beat SPY the next month.
- The **base rate** is the share of all members that did: what a random pick scores.

### 3.2 Three periods, cut by time

| Period | Years | Rows | Months | Base rate (share beating SPY) | Used for |
| --- | --- | --- | --- | --- | --- |
| Train | 2010–2019 | 55,722 | 120 | 50.3% | Learning and tuning |
| Validation | 2020–2022 | 17,981 | 36 | 49.9% | Comparing the tuned models |
| Test | 2023 – Sept 2026 | 22,614 | 45 | 45.1% | One final check, never used for any choice |

- **The cut is by time, never random.** A random split would let a model learn from March 2024 and
  be tested on February 2024.
- **Every strategy is judged on the same test years,** the plain rule in Chapter 7 included.
- **A one-month gap sits before every judged period.** A December row is labelled with January's
  result, so a model judged on January mustn't train on it. The model judged on 2020–2022 trains
  on decisions up to November 2019.

### 3.3 Tuning across successive years

Each model has settings to choose, such as tree depth or penalty strength. The signal moves between
periods ([Chapter 5](05_eda.md)), so settings are scored on **six successive years**, each trained
only on the years before:

| Fold | Trains on decisions | Scored on | Training rows | Scored rows |
| --- | --- | --- | --- | --- |
| 1 | Jan 2010 – Nov 2013 | 2014 | 20,598 | 5,532 |
| 2 | Jan 2010 – Nov 2014 | 2015 | 26,124 | 5,590 |
| 3 | Jan 2010 – Nov 2015 | 2016 | 31,708 | 5,788 |
| 4 | Jan 2010 – Nov 2016 | 2017 | 37,479 | 5,885 |
| 5 | Jan 2010 – Nov 2017 | 2018 | 43,357 | 5,927 |
| 6 | Jan 2010 – Nov 2018 | 2019 | 49,282 | 5,945 |

- **Each model tries 30 random settings** (20 for the slower neural network).
- **The winning setting has the best score:** the **average precision across the six years minus
  half their spread** (how much the yearly results vary), so steady beats brilliant-then-poor.
- **The tuned models are compared on 2020–2022,** which no fold touched. The best model becomes the
  **headline**; the plain rules are shown, but aren't candidates.
- **Finally every model is retrained up to November 2022** and checked once on 2023 onwards.

### 3.4 Preparing the inputs, inside each training period

Different kinds of model need different preparation:

| Models | Blank values | Extreme values | Scale |
| --- | --- | --- | --- |
| The three gradient-boosting models | Read as they are: the model learns which way to send a blank | Not a problem for trees | Not needed |
| Decision tree, random forest | Filled with the training period's median, plus a "was blank" marker | Not a problem for trees | Not needed |
| Logistic regression, neural network | Median, plus the marker | Limited to the training period's 1st–99th percentile | Standardised |

- **Every value used for preparation is learned from the training rows alone,** never from the
  rows being scored. A median computed over all years would let 2022 data shape a model judged on
  2016.
- **Each model can also use the stock-level features as percentiles among that month's members**
  ("top 10% by volatility this month"). They mean the same in calm and wild markets, have no
  extreme values, and use only the same month's rows.
- **The tuning decides, model by model, whether raw values or percentiles do better.** In the end
  only the decision tree and the ranking model chose percentiles; the headline uses raw values.
- **Market and economic features stay as they are:** they're the same for every stock in a month.

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

### 3.6 Tuning: promising, but mostly by selection

On 2014–2019, six of the seven models' best settings beat the 49.7% base rate. Logistic regression
fell just below it.

| Model | Best setting's precision | Its worst year | Best setting's score | Median try's score |
| --- | --- | --- | --- | --- |
| Gradient boosting, ranking | 55.1% | 51.7% | 53.6% | 46.1% |
| Decision tree | 54.3% | 52.5% | 53.1% | 50.3% |
| Random forest | 55.0% | 50.0% | 53.0% | 49.3% |
| Gradient boosting, beat or not | 55.7% | 45.8% | 52.8% | 48.4% |
| Neural network | 54.0% | 50.0% | 52.2% | 47.6% |
| Gradient boosting, by how much | 54.0% | 46.7% | 50.4% | 46.4% |
| Logistic regression | 49.2% | 47.5% | 48.1% | 47.4% |

- **The score is what picks a setting** (Section 3.3).
- **The last two columns are the warning.** The best of 20–30 tries scored about 3 to 7 points above
  the typical (median) try, partly by luck of the draw (logistic regression, under 1 point).
- **The ranking model led the tuning by a small margin.** The model later chosen as the headline
  came sixth of seven.

Only untouched years can tell how much is real.

### 3.7 The comparison on 2020–2022: two models beat a random pick

| | Precision | Average return vs SPY, per month |
| --- | --- | --- |
| Plain rule: 6-month top 10 | **53.1%** | +0.56% |
| Gradient boosting, by how much (**headline**) | 51.9% | +1.11% |
| Decision tree | 51.4% | +0.90% |
| Plain rule: last month's top 10 | 51.1% | +0.70% |
| Gradient boosting, beat or not | 49.4% | **+1.67%** |
| Logistic regression | 48.6% | +0.65% |
| Average of the models | 48.6% | +0.36% |
| Neural network | 46.9% | −0.60% |
| Gradient boosting, ranking | 46.1% | +0.99% |
| Random forest | 43.3% | −0.87% |
| *Base rate* | *49.9%* | |

- **Two models' top 10 beat SPY more often than the base rate:** the headline and the decision
  tree. So did both plain rules.
- **The headline was chosen by the tuning's score** (Section 3.3). The by-how-much model scored
  best on it among the models: the best hit rate of any model, and the best worst year (47.5%).
- **Its picks gained 1.11% a month over SPY,** the second-most.
- **The 6-month rule scored a little higher on the same measure,** but the rules are benchmarks,
  not candidates.
- **The random forest, third in the tuning, did worst.**

### 3.8 The test (2023 onwards): the promise didn't hold

Every model was retrained to November 2022 and scored once on 45 months nothing had been chosen on.

| | Precision | Average return vs SPY, per month |
| --- | --- | --- |
| Plain rule: 6-month top 10 | **52.9%** | **+1.47%** |
| Neural network | 51.6% | +0.89% |
| Logistic regression | 48.9% | +0.32% |
| Decision tree | 48.2% | +0.22% |
| Average of the models | 47.8% | +0.25% |
| Plain rule: last month's top 10 | 46.4% | +0.43% |
| Gradient boosting, beat or not | 44.7% | −0.52% |
| Gradient boosting, by how much (**headline**) | 43.6% | −0.83% |
| Gradient boosting, ranking | 42.7% | −1.73% |
| Random forest | 40.4% | −0.72% |
| *Base rate* | *45.1%* | |

- **The headline did worse than a random pick (43.6% against 45.1%) and trailed SPY by 0.83% a
  month.** The 6-month rule did better on both.
- **Of the two models that beat the base rate on 2020–2022,** the headline fell from 51.9% to
  43.6%, and the decision tree from 51.4% to 48.2%, still a little above the test's lower base
  rate.
- **The 2020–2022 order didn't carry over.** The neural network and logistic regression, both below
  the base rate then, led the models on the test. The three gradient-boosting models and the random
  forest came last.
- **The neural network's 51.6% (+0.89% a month) is the best model result,** but it came sixth of
  eight on 2020–2022. Nothing seen before the test would have chosen it; choosing it now would be
  choosing on the test.

### 3.9 What the headline looks at

The by-how-much model spreads its attention thinly: its 15 most important inputs, of 147, carry
20% of the total. **Most describe the market, not the stock:**

| Inputs | They describe | Which |
| --- | --- | --- |
| 11 of the 15 | The market | SPY's last-month and 6-month returns, the Dow's 12-month return, the 5- and 10-year Treasury yields, potential GDP growth, the gap between the month's best and worst members, how last month's winners did against SPY, and three calendar months (August, May, April) |
| The other four | The stock | The utilities flag (the largest single input), beta, and two price indicators |

The market inputs have the same value for every stock in a month. On their own they can't tell
stocks apart; they change how the model weighs the rest.

Potential GDP growth moves slowly and smoothly, so to a model it may work partly as a clock,
letting it fit what happened in particular training years. The calendar months may likewise pick
up seasonal patterns that held by chance in those years. **That's a reading of the importance
ranking, not a measured effect.**

As in Chapter 5, no feature has a strong, steady signal, and the models found nothing stronger
combined.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Blanks never filled with zero | Zero is a real value for a return or a beta; a filled blank would look like one |
| The ranking model learns grades 0–9 within each month | Grades keep the size of the win without letting one huge takeover month dominate |
| The by-how-much model's target is limited to its training period's 1st–99th percentile, and its errors are scored with a loss that softens large misses | A few +100% months would otherwise steer it |
| Random search over settings, with a fixed seed | Covers wide ranges more efficiently than a grid, and gives the same tries on every rerun |
| One headline, chosen on 2020–2022 before the test was read; every model still tested and simulated | Showing the others keeps the choice honest, but they're never picked from |
| No reweighting of winners and losers | About half of member-months beat SPY, so the classes are already balanced |
| The neural network averaged over five starting seeds, stopping when its latest 15% of training months stop improving | One network's result depends on its random start; the stopping data is the most recent, as in real use |
| Logistic regression with a plain (L2) penalty | The sparse (L1) version took minutes per try and was unstable with near-duplicate features |

---

## 5. Caveats

- **The test years have a lower base rate.** Only 45% of member-months beat SPY in 2023–2026,
  against about 50% before, because a few very large companies carried the index. That's why the
  top picks' precision is judged against each period's own base rate.
- **Six tuning years is still a short history** for an effect that comes and goes. The average
  across folds reduces, but can't remove, the chance of settings that suit 2014–2019 by luck.
- **Precision is not profit.** It counts winners, not their size. The "return vs SPY" above is the
  average of each month's picks, before costs and without holding periods. Chapter 7 trades the
  models with both.
- **36 and 45 months are short.** A gap of three or four points in precision between two models
  can be chance. The conclusion rests on the pattern (the 2020–2022 order not carrying over to the
  test, and the headline below its base rate there), not on any single gap.
- **Some early takeovers have no free price at all ([Chapter 3](03_monthly_table.md)),** so the
  training years are slightly survivor-biased.
