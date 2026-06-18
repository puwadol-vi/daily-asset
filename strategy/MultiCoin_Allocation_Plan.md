# Multi-Coin Allocation Plan

### Oct 2026 – Jun 2029 | Separate capital pool from BTC Call Option Snowball Plan

---

## Overview

A momentum-weighted spot portfolio across 6 coins (BTC, ETH, BNB, SOL, XRP, PAXG or XAUT),
built from $0 through daily buying. Two signals control buying behavior:

- **Fast signal** — which coin to buy today (daily, EMA12/26 on ratio charts)
- **Slow signal** — target allocation ratio per coin (weekly, 200D EMA distance)

Leverage layers on top of spot when trend is confirmed strong.
Options hedge the portfolio only when market looks dangerous.

---

## Coins

BTC, ETH, BNB, SOL, XRP, PAXG or XAUT

---

## Slow Signal — Weekly Target Allocation (every Monday)

### Step 1 — Calculate ALT/BTC ratio distance from 200D EMA

For each coin open the ratio chart vs BTC on TradingView (daily timeframe).
Note the 200D EMA value. Calculate:

**Distance = (current ratio − 200D EMA) ÷ 200D EMA × 100**

### Step 2 — Apply floor and buffer

If distance is negative and below −10, cap it at −10.
Then add 10 to every distance. Minimum raw score = 0.

| Distance result      | Raw score    |
| -------------------- | ------------ |
| +18%                 | 18 + 10 = 28 |
| +8%                  | 8 + 10 = 18  |
| −3%                  | −3 + 10 = 7  |
| −15% (capped at −10) | −10 + 10 = 0 |

Any coin with raw score 0 gets 0% target allocation that week.
Its existing holdings remain — it simply receives no new daily buys.

### Step 3 — Weight to 100%

Divide each raw score by the sum of all raw scores.

**Example:**

| Coin         | Distance | Raw score | Target %    |
| ------------ | -------- | --------- | ----------- |
| SOL          | +18%     | 28        | 28/66 = 42% |
| ETH          | +8%      | 18        | 18/66 = 27% |
| BNB          | +3%      | 13        | 13/66 = 20% |
| BTC          | −3%      | 7         | 7/66 = 11%  |
| XRP          | −15%     | 0         | 0%          |
| PAXG or XAUT | −15%     | 0         | 0%          |

Use these target percentages Monday through Sunday.
Recalculate every Monday morning before buying.

---

## Fast Signal — Daily Buy

### Step 1 — Run round robin on all 15 ratio charts (daily timeframe)

Check EMA12 vs EMA26 on each ratio. Winner = coin whose EMA12 is above EMA26.

| Pair    | Check              | Winner     |
| ------- | ------------------ | ---------- |
| ETH/BTC | EMA12 above EMA26? | ETH or BTC |
| BNB/BTC | EMA12 above EMA26? | BNB or BTC |
| SOL/BTC | EMA12 above EMA26? | SOL or BTC |
| XRP/BTC | EMA12 above EMA26? | XRP or BTC |
| BNB/ETH | EMA12 above EMA26? | BNB or ETH |
| SOL/ETH | EMA12 above EMA26? | SOL or ETH |
| XRP/ETH | EMA12 above EMA26? | XRP or ETH |
| SOL/BNB | EMA12 above EMA26? | SOL or BNB |
| XRP/BNB | EMA12 above EMA26? | XRP or BNB |
| XRP/SOL | EMA12 above EMA26? | XRP or SOL |

...

Each coin scores 0–4 points (max wins in 4 pairs each).

### Step 2 — Find buy target

From coins with score above 0:

- Find which is most underweight vs its Monday target allocation
- That coin receives today's daily buy

If top scorer is already at or above target → buy second scorer most underweight.
If all scoring coins are at or above target → hold daily buy in USDT, roll to tomorrow.
If all 5 coins score 0 (all ratios below EMA12/26) → hold in USDT, roll to tomorrow.

### Step 3 — Split daily buy

Single coin qualifies → buy full amount into that coin.
Two coins qualify equally underweight → split 60/40 toward higher scorer.

---

## Leverage Layer

Only open a futures long when ALL THREE conditions are true:

| Condition                                               | How to check                     |
| ------------------------------------------------------- | -------------------------------- |
| Coin ratio above 200D EMA for 30+ consecutive days      | Track on slow signal spreadsheet |
| Ratio distance above 200D EMA is 15%+                   | Slow signal calculation          |
| EMA12 above EMA26 on coin's own daily chart (not ratio) | TradingView daily chart          |

**Leverage parameters:**

- Type: cross margin on Binance futures
- Leverage setting: 3x
- Position size: 50% of that coin's current spot holding value
- Max coins with leverage open simultaneously: 2

**Close leverage when:**

- Coin ratio drops below 200D EMA for 3 consecutive days → close futures only, keep spot
- Ratio distance drops below 5% → reduce futures position by 50%

**Never open new leverage when:**

- Total portfolio drawdown from peak exceeds 20%
- More than 3 of 5 coins have ratio below 200D EMA simultaneously

---

## Hedge — Options

### Trigger conditions (any ONE is enough)

| Condition                                                                 | How to check                         |
| ------------------------------------------------------------------------- | ------------------------------------ |
| Total crypto market cap drops 20%+ from recent peak in one month          | CoinMarketCap total market cap chart |
| 4 or more coins score 0 in fast signal round robin for 3 consecutive days | Daily round robin tracker            |
| BTC ratio distance drops below −15%                                       | Slow signal calculation              |

### Hedge action

- Instrument: BTC put option on Deribit
- Strike: 15% below current BTC price
- Expiry: 3 months out
- Size: 5% of total portfolio value at time of purchase

### Exit hedge

Sell put when either:

- Total crypto market cap recovers 10% from the low that triggered the hedge
- Put reaches 2x purchase price — take profit, do not replace unless trigger fires again

---

## Portfolio State — What to track weekly

| Coin         | Spot value | Current % | Target % | Gap | Round robin score | Distance | Leverage open |
| ------------ | ---------- | --------- | -------- | --- | ----------------- | -------- | ------------- |
| BTC          |            |           |          |     |                   |          |               |
| ETH          |            |           |          |     |                   |          |               |
| BNB          |            |           |          |     |                   |          |               |
| SOL          |            |           |          |     |                   |          |               |
| XRP          |            |           |          |     |                   |          |               |
| PAXG or XAUT |            |           |          |     |                   |          |               |
| USDT         |            |           | —        | —   | —                 | —        | —             |

---

## Monday Weekly Checklist

1. Calculate ratio distance from 200D EMA for all 5 coins
2. Apply floor (cap at −10), add 10, sum, divide → new target allocation %
3. Compare current portfolio % vs new target → note underweight coins
4. Check leverage conditions for any coin (30 days, 15% distance, EMA12/26)
5. Check hedge trigger conditions (market cap, round robin scores, BTC distance)
6. Update portfolio tracker

## Daily Checklist

1. Run round robin — check EMA12 vs EMA26 on all 10 ratio charts
2. Tally scores for all 5 coins
3. Find most underweight qualifying coin
4. Execute daily buy
5. If no qualifier — hold in USDT, roll to tomorrow

---

## Exit — June 2029

1. Close all open futures positions first (market order)
2. Sell spot positions largest to smallest
3. Convert all to USDT or transfer to next plan

---

## Relationship to BTC Call Option Snowball Plan

Separate capital pool. Both plans run simultaneously Oct 2026 → Jun 2029.
This plan: spot + selective futures, daily buying, multi-coin allocation.
Snowball plan: BTC call options only, monthly entry, single asset.
No capital moves between the two plans.
