# Snowball Backtest — SMC BOS/CHoCH

Smart Money Concepts (BOS/CHoCH) strategy
(LuxAlgo's "Smart Money Concepts" Pine Script indicator) to Python. This is

---

## 1. How "small CHoCH" is actually calculated

Two structure detectors run side by side, identical algorithm, different
window size:

- **BIG** ("swing" in the original indicator) — 50-bar window.
- **SMALL** ("internal" in the original indicator) — 5-bar window (this is
  the one that drives the strategy; BIG is reference-only).

### Step 1 — pivot detection (the fractal)

A bar `size` bars back is confirmed as a **swing HIGH** once none of the
`size` bars _since_ it have made a higher high. Symmetrically, a bar `size`
bars back is confirmed as a **swing LOW** once none of the bars since it
have made a lower low. Concretely, at bar `i`:

```
candidate = i - size
new_leg_high = high[candidate] > max(high[i-size+1 .. i])   # nothing since beat it -> HIGH confirmed
new_leg_low  = low[candidate]  < min(low[i-size+1 .. i])     # nothing since beat it  -> LOW confirmed
```

This means confirmation always lags the actual peak/trough by **exactly
`size` bars** — deterministic, unlike a %-move zigzag (V8/V9) whose lag
varies with how fast price reverses. For SMALL (size=5), you always know
about a pivot exactly 5 days after it happened. Every confirmed pivot is
labeled **HH/LH** (vs. the previous confirmed high) or **HL/LL** (vs. the
previous confirmed low); the very first pivot of each kind is left
unlabeled (nothing to compare against yet).

### Step 2 — BOS vs CHoCH (the trend-bias state machine)

Each structure (BIG and SMALL, independently) keeps a running trend bias:
bullish, bearish, or none yet. On every bar, check whether close just
**crossed** back above the structure's current confirmed swing-high level
(today's close > level, yesterday's close <= level — a crossing event, not
just "currently above"), and that level hasn't already been used since it
was set:

- If the bias was **bearish** → label it **CHoCH** (a reversal).
- If the bias was **already bullish** → label it **BOS** (a continuation).
- Either way, bias becomes/stays bullish, and the level is marked "crossed"
  so it can't fire again until a fresh swing high replaces it.

Symmetric logic for a close crossing back _below_ the swing-low level
(bearish CHoCH/BOS). **"Small green CHoCH"** = SMALL registers a bullish
CHoCH. **"Small red CHoCH"** = SMALL registers a bearish CHoCH. SMALL BOS
events happen too (continuation, not reversal) but are logged for
reference only — the strategy only ever acts on CHoCH.

One extra rule: SMALL's crossing is suppressed if SMALL's level is
_exactly_ the same price as BIG's current level at that moment (smc.txt's
`extraCondition`) — avoids announcing the same level twice.

**Net effect on timing**: from the actual peak/trough to a usable SMALL
CHoCH signal, there are two lags stacked — a fixed 5-bar pivot-confirmation
lag, then a variable wait (0 to many bars) until price actually comes back
and crosses the confirmed level. The first is predictable; the second
isn't.

---

## 2. Strategy & money-management logic

### Entry / re-entry

Fires every time SMALL registers a bullish CHoCH ("small green CHoCH")
while flat. Margin = **50% of the current bank** (not a fixed $ amount) —
this is how gains and losses compound _across_ cycles, since every new
entry's size depends on what earlier cycles left in the bank. Skipped
entirely if the bank is at or below zero.

### Exit

Full close the moment SMALL registers a bearish CHoCH ("small red CHoCH")
while a position is open, **or** a real liquidation first if the day's low
reaches the liquidation price before a CHoCH fires (checked every bar,
independent of CHoCH). No compounding _within_ a cycle — one layer, never
added to, never partially reduced.

### Leverage — the current rule (validated by full re-simulation across all

5 assets × 2 scenarios = 10 cases, not just a bucket-level snapshot):

| Condition                              | Leverage |
| -------------------------------------- | -------- |
| Action Zone bearish at entry (any ADX) | **2x**   |
| Action Zone bullish + ADX14 ≥ 22       | **5x**   |
| Action Zone bullish + ADX14 < 22       | **10x**  |

- ADX14 at a CHoCH entry measures the strength of the trend that's just
  _ending_, not the one starting — high ADX at a reversal signal usually
  means you're catching a bounce inside an already-extended move. Measured
  correlation: `adx14_at_entry` vs. `%pnl` = **-0.36**.
- Action Zone (EMA12 vs EMA26) bearish at entry means the medium-term trend
  still disagrees with the fast SMALL reversal signal — lower-confidence
  setup. Bearish-zone entries underperform at _every_ ADX level tested.
- Because margin is 50% of the bank, a liquidation doesn't just cost that
  trade's margin — it permanently shrinks the base every later entry
  compounds from. That's why the red-zone cut was extended to _all_ ADX
  levels, not just low-ADX: re-simulating the narrower cut vs. the full cut
  showed the full cut wins 8 of 10 cases, some by a large margin.
- **Important methodology note**: several rejected alternatives looked
  _better_ in a naive bucket-level dollar-sum snapshot but were actually
  _worse_ once properly re-simulated end-to-end, because bucket sums don't
  capture how an early liquidation cripples all later compounding. Always
  trust the full re-simulation over an aggregate snapshot for this
  strategy — see `plan.md` for the specific case this bit us.

### Two scenarios per asset, auto-detected (not hand-picked)

- **Scenario A**: the first small green CHoCH on/after **2022-07-01**.
- **Scenario B**: the first small green CHoCH on/after **2023-01-01**.

(This rule was verified to exactly reproduce BTC's original hand-picked
dates — 2022-07-07 / 2023-01-08 — before being applied uniformly to
ETH/BNB/SOL/XRP.) Each scenario has its own independent starting bank
($2000), position state, and tradeable gate — they can diverge in position
state from their start date onward, sharing only the underlying
structure/CHoCH signals (computed once).

### Multi-asset

BTC, ETH, BNB, SOL, XRP via `ccxt` Binance spot OHLCV (1D). Same engine,
same leverage rule, same $2000 starting bank, applied independently per
asset — no cross-asset logic.

---

## 3. Every column/indicator explained

| Column                                                                       | What it is                                                                                                                                                                                                                                                                           |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `open/high/low/close/volume`                                                 | Raw daily OHLCV                                                                                                                                                                                                                                                                      |
| `pct_change`                                                                 | Day-over-day % change in close                                                                                                                                                                                                                                                       |
| `ema12` / `ema20` / `ema26`                                                  | Exponential moving averages. EMA20 is drawn on the candle chart as a plain reference line. EMA12 vs EMA26 is compared to derive...                                                                                                                                                   |
| `az_bullish`                                                                 | **Action Zone**: `True` if EMA12 >= EMA26 (bullish), `False` if not, `None` during EMA warmup. Precomputed in Python — feeds both the chart's Action Zone strip and the leverage rule. Reference only in the sense that it doesn't gate entries/exits, but it **does** set leverage. |
| `adx14` / `di_plus` / `di_minus`                                             | Raw ADX(14) and directional indicators. `adx14` feeds the leverage rule (threshold 22); `di_plus`/`di_minus` are reference-only (tested as an ADX alternative, found weaker — see `plan.md`).                                                                                        |
| `big_swing_high` / `big_swing_low`                                           | BIG structure's confirmed pivot prices, placed at the true peak/trough bar (not the later confirmation bar — that's a display choice, see Section 1's lag discussion)                                                                                                                |
| `big_pivot_label`                                                            | `HH`/`HL`/`LH`/`LL` for the BIG pivot at that bar                                                                                                                                                                                                                                    |
| `big_break`                                                                  | `BULL_BOS` / `BULL_CHOCH` / `BEAR_BOS` / `BEAR_CHOCH` — fires on the bar the crossing actually happens                                                                                                                                                                               |
| `small_swing_high` / `small_swing_low` / `small_pivot_label` / `small_break` | Same four, for SMALL — `small_break` containing `BULL_CHOCH` is the literal entry trigger, `BEAR_CHOCH` the exit trigger                                                                                                                                                             |
| `structure_action`                                                           | Combined text log of every pivot confirmation + BOS/CHoCH event for BIG and SMALL, this bar (shared across scenarios — structure doesn't depend on scenario)                                                                                                                         |
| `{a,b}_liquidate_price`                                                      | This scenario's current position's liquidation price (`entry_price × (1 − 1/leverage)`, MMR=0), blank when flat                                                                                                                                                                      |
| `{a,b}_pct_liquidate`                                                        | `(liquidate_price − close) / close × 100`                                                                                                                                                                                                                                            |
| `{a,b}_leverage`                                                             | **Real-time effective account leverage** (`notional / total`) — not the same as the leverage chosen at entry; this one drifts as price moves                                                                                                                                         |
| `{a,b}_position_size`                                                        | Units of the asset held (0 when flat)                                                                                                                                                                                                                                                |
| `{a,b}_notional`                                                             | `position_size × close`                                                                                                                                                                                                                                                              |
| `{a,b}_total`                                                                | The account equity curve: `margin_balance + realized_total` (while flat, `margin_balance` = 0, so `total` = `realized_total`)                                                                                                                                                        |
| `{a,b}_pnl` / `{a,b}_pct_pnl`                                                | Day-over-day change in `total`, absolute and %                                                                                                                                                                                                                                       |
| `{a,b}_margin`                                                               | `isolated_margin + (close − avg_entry) × position_size` — this position's current margin balance                                                                                                                                                                                     |
| `{a,b}_position`                                                             | `notional / leverage` — the "clean" cost-basis reference used for the stacked Total chart                                                                                                                                                                                            |
| `{a,b}_unrealized`                                                           | `margin − position` (blank when flat)                                                                                                                                                                                                                                                |
| `{a,b}_realized`                                                             | The bank — starts at $2000, ENTRY draws 50% of it out as margin, EXIT/LIQUIDATION pays the position's full closing value back in                                                                                                                                                     |
| `{a,b}_action`                                                               | This scenario's own ENTRY/EXIT/LIQUIDATION log for this bar                                                                                                                                                                                                                          |

### Liquidation mechanics

`MMR = 0` (no maintenance-margin buffer, same simplification as V5-V7):
`liquidate_price = (avg_entry × size − isolated_margin) / size`, which
simplifies to `entry_price × (1 − 1/leverage)` for a fresh position. At
10x that's a 10% adverse move to liquidation; at 5x, 20%; at 2x, 50%.
Checked every bar against the day's **low**, not just the close — real
intrabar risk, not a close-only approximation.

---

## 4. Things worth knowing that are easy to miss

- **"No compounding within a cycle" ≠ "no compounding at all."** A single
  position is never added to mid-cycle, but the bank-fraction margin
  sizing (50% of whatever the bank currently holds) means gains and losses
  very much compound _across_ cycles — a big win early makes every
  subsequent entry bigger. This is also why a bad liquidation is more
  costly than its raw dollar size suggests: it shrinks the base every
  future entry compounds from.

- **`fetch_ohlcv` pulls live data up to today, not just up to `DISPLAY_END`
  (2025-10-01).** The generator correctly truncates its CSV output to
  `DISPLAY_END`, but any ad-hoc scratch script that reuses `fetch_ohlcv`
  directly and reports the _last row_ of the full fetch will silently
  include months of extra, untruncated trading — this caused a real,
  previously-reported wrong conclusion during rule testing (see `plan.md`).
  Always filter to `date < DISPLAY_END` before reading a "final" value from
  a fresh re-simulation.

- **BOS is not an entry/exit trigger — only CHoCH is.** Both are computed
  and logged (for both BIG and SMALL) but a continuation (BOS) never opens
  or closes a position; only a reversal (CHoCH) on SMALL does.

- **BIG structure never directly gates the strategy.** It's computed
  purely for reference/charting and for the `extraCondition` de-dupe rule
  against SMALL. Every leverage-rule variant that tried to give BIG a
  say (e.g. requiring BIG agreement before entry) is untested here — open
  question if you want to explore it.

- **The scenario dates are structural facts about the price data, not
  tuned parameters** — they're just "the first SMALL green CHoCH after a
  fixed calendar cutoff," so they'll change if you re-run the generator
  against a longer/shorter fetch window or a different cutoff, but they're
  not something that was fit to the outcome.

- **This is a backtest against a small number of historical entries per
  asset (13-19 cycles each).** The leverage rule was tuned and validated
  against exactly these 10 cases — there's real overfitting risk baked in
  simply because there's no out-of-sample data left to check it against.
  Treat the specific thresholds (22 ADX, 2x/5x/10x, 50% bank fraction,
  $2000 start) as "best fit to this exact dataset," not universal
  constants. Not financial advice.

- **`index.html` never computes anything.** Every column it draws (Action
  Zone bullish/bearish, ADX/DI lines, pivot labels, BOS/CHoCH markers,
  leverage, liquidation price, the equity curve) is read directly from the
  CSV. If a number looks wrong, the bug is in `generate_calc_csv_v10.py`,
  not the viewer.
