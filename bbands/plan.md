# BBands BO [LuxAlgo] — Backtest Plan

## 1. Goal

An HTML report that lets the user pick:

- **Length** — 7, 8, 9, 10
- **Mult** — 0.10, 0.15, 0.20, 0.25
- **Entry rule** (long) / mirrored (short)
- **Exit rule** (long) / mirrored (short)
- **Side** — long only / short only / both

...and instantly see the resulting trade list + equity/drawdown, without re-running a backtest engine per click (576 combos = 4 × 4 × 3 × 4 × 3 is too many to precompute in full, so the UI computes the trade simulation on the fly from a lightweight precomputed signal table).

## 2. Indicator recap — BBands BO [LuxAlgo] (`bbands/script.txt`)

Weekly close (`src`), for a given `length`/`mult`:

```
stdev = ta.stdev(src, length) * mult
ema   = ta.ema(src, length)
upper = ema + stdev
lower = ema - stdev

# rolling window i = 0..length-1 (this bar back to length-1 bars ago)
bull_num += max(src[i] - upper[i], 0);  bull_den += abs(src[i] - upper[i])
bear_num += max(lower[i] - src[i], 0);  bear_den += abs(lower[i] - src[i])

bull = bull_num / bull_den * 100   # green line, 0-100
bear = bear_num / bear_den * 100   # red line,   0-100
```

`bull`/`bear` are 0 when no bar in the window broke the respective band.

## 3. The 8 primitives

The 3 entry-long + 4 exit-long conditions given, plus their short-side mirrors (swap green↔red), reduce to 8 weekly booleans. `G` = bull (green), `R` = bear (red); `_last`/`_this` = previous/current week.

| bit | primitive       | condition                                                                                 |
| --- | --------------- | ----------------------------------------------------------------------------------------- |
| 0   | `green_go_pos`  | `G_last == 0 and G_this > 0`                                                              |
| 1   | `red_go_pos`    | `R_last == 0 and R_this > 0`                                                              |
| 2   | `cross_up`      | `G_last < R_last and G_this > R_this`                                                     |
| 3   | `cross_down`    | `G_last > R_last and G_this < R_this`                                                     |
| 4   | `red_peak`      | `R_last > R_this`                                                                         |
| 5   | `green_peak`    | `G_last > G_this`                                                                         |
| 6   | `green_go_zero` | `G_last > 0 and G_this == 0`                                                              |
| 7   | `red_go_zero`   | `R_last > 0 and R_this == 0` _(added — mirror of `green_go_zero`, needed for exit_short)_ |

### Rule → primitive mapping

|              | Long            | Short (mirror) |
| ------------ | --------------- | -------------- |
| **Entry** #1 | `green_go_pos`  | `red_go_pos`   |
| **Entry** #2 | `cross_up`      | `cross_down`   |
| **Entry** #3 | `red_peak`      | `green_peak`   |
| **Exit** #1  | `green_peak`    | `red_peak`     |
| **Exit** #2  | `cross_down`    | `cross_up`     |
| **Exit** #3  | `green_go_zero` | `red_go_zero`  |
| **Exit** #4  | `red_go_pos`    | `green_go_pos` |

If you spot another useful primitive/rule later, it slots into this table without changing the pipeline shape.

## 4. Data pipeline

### 4.1 `bbands/raw_data.csv`

One row per weekly close.

```
close_date | bull_7_0.10 | bear_7_0.10 | bull_7_0.15 | bear_7_0.15 | ... | bull_10_0.25 | bear_10_0.25 | close_price
```

16 length×mult combos × 2 (bull, bear) = 32 value columns + `close_date` + `close_price`.

- Source: BTC/USDT weekly candles (assumption — confirm asset/exchange).
- Rows where a combo's EMA/stdev warm-up isn't complete (< `length` closed bars of history) are left blank/NaN for that combo's columns.

### 4.2 `bbands/process_data.csv`

One row per weekly close, one **bitmask integer column per combo** (per your choice):

```
date | 7_0.10 | 7_0.15 | 7_0.20 | 7_0.25 | 8_0.10 | ... | 10_0.25
```

Each cell = an 8-bit integer (0–255) built from the bit table in §3, computed from that combo's `bull`/`bear` columns in `raw_data.csv`. This is the only file the report reads at click-time — no re-deriving indicator math in the browser.

## 5. Backtest / simulation logic (runs client-side per parameter change)

**Inputs:** `length`, `mult` → picks the `process_data.csv` column. `entry_rule` (1–3), `exit_rule` (1–4), `side` (long / short / both).

**Position state machine, per week in order:**

1. If a position is open on a side, check that side's exit-rule bit for the current week.
   - If true → close at this week's `close_price`. Record the trade (entry date/price, exit date/price, % change, updated capital).
2. Immediately after (same week), check entry-rule bit for that side.
   - If true → open a new position at this week's `close_price` (same-week re-entry is allowed, per your answer).
3. Repeat next week.

**Side = both → hedge mode (per your answer):** long and short are tracked as two independent books, each running the state machine above on its own primitives (long book uses entry/exit-long bits, short book uses entry/exit-short bits), each starting from the same initial capital and compounding independently. The order list merges both books' closed trades sorted by date; each row is tagged `LONG`/`SHORT` so its `current capital` / `% drawdown` is read against the right book. (Flagging this as my resolution of an otherwise-undefined case — correct me if you want a single blended equity curve instead.)

**Capital model (per your answer):** 100% compounding, no fees/slippage.

- Start at `INITIAL_CAPITAL` (placeholder value — needs a number, e.g. 100 or 10,000).
- Each trade: `capital *= (1 + pct_change)`, where `pct_change = (exit_price - entry_price) / entry_price` for long, inverse sign for short.
- `% drawdown` = running `(capital - running_peak_capital) / running_peak_capital` evaluated at each trade close (per book, in hedge mode).

## 6. Report contents (per selection)

Order list table:

| entry date | entry price | exit date | exit price | % change | current capital | % drawdown | (side, if "both") |

Plus whatever summary header makes sense (win rate, total return, max drawdown) — not specified yet, can add.

## 7. Proposed file layout

```
bbands/
  script.txt                 # LuxAlgo source (already have)
  plan.md                    # this file
  raw_data.csv                # generated: weekly bull/bear/close per combo
  process_data.csv            # generated: 8-bit signal mask per combo
  generate_raw_data.py         # ccxt weekly OHLCV -> raw_data.csv
  generate_process_data.py     # raw_data.csv -> process_data.csv
  report.html                  # selectors + order-list table, reads process_data.csv (as JSON) client-side
```

## 8. Open assumptions to confirm before implementation

- **Asset/exchange:** BTC/USDT weekly candles via `ccxt` (Binance) — same convention as other modules. Confirm.
- **Week boundary:** Binance weekly candle close (Monday 00:00 UTC) — confirm this is the intended "close_date".
- **Initial capital value:** need an actual number for the `current capital` column starting point.
- **Hedge-mode display:** confirmed assumption above (two independent books) — flag if wrong.
