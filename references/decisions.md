# Decisions log

The full discussion lives in [Project_Ideas_Brainstorm.md](Project_Ideas_Brainstorm.md). This file
keeps only what was decided and why.

## 2 Nov 2026

**Idea H: monthly winners on the S&P 500.** Buy last month's top performers, hold for X months, and
compare against SPY. An ML model ranks all members each month. The plain rule is the baseline.

**Start in 2010.** Wikipedia's change history is thin before ~2008 (43 changes in the 2000s versus
220 in the 2010s).

**Data sources**

| Data | Source | Why |
|---|---|---|
| Point-in-time membership | Wikipedia: current list + "Historical components of the S&P 500" | One request each, and it's free |
| Prices, current members and removed members still trading | yfinance (daily, adjusted) | Free, full daily history |
| Prices, removed members yfinance lacks | Alpha Vantage `TIME_SERIES_MONTHLY_ADJUSTED` | Free tier has full **monthly** history only. Full daily history is premium |

**Survivorship gap (members removed 2010 to Oct 2026):** 320 removed and not in today's list. yfinance
covers 107 of them. 213 are missing: 138 acquired, 44 market cap, 21 spin-offs, 3 failed banks, 4 ticker
changes, 3 other. Acquisitions matter most for this idea, because takeover jumps are a common reason
a stock is the month's top gainer.

**Alpha Vantage checks**

- Adjusted close includes dividends and splits (KO matched yfinance within 0.1%, 2005–2026).
- It has bought-out and failed names: TWTR, PXD, CMA, HOLX, SIVB.
- Some old tickers return the company that reused the symbol later (e.g. STI), and some return
  nothing (LEH, BBBY, FRC). Every pull is checked against the removal date (`validate()`).
- yfinance has the same reuse trap: `FB` now returns a different security.

**yfinance daily download (`yahoo-daily`)**

- **Universe: 623 tickers.** That's the 503 current members, 107 removed members yfinance covers, and
  13 benchmark series (SPY, the 11 SPDR sector ETFs and ^VIX).
- **Dates:** from 1 Jan 2007 (a 3-year warm-up for the 12- and 24-month features and the 200-day
  averages) to yesterday's close. Today's half-finished bar is never saved.
- **Columns:** unadjusted OHLC, adjusted close, volume, dividends and splits. The trade happens at the
  next open, so the adjusted open is rebuilt as `open × adj_close / close`.
- **Storage:** one parquet file per ticker in `data/raw/yahoo/daily/`, plus `_manifest.csv`.
  Reruns skip tickers that already have a file. `--refresh` downloads everything again.
- **First run:** all 623 `ok`, 2.84M daily rows, all ending 30 Oct 2026.

**Tooling:** Cookiecutter Data Science v2.3.0 layout, uv, Python 3.12, pytest, ruff. No Makefile
(Windows), so each step is a command in `sp500_momentum.dataset`.

**Repo:** private on GitHub while in progress, public near completion.
