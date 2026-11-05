# Chapter 8: Automation

> **This draft covers Part 1, the monthly run.** Notifications, the live dashboard, the cloud run
> and the run-all notebook are added as they're built.

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

---

## 5. Caveats

- **The picks are a research output, not advice.** The backtest found that the model doesn't beat a
  plain 6-month rule, and that nothing chosen in advance clearly beats SPY per unit of risk.
- **The run depends on free sources** (Wikipedia, Yahoo, FRED), which can change format or limit
  requests. The checks catch an incomplete month, not every possible error in the data.
- **It runs on one computer for now.** A copy in the cloud, so it doesn't depend on the computer
  being on, is a separate step.
- **New companies need their price history and sector.** Additions to the index are picked up from
  the current list automatically. Removals need their sector filled in by hand, and the run says so.
