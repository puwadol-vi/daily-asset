# Grid Trading + Conditional Option Hedge Strategy

---

## Overview

Run a price grid within a defined S/R range — buys each dip, sells each bounce, collecting the spread repeatedly. Options are **not open by default**. A protective put is only added when specific risk conditions trigger, and removed when conditions clear. This keeps option cost near zero during calm periods while providing real protection when the grid is under stress.

---

## Grid Setup

### Step 1 — Define the range

| Parameter | How to determine |
|---|---|
| Upper bound | Nearest significant resistance above current price |
| Lower bound | Nearest significant support below current price |
| Minimum range | Upper must be ≥ 10% above lower. If smaller, wait for clearer S/R. |
| Grid count | 10 levels |
| Grid spacing | (Upper − Lower) ÷ 10 |
| Capital per level | Total grid capital ÷ 10 |

**Do not open a grid when:**
- ADX > 35 (strong trend — grid will get destroyed on one side)
- BOS is already broken below the lower bound
- Range cannot be clearly defined by visible S/R levels

### Step 2 — Place orders

Place 10 limit buy orders at equal intervals from lower bound up.
Each buy has a paired sell order exactly 1 grid spacing above it.

| Filled buy → sell fills = 1 completed cycle | Profit per cycle ≈ grid spacing % |
|---|---|

**Example — BTC grid $90,000 – $110,000, 10 grids, $10,000 capital:**

| Level | Buy | Sell | Capital |
|---|---|---|---|
| 1 | $90,000 | $92,000 | $1,000 |
| 2 | $92,000 | $94,000 | $1,000 |
| 3 | $94,000 | $96,000 | $1,000 |
| ... | ... | ... | $1,000 |
| 10 | $108,000 | $110,000 | $1,000 |

Profit per completed cycle: ~2.2% per level.

---

## Grid Operation Rules

- Do not move grid levels once set. S/R defines the grid — it stays fixed.
- When a sell fills (cycle complete), capital re-queues at the original buy level.
- Grid reset: only when price breaks the range by > 5% AND a new clear S/R range can be identified. Cancel all orders, restart setup from Step 1.

---

## Hedge — Protective Put (Conditional)

Options are **not always open**. Buy a put only when a risk trigger fires.

### Trigger conditions — any ONE is enough

| Condition | How to check |
|---|---|
| Price drops into lower 40% of grid range | (price − lower) ÷ (upper − lower) < 0.40 |
| Grid is ≥ 60% filled — 6+ buy levels absorbed with no sell fills yet | Count open filled buys vs completed cycles |
| BTC weekly close drops below 21W EMA | Weekly chart |
| ADX rising above 30 while price is declining | Daily ADX direction |

### Hedge parameters

| Parameter | Value |
|---|---|
| Instrument | Put option on the grid coin |
| Strike | At grid lower bound (or 5% below if lower bound is very close to current price) |
| Expiry | 3–4 weeks |
| Size | 3% of total grid capital at time of purchase |
| Platform | Deribit or Binance Options |

**One active hedge at a time.** If a trigger fires while a hedge is already open, do not add a second put — reassess whether to close the grid entirely instead.

### Exit the hedge

| Trigger | Action |
|---|---|
| Price recovers above 60% of grid range | Sell put — take profit or accept small loss |
| Put reaches 2× purchase price | Sell, bank profit. Do not re-hedge unless a trigger fires again |
| Expiry within 1 week — put is OTM | Let expire (cost was small) |
| Expiry within 1 week — put is ITM | Sell put — use profit to offset grid inventory losses |

---

## Grid Failure — Close the Grid

| Condition | Action |
|---|---|
| Price closes below grid lower bound on 2 consecutive daily candles | Cancel all open grid orders. Sell all accumulated inventory at market. |
| Hedge is active and ITM at grid close | Sell put — profit offsets part of inventory loss |
| Hedge is active and OTM at grid close | Sell for remaining value or let expire |

After a grid close: wait at least 2 weeks and require a fresh identifiable S/R range before opening a new grid on the same coin.

---

## Risk Limits

- Max grid capital per coin: 30% of spot holdings for that coin
- Max grids running simultaneously: 2 coins
- Never run a grid when the coin's BOS is broken on the daily chart
- Never use leverage inside the grid — spot only
- Max hedge spend per grid deployment: 5% of grid capital total. If puts have cost 5% with no payoff, close the grid and reassess the range.

---

## Grid + Hedge Tracker

| Coin | Lower | Upper | Grid capital | Levels filled | Cycles done | Hedge active | Hedge strike | Hedge expiry | Hedge cost |
|---|---|---|---|---|---|---|---|---|---|
| | | | | / 10 | | Yes / No | | | |

---

## Weekly Checklist

1. Count filled buy levels and completed sell cycles → current fill ratio
2. Check if any hedge trigger condition is now active
3. If hedge is open: check put value, days to expiry, and exit conditions
4. Check if price has been below lower bound for 2 consecutive days → grid failure
5. Check ADX — if > 35, prepare to close grid before it trends through the range
6. Log grid state in tracker

---

## Plan Summary

| Decision | Rule |
|---|---|
| Grid range | Nearest resistance (upper) and support (lower) — minimum 10% apart |
| Grid levels | 10 equal intervals, equal capital per level |
| Open hedge | Any 1 of 4 risk triggers fires |
| Hedge instrument | Put option at lower bound strike, 3–4 week expiry, 3% of grid capital |
| Exit hedge | Risk clears (price >60% of range) · Put 2× · Near expiry OTM/ITM |
| Grid failure | Price below lower bound 2 consecutive days → close all |
| Max hedge spend | 5% of grid capital total per deployment |
| Leverage | Never — spot grid only |
