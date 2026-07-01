# Full Asset Status — Plan

Layout · Data Sources · Per-Asset Thresholds · Workflow

---

## Post Layout — Daily

```
📊 BTC Daily Status — @{DD Mon YYYY}

[🟢/🔴 BTC] · $[PRICE]  ([+/-X.XX%])

📈 Technical
• EMA 200: [🟢/🔴]  ·  RSI: [X.X] [🔵/🟢/🟡/🔴]  ·  Action Zone: [🟢/🔴]

⛓️ Onchain
Realized $[V]  ·  STH $[V]  ·  LTH $[V]  |  TMM $[V]
MVRV [V] [🔵/🟢/🟡/🔴]  ·  STH [V]  ·  LTH [V]  |  Z-SCORE [V]

🔗 Signal guide & emoji meanings link pinned in the comments below!
```

---

## Post Layout — Weekly

```
📊 BTC Weekly Status — @{DD Mon YYYY} ({DD Mon} - {DD Mon})

[🟢/🔴 BTC] · $[PRICE]  ([+/-X.XX%] 7d)

📈 Technical
• EMA 200: [🟢/🔴]  ·  ADX: [X.X] [🟢/🔴]  ·  RSI: [X.X] [🔵/🟢/🟡/🔴]
• Action Zone: [🟢/🔴] $[CROSS PRICE] ([N] days ago)
• Key Levels: R $[RESISTANCE]  ·  S $[SUPPORT]
• BOS: [status]

⛓️ Onchain
Realized $[V]  ·  STH $[V]  ·  LTH $[V]  |  TMM $[V]
NUPL [V] [🔵/🟢/🟡/🔴]  ·  Supply Profit [X%]
✨ [AI: 1-line insight on Realized / TMM / NUPL / Supply Profit]
MVRV [V] [🔵/🟢/🟡/🔴]  ·  STH [V]  ·  LTH [V]  |  Z-SCORE [V] [🔵/🟢/🟡/🔴]
SOPR  ·  STH [V]  ·  LTH [V]
✨ [AI: 1-line insight on MVRV / Z-SCORE / SOPR]
F&G: [VALUE] [🔴/🟠/🟡/🟢/🟢]  · Dom: [X.X%]

🌊 Elliott Wave
✨ [AI: 1-line insight describe the elliot wave]
〽️ Wave Patterns
✨ [AI: 1-line insight describe the wave pattern]

🔗 Signal guide & emoji meanings link pinned in the comments below!
✨ = AI-generated insight
```

---

## Per-Metric Thresholds

### Technical

|             |                                  |                             |              |                      |
| ----------- | -------------------------------- | --------------------------- | ------------ | -------------------- |
| EMA 200     | 🔴 Price below EMA 200           | 🟢 Price above EMA 200      |
| ADX (14)    | 🔴 ≤ 20 (ranging)                | 🟢 > 20 (trending)          |
| RSI         | 🔵 < 30 (oversold)               | 🟢 30 – 70                  | 🟡 70 – 80   | 🔴 > 80 (overbought) |
| Action Zone | 🔴 EMA12 below EMA26 (bear)      | 🟢 EMA12 above EMA26 (bull) |
| BOS         | BOS confirmed (structure broken) | LH forming (first warning)  | HH/HL intact |

### Onchain

|              |                          |                   |                      |                      |                             |
| ------------ | ------------------------ | ----------------- | -------------------- | -------------------- | --------------------------- |
| NUPL         | 🔵 < 0 (loss)            | 🟢 0 – 0.5        | 🟡 0.5 – 0.75        | 🔴 > 0.75 (euphoria) |
| MVRV         | 🔵 ADD < 1.0             | 🟢 HOLD 1.0 – 2.0 | 🟡 WARN 2.0 – 3.5    | 🔴 EXIT > 3.5        |
| MVRV Z-SCORE | 🔵 < 0                   | 🟢 0 – 4          | 🟡 4 – 7             | 🔴 > 7               |
| F&G          | 🔴 (0 – 24) Extreme Fear | 🟠 (25 – 44) Fear | 🟡 (45 – 55) Neutral | 🟢 (56 – 74) Greed   | 🟢 (75 – 100) Extreme Greed |

|               |                                                                                                                                                     |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Realized      | Global avg cost basis of all BTC (price when each coin last moved). Price above = market in profit. Price below = historically rare undervaluation. |
| Realized STH  | Cost basis of short-term holders (coins moved < 155 days ago). Acts as key support when price is above it, resistance when below.                   |
| Realized LTH  | Cost basis of long-term holders (coins held > 155 days). Very stable floor — rarely breached even in deep bear markets.                             |
| TMM           | True Market Mean — volume-weighted avg of all on-chain transaction prices. Mid-cycle fair value reference between Realized and current price.       |
| NUPL          | Net Unrealized Profit/Loss. How much of the network is sitting on paper gains.                                                                      |
| Supply Profit | % of circulating supply currently at a profit (cost basis below current price). High % = late cycle risk.                                           |
| MVRV          | Market Value vs Realized Value. How over/undervalued relative to network cost basis.                                                                |
| MVRV STH      | MVRV for short-term holders only. < 1 = STH underwater — often signals capitulation or bounce.                                                      |
| MVRV LTH      | MVRV for long-term holders. Rises sharply near cycle tops as LTH unrealized gains peak.                                                             |
| MVRV Z-SCORE  | Standardized MVRV using historical std dev — removes cyclical noise.                                                                                |
| SOPR STH      | Sell price ÷ buy price for STH coins spent. < 1 = STH selling at a loss (capitulation signal).                                                      |
| SOPR LTH      | Same ratio for LTH coins spent. < 1 is rare — signals extreme bear / LTH capitulation.                                                              |
| F&G           | Market-wide sentiment index (0–100) from alternative.me. Contrarian signal at extremes.                                                             |
| Dom           | BTC % of total crypto market cap. Direction only — no fixed threshold. ↑ rising = BTC outperforming alts (risk-off). ↓ falling = altseason.         |

---

## Images (Weekly only)

| #   | Name        | Description                                          |
| --- | ----------- | ---------------------------------------------------- |
| 1   | Action Zone | Candlestick chart with EMA 200/12/26 + Action Zone   |
| 2   | Onchain     | Line chart: Close price · Realized · STH · LTH · TMM |

---

## AI Read (Weekly only)

Claude (`claude-opus-4-7`) receives the last 120 daily candles (OHLCV) and relevant metrics, and outputs 4 lines:

```
Read1: [1-line insight on Realized / TMM / NUPL / Supply Profit]
Read2: [1-line insight on MVRV / Z-SCORE / SOPR]
Wave: [Elliott Wave call] · [1-line context]
Pattern: [chart pattern] · [brief note]
```

---

_Not financial advice_
