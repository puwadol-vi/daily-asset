# Dynamic Grid Trading — Parameter Adjustment Logic

Practical tuning guide for the parameters found in `Dynamic_Grid_Trading_Strategy.md`. That file
is the sourced research (what the videos said, with citations); this file is "if you turn this
knob, here's what happens and why" — grounded in the same sources, but written for someone about
to pick values, not research them.

---

## Raw data required

- **Just OHLC candles** — no order book, funding rate, or volume feed is described as a primary
  input in the sourced videos (`[V2]` mentions "liquidity" and "momentum" matter conceptually but
  doesn't describe ingesting separate liquidity/volume data streams for them).
- **Source**: FMP (Financial Modeling Prep, paid/cleaned) preferred; YFinance as a free fallback
  for daily-only use, not for the intraday grid runs.
- **Granularity**: 15m / 30m / 60m tested — the real report used **60m** for BTC.
- **Three modes**, same OHLC shape throughout: historical (backtest) → real-time (paper/forward
  test) → synthetic (generated price paths for stress-testing, see `Dynamic_Grid_Trading_Strategy.md`).

So: if you're wiring this into `grid_signal`, the data-fetch layer is basically the same shape as
`option_signal/main.py`'s `ccxt` OHLCV pull — no new data source category needed, just a different
candle interval (60m vs. that module's 4H) and a much longer lookback for the ATR-baseline window
(100 candles minimum, per the field below).

## What triggers a zone change when the market changes

Two things gate it, and neither is a single hard indicator — this is the least concretely-sourced
part of the whole strategy:

1. **A "Volatility Factor" from Historical Volatility** — volatility calculated from past price
   data (which historical-vol calculation, over what window, isn't stated as a formula). The real
   report's `atr_window: 5` vs `atr_baseline_window: 100` fields are a plausible way to compute
   this — a short ATR compared against its own long-run baseline is a standard way to detect "vol
   is unusually high/low right now" — but no transcript confirms this is literally what's
   computed. Treat it as the leading hypothesis, not a sourced fact.
2. **A momentum confirmation** — "state-based" / "time series momentum" is checked before the
   system re-enters positions under a new structure, so a vol spike alone doesn't necessarily
   flip the grid; the shift needs directional confirmation too.

**What we know for sure**: the trigger is regime-based, not continuous — one full-year BTC test
only produced **2 distinct grid structures** total, i.e. this should not be recalculating the zone
every candle. It's closer to "detect state changed → rebuild once" than "smoothly resize every
bar." If you implement this, a sensible starting design is: compute the ATR ratio (or your chosen
vol measure) every candle, but only trigger a rebuild when it crosses a threshold band (with
hysteresis, so it doesn't flip-flop) — no threshold value is given in the sources, so that number
would need its own backtesting pass, not a borrowed constant.

---

## How each core concept is actually calculated (as far as the sources go)

The videos explain these in words, not equations. This is the literal ceiling of what's sourced —
if you need a runnable formula, you'll be filling a gap the creator never specifies.

| Concept | What's actually said | What's missing |
|---|---|---|
| **Price Level (P-level)** | Take the total zone width, divide into N "slots"/"channels" (e.g. 10). In the *dynamic* version, slot spacing isn't uniform — it varies by regime. | No formula for *how much* spacing varies per regime. |
| **Price Distribution / Price Profile** | Build a distribution of price over a historical lookback window, then classify it into Trend / Momentum / Volatility states; this informs where the zone gets drawn. | No bin count, no percentile cutoff, no window length. Structurally similar in spirit to the VPVR histogram already in `option_signal/main.py` — but that's an analogy we're drawing, not something the videos confirm. |
| **Volatility / Historical Volatility** | "Calculated from past data," then multiplied by a Safety Factor (1x baseline / 2x forward-looking). | No stated formula — could be stdev of returns, ATR, or something else; not specified. The "25% volatility" figure that shows up in the sources is a **synthetic stress-test input** (used to *generate* fake price paths for testing) — don't confuse it with a live regime-detection threshold. |
| **Zone Distance** | Directional rule only: expand under high volatility, tighten under low/sideways volatility, to avoid order clustering. | No formula tying a volatility reading to a specific zone-width number. |
| **Time Series Momentum** | A filter called "Rebound Beta," threshold **0.5%**, gates whether a level is engaged. | What Rebound Beta mathematically measures isn't explained beyond "momentum filter." |

**Practical takeaway**: the videos hand you the *shape* of the system (regime detection → zone
width/spacing decision, momentum → entry gate) and the *tested outcome numbers* (zone %, TP %,
risk %), but not the intermediate formulas connecting raw price data to those regime/zone
decisions. If `grid_signal` gets built, that connective logic (e.g. exactly how `atr_window: 5` /
`atr_baseline_window: 100` becomes a zone-width decision) will need to be designed and backtested
independently — it can't be copied from these sources because it was never stated at that level of
detail.

---

## Grid Zone (`grid_zone_pct`)

**What it is**: the total price range the grid covers, as a % above + below the center price.
E.g. `grid_zone_pct = 0.10` at a $100k center price ≈ $90k–$110k (10% up, 10% down = 20% total
width, per the baseline example in `Dynamic_Grid_Trading_Strategy.md`).

**Tested values**: 10% baseline → 15% (better) → **29.29% Bayesian-optimized best**. Search range
tried was 2%–30%.

**How to adjust it**:
- **Wider zone (↑)** — the grid can absorb a bigger price swing before price walks outside the
  range entirely (which is when a grid stops working — everything on one side just sits unfilled).
  This is *why* the optimizer pushed zone width almost to the top of its search range (29.29% of
  a 2–30% range): a narrow zone gets blown through by normal BTC volatility, so widening it was
  the single biggest lever between the -7.24% baseline report and the ~77% optimized result.
  Tradeoff: each grid level is now further apart in price, so a full buy→sell cycle takes longer
  and locks up capital longer.
- **Narrower zone (↓)** — more trades per unit of price movement (tighter spacing = more fills),
  good in genuinely low-volatility/sideways conditions. But it's fragile: any real trend or
  volatility spike pushes price outside the zone fast, at which point the grid is just holding a
  stack of unfilled/underwater orders on one side (`[V1]`'s "traditional linear grid" failure
  mode — 1-2% spacing, 80-90% drawdowns).
- **Rule of thumb from the sources**: don't pick a fixed number and leave it — the entire point of
  "dynamic" is that zone width should track the current **volatility regime**, not sit at one
  static % forever. The 29.29% figure is what fit *this* BTC backtest window, not a universal
  constant.

---

## Grid Level / N-Grid (`n_grids`)

**What it is**: how many discrete buy/sell levels are laid out inside the zone. More levels means
each level is closer together (spacing = zone width ÷ n_grids, same shape as the fixed-range grid
in `strategy/Grid_Option_Hedge_Strategy.md`).

**Tested value**: 10, in every report we've seen so far (baseline *and* the videos' worked
examples) — none of the 3 videos show a run with a different `n_grids`, and the optimized-run
report hasn't been captured yet, so we don't have direct evidence 10 is itself optimized versus
just "the default nobody varied." Treat 10 as a reasonable starting point, not a proven optimum.

**How to adjust it**:
- **More levels (↑)** — smaller price move needed to fill+complete each cycle, so more frequent
  (but smaller) profit events; capital gets sliced thinner per level (`init_cash × risk_pct ÷
  n_grids`-ish sizing), so **each individual trade's P&L shrinks**. Combined with a wide zone this
  can mean levels are close together only in the *count* sense while still being far apart in
  price — check spacing (`zone_width / n_grids`) in $ terms, not just the level count.
- **Fewer levels (↓)** — bigger profit per completed cycle, but less frequent fills and larger
  capital chunks tied up per level (more concentrated risk if one level gets stuck).
- **Interacts directly with Grid Zone**: `n_grids` and `grid_zone_pct` are not independent — a
  30% zone with 10 grids has ~3% spacing per level; the same 30% zone with 20 grids has ~1.5%
  spacing. If you widen the zone without also reconsidering `n_grids`, you're implicitly also
  widening the per-level spacing.

---

## Risk per Trade (`risk_pct`)

**What it is**: fraction of capital allocated to each position/trade.

**Tested values**: 20% baseline → **25% Bayesian-optimized best** (search range 10%–45%).

**How to adjust it**: higher `risk_pct` = bigger position per level = faster capital deployment
and bigger P&L swings (up and down) per fill; the optimizer only moved this modestly (20%→25%)
compared to how much it moved `grid_zone_pct` (10%→29%), suggesting this strategy's returns are
much more sensitive to zone width than to per-trade sizing — don't spend equal tuning effort on
both.

---

## Take Profit (`take_profit`)

**What it is**: the % gain at which a filled position closes (no trailing stop used in the sourced
runs — `stop_loss: None`, `sl_trail: False` in the real report).

**Tested values**: 3% baseline → **2% Bayesian-optimized best** (2.28% in one trial; search range
1%–10%).

**How to adjust it**: counterintuitively, the optimizer *tightened* TP (3%→2%) rather than
widening it. With a much wider grid zone, price crosses each level's TP distance more often, so a
smaller TP per level compounds into more completed cycles rather than a few large ones. If you
widen `grid_zone_pct`, revisit `take_profit` in the same pass — they were optimized together, not
independently (both are Optuna search dimensions in `[V3]`).

---

## Trade Mode (`trade_mode`)

**What it is**: `buy_only`, `sell_only`, or bidirectional (both).

**How to adjust it**: bidirectional beat one-sided in both `[V2]`'s and `[V3]`'s best runs — the
one concrete report we have (`buy_only`, baseline params) lost money (-7.24% return, Sortino
-0.20) specifically *because* it only captured half the grid's cash-flow opportunity. Unless
there's a directional-bias reason to run one-sided (e.g. deliberately wanting only downside
accumulation), bidirectional is the evidenced default.

---

## Safety Factor (`sl_safety`)

**What it is**: a multiplier that scales position sizing / frequency to account for uncertain
future volatility — described in `[V2]` as trading off "how much headroom to leave for volatility
you haven't seen yet" against capital efficiency.

**Tested values**: 1.0 (baseline, used in the real report) vs. 2.0 ("forward-looking protection").
Not part of `[V3]`'s Bayesian search — no optimized value exists yet.

**How to adjust it**: raise it (toward 2.0) if you expect the current volatility regime to worsen
and want the grid to size/space itself more conservatively ahead of that; lower it (toward 1.0) if
you trust the current regime read and want full capital efficiency. This is the one major lever
in the sourced material that hasn't been run through formal optimization — treat any value here as
a manual risk dial, not a backtested number.

---

## Other / lower-priority knobs

These appear in the real report's field list but aren't explained at the formula level in any
transcript — sourced as *existing*, not as *how they work*:

| Field | Baseline value | What we know |
|---|---|---|
| `rebound_beta` | 0.005 (0.5%) | Used for rebound/re-entry sizing per `[V2]`; not detailed further. |
| `atr_window` | 5 | Short-window ATR — plausibly feeds the volatility-regime detector, paired with `atr_baseline_window`. Inferred from naming, not confirmed. |
| `atr_baseline_window` | 100 | Long-window ATR baseline — the `atr_window`/`atr_baseline_window` ratio is a plausible regime signal (fast vol vs. its own long-run average), but this is our inference, not a sourced claim. |
| `stddev_period` | 10 | Likely feeds zone-width or rebound calculations; not detailed further. |
| `cluster_threshold` | 0.005 | Plausibly the distance threshold behind `[V1]`'s "Anticlustering" logic (preventing multiple orders from stacking at the same price level). |

Don't tune these first — adjust `grid_zone_pct`, `n_grids`, `take_profit`, and `trade_mode` before
touching this group, since those four are the ones with actual before/after evidence behind them.
If a future video/report clarifies these, fold the update into both this file and
`Dynamic_Grid_Trading_Strategy.md`.

---

## Suggested tuning order (most to least leverage, per the evidence above)

1. **`trade_mode`** → bidirectional, unconditionally (biggest single fix vs. the losing baseline).
2. **`grid_zone_pct`** → the parameter the optimizer moved the most; tune this before anything else.
3. **`take_profit`** → re-tune jointly with zone width, not independently.
4. **`n_grids`** → check $ spacing (`zone_width / n_grids`) after settling zone width, don't set it first.
5. **`risk_pct`** → smaller effect than the above; fine to leave near 20-25% initially.
6. **`sl_safety`** and the ATR/stddev/cluster group → manual/exploratory, no optimized values exist yet.
