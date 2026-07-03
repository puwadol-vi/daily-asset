# Bitcoin Options Income Strategy — as implemented (`option_signal`)

This is the concrete spec implemented by `option_signal/main.py`. The original
generic strategy write-up lives at
`strategy/Bitcoin_Options_Income_Strategy.md` — this file documents the
choices made to turn that into a running daily alert.

This module is **advisory only**: it posts a Discord checklist + suggested
strike, it does not place orders on Binance.

Every header line follows the same `label - value (threshold)` format, e.g.
`Trend : uptrend - 28.0 ADX — (+DI 22.6 / -DI 13.1) (ADX >= 25 & +DI>-DI)` —
the verdict, the raw number, and the exact condition that produced it are
all on one line, so nothing is asserted without showing why.

---

## 1. Cadence (differs from the generic doc)

- **Daily Binance options, 1 DTE** — not the "3-7 DTE" range in the generic
  doc. Binance BTC daily options list and expire at **08:00 UTC every day**
  (T+2/T+3 lifetime contracts), so "the 1-DTE contract" on any day is just
  the option expiring at tomorrow's 08:00 UTC rollover — no option-chain
  lookup is needed, it's computed from the clock (`next_expiry()` in
  `main.py`, always `now + 1 day`).
- **Runs every day** (cron `5 8 * * *` = 08:05 UTC / 15:05 ICT, including
  Sat/Sun), ~5 minutes after the daily rollover so the suggested strike is
  priced off a fresh contract with the full theta-decay window ahead of it.
- Opening late in the day (well after the 08:00 UTC rollover) means capturing
  less than a full day of premium decay before the next day's expiry — the
  alert includes an entry-timing note (🟢 fresh / 🟡 late) for this reason.

## 2. Indicator Filter Stack (as coded)

1. **ADX (14) + DMI** on 4H candles — `ta.trend.ADXIndicator`.
   - `adx()` = trend strength. `adx_pos()`/`adx_neg()` (+DI/-DI) = trend
     **direction** — which side (up or down) is actually winning.
   - Sideways: ADX < 25 (neither direction confirmed).
   - Strong trend: ADX > 40 **and** DI dominance on one side.
2. **EMA(200)** on 4H candles — a second, independent trend confirmation.
   `near` requires price to be on the agreeing side of EMA200 as well as the
   ADX/DI read; if they disagree, it's demoted to `structure` (see below).
3. **Stochastic RSI (14, 14, 3, 3)** on 4H candles —
   `ta.momentum.StochRSIIndicator`. Shown as context (oversold <20 /
   overbought >80) but does **not** gate any setup — trend direction and
   structure decide that, not momentum exhaustion.
4. **VPVR (real volume-by-price histogram)** — not a proxy:
   - Trailing 360 4H candles (~60 days), price range split into 50 bins.
   - Each candle's volume assigned to the bin of its typical price
     `(high + low + close) / 3`.
   - POC = highest-volume bin. HVNs = bins at/above the 70th volume percentile.
   - Support = nearest HVN at/below current price. Resistance = nearest HVN
     above current price.
5. **Funding rate** (BTC/USDT perp, `fetch_funding_rate`) — a crowding gauge,
   not a trend filter. See the overlay section below.
6. **Live option IV vs. realized vol** — Binance's public options endpoint
   (`eapi/v1/mark`) gives the real `markIV`/`delta`/`markPrice` for the
   actual listed contract nearest our computed strike; compared against
   realized vol from trailing 4H log-returns. See the overlay section below.

## 3. Setups

Each side (put/call) independently gets one of three states, driven by
**trend direction relative to that side**, not a reversal trigger:

**🚫 skip — trend confirmed against this side**
- ADX ≥ 25 and DI dominance opposes this side (downtrend → skip puts,
  uptrend → skip calls)
- Rationale: in a real trend, price can blow through any strike — don't
  sell into it at all, regardless of how far out you'd go.

**🎯 near-the-money — trend confirmed in favor of this side**
- ADX > 40 and DI dominance favors this side (uptrend → puts, downtrend
  → calls)
- → strike: spot ∓ `1.0 × ATR(14)` — closer to money than the structure
  play (more premium, more risk) because the strong trend itself is the
  reason price shouldn't reverse through it.

**🛡️ at-structure — genuinely confirmed sideways (ADX < 25)**
- Not "not opposed" — actually sideways, both directions ruled out
- A support (put) / resistance (call) HVN exists to sell against
- → strike: HVN level ∓ `2.0 × ATR(14)`, priced conservatively further out
  since there's no directional conviction backing it, only the structural
  level.

**⏸️ no confirmed signal — not badged as a "go"**
- ADX 25-40, not opposing this side, but not confirmed sideways or
  confirmed strong either — a trend could still be forming in either
  direction, so this is deliberately *not* shown as an actionable signal
- If a support/resistance HVN exists, the message still prints a
  **reference-only** level (`HVN ∓ 2.0×ATR`, same formula as the structure
  play) so the user can decide for themselves — it's just not asserted as
  a confirmed setup the way 🛡️/🎯 are.
- If there's no HVN at all on that side, no level is shown — a data gap.

Strike buffers are ATR-scaled rather than a fixed percentage so they widen
automatically in high-volatility regimes instead of staying pinned close to
spot or the structural level. **The ATR math is always what picks the
strike** — for all three of 🎯/🛡️/⏸️, the real listed Binance contract
nearest that ATR-computed price is then looked up purely so the message can
show its actual delta/premium/IV instead of a synthetic estimate. Delta is
never the selection criterion, only a display value attached to the
ATR-chosen strike.

## 4. Risk overlays (funding + IV/RV)

Applied only to a base `near` state (the highest-conviction, tightest-strike
play — the one most exposed to a squeeze or a mispriced entry). Each overlay
can only **demote** `near` → `structure` (or → no-signal if there's no HVN
to fall back on) — none of them can upgrade a signal. This matches the
"less risk" preference this module is built around: additional information
only ever makes the module more conservative.

- **Funding rate crowding**: a PUT needs an uptrend to reach `near`, but if
  perp funding is already extremely positive (`> 0.05%/8h`, ~55%/yr) —
  longs paying heavily to stay long — that's flush-down risk, exactly what
  breaks the "trend won't reverse" thesis. Demote. CALL mirrors this with
  extremely negative funding (crowded shorts, squeeze-up risk).
- **IV vs. realized vol**: the real listed contract nearest our computed
  strike is looked up live (`eapi/v1/mark`) for its `markIV`, compared
  against realized vol (annualized stdev of 4H log-returns, ~7-day
  lookback). Ratio < 0.8 → premium too cheap for the risk being taken,
  demote. Ratio > 2.0 → a vol spike / event risk, demote — a strong ADX
  trend doesn't protect against a genuine shock. 0.8–2.0 is the healthy
  zone: no demotion. This IV/RV check only gates `near`; for `structure`
  and `⏸️`, the same live lookup runs but purely for display (real
  delta/premium/IV shown alongside the ATR-picked strike), never demoting.
- Both checks are soft-fail: if the funding or options API call errors out,
  that overlay is skipped rather than failing the whole alert — the core
  ADX/VPVR signal is the critical path, these are enrichments.

## 5. What's intentionally not automated

- **The roll** (buy back and roll to next cycle if a level breaks) — manual,
  per the generic doc's Key Rules section.
- **Actual order placement** — this module only alerts; sizing, margin, and
  execution stay manual on Binance.
