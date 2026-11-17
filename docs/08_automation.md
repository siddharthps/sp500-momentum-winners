# Chapter 8: Automation

> **Sections:** each run (3.1), what gets published (3.2), who sees what (3.3), running it
> yourself (3.4), the run in the cloud (3.5).

## 1. Goal

Run the strategies **forwards**: each month, from fresh data, record what each would buy at the next
open, before the result is known. That record is the one test no choice in this project could have
touched.

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

**It runs in the night after a month's last close** (the Sunday night, when a month ends at a
weekend), before the next open, so the golden rule holds: features at the month-end close, the trade
at the next open. If that run can't finish (prices not yet complete, or a service down), the next
night tries again, after the open: those picks use the same month-end data, so nothing leaks, but
they couldn't have been traded, so they're kept in the record and left out of the live result. It
runs on GitHub's servers (Section 3.5), so it doesn't depend on any one computer being on.

---

## 3. What came out

### 3.1 Each run, step by step

- **Prices are downloaded whole, not appended.** A dividend or split changes every earlier adjusted
  price, so new days can't simply be added to old ones. Each active stock's full history is fetched
  again (about a minute); removed companies' histories don't change.
- **Nothing is picked until the month is complete.** The run stops, publishes nothing and says why
  if:
    - the latest month-end isn't the month's last trading day (the download hasn't caught up; the
      three holidays that can fall on a month's last weekday are allowed for);
    - SPY has no close, or fewer than 95% of members have a price;
    - a member has no sector (a company that has just left the index needs one added by hand);
    - the feature columns differ from the ones the model was trained on.
- **The model is refitted, never re-tuned.** Its settings were tuned on 2014–2019 and the model
  chosen on 2020–2022 (Chapter 6), and they stay frozen. Each month it relearns from every month
  with a known result, with the backtest's one-month gap. It's the backtest's own code: run as of
  January 2023, it reproduces the backtest's scores for all 501 members to the last decimal
  (rechecked on the final data, 16 Nov 2026).

### 3.2 What gets published

Each month, two lists of ten, with their scores: the **headline model's** (the model chosen in
advance) and the **6-month rule's** (which beat it in every test). Showing only the model would hide
the project's own finding; showing only the rule would drop the choice made in advance. Side by
side, they're a live head-to-head.

The rule chosen in Chapter 7 (the top 5 by 6-month return, held six months) isn't published. The
live record compares one thing, how stocks are chosen, so the rule appears in the model's form: ten
names, held one month. Tracking more rules would make the live record another place to pick a
winner from.

The first file, for October 2026, was made on 5 November: after the open it would have traded at,
and before the final rebuild. It uses only data to 30 October, so nothing leaks, but it couldn't
have been traded and doesn't come from the frozen model; its timestamp sets it apart. The first
truly live picks are made on 1 December 2026.

### 3.3 Who sees what

| Where | What | Who |
| --- | --- | --- |
| **Public Telegram channel** | Both lists, the month's index changes and the share of members priced; from January 2027, also how last month's picks did against SPY | Anyone, in a browser |
| **Private Telegram chat** | Why a run stopped, in its checks' own words, or that publishing failed (the picks are kept) | The project's owner |
| **[Dashboard](https://sp500-momentum-winners.streamlit.app/)** | This month's picks, the live record (from January 2027), the backtest (as in Chapter 7) and input drift | Anyone |
| **Public dataset** (Hugging Face) | This project's own numbers: the member table and features without raw prices, model scores, live picks, results | Anyone |
| **Private dataset** (Hugging Face) | Everything, including the vendors' prices (they may be used but not redistributed) and the trained models | The cloud run, by token |

- **The channel is public on purpose:** Telegram timestamps each post, proof the picks existed
  before their results. Every picks message says it's research, not advice. The bot only sends,
  so it needs no server.
- **Input drift is the one check that works before any live result:** do this month's values of the
  model's ten most important stock inputs look unlike the training years'? (A Population Stability
  Index above 0.25 is a major shift.) The dashboard reads only the public dataset and picks up each
  run within six hours.
- **The datasets save a rebuild from nothing,** which takes an Alpha Vantage key, a FRED key and
  twelve nights of downloads. Every upload is scanned for the project's secrets first, because a
  leaked token can't be removed from a dataset's history. The data this book reports is tagged
  `final-2026-11b` (an earlier tag, `final-2026-11`, is the rebuild before two data fixes); the
  monthly uploads don't move it.

### 3.4 Running it yourself

- **One notebook walks through the whole workflow** (data, rebuild, predict, simulate, the latest
  trades) by calling the monthly run's own functions, so it can't drift from what runs unattended.
  It has no side effects (no message, no upload, no write to the live record), so pressing "run all"
  can't change the public record. One setting picks the data: local files, the private dataset, or
  a fresh download. Retuning is off by default, so it runs in about two minutes, not two hours.
- **A container image** gives anyone the tested environment on any machine with Docker. It's built
  from the exact package versions the tests passed with, and holds no data or secrets (it's public;
  they're supplied at run time). Its tests run inside it on every change that could affect it, it's
  republished each time such a change is accepted, and every build is scanned for known
  vulnerabilities. It's about 2.9 GB, mostly scientific libraries.

### 3.5 The run in the cloud

The first truly live picks come after this project ends, and the record is only worth something if
no month is missed. So the run lives on GitHub's servers, not on one computer:

- **Each night it first checks whether last month's picks are in the running record.** Usually they
  are, and it stops within a minute. The night after a month's last close (Section 2) they aren't,
  so it rebuilds from the private dataset plus fresh prices and runs the five steps.
- **A separate alarm clock starts it.** GitHub's scheduler can run hours late (about seven in the
  first week here) or drop a run, so a small script on Cloudflare starts the job each night, with
  GitHub's own schedule as a backup an hour later. Whichever runs second finds the month done, or
  tries again if the first failed.
- **"Done" comes from the running record,** which travels with the dataset, so a fresh machine knows
  what's been done and a month is never picked twice. A missed night is caught up on a later one,
  after the open, so those picks stay out of the live result (Section 2).
- **The picks are recorded before they're posted.** The running record is uploaded first, and the
  picks go to the public channel only once it's there. If that upload fails, nothing is posted, the
  private chat is told, and the next night tries again, so a month is posted at most once.
- **Failures are loud.** Downloads are retried with longer waits; if prices are still incomplete,
  the checks stop the run, nothing is published, and the private chat is told. The same happens if
  the job fails to start or the FRED key is missing.
- **Its keys** (Hugging Face, Telegram, FRED) live in the repository's secret store, never in the
  code or the logs, and the job can only read the repository, not change it.

---

## 4. Decisions and why

| Decision | Why |
| --- | --- |
| Refit monthly with fixed settings; never re-tune | Fitting uses new data; tuning on live months would quietly turn the live record into another tuning loop |
| Last month's live result in each message, scored from the next open to the month-end close | That's the honest live record; it's ready on the first weekday of the next month, before the backtest's next-open-to-next-open return could be |
| A failed message never fails a run | Notifications report on the job; they must never become a reason it fails |

---

## 5. Caveats

- **The picks are a research output, not advice.** The backtest found that the model doesn't beat a
  plain 6-month rule, and that nothing chosen in advance clearly beats SPY per unit of risk.
- **The run depends on free sources** (Wikipedia, Yahoo, FRED, whose archive of past versions needs
  a free key), which can change format or limit requests. The checks catch an incomplete month, not
  every possible error in the data.
- **The live result is measured slightly differently from the backtest** (to the month-end close,
  not the next open): one overnight move, the price of reporting on the first weekday.
- **The job relies on two outside services staying up:** GitHub, which runs it, and Cloudflare,
  which starts it. GitHub switches jobs off in quiet public repositories after 60 days; the trigger
  switches this one back on each night. Its access token expires on 16 Nov 2027: if it isn't
  renewed, GitHub's own schedule still runs the job, but only until that 60-day switch-off.
- **Companies that leave the index need their sector added by hand.** Additions are picked up from
  the current list automatically. Until a removed company's sector is filled in, the run stops and
  names it.
