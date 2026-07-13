# Momentum Trading — concepts & logic

Reference notes on momentum trading, written up from a Q&A discussion. This is a concepts
doc, not a coded spec — no `momentum_trading/main.py` exists yet.

**Core definition**: trade *in the direction of already-demonstrated strength/weakness*.
"Buy high, sell higher" is the most visual instance of this (breakout longs), but it is only
one of several techniques under the same umbrella — see the variants below.

Momentum is the mirror-opposite philosophy of mean-reversion (buy under mean / sell over
mean — a bet *against* the current move). Momentum bets *with* the move.

---

## 1. Long momentum ("buy high, sell higher")

Buy an asset because it is already strong and rising, expecting the strength to continue.
Entry is typically a breakout to a new high out of consolidation.

**Logic — why it works**: a breakout out of a genuine base represents a real shift in
supply/demand that many participants are watching. Buying it accepts a worse price than the
base in exchange for confirmation that the move has real participation behind it.

**Confirmation checklist** (avoids buying a random spike):
- Breaking a well-defined prior base/resistance, not a random number.
- Volume expands on the breakout (participation, not just drift).
- Not badly extended from its moving average (room left to run).
- RSI elevated but not pinned at an extreme (e.g. ~60–70, not 85+ for days).
- Ideally aligned with the higher-timeframe trend (e.g. price > EMA200) — don't take a
  momentum long against the dominant trend.

## 2. Short-side momentum ("sell low, cover lower")

The exact mirror of long momentum: short an asset that is already weak/falling, expecting
continued weakness. Same philosophy (trade with the move), opposite direction, opposite
polarity on every filter below.

**Confirmation checklist** (mirrored):
- Breaking down through a well-defined prior base/support, not a random number.
- Volume expands on the breakdown.
- Not badly extended *below* its moving average.
- RSI weak but not pinned at an oversold extreme (e.g. ~30–40, not sub-15 for days —
  extreme oversold readings raise short-squeeze/bounce risk).
- Ideally aligned with the higher-timeframe trend (price < EMA200).

---

## 3. Indicator-crossover momentum

Entry trigger is a momentum **indicator** shifting, not a price extreme. This means entry
can happen *before* price ever makes a new high/low — inside a range, ahead of any
structural breakout.

**Example market environment**: BTC chops sideways for 6 weeks between $58k–$64k. Through
this whole period: RSI(14) oscillates 40–55 (never confidently bullish), MACD line sits
below its signal line and below zero (sellers have the technical edge), ADX is low (~15,
confirming genuine chop, not a hidden trend).

Then, still *inside* the range (price hasn't broken $64k):
- RSI pushes above 50 and holds there for several days, itself making higher lows.
- MACD line crosses above its signal line, then later above the zero line too.

**What this is detecting**: buyers are absorbing supply more aggressively on every dip
within the range — the *velocity* of buying is increasing before the price chart shows a
structural breakout. The indicator is a leading read on who's in control.

**Trade-off vs. waiting for the breakout**: entering here (e.g. ~$61–62k, still range-bound)
gets a better price *if* the breakout follows, at the cost of more false signals — the range
could simply reject again at $64k without ever breaking out. Breakout-momentum entries are
later/more expensive but have already proven the move is real.

**Common triggers used for this variant**:
- MACD line crosses above/below its signal line, or above/below the zero line.
- RSI crosses above/below 50 (not the 30/70 extremes — 50 marks a bull/bear momentum bias
  shift, not overbought/oversold).
- ROC (Rate of Change) turns positive/negative after being on the other side.

---

## 4. Pullback / continuation entries

Within an already-confirmed trend, buy the **first pullback** (a dip to a rising support,
not a new high). Still momentum in philosophy (trading with the existing strong move), but
the entry price is a dip, not an extreme.

**The hard problem**: separating "just a healthy pause" from "the start of a deeper
reversal." No single filter is bulletproof — require 2–3 of these to agree:

| Filter | Healthy pullback (buy it) | Reversal warning (stand aside) |
|---|---|---|
| Retracement depth (vs. prior up-leg) | ≤ 50% | > 61.8% |
| Swing structure | Makes a **higher low** vs. last swing low | **Breaks below** the last swing low |
| Support held | Holds above rising EMA20/50 | Closes and stays below EMA20/50 |
| Volume on the dip | Contracts (low-conviction selling / profit-taking) | Expands (real distribution) |
| DI+/DI− (from ADX) | DI+ still above DI− | DI− crosses above DI+ |
| Duration | Short — a few candles, then resumes | Extended — many days without reclaiming the prior high |

**Rule of thumb**: buy the dip if retracement ≤ 50%, the last higher low holds, volume is
light on the way down, and DI+ is still above DI−. Stand aside (or exit an open position) if
retracement > 61.8%, the last swing low breaks, volume expands to the downside, or DI−
crosses above DI+.

---

## 5. Good high vs. bad high (applies symmetrically to short-side lows)

| Filter | Good high (buyable) | Bad high (chasing exhaustion) |
|---|---|---|
| Prior structure | Breaking a well-defined base/resistance | No base — already mid-air |
| Volume | Expanding on the break | Shrinking / climactic spike |
| Extension from MA | Modest (e.g. 3–5% above EMA20) | Very stretched (e.g. 20%+ above EMA20) |
| RSI level | Elevated but not extreme (~60–70) | Pinned at extreme (85–95+) for multiple days |
| Follow-through | Closes near the high, holds the breakout on retest | Immediate rejection / long wick back below the level |

*Mirror for shorts*: well-defined support breakdown with expanding volume and a modest
extension below the MA is a "good low"; a parabolic crash already 20%+ below EMA20 with
RSI pinned under 15 is a "bad low" — more likely a short-squeeze setup than continuation.

**Concrete good-high example**: BTC bases $60k–$65k for 4–6 weeks (volatility compresses,
volume dries up), then closes above $65k on ~2x average volume with RSI at 65 (not 90) and
price only 3–5% above EMA20. Buyable — real structure broken, room left to run.

**Concrete bad-high example**: BTC already ran 35% in 6 days with no pause, RSI pinned 90+
for days, price 20%+ above EMA20, and volume on the latest up-candles *shrinking* (buyers
running out). This is a parabolic blow-off — likely to reverse sharply, not continue.

---

## Risk handling (applies to all variants above)

Momentum trades tend to reverse *sharply* — crowded positioning unwinds fast. Discipline
required regardless of which variant triggered the entry:

- Hard stop below the recent swing low (long) / above the recent swing high (short), or an
  ATR-based stop from entry.
- Never average into a losing momentum trade assuming "even more extended now" — that's
  the same mistake as fighting a real trend in mean-reversion.
- Confirm with the higher-timeframe trend direction where possible (see
  `../trend_following/Trend_Following_Concepts.md`) — momentum entries against the
  dominant trend have a materially worse hit rate.

_Not financial advice._
