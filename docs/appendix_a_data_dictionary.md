# Appendix A: Data dictionary

Every column of the final table: **one row per S&P 500 member per month-end**, from January 2010.
The table has 186 columns: 10 identifiers and prices, 24 targets, and the 152 features a model can
use. [Chapter 4](04_features.md) explains why each group of features exists. This appendix says
exactly what each column holds.

> **The golden rule applies to every input.** It uses only what was known at the month-end close of
> its own row's date. Ranks and percentiles compare members on the same date only. Economic figures
> are used only once they had been published.

**How to read the time windows.** All inputs are built from **monthly bars** (each month's open,
high, low, close and volume), for every stock alike, so "14 periods" means 14 months. Returns are
adjusted for dividends and splits. "The decision month" is the month that ends on the row's date.

---

## 1. Identifiers and prices

| Column | What it holds |
| --- | --- |
| `date` | The decision date: the last trading day of the month |
| `month` | The same month as text (year-month) |
| `ticker` | The member's ticker in the index records on that date |
| `price_ticker` | The ticker whose prices are used. Usually the same as `ticker`; it differs after a repaired rename, where a company's history continues under its new symbol |
| `source` | Where the prices come from: daily prices, or monthly-only prices for companies that left the index and have no daily history |
| `has_price` | Whether a price was found for this member and month. Members without one stay in the table, so the gap can be measured |
| `close_adj` | The month-end close, adjusted for dividends and splits |
| `entry_px` | The price a decision can actually trade at: the next trading day's adjusted open. For monthly-only stocks, the month-end adjusted close, the closest price they have |
| `dollar_vol` | The median daily trading value (price × volume) in the month. Used to spot a ticker that now belongs to a much smaller company. Blank for monthly-only stocks |
| `sector` | The company's sector (11-sector scheme), its final one for companies that left. See [Chapter 4](04_features.md) for how sectors were found |

The public dataset leaves out `close_adj`, `entry_px`, `dollar_vol` and `source`: those are the
price vendors' own data. Every return and feature derived from them is included.

---

## 2. Targets: what happened next (24 columns)

These are the answers a model is judged on, never its inputs. Each comes in four holds, **X = 1, 3,
6 or 12 months**:

| Column | What it holds |
| --- | --- |
| `fwd_ret_Xm` | The stock's return over the next X months, from `entry_px` now to `entry_px` X months later. Blank when the end of the hold is beyond the data |
| `fwd_trunc_Xm` | True when the stock's prices end during the hold (it was delisted). The position is then valued at its last price and held as cash for the rest, as a real holder would have been paid out |
| `spy_fwd_ret_Xm` | SPY's return over the same X months, measured the same way |
| `fwd_excess_Xm` | The stock's return minus SPY's |
| `is_beat_spy_Xm` | 1 if the stock beat SPY over the hold, 0 if not. **The models' main target is `is_beat_spy_1m`** |
| `is_top_decile_Xm` | 1 if the stock's return was in the top 10% of that month's members |

---

## 3. Past returns (5 columns)

The plain rule's signals: how much the stock rose.

| Column | What it holds |
| --- | --- |
| `ret_1m` | Return over the decision month |
| `ret_3m`, `ret_6m`, `ret_12m` | Return over the past 3, 6 and 12 months |
| `ret_12_1m` | Return from 12 months ago to 1 month ago, skipping the latest month. The standard momentum measure in research, because the latest month tends to reverse |

---

## 4. Technical indicators (52 columns)

Standard technical indicators with their usual settings, applied to monthly bars. Indicators that
come out in dollars or shares are made comparable between a $20 and a $500 stock: price-like values
are divided by the close, and running volume totals become their 12-month change relative to 12
months of volume.

**Trend and momentum**

| Column | What it holds |
| --- | --- |
| `ta_adx`, `ta_adxr`, `ta_dx` | Trend strength (Average Directional Index over 14 months, its smoothed version, and the raw directional movement index) |
| `ta_plus_di`, `ta_plus_dm`, `ta_minus_dm` | The upward and downward parts of that trend measure (the "dm" ones ÷ price) |
| `ta_aroon_up`, `ta_aroon_down`, `ta_aroonosc` | How recently the 14-month high and low were set, and their difference |
| `ta_apo`, `ta_ppo` | The gap between a 12- and a 26-month average price (÷ price, and in percent) |
| `ta_macd`, `ta_macd_signal`, `ta_macd_hist` | MACD (12- vs 26-month averages), its 9-month signal line, and the gap between them, all ÷ price |
| `ta_macdext`, `ta_macdext_signal`, `ta_macdext_hist` | The same, from the configurable version of MACD with its standard settings |
| `ta_macdfix`, `ta_macdfix_signal`, `ta_macdfix_hist` | The same, from the fixed 12/26 version |
| `ta_mom` | The price change over 10 months ÷ price |
| `ta_roc` | The rate of change over 10 months, in percent |
| `ta_trix` | The rate of change of a triple-smoothed 30-month average. The slowest indicator, so the most often blank for recent listings |
| `ta_bop` | Balance of power: where the month closed relative to its open, within its range |

**Overbought and oversold**

| Column | What it holds |
| --- | --- |
| `ta_rsi` | Relative Strength Index over 14 months (0–100) |
| `ta_cmo` | Chande Momentum Oscillator over 14 months (−100 to 100) |
| `ta_cci` | Commodity Channel Index over 14 months: distance from the average typical price |
| `ta_stoch_k`, `ta_stoch_d` | Slow stochastics: where the close sits in its recent range, smoothed |
| `ta_stochf_k`, `ta_stochf_d` | Fast stochastics: the same, less smoothed |
| `ta_stochrsi_k`, `ta_stochrsi_d` | Stochastics applied to the RSI |
| `ta_willr` | Williams %R over 14 months: the close relative to the high–low range (−100 to 0) |
| `ta_ultosc` | Ultimate Oscillator: buying pressure over 7, 14 and 28 months combined |
| `ta_mfi` | Money Flow Index over 14 months: an RSI weighted by volume |

**Volume**

| Column | What it holds |
| --- | --- |
| `ta_obv` | On-balance volume: its change over 12 months ÷ 12 months of volume |
| `ta_ad` | The accumulation/distribution line: its change over 12 months ÷ 12 months of volume |
| `ta_adosc` | The accumulation/distribution oscillator (3- vs 10-month) ÷ average monthly volume |

**Volatility**

| Column | What it holds |
| --- | --- |
| `ta_atr` | Average true range over 14 months ÷ price: the typical monthly range |
| `ta_natr` | The same in percent. A rescaled copy of `ta_atr`, removed in the final run |

**Cycles** (Hilbert transform; these need about five years of history)

| Column | What it holds |
| --- | --- |
| `ta_ht_dcperiod`, `ta_ht_dcphase` | The length and phase of the dominant price cycle |
| `ta_ht_phasor_inphase`, `ta_ht_phasor_quadrature` | The two parts of that cycle ÷ price |
| `ta_ht_sine`, `ta_ht_leadsine` | The sine of the cycle and a leading version |
| `ta_ht_trendmode` | 1 if the price is trending, 0 if it's cycling |

**Price position within the month**

| Column | What it holds |
| --- | --- |
| `ta_avgprice` | The average of open, high, low and close, relative to the close |
| `ta_medprice` | The midpoint of high and low, relative to the close |
| `ta_typprice` | The average of high, low and close, relative to the close |
| `ta_wclprice` | The weighted close (close counted twice), relative to the close |

---

## 5. Stock risk, position and volume (22 columns)

| Column | What it holds |
| --- | --- |
| `vol_3m`, `vol_12m` | Volatility: the standard deviation of monthly returns over 3 and 12 months |
| `downside_vol_12m` | Volatility of the losing months only, over 12 months |
| `beta_36m` | Beta to SPY over 36 months (at least 24): how much the stock moves with the market |
| `ivol_36m` | Idiosyncratic volatility: how much the stock moves on its own, after its market part is removed |
| `drawdown_12m` | How far the close is below its highest close of the past 12 months |
| `drawdown_ath` | How far the close is below its highest close in the data (from 2000) |
| `dist_high_12m`, `dist_low_12m` | The close relative to the 12-month high and low |
| `ma3_ratio`, `ma10_ratio` | The close relative to its 3- and 10-month average |
| `above_ma10` | 1 if the close is above its 10-month average (a common trend rule) |
| `up_months_12m` | The share of the past 12 months that rose |
| `ret_1m_z` | Last month's return in units of the stock's usual volatility (the 12 months before) |
| `range_1m` | The month's high-to-low range ÷ close |
| `max_ret_12m` | The best single month of the past year: separates one big jump (often takeover news) from a steady climb |
| `log_dollar_vol` | The month's trading value, on a log scale: a size and liquidity measure |
| `dollar_vol_ratio` | The month's trading value relative to its average over the year before: a volume spike |
| `div_yield_12m` | Dividends paid over the past year ÷ price |
| `mom_12_1m_per_vol` | The 12-1 month return ÷ 12-month volatility: momentum per unit of risk |
| `resid_mom_12_1m` | Residual momentum: the 12-1 month return after removing the market's part, scaled by its own volatility |
| `seasonality_5y` | The stock's average return in next month's calendar month over the past 5 years (at least 3) |

---

## 6. Compared with other members (17 columns)

Each compares the stock with the other members **on the same date**.

| Column | What it holds |
| --- | --- |
| `rank_ret_1m`, `rank_ret_3m`, `rank_ret_6m`, `rank_ret_12m`, `rank_ret_12_1m` | The percentile of each past return among that month's members (1 = the top) |
| `sector_rank_ret_1m`, `sector_rank_ret_12_1m` | The same, within the stock's sector |
| `rs_spy_1m`, `rs_spy_12m` | Return over 1 and 12 months minus SPY's |
| `rs_sector_1m`, `rs_sector_12m` | Return over 1 and 12 months minus its sector fund's |
| `breadth_above_ma10` | The share of members trading above their 10-month average: how broad the market's rise is |
| `dispersion_1m` | The gap between the 90th and 10th percentile of members' monthly returns: how far apart winners and losers are |
| `winners_excess_1m` | How last month's top 10 by return did this month, versus SPY: is momentum working right now? |
| `winners_excess_12m` | The same, averaged over the past 12 months |
| `new_member_12m` | 1 if the stock joined the index within the past year |
| `months_in_index` | Months since its latest addition to the index, capped at 120 (10 years or more) |

---

## 7. Market (24 columns)

One value per month, the same for every member, except the sector fund, which follows the stock's
sector.

| Column | What it holds |
| --- | --- |
| `mkt_spy_ret_1m`, `_3m`, `_6m`, `_12m` | SPY's return over 1, 3, 6 and 12 months |
| `mkt_dji_ret_1m`, `_3m`, `_6m`, `_12m` | The Dow Jones Industrial Average, the same windows |
| `mkt_gold_ret_1m`, `_3m`, `_6m`, `_12m` | Gold futures, the same windows |
| `mkt_wti_ret_1m`, `_3m`, `_6m`, `_12m` | Crude oil (WTI) futures, the same windows |
| `mkt_dgs10_chg_1m`, `_3m`, `_12m` | The change in the 10-year Treasury yield over 1, 3 and 12 months |
| `sector_etf_ret_1m`, `_3m`, `_12m` | The return of the stock's sector fund. Real Estate uses the financials fund before its own started (2015), and Communication Services uses SPY before 2018 |
| `vix` | The VIX, the market's expected volatility, at the month-end |
| `vix_pct_60m` | Where that VIX level sits within the past 5 years (0–1) |

---

## 8. Economy (9 columns)

Used only once published: a monthly figure is used from the end of the following month, and a daily
yield from the next day.

| Column | What it holds |
| --- | --- |
| `cpi_yoy`, `cpi_mom` | Core inflation (prices excluding food and energy): change over 12 months and over 1 month |
| `fedfunds` | The Fed Funds rate (the previous month's average) |
| `dgs1`, `dgs5`, `dgs10` | The 1-, 5- and 10-year Treasury yields |
| `yield_slope_10_1` | The 10-year yield minus the 1-year: the slope of the yield curve |
| `gdppot_yoy`, `gdppot_qoq` | Growth of potential GDP (the economy's estimated capacity) over a year and a quarter. A projection that gets revised; only the latest version exists, a mild look-ahead accepted and stated in [Chapter 4](04_features.md) |

---

## 9. Flags (23 columns)

| Column | What it holds |
| --- | --- |
| `month_of_year_01` … `month_of_year_12` | 1 for the decision month's calendar month, else 0: for seasonal effects |
| `sector_is_communication_services`, `sector_is_consumer_discretionary`, `sector_is_consumer_staples`, `sector_is_energy`, `sector_is_financials`, `sector_is_health_care`, `sector_is_industrials`, `sector_is_information_technology`, `sector_is_materials`, `sector_is_real_estate`, `sector_is_utilities` | 1 for the stock's sector, else 0 |

---

## 10. Other tables

The project also keeps a few smaller tables alongside the main one:

| Table | What it holds |
| --- | --- |
| Model scores | Each model's out-of-sample score for every member and month from 2014, from a model that never saw that month |
| Strategy returns | The monthly returns of every simulated strategy and of SPY, used by the dashboard |
| The live record | Each month's live picks, and how they did once the month was over |
| Monitoring | How far this month's inputs have drifted from what the live model was trained on |
