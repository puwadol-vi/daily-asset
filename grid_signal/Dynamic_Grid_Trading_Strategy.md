# Dynamic Grid Trading Strategy — sourced from video research

This is a research write-up, not a coded spec yet — no `grid_signal/main.py` exists. Every rule
and number below was extracted from 3 YouTube videos via NotebookLM (see `link.txt`), which form
a single creator's 3-part series: concept → backtest/validation → hyperparameter optimization.
Each claim is tagged `[V1]` / `[V2]` / `[V3]` — see **Sources** at the bottom for titles/URLs.
This is different from `strategy/Grid_Option_Hedge_Strategy.md` (a separate, fixed-range S/R +
option-hedge grid) — this doc covers a _volatility/regime-adaptive_ grid instead.

---

## Overview

Traditional ("linear") grid bots use fixed 1–2% spacing between buy/sell levels, which works only
in sideways markets and gets destroyed (80–90% drawdown) when price trends hard in one direction
`[V1]`. A **Dynamic / Adaptive Grid** instead reconstructs its own structure — zone width, order
spacing, position size, and buy/sell frequency — based on the current **volatility regime** and
**momentum (trend strength)**, so the same system survives sideways, trending, high-vol, and
low-vol conditions without manual re-tuning `[V1] [V2]`.

---

## Raw data / inputs

- **Price series only, effectively** — cleaned OHLC candles from a data API. `[V2]` names **FMP
  (Financial Modeling Prep)** as the preferred paid/cleaned source, with **YFinance** as a free
  fallback for daily data (not used for the grid runs, which need intraday). No order book,
  funding rate, or volume feed is described as a primary input — `[V2]` explicitly notes
  "liquidity" and "momentum" matter to the strategy but does **not** detail those being ingested
  as separate raw data streams the way price is `[V2]`.
- **Granularity tested**: 15m, 30m, 60m — **60m is what the real report used for BTC** `[V2]`.
- **Three data modes**: historical (backtest), real-time (forward/paper testing), and synthetic
  (generated for stress-testing — see Validation methodology below) `[V1] [V2]`.

---

## Grid Setup

| Element                        | Rule                                                                                                                              | Source        |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| Range basis                    | Not a fixed price range — set from **Price Distribution** / **Price Profile** analysis of the asset, not a manually-drawn S/R box | `[V1]`        |
| Grid spacing ("Zone Distance") | Variable, not a flat 1–2% — recalculated as volatility regime changes                                                             | `[V1]` `[V2]` |
| Baseline test config           | 10-level grid, 10% zone up / 10% zone down (20% total range)                                                                      | `[V2]`        |
| Improved config (winner)       | 15% zone up / 15% down = **30% total range** — outperformed the 10% baseline                                                      | `[V2]`        |
| Bayesian-optimized zone        | **Grid Zone = 29.29%** (search range tested: 2%–30%)                                                                              | `[V3]`        |
| Trading mode                   | Bidirectional (simultaneous buy + sell) outperformed buy-only/sell-only in both `[V2]` and `[V3]`'s best runs                     | `[V2]` `[V3]` |

---

## What makes it "dynamic"

- **Regime-driven reconstruction**: grid structure changes automatically when the **volatility
  regime** shifts — not continuously micro-adjusted, but re-cut when a regime change is detected
  (one test ran only 2 distinct grid structures across a full year) `[V1]` `[V3]`.
  - **What actually drives the regime read**: a **"Volatility Factor"** derived from **Historical
    Volatility** (volatility computed from past price data), combined with the **Safety Factor**
    to add forward-looking headroom for volatility not yet seen `[V2]`. No transcript gives the
    exact formula (e.g. a lookback window length or a specific ratio/threshold) — the real
    report's `atr_window: 5` / `atr_baseline_window: 100` fields (see below) are a plausible
    concrete implementation of "Historical Volatility" (short ATR vs. its own long-run baseline),
    but that mapping is our inference, not something either video states directly.
  - **Trigger condition described in words, not formula**: reconstruction fires when price moves
    from a low-volatility "sideways" state into a "high volatility"/"sell-off" state (and back)
    `[V2]`. Confirmed via a **momentum check** ("state-based" / "time series momentum") before the
    system actually re-enters positions in the new structure `[V2]`.
  - **P-level construction**: the zone is divided into N "slots"/"channels" (e.g. 10); in the
    dynamic version slot spacing is uneven and varies by regime, but no formula for the exact
    variance is given `[V1]`.
  - **Price Distribution / Price Profile**: built from a historical price distribution over a
    lookback window, then classified into Trend/Momentum/Volatility states to inform where the
    zone gets drawn `[V1]`. No bin count, percentile cutoff, or window length is stated — see
    `LOGIC.md`'s "How each core concept is actually calculated" table for the full breakdown of
    what's sourced vs. inferred for every core term (P-level, Distribution/Profile, Volatility,
    Zone Distance, Momentum).
  - Caution: a later broad query returned "0.29%" and "4.10%" as example zone-width figures —
    these don't match the directly-sourced 29.29% zone / 4.10–4.3 Sortino target established
    earlier in this doc and are most likely NotebookLM misreading the same digits out of context.
    Not incorporated above; treat the earlier, source-scoped answers as authoritative.
- **Momentum filter**: Time-Series Momentum / trend strength gates order entries — in a strong
  down-move (e.g. BTC $100k → $60k), buy orders are slowed or paused entirely rather than
  "catching a falling knife" `[V1]` `[V2]`.
- **Sideways behavior**: in low-volatility/ranging conditions, the grid uses narrower sub-zones
  and higher trade frequency — this is the grid's "sweet spot" for cash flow `[V1]` `[V2]`.
- **Zone Bundling / Anticlustering**: prevents multiple orders from stacking at the same price
  level (avoids "sunk cost" pile-ups that a hard downtrend then traps) `[V1]` `[V2]`.

---

## Capital & position sizing

| Parameter                              | Value tested                                                                   | Source |
| -------------------------------------- | ------------------------------------------------------------------------------ | ------ |
| Starting capital (backtest)            | $5,000                                                                         | `[V2]` |
| Allocation per trade (baseline)        | 20%                                                                            | `[V2]` |
| Risk per Trade (Bayesian search range) | 10%–45%                                                                        | `[V3]` |
| Risk per Trade (optimal)               | **25% (0.25)**                                                                 | `[V3]` |
| Safety Factor                          | 1.0 baseline vs. **2.0** for forward-looking / uncertain-volatility protection | `[V2]` |

Position size and order frequency are **not equal across zones** — they scale with the local
volatility/momentum read for that zone, not a flat per-level split `[V1]`.

---

## Entry / exit rules

- No standard technical indicators (RSI, MACD) gate entries — logic runs on **Price Levels
  (P-levels)** and price distribution/profile instead `[V1]`.
- Entry requires a momentum-filter confirmation, not just "price touched the level" `[V2]`.
- Modes supported: Buy-only, Sell-only, Bidirectional — bidirectional won in both backtests `[V2] [V3]`.
- **Take Profit** (exit), not a trailing stop, closes each position:
  - Baseline test: TP = 3% `[V2]`
  - Bayesian search range: 1%–10% `[V3]`
  - Optimal: **TP = 2%** (also cited as 2.28% in one trial) `[V3]`
- Rebound Beta: 0.5% (used for rebound/re-entry sizing) `[V2]`

---

## Risk management

- **No simple static stop-loss by default** — losing positions are managed via **cost adjustment**
  (blending down the effective cost basis using generated cash flow) plus limited stop-losses on
  positions that get "stuck" `[V2] [V3]`. `[V3]`'s AI agent flagged that adding an explicit stop-loss
  could further reduce worst-case single-trade losses — noted as a suggestion, not yet adopted.
- **Volatility & Momentum filters** pause new buy orders during sharp 20–30%+ moves to avoid
  being dragged into a trend `[V1] [V2]`.
- Objective functions used to judge "is this config good": **Sortino Ratio** and **Calmar Ratio**
  (favored over raw return) plus **Max Drawdown** and **CVaR** `[V2] [V3]`.
- Minimum bar for "ready to run": **Profit Factor > 1.5** `[V2]`.
- Never uses leverage or hedging/"square" tactics — described as a common cause of blown accounts
  when combined with a grid the trader doesn't fully understand `[V1]`.

---

## Tested parameters — ready to reuse (no need to re-derive)

These are numbers the creator already backtested/optimized across the 3 videos — useful as
starting defaults instead of running our own search from scratch.

| Parameter               | Baseline (V2)                      | Bayesian search range (V3) | Optimal found (V3)                                                |
| ----------------------- | ---------------------------------- | -------------------------- | ----------------------------------------------------------------- |
| Grid zone (total range) | 20% → improved to 30%              | 2% – 30%                   | **29.29%**                                                        |
| Risk per trade          | 20%                                | 10% – 45%                  | **25%**                                                           |
| Take profit             | 3%                                 | 1% – 10%                   | **2%** (2.28% in one trial)                                       |
| Safety Factor           | 1.0 / 2.0 (not re-optimized in V3) | —                          | —                                                                 |
| Trading mode            | Bidirectional beat one-sided       | —                          | Bidirectional                                                     |
| Grid levels             | 10 (fixed in V2's baseline)        | not respecified            | not respecified (2 regime-structures observed over the test year) |
| Rebound Beta            | 0.5%                               | —                          | —                                                                 |

**Result achieved with the V3 optimal set**: 76.89%–76.94% return vs. a BTC benchmark that fell
45.8% over the same 2025–2026 backtest window; Sortino Ratio peaked at 4.3 `[V3]`. V2's own best
(15%-zone, bidirectional, pre-optimization) run returned 56.14% over the same period with a 1.73
Sortino `[V2]` — the Bayesian pass in V3 is a meaningful improvement on the same core structure,
not a different strategy.

**Caveat**: neither video gives a candle interval/timeframe for these backtests, and the exact
grid-level count for the optimized (V3) run isn't stated — those two gaps need to be resolved
(re-ask NotebookLM, scoped to source `08068016` and `5fdf5476`, or check the creator's other
videos) before treating this table as a literal implementation config.

---

## Real hyperparameter field names + a documented baseline run

`[V2]`'s backtest tool shows an actual `GridTradingStrategy` config/report on screen. These are
the real field names — worth reusing verbatim if `grid_signal` ends up wrapping/porting this
strategy — plus one full example run at the **baseline** (non-optimized) settings, useful as a
concrete negative example: buy-only + 10% zone underperforms bidirectional + wider zone.

| Field | Value in this run | Notes |
|---|---|---|
| `ticker` | BTC-USD | |
| `timeframe` | **60m** | resolves the "candle interval not stated" gap below |
| `start_date` / `end_date` | 2025-08-01 → 2026-07-04 | matches the "2025–2026" window cited elsewhere |
| `use_synthetic` | False | this run used real historical data, not the synthetic stress-test path |
| `init_cash` | 5000.0 | matches `[V2]`'s $5,000 starting capital |
| `risk_pct` | 0.2 (20%) | = "Risk per Trade" / "Allocation per trade" baseline |
| `sl_safety` | 1.0 | = "Safety Factor" baseline (1.0, not the 2.0 robust variant) |
| `stop_loss` | None | confirms "no static stop-loss by default" |
| `take_profit` | 0.03 (3%) | matches baseline TP |
| `sl_trail` | False | no trailing stop |
| `n_grids` | 10 | matches the 10-level baseline |
| `rebound_beta` | 0.005 (0.5%) | matches |
| `trade_mode` | **buy_only** | not bidirectional — explains the weak result below |
| `grid_zone_pct` | 0.1 (10%) | matches the 10% baseline zone, not the 29.29% optimized one |
| `atr_window` | 5 | short ATR window — likely feeds the volatility-regime read |
| `atr_baseline_window` | 100 | long ATR window — `atr_window`/`atr_baseline_window` ratio is plausibly how "volatility regime" is detected, but this isn't confirmed by any transcript, only inferred from field naming |
| `stddev_period` | 10 | likely feeds zone-width/rebound calc |
| `cluster_threshold` | 0.005 | plausibly the "Anticlustering" logic's distance threshold |

**Result of this exact baseline+buy_only run** (not the winning config — shown for contrast):

| Metric | Value |
|---|---|
| Period | 2025-08-05 → 2026-07-05 (326 days) |
| Start / End value | $5,000 → $4,638.05 |
| Total Return | **-7.24%** |
| Benchmark Return | -45.13% (still beat buy-and-hold despite losing money outright) |
| Max Drawdown | 28.32% |
| Total Trades | 75 (74 closed, 1 open) |
| Win Rate | 44.6% |
| Profit Factor | 0.94 (below the >1.5 "ready" bar from `[V2]`) |
| Sortino Ratio | -0.20 |
| Calmar Ratio | -0.28 |

This is consistent with the doc's claim above that bidirectional + wider zone (15–29%) is what
makes the strategy actually profitable — `buy_only` + the narrow 10% zone is the "before" picture,
not something to copy as-is.

---

## Validation methodology (why these numbers are more trustworthy than a typical backtest)

- **Synthetic data / stress testing**: Stochastic-volatility-generated synthetic price paths (not
  historical data) — one run used 10,000 steps at 25% volatility / 1.25% drift starting at $5,000,
  simulating BTC crashing to $2,000. Result: 87% max drawdown but only 15% realized loss (matched
  the creator's predefined annual downside limit) `[V2]`.
- **In-sample / out-of-sample + synthetic-first**: parameters are tuned on synthetic data the
  model has never seen, _then_ validated against real 2025–2026 BTC data — in one case this
  produced a 20% real-data improvement over the synthetic-tuned baseline, i.e. it generalized
  rather than overfitting `[V3]`.
- **Optimization tooling**: Optuna (Bayesian optimization), 200–300 trials standard, up to 1,000
  for deeper runs; objective = Sortino or Calmar ratio, not raw return `[V3]`.
- **Platform**: built in Python on an IDE-like AI platform ("Any Gravity"), using an MCP server for
  data and Gemini 1.5 Pro (also supports Claude Opus/Sonnet) as the evaluating agent `[V2] [V3]`.

---

## Divergences between the 3 videos

- V1 is purely conceptual — no concrete tuned numbers, just the case for _why_ dynamic > linear
  grids. V2 and V3 supply the actual numbers.
- V2's "best" config (15% zone, 3% TP, no formal optimization) and V3's Bayesian-optimized config
  (29.29% zone, 2% TP) are **not the same run** — V3 is a later, more rigorous pass over the same
  underlying system, not an independently-designed alternative. Zone width nearly doubled and TP
  tightened once formal optimization was applied — worth treating V3's numbers as the stronger
  starting point, with V2 as the sanity-check baseline.
- Neither V2 nor V3 states the number of grid levels used in the _optimized_ run — V2's own
  baseline used 10, but V3 doesn't confirm whether that held after optimization.

---

## Open questions / not yet automated

- ~~Candle interval~~ — resolved: **60m**, confirmed by the real report above `[V2]`.
- Exact grid-level count for the *optimized* (V3, 29.29%-zone) run specifically is still not
  stated — the `n_grids: 10` value above is confirmed only for the baseline/buy_only report, not
  necessarily what the Bayesian-optimized bidirectional run used.
- No explicit stop-loss is used by default (`stop_loss: None` confirmed in the real report); V3's
  AI agent suggested adding one but this wasn't adopted in the reported results — decide whether
  `grid_signal` should include one.
- "Price Distribution" / "Price Profile" — the exact algorithm for turning these into concrete
  zone boundaries still isn't given as a formula in any transcript. The real report above narrows
  this down to 4 named inputs (`atr_window: 5`, `atr_baseline_window: 100`, `stddev_period: 10`,
  `cluster_threshold: 0.005`), but how they combine into a zone boundary / regime read is inferred
  from field naming, not confirmed by the videos — still the biggest gap before this becomes code
  (VPVR from `option_signal/main.py` remains a plausible reusable building block for the
  distribution/profile piece, but that's an assumption, not something sourced from these videos).

---

## Sources

| Video                                                                                     | URL                                         | Contribution                                                                    |
| ----------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| `[V1]` Introduction to Dynamic Grid Trading Strategy                                      | https://www.youtube.com/watch?v=vM1B_ekRycg | Concept: why adaptive > linear grids, regime/momentum framing, no tuned numbers |
| `[V2]` From Backtest to Verdict: AI Agents Evaluate a Bitcoin Dynamic Grid Trading System | https://www.youtube.com/watch?v=ox6GHbBseKw | First concrete backtest numbers, synthetic stress test, baseline config         |
| `[V3]` AI Agent + Bayesian Optimization: Automating Dynamic Grid Trading Hyperparameters  | https://www.youtube.com/watch?v=6zCpxOkk97Q | Optuna-optimized final parameter set, walk-forward/synthetic validation         |

_Not financial advice._
