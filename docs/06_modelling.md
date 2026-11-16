# Chapter 6: Modelling

> **Part 1, the setup** (3.1–3.5): the models, and how they're trained and judged fairly. **Part 2,
> the results** (3.6–3.9). Chapter 7 trades them.

## 1. Goal

Build models that rank each month's members by their chance of beating SPY next month, so that buying
the top few beats the plain rule ([Chapter 1](01_problem.md)) and SPY. Every result depends on one
guarantee: **a model only learns from what was knowable before the period it's judged on.**

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

Of the monthly table's 101,363 rows, **96,404 can be used**: members with a price and a known
next-month result. That's about 480 a month over 201 months, each with **147 features**. The same rows are asked three questions:

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
| Train | 2010–2019 | 55,809 | 120 | 50.3% | Learning and tuning |
| Validation | 2020–2022 | 17,981 | 36 | 49.9% | Comparing the tuned models |
| Test | 2023 – Sept 2026 | 22,614 | 45 | 45.1% | One final check, never used for any choice |

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
| 1 | Jan 2010 – Nov 2013 | 2014 | 20,680 | 5,536 |
| 2 | Jan 2010 – Nov 2014 | 2015 | 26,211 | 5,590 |
| 3 | Jan 2010 – Nov 2015 | 2016 | 31,795 | 5,788 |
| 4 | Jan 2010 – Nov 2016 | 2017 | 37,566 | 5,885 |
| 5 | Jan 2010 – Nov 2017 | 2018 | 43,444 | 5,927 |
| 6 | Jan 2010 – Nov 2018 | 2019 | 49,369 | 5,945 |

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

On 2014–2019, six of the seven models' best settings beat the 49.7% base rate; logistic regression
fell just below it.

| Model | Best setting's precision | Worst year | Median of its tries |
| --- | --- | --- | --- |
| Random forest | 57.1% | 45.8% | 52.5% |
| Decision tree | 55.1% | 53.3% | 53.2% |
| Gradient boosting, ranking | 54.9% | 51.7% | 49.4% |
| Gradient boosting, beat or not | 54.0% | 43.3% | 49.4% |
| Gradient boosting, by how much | 51.0% | 43.3% | 49.6% |
| Neural network | 50.8% | 46.7% | 49.6% |
| Logistic regression | 49.0% | 45.8% | 48.3% |

The last column is the warning: **for most models, the typical setting scored about the base rate**,
and the best of 20–30 tries is a few points higher, partly by luck of the draw. The two tree models
stood out: even their typical settings scored 52–53%. Only untouched years can tell how much is real.

### 3.7 The comparison on 2020–2022: four models beat a random pick

| | Precision | Average return vs SPY, per month |
| --- | --- | --- |
| Decision tree | **53.6%** | +0.90% |
| Plain rule: 6-month top 10 | 53.1% | +0.56% |
| Gradient boosting, by how much (**headline**) | 52.8% | +1.29% |
| Gradient boosting, beat or not | 51.9% | **+1.65%** |
| Random forest | 51.7% | +0.42% |
| Plain rule: last month's top 10 | 51.1% | +0.70% |
| Neural network | 49.4% | −0.74% |
| Gradient boosting, ranking | 46.9% | +0.73% |
| Logistic regression | 46.4% | +0.19% |
| Average of the models | 45.0% | −0.04% |
| *Base rate* | *49.9%* | |

**Four models' top 10 beat SPY more often than the base rate, and so did both plain rules.** The
headline was chosen by the same rule as the tuning (average across the years minus half the spread),
and the by-how-much model scored best on it: the third-best hit rate, and by far the steadiest, with
its worst year at 51.7%. Its picks gained 1.29% a month over SPY, the second-most. Averaging the
models did worst of all.

### 3.8 The test (2023 onwards): the promise didn't hold

Every model was retrained to November 2022 and scored once on 45 months nothing had been chosen on.

| | Precision | Average return vs SPY, per month |
| --- | --- | --- |
| Plain rule: 6-month top 10 | **52.9%** | **+1.47%** |
| Random forest | 50.4% | +0.16% |
| Logistic regression | 48.9% | +0.24% |
| Neural network | 47.3% | −0.32% |
| Decision tree | 47.1% | −0.30% |
| Plain rule: last month's top 10 | 46.4% | +0.43% |
| Average of the models | 46.2% | −0.72% |
| Gradient boosting, by how much (**headline**) | 45.1% | −0.72% |
| Gradient boosting, beat or not | 44.0% | −1.15% |
| Gradient boosting, ranking | 42.0% | −1.93% |
| *Base rate* | *45.1%* | |

**The headline did no better than a random pick, and trailed SPY;** the 6-month rule did better on
both. All four models that beat the base rate on 2020–2022 fell back: the decision tree from 53.6% to
47.1%, the headline from 52.8% to 45.1%. Only the random forest stayed a little above the base rate,
with almost no gain over SPY (+0.16% a month). It came third on 2020–2022, so nothing seen before the
test would have chosen it; choosing it now would be choosing on the test.

### 3.9 What the headline looks at

The by-how-much model spreads its attention thinly: its 15 most important inputs, of 147, carry 20% of
the total. **Most describe the market, not the stock:** SPY's, the Dow's and gold's recent returns,
VIX, the 10-year yield, how momentum has been doing, and January. Those have the same value for every
stock in a month, so on their own they can't tell stocks apart; they change how the model weighs the
rest. Two sector flags (utilities, energy) and one stock measure (beta) complete the list. As in
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
  chance. The conclusion rests on the pattern (four models above their base rate on 2020–2022, every one
  of them falling back on the test; the headline at it), not on any single gap.
- **Some early takeovers have no free price at all ([Chapter 3](03_monthly_table.md)),** so the
  training years are slightly survivor-biased.
