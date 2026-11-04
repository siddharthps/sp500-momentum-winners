# Chapter 6: Modelling

> **This draft covers Part 1, the setup:** which models, what they learn, and how they're trained and
> judged fairly. The results are added once the models are trained.

## 1. Goal

Build models that rank each month's members by their chance of beating SPY next month, so that buying
the top few beats the plain rule from Chapter 7, and SPY. Before any model is trained, the setup has
to guarantee one thing: **a model only ever learns from what was knowable before the period it's judged
on.** Every result after this depends on that.

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

Of the monthly table's 101,431 rows, **88,137 can be used**: members with a price whose next-month
result is known. The others are members with no price yet, and the latest month, whose result isn't in.
That's about 450 rows a month over 201 months. Each row offers **152 features**.

The same rows are asked three different questions, because the strategy can be framed three ways:

| Framing | Question | Used by |
| --- | --- | --- |
| Beat or not | Will this stock beat SPY next month? (yes/no) | Four classifiers and the neural network |
| By how much | What will its return be, minus SPY's? | One regression model |
| Better than the others | Where will it rank among this month's members? (graded 0–9 by tenth) | One ranking model |

The strategy only uses the *order* within each month (buy the top few), so all of them are judged the
same way: how often each month's top picks beat SPY, and by how much.

### 3.2 Three periods, cut by time

| Period | Years | Rows | Months | Share beating SPY | Used for |
| --- | --- | --- | --- | --- | --- |
| Train | 2010–2019 | 48,137 | 120 | 50.6% | Learning and tuning |
| Validation | 2020–2022 | 17,443 | 36 | 50.0% | Comparing the tuned models |
| Test | 2023 – Sept 2026 | 22,557 | 45 | 45.2% | One final check, never used for any choice |

The cut is by time, never at random. A random split would let a model learn from March 2024 and be
tested on February 2024. The test years are the same ones every strategy in this project is judged
on, including the plain rule in Chapter 7.

**A one-month gap sits before every period a model is judged on.** A row from the end of December is
labelled with January's result. If it were in the training data of a model judged on January, that
model would have seen part of the answer. So each training window stops a month early: the model
judged on 2020–2022 trains on decisions up to November 2019.

### 3.3 Tuning across successive years

Each model has settings to choose, such as the depth of a tree or the strength of a penalty. Choosing
them on one stretch of years risks fitting that stretch's quirks; the exploratory analysis showed the
signal moves between periods. So settings are scored on **six successive years**, each time training
only on the years before:

| Fold | Trains on decisions | Scored on | Training rows | Scored rows |
| --- | --- | --- | --- | --- |
| 1 | Jan 2010 – Nov 2013 | 2014 | 16,991 | 4,672 |
| 2 | Jan 2010 – Nov 2014 | 2015 | 21,656 | 4,810 |
| 3 | Jan 2010 – Nov 2015 | 2016 | 26,449 | 5,060 |
| 4 | Jan 2010 – Nov 2016 | 2017 | 31,490 | 5,251 |
| 5 | Jan 2010 – Nov 2017 | 2018 | 36,726 | 5,404 |
| 6 | Jan 2010 – Nov 2018 | 2019 | 42,115 | 5,564 |

The settings that do best **on average across the six years** win: they've worked in several different
markets, not just one. The tuned models are then compared on 2020–2022, which no fold has touched. The
chosen model is retrained on everything up to November 2022 and checked once on 2023 onwards.

### 3.4 Preparing the inputs, inside each training period

Different kinds of model need different preparation:

| Models | Blank values | Extreme values | Scale |
| --- | --- | --- | --- |
| The three gradient-boosting models | Read as they are: the model learns which way to send a blank | Not a problem for trees | Not needed |
| Decision tree, random forest | Filled with the training period's median, plus a "was blank" marker | Not a problem for trees | Not needed |
| Logistic regression, neural network | Median, plus the marker | Limited to the training period's 1st–99th percentile | Standardised |

**Every value used for preparation is learned from the training rows alone**, never from the rows being
scored. A median computed over all years would let 2022 data shape a model judged on 2016.

Each model can also be given a second version of the stock-level features: each one turned into the
stock's **percentile among that month's members**. "In the top 10% by volatility this month" stays
meaningful in calm and wild markets alike, and extreme values disappear. It uses only the same month's
rows, so it can't mix periods. Whether a model does better with raw values or percentiles is decided by
the tuning, model by model. Market and economic features have one value per month for every stock, so
they stay as they are.

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

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Split by time, with a one-month gap before every judged period | A row's label is next month's result; without the gap, a model could see part of the answer |
| Tune on six successive years inside 2010–2019, compare on 2020–2022, test once on 2023+ | Settings must work across several markets. Keeping 2020–2022 apart gives an untouched comparison before the one final test |
| Preparation learned from training rows only | Otherwise later data leaks into earlier models through something as small as a median |
| Blanks never filled with zero | Zero is a real value for a return or a beta; a filled blank would look like one |
| Extreme values limited only for the models they distort | Trees aren't affected by scale or outliers; linear models and neural networks are |
| Within-month percentiles as a tuning choice | They suit a question about *relative* winners, but whether they help is for the data to show |
| A ranking and a by-how-much model alongside the classifiers | The strategy uses the order within each month. A model trained on that order, or on the size of the win, may pick better than one trained only on "beat or not" |
| The ranking model learns grades 0–9 within each month | Grades keep the size of the win without letting one huge takeover month dominate |
| The by-how-much model's target is limited to its training period's 1st–99th percentile | A few +100% months would otherwise steer it |
| Every model judged by its top picks, not overall accuracy | The strategy buys a handful of stocks; being right about the other 440 doesn't matter |

---

## 5. Caveats

- **The test years have a lower base rate.** Only 45% of member-months beat SPY in 2023–2026, against
  about 50% before, because a few very large companies carried the index. Precision of the top picks
  is judged against each period's own base rate for that reason.
- **Six tuning years is still a short history** for an effect that comes and goes. The average across
  folds reduces, but can't remove, the chance of settings that suit 2014–2019 by luck.
- **Previews only.** The early years still miss most acquired companies; the training years still miss
  about 12,700 member-months (up to about 12,000 can still be filled), and every model is retrained
  once the download finishes.
