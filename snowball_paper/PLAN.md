# Snowball Trading Strategy — Plan (Entry / Exit)

This is a research-grounded plan, not a coded spec yet — no `snowball/main.py` exists. Source
material was pulled via the `notebooklm-py` CLI (see `NOTEBOOKLM.md` for the tool
itself) from a single Thai-language video:

- **Source**: "การเทรดตามแนวโน้มด้วย Snowball Trading Strategies"
  https://www.youtube.com/live/O_TaSnZomi0 (added as `watch?v=O_TaSnZomi0` — the `/live/` URL
  form was rejected by the source-add RPC, the `watch?v=` form worked)

Everything under **"Sourced from the video"** below is grounded in that transcript (asked via
`notebooklm ask`, not paraphrased from memory). Everything under **"Design — not in the
source"** is our own extension to satisfy this repo's actual requirement (the video is
explicitly silent on options mechanics — confirmed directly via `notebooklm ask`, see below).

---

## The core concept (sourced)

Snowball is a **trend-continuation** strategy built on three required factors, all of which
must be present — not a single indicator crossover:

1. **Discount (H)** — price has deviated significantly from "Fair Value"/mean (conceptually:
   `Price = Fair Value + Expectation`; extreme fear/negative expectation creates a large gap
   `H` below fair value — or the mirror, extreme greed, above it for a short setup).
2. **Momentum** — a catalyst/event confirms the discount is about to resolve, evidenced by a
   simultaneous **positive change in both price and volume** (in commodities, the source also
   points to the COT report for confirming positioning behind the move).
3. **Continuity** — the momentum has to persist over **distance (D)**, not just spike once.
   This is what lets the position "snowball" — small initial risk, profit compounding as the
   trend keeps rolling.

Philosophy stated explicitly in the source: **"Limit Risk, High Return"**, not "High Risk,
High Return." The edge comes from distance traveled while risk stays small and linear, not
from leverage. The source explicitly rejects Fibonacci, chart patterns, Elliott Wave, and
indicator-crossover systems as the basis for this — it's a price-behavior/momentum read, not
a pattern-recognition system.

---

## Entry logic (sourced)

Three gates, all required, in order:

1. **Identify the discount zone** — price has run away from a moving average / mean by a
   meaningful margin, or a fair-value distortion is identifiable (e.g. panic-driven
   overselling). This alone is *not* an entry signal — it's a watchlist condition.
2. **Wait for the catalyst + momentum shift** — do not buy the falling knife. Wait for the
   catalyst (an event/story) to appear and for price **and** volume to turn positive together.
   No averaging down while price is still falling — this is the strategy's explicit rejection
   of Martingale-style entries.
3. **Wait for "setting the base" (ตั้งลำ), then enter at the "explosion" point (E₁)** — do not
   buy the exact low; buy once price has already started lifting out of the bottom zone.

**Initial position size**: deliberately small (source's own example: 0.01–0.02 lots) — the
point is to make the initial loss small and *linear*, not to size for conviction.

**Scaling in (pyramiding)**: once E₁ is profitable and momentum is confirmed continuing, add
further entries (A₁ → A₂ → A₃ → A₄), each layer added only if the prior layer is already
profitable — an "inverted pyramid." **Never add to a position that is currently underwater**
— the source calls scaling into a loser the "Pyramid of Death" (losses compound
quadratically instead of linearly). If A₁ isn't working, there is no A₂.

---

## Exit logic (sourced)

Two separate exit mechanisms, serving different jobs:

1. **Initial hard stop-loss** (defensive, active immediately at entry) — a small,
   predetermined stop sized against the small initial position (source's own example ratio:
   ~10 pips risked to hunt ~100 pips of distance, i.e. a 1:10 risk/reward framing). This is
   what makes the "limit risk" half of the philosophy real — every single entry must have
   this from the moment it's placed.
2. **Trailing / progressive stop** (offensive, activated once the trend confirms and scaling
   begins) — ratchets in the trader's favor as each pyramid layer adds, locking in the
   growing "mass" of the position. This is the mechanism that actually closes most winning
   trades — not a fixed take-profit level.

Additionally, a position is closed on **loss of continuity** — if momentum (price+volume)
stops confirming and the move stalls, that's a sign the "snowball" has stopped rolling, and
is treated as an exit trigger in its own right, independent of whether the trailing stop has
been hit yet.

A **target/distance projection (E₁ → E₅)** exists conceptually — the anticipated total travel
of the move — but the source frames the trailing stop and continuity check as the *actual*
exit mechanism in practice, not a fixed price target reached mechanically.

**Summary**: enter small, defend with a hard initial stop, then let a trailing stop (paired
with a continuity check) do the actual exiting as the position scales up.

---

## Design — bridging to leveraged futures and options (not in the source)

Asked directly: the source **does not discuss options mechanics at all** — no mention of
time decay, strike selection, or delta, and it explicitly frames itself as a **linear
system** (P&L moves proportionally with price, the way spot/futures/lots do). This section is
our own design work to satisfy the actual requirement — extending a linear-risk concept onto
an instrument (options) that is non-linear by construction.

**Key insight carried over unchanged, regardless of instrument**: the three-factor read
(discount → momentum → continuity) and the trailing-stop/continuity exit are all computed
**on the underlying price series** (and its volume). None of that changes between futures and
options — the discount/momentum/continuity detector is instrument-agnostic. What differs is
only **how a signal on the underlying gets translated into a position and a close-out
action.**

### Futures / leveraged perpetuals — direct mapping, no translation needed

This instrument matches the source's own linear model almost exactly:

| Snowball concept | Futures implementation |
|---|---|
| Small initial size (0.01–0.02 lot) | Small initial contract size / low leverage notional — e.g. cap initial risk to a fixed % of account (say 0.25–0.5%), sized from the stop distance, not from a lot-count convention |
| Initial hard stop | Price-based stop order at entry, sized to the same fixed-risk-% budget |
| Pyramid scale-in (A₁→A₄) | Add contracts at each confirmed-momentum layer, same "only add to a winner" rule |
| Trailing/progressive stop | Standard trailing stop on the futures price, ratcheted after each add |
| Continuity-loss exit | Close entirely if price+volume momentum stalls, independent of stop level |

Leverage itself is a red herring here — the source's point is that the strategy doesn't need
high leverage to produce a high return, because distance × (compounding position size) does
the work. Leverage just changes the notional-per-contract; **the risk budget per trade should
stay fixed in account-% terms regardless of leverage used**, so higher leverage → smaller
contract count for the same $ risk, not a bigger bet.

### Options — needs real translation, since risk isn't linear

Two structurally different ways to run Snowball through options, and the choice matters:

**Option A — Buy calls (long discount) / buy puts (short overvalue), long-premium only.**
This is arguably the *more* natural fit for "Limit Risk, High Return" than futures: max loss
is capped at premium paid by construction, and upside is theoretically open — the same
asymmetric shape the source is chasing, just enforced by the instrument instead of a manual
stop. Design points:
- **Strike/moneyness selection for the initial small entry**: use a modestly OTM, low-delta
  contract (e.g. delta ~0.20–0.30) so premium at risk is small in $ terms — this is the
  options analogue of the "0.01 lot" sizing rule. A far-OTM near-zero-delta contract is *not*
  equivalent — it barely participates in the underlying's move and defeats the point.
- **Expiry selection ("distance" needs time)**: since the strategy explicitly needs the trend
  to travel a distance over time (continuity), the expiry must have enough DTE to outlast the
  expected time-to-target — not just the time-to-entry-confirmation. Pick expiry based on the
  expected duration of the move (e.g. weeks, not days), never the shortest/cheapest available
  contract.
- **Scaling in (pyramid)**: each additional layer (A₂, A₃...) can be a new contract at a
  strike closer to the money (higher delta) as the trend confirms, since by then the
  underlying has already moved favorably — mirrors the source's "add only to a winner."
- **Initial stop-loss**: define it as a fixed **% of premium** willing to lose (not a fixed
  underlying price level) — e.g. exit if the option loses 30–40% of its value from entry.
  This keeps the same "small linear-feeling loss" property even though the option's own P&L
  curve is convex.
- **Trailing stop**: track the *underlying's* price for the trailing-stop trigger level (same
  logic as futures), but execute the exit by closing the option position once the underlying
  hits that trailing level — don't try to trail the option's own premium directly, since theta
  decay would corrupt a premium-based trailing stop over time.
- **Theta/roll rule (options-only concern, no futures equivalent)**: if continuity is still
  confirmed but the current contract is approaching expiry (e.g. <30% of original DTE
  remaining) and decay is accelerating, **roll to a further-dated contract** rather than
  holding into fast time-decay — treat an impending expiry as a forced structural exit
  regardless of the underlying's trailing-stop status, then re-enter the equivalent strike in
  a later expiry if the discount/momentum/continuity read is still intact.

**Option B — Sell premium (e.g. cash-secured puts / covered calls) in the discount
direction.** Not recommended for this strategy: selling premium caps the upside precisely
where Snowball's edge lives (letting distance compound), and the "Limit Risk, High Return"
framing directly conflicts with a defined-max-profit, theoretically-open-risk structure. This
is closer to `option_signal`'s existing sell-side approach — a different strategy family, not
a good match for Snowball's asymmetry. **Recommendation: Option A (long premium) is the
correct options implementation of this strategy, not Option B.**

### Unified entry/exit decision table (instrument-agnostic core + per-instrument execution)

| Stage | Signal (same for all instruments) | Futures action | Options action (long premium) |
|---|---|---|---|
| Watchlist | Price deviates from mean/fair value by margin H | — | — |
| Entry gate | Price + volume turn positive together, base is set | Enter small size at E₁ | Buy low-delta (~0.20–0.30) call/put, expiry ≥ expected move duration |
| Initial stop | N/A (risk budget fixed at entry) | Fixed price-distance stop, sized to small % account risk | Fixed % of premium loss (e.g. 30–40%) |
| Scale-in | Prior layer profitable + momentum still confirmed | Add contracts (A₂...A₄) | Buy additional, higher-delta contract at same or later expiry |
| Trailing exit | Underlying hits ratcheting trailing level | Close via trailing stop on price | Close option once underlying hits the same trailing level |
| Continuity exit | Price+volume momentum stalls | Close regardless of stop level | Close regardless of stop level |
| Options-only forced exit | N/A | N/A | Roll to further expiry if DTE runs low while continuity still holds |

---

## Open questions / not yet resolved

- No concrete formula for the discount threshold (H) or the momentum confirmation (how much
  price/volume change counts) is given in the source — both are qualitative ("run away from
  the mean," "positive change in both") and will need their own thresholds defined and
  backtested before this becomes code, the same gap pattern seen in `grid_signal`'s
  Volatility Factor.
- The 1:10 stop:distance ratio is a single illustrative example from the source, not a
  backtested constant — treat it as a starting risk-framing, not a tuned parameter.
- Delta band (~0.20–0.30) and premium-stop % (30–40%) for the options translation above are
  this plan's own design choices, not sourced from anywhere — flag for review/backtest before
  committing to them.
- Whether to size the futures risk-%-per-trade as fixed across all layers or increase it for
  later pyramid layers (since they're only added to confirmed winners) isn't addressed by the
  source and needs a decision before implementation.

_Not financial advice._
