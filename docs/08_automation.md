# Chapter 8: Automation

> **Part 1** (sections 3.1–3.4): the monthly run. **Part 2** (section 3.5): notifications.
> **Part 3** (section 3.6): the data snapshots. **Part 4** (section 3.7): the live dashboard. The
> cloud run and the run-all notebook are added as they're built.

## 1. Goal

Everything before this chapter looks backwards. This step makes the system look **forwards**. Once
a month it answers *"what would each strategy buy at the next open?"* from fresh data, saves the
answer, and so builds a record of picks made before their results were known. That record is the
only test this project will ever have that no choice could have touched.

---

## 2. What was done

**One command, five steps, run once a month:**

| Step | What it does | Why |
| --- | --- | --- |
| 1. Update the data | Today's index members and recent changes, removed members' coverage, the full price history of every active stock and benchmark, the economic series | Membership changes every month; prices need the latest month-end |
| 2. Rebuild | The monthly table and the features, exactly as for the research | One code path for research and live picks |
| 3. Check | The latest month-end must be complete before anything is trusted (below) | A half-updated month would silently give stale picks |
| 4. Pick | The headline model's top 10 and the 6-month rule's top 10 | Both published, labelled |
| 5. Save | One file of picks per month, and a running record of every pick | The record is what later monitoring reads |

**It runs on the first weekday of each month at 07:00 (US Central),** after the month's last close
and before the next open, so the golden rule still holds: features at the month-end close, the trade
at the next open. If the computer is off that morning, the run happens on the first weekday it's on
afterwards. A month that's already done is never redone by accident.

---

## 3. What came out

### 3.1 Prices are re-downloaded, never appended

The obvious update, adding the newest days to each stored price history, would be wrong. The
adjusted close (used for every return) is recomputed backwards every time a company pays a dividend
or splits its shares. New days appended to an old file would mix two different adjustments and
distort returns. So each active stock's whole history is downloaded again (about a minute). Removed
companies' histories never change, so they are left as they are.

### 3.2 The checks before any pick

The run stops, writes nothing, and says why if:

- **the latest month-end isn't the month's last trading day.** This would mean the download hadn't
  caught up. Only three exchange holidays can fall on a month's last weekday (Good Friday, Memorial
  Day and Thanksgiving), and they're allowed for.
- **SPY has no close for that month,** or fewer than 95% of the month's members have a price;
- **a member has no sector.** This happened on the first run: a company had just left the index, so
  its sector no longer came from the current list. It would have added a feature column the model
  had never seen. It now stops the run until the sector is filled in;
- **the feature columns differ from the ones the model was tuned on,** in name or order.

### 3.3 The model is refitted each month, never re-tuned

The headline model's settings were chosen once, on 2014–2022, and stay frozen. Each month it is
**refitted** on every month whose result is known, with the same one-month gap before the scored
month as in the backtest. The settings stay as they were, but the model learns from the latest
years.

**The refit is the backtest's own code.** Run as of January 2023, it trains on exactly the test
fold's rows. It reproduces the backtest's January 2023 scores for all 497 members to the last
decimal, with the same top 10.

### 3.4 Both strategies are published

Each month's file lists the headline model's top 10 (the model chosen in advance) and the 6-month
rule's top 10 (the stronger strategy in every test), with their scores. Publishing only the model
would hide the project's own finding; publishing only the rule would drop the choice made in
advance. Side by side, they start a live head-to-head.

The first file, for the end of October 2026, was made on 5 November, *after* the next open it would
have traded at. It uses only data up to 30 October, so nothing leaks, but it couldn't actually have
been traded. Every pick records when it was made, so this one can be set apart. The first truly live
month is the one made on 1 December 2026.

### 3.5 Part 2: notifications

A scheduled job's most likely failure is a silent one. So every run now reports, and the messages
are split by who they're for:

| Message | Where | When |
| --- | --- | --- |
| Both strategies' picks, the index changes that month, and the share of members priced | **A public channel** | Each monthly run |
| How last month's picks did: each list's return from the next open to the month-end close, against SPY's, and how many of the ten beat it | The same message | From January 2027, once a full month of live picks has passed |
| Why a run stopped, exactly as its checks put it (for example "no sector for KVUE") | A private chat | On any failure |
| The night's Alpha Vantage pull: how many tickers were tried, how they came back, and how many are left; a reminder to retire the job when the queue is empty | The private chat | Each night until the download ends |

**The channel is public on purpose.** The picks are already published in the repository each month,
so the channel reveals nothing new. Its value is that Telegram timestamps each post independently of
the repository, which shows the picks existed before their results were known. Anyone can read its
history in a browser, without an account. Operational alerts would only be noise there, so they go
to a private chat.

Every picks message ends with the same line: a research output, not advice; in backtests the model
didn't beat the plain 6-month rule, and neither clearly beat SPY per unit of risk.

A message that fails to send never fails the run, so the picks are saved either way. The bot only
sends: it never listens, so it needs no server.

### 3.6 Part 3: the data snapshots

Rebuilding this project from nothing takes an Alpha Vantage key and about nine nights of downloads
for the delisted companies. A snapshot removes that barrier, and gives the dashboard and the cloud
run one place to read from. There are **two snapshots**, because the price data isn't ours to give
away:

| | Private | Public |
| --- | --- | --- |
| **Contents** | Everything: the downloads, every table, the trained models | What this project computed: features and the member table with the raw price and volume columns removed, every model's out-of-sample scores, the live picks, the result tables |
| **Who can read it** | Anyone with access, by token: the cloud run, the dashboard, collaborators | Anyone, without an account |
| **Why** | Yahoo Finance's and Alpha Vantage's terms allow personal use and forbid redistribution | Returns, ranks, indicators and results are this project's own calculations; index membership (from Wikipedia) and the economic series (US government data) can be shared with attribution |

With access to the private snapshot, the whole pipeline after the downloads runs without any
source or key. Everyone else can follow and check the analysis from the public tables, and rebuild
the prices with their own access.

**Every upload is checked first.** Before anything is sent, every file is scanned for the project's
secrets (the API key and the tokens). If one is found, the upload is refused, and only the file's
name is reported. A leaked token can't be removed from a dataset's history, only revoked. The first
scan covered 700 files and found none.

**What was verified:**
- the private snapshot is private (an anonymous request is refused), and complete;
- the public one opens without an account, and none of its tables has a raw price column;
- a download of the private snapshot matched the local files byte for byte (700 of 700).

Each upload is a commit in the dataset's history. The final snapshot after the last rebuild will be
tagged, so the numbers in this book can always be traced to the exact data behind them.

### 3.7 Part 4: the live dashboard

A public web page, **[sp500-momentum-winners.streamlit.app](https://sp500-momentum-winners.streamlit.app/)**,
shows the project at a glance and keeps itself up to date:

| Tab | Shows |
| --- | --- |
| Overview | The idea, what the backtests found, "research output, not advice" |
| This month's picks | Both lists, with sectors and scores, and the date to trade at |
| Live record | Each live month's return for both strategies against SPY's, how many picks beat it, and the base rate. Empty until January 2027, and it says so |
| Backtest | $10,000 month by month, for the test years or 2020–2022, and the summary table: the same numbers as Chapter 7 |
| Model monitoring | **Input drift** for the model's ten most important stock-level inputs, and the live hit rate once months accrue |

**It reads only the public dataset,** so the page holds no secret and shows only public data. Each
monthly run pushes new tables there, and the page picks them up within six hours. The page never
downloads the large feature table: the run precomputes four small tables for it.

**Input drift is the monitoring that works before any result exists.** For each of the model's most
important inputs, the page compares this month's spread of values across stocks with the training
years' spread, using the Population Stability Index. It's the standard measure in credit and
model-risk work: under 0.1 is stable, 0.1–0.25 a moderate shift, over 0.25 a major one. A major
shift means the model is being asked about a market unlike the one it learned from, which is worth
knowing before trusting its picks. Market-wide inputs (such as SPY's last month) are left out:
they have one value per month, so a month has no spread to compare.

**The page's numbers match the book's.** Its test-year figures (the chosen rule 60.7% a year, the
6-month rule 33.0%, the headline model 4.1%, SPY 19.7%) are recomputed from the same simulation and
agree with Chapter 7.

**Where it's hosted.** The plan was Hugging Face Spaces, next to the datasets. Deploying found that
Spaces now host Streamlit only through paid plans (only static pages are free). It runs instead on
Streamlit Community Cloud, Streamlit's own free host, straight from the public repository. Because
the page reads its data from the dataset rather than bundling it, moving hosts changed no code.
An idle page sleeps; the next visitor wakes it in about half a minute.

**Found while building it: two inputs were one.** The drift chart showed two volatility inputs with
exactly the same score. One turned out to be exactly 100 times the other. Both are average true
range divided by the price, so they're the same number rescaled. It's the same kind of copy dropped
earlier for three other indicators, and it's removed before the final rebuild. The same check showed
that two chart labels had wrongly called such inputs "in dollars". Every price-like indicator here
is divided by the price, so none is in dollars.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Publish both the headline model's and the 6-month rule's picks | Either one alone would hide something: the finding, or the choice made in advance |
| Refit monthly with fixed settings; never re-tune | Fitting uses new data; tuning on live months would quietly turn the live record into another tuning loop |
| The same one-month gap as the backtest | Live picks come from exactly the method that was tested |
| Re-download whole price histories for active stocks | Appending would mix two dividend adjustments |
| First weekday of the month, 07:00, with catch-up | The month-end data is final, and the picks are ready before the open |
| Fail loudly on an incomplete month, a missing sector or changed columns | An automated run has nobody watching; stale or mis-shaped data must stop it |
| Picks to a public channel; failures and the nightly pull to a private chat | The public message is the project's face and an independent timestamp; operational alerts are for the operator |
| Last month's live result in each message, scored from the next open to the month-end close | That's the honest live record; it's ready on the first weekday of the next month, before the backtest's next-open-to-next-open return could be |
| A failed message never fails a run | Notifications report on the job; they must never become a reason it fails |
| A private full snapshot and a public derived one | Reproducible for anyone given access, open for everyone else, and within the price vendors' terms |
| Every upload scanned for secrets first | A leaked token can only be revoked, never removed from the history |
| A preview snapshot now, the final one tagged after the last rebuild | The dashboard and cloud run can be built on real files now; the book's numbers stay traceable |
| A dashboard that reads only the public dataset | No secret on a public page; it can't show licensed prices by mistake |
| Drift measured on stock-level inputs only | A market-wide input has one value a month: nothing to compare |
| Hosted on Streamlit Community Cloud | Free and made for this; Hugging Face now charges for Streamlit hosting |

---

## 5. Caveats

- **The picks are a research output, not advice.** The backtest found that the model doesn't beat a
  plain 6-month rule, and that nothing chosen in advance clearly beats SPY per unit of risk.
- **The run depends on free sources** (Wikipedia, Yahoo, FRED), which can change format or limit
  requests. The checks catch an incomplete month, not every possible error in the data.
- **The live result is measured slightly differently from the backtest:** from the next open to the
  following month-end close, rather than to the open after it. The difference is one overnight
  move, the price of reporting on the first weekday of the month.
- **It runs on one computer for now.** A copy in the cloud, so it doesn't depend on the computer
  being on, is a separate step.
- **New companies need their price history and sector.** Additions to the index are picked up from
  the current list automatically. Removals need their sector filled in by hand, and the run says so.
