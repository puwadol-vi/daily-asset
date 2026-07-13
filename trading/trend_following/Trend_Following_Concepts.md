# Trend Following — concepts & logic

Reference notes on trend following, written up from a Q&A discussion. This is a concepts
doc, not a coded spec — no `trend_following/main.py` exists yet. `option_signal`'s ADX/DMI +
EMA200 trend filter is the closest existing implementation of these ideas in this repo.

**Core definition**: a move that has already started is more likely to continue than not.
Don't try to catch the top or bottom — wait for a direction to establish itself, confirm it,
ride it until the confirmation fails. Unlike momentum trading (shorter horizon, indicator
acceleration), trend following operates on weeks-to-months and confirms with slower,
regime-level tools (moving averages, ADX/DMI).

**Key property that shapes everything below**: trend following typically has **no
price-based take-profit target**. Capping profit with a fixed TP kills the strategy's edge —
most trend systems have far more losing/breakeven trades than winners, and are only
profitable because the rare winners are allowed to run large. Exits are driven by the trend
ending, or a trailing stop, not a price target.

---

## Entry logic

**Confirm strength, then confirm direction — require both, not either alone.**

| Component | What it measures | Typical rule |
|---|---|---|
| ADX(14) | Trend **strength**, direction-agnostic | ADX > ~25 → a real trend exists (below that, treat as chop, don't trust direction signals) |
| DI+ / DI− (part of DMI, alongside ADX) | Trend **direction** | DI+ > DI− → bullish pressure dominates (mirror for bearish) |
| EMA(200) | Broader regime filter | Price > EMA200 → uptrend regime (mirror for downtrend) |

**Combined entry rule** (uptrend / long example):
`ADX(14) > 25` **AND** `DI+ > DI−` **AND** `price > EMA200` → uptrend confirmed → open long.

Mirror all three conditions for a downtrend / short entry.

**Why all three, not just one**:
- ADX alone only tells you *something* is trending, not which way.
- DI+/DI− alone can whipsaw in low-ADX chop (frequent crossovers with no real follow-through).
- EMA200 alone is a lagging regime filter with no strength read — price can sit above EMA200
  while the trend has already gone flat (low ADX).

**ADX lifecycle to keep in mind at entry** (it is not a static reading):
1. Base: ADX low (<20), DI+/DI− tangled — price basing/chopping.
2. Breakout: DI+ crosses above DI−, ADX starts climbing from the low base.
3. **Confirmed trend**: ADX crosses above 25 — this is the entry-confirmation moment.
4. Acceleration: ADX keeps climbing (e.g. into the 40s–50s).
5. Maturation: ADX can start *declining* while price still climbs — this is deceleration,
   not reversal, and is a common source of premature exits if ADX is over-relied upon (see
   Exit logic below).
6. Exhaustion/reversal: ADX drops back below 25 and/or DI+ crosses back below DI−.

**Value bands for reference**:

| ADX | Character |
|---|---|
| 0–20 | No trend / chop — frequent DI+/DI− crossovers, unreliable directional signals |
| 20–25 | Transition zone — trend may be starting, not yet confirmed |
| 25–40 | Established trend — directional signals considered reliable |
| 40–60 | Strong trend |
| 60+ | Rare, very strong/extended — often flagged as exhaustion risk rather than "more bullish" |

---

## Exit logic

Three candidate exit mechanisms, ranked by recommended reliance:

### 1. Trailing stop (primary — recommended as the main trigger)

`highest high since entry − 3×ATR(14)` (a "Chandelier"-style stop), ratcheting up as price
rises, never down. Reacts directly to price action, isn't laggy, and is what usually
triggers first in a real reversal. Also caps the false-start loss when paired with an
initial hard stop at entry (e.g. `entry − 2×ATR`).

### 2. DI cross (secondary — good standalone reversal confirmation)

`DI+ crosses below DI−` → control has genuinely flipped from buyers to sellers. This is a
direct directional-flip signal, not a strength/deceleration measure, so it doesn't suffer
from the ADX-deceleration problem below. Reasonable to treat as an exit trigger on its own,
independent of ADX's reading at the time.

### 3. EMA cross / EMA200 close-below (backstop — laggiest, use as filter not trigger)

`price closes back below EMA200` → slower, regime-level confirmation the uptrend is over.
Most useful as a "don't re-enter into a still-broken regime" filter rather than the primary
close-out trigger, since it lags both of the above.

### Why NOT to use "ADX drops below 25" as a standalone exit trigger

ADX falls during **normal trend deceleration**, not only at reversals (see lifecycle step 5
above). A mature, still-healthy uptrend can see ADX fall from 45 back toward 25 while price
keeps grinding higher. Exiting purely on "ADX < 25" produces frequent premature exits from
trends that haven't actually ended. At most, use an ADX threshold as a **re-entry filter**
("don't open a new long until ADX is back above 25"), not as a trigger to close an existing
position.

### Recommended exit stack

Exit on **whichever comes first**:
- Trailing stop hit (primary), or
- DI+ crosses below DI− (secondary confirmation)

Use EMA200 close-below as a slower backstop / re-entry filter, and treat a falling-but-still
->25 ADX as "decelerating but still trending" rather than an exit signal by itself.

_Not financial advice._
