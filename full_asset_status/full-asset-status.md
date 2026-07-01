# Full Asset Status — Plan

Layout · Data Sources · Per-Asset Thresholds · Workflow

---

## 1. Modes

| Mode       | Trigger                | Images                      | AI Read |
| ---------- | ---------------------- | --------------------------- | ------- |
| **Daily**  | Tue–Sun at 07:02 UTC+7 | None                        | No      |
| **Weekly** | Monday at 07:02 UTC+7  | 2 images (candle + onchain) | Yes     |

---

## 2. Post Layout — Daily

### Output Format

```
📊 Pixel Chart Diary - BTC Daily Status — @{DD Mon YYYY}

[🟢/🔴 BTC] · $[PRICE]  ([+/-X.XX%])

📈 Technical
• EMA 200: [🟢/🔴]  ·  RSI: [X.X] [🔵/🟢/🟡/🔴]  ·  Action Zone: [🟢/🔴]

⛓️ Onchain
Realized $[V]  ·  STH $[V]  ·  LTH $[V]  |  TMM $[V]
MVRV [V] [🔵/🟢/🟡/🔴]  ·  STH [V]  ·  LTH [V]  |  Z-SCORE [V] [🔵/🟢/🟡/🔴]

🔗 Signal guide & emoji meanings link pinned in the comments below!
```

### Example

```
📊 Pixel Chart Diary - BTC Daily Status — @01 Jul 2026

🔴 BTC · $58,624.71  (-0.13%)

📈 Technical
• EMA 200: 🔴  ·  RSI: 30.6 🟢  ·  Action Zone: 🔴

⛓️ Onchain
Realized $51,775.63  ·  STH $69,352.76  ·  LTH $49,763.10  |  TMM $75,835.70
MVRV 1.13 🟢  ·  STH 0.87  ·  LTH 1.21  |  Z-SCORE 0.24 🟢

🔗 Signal guide & emoji meanings link pinned in the comments below!
```

---

## 3. Post Layout — Weekly

### Output Format

```
📊 Pixel Chart Diary - BTC Weekly Status — @{DD Mon YYYY} ({DD Mon} - {DD Mon})

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

### Example

```
📊 Pixel Chart Diary - BTC Weekly Status — @29 Jun 2026 (22 Jun - 28 Jun)

🔴 BTC · $58,624.71  (-6.55% 7d)

📈 Technical
• EMA 200: 🔴  ·  ADX: 37.9 🟢  ·  RSI: 30.6 🟢
• Action Zone: 🔴 $75,539.50 (40 days ago)
• Key Levels: R $60,260.21  ·  S N/A
• BOS: BOS confirmed

⛓️ Onchain
Realized $51,775.63  ·  STH $69,352.76  ·  LTH $49,763.10  |  TMM $75,835.70
NUPL 0.12 🟢  ·  Supply Profit 47.3%
✨ [AI read about Realized, TMM, NUPL, Supply Profit]
MVRV 1.13 🟢  ·  STH 0.87  ·  LTH 1.21  |  Z-SCORE 0.24 🟢
SOPR  ·  STH 1.000  ·  LTH 0.850
✨ [AI read about MVRV, Z-SCORE, SOPR]
F&G: 11 🔴  · Dom: 55.4%

🌊 Elliott Wave
✨ A-B-C correction · sharp drop from $82.8K peak to $58.6K, lost key $63K support with no bounce
〽️ Wave Patterns
✨ Descending channel · price pinned near channel lows, no reversal signal yet

🔗 Signal guide & emoji meanings link pinned in the comments below!
✨ = AI-generated insight
```

---

## 4. Schedule

| Channel            | Frequency | Time        | Cron        | Mode detection                                        |
| ------------------ | --------- | ----------- | ----------- | ----------------------------------------------------- |
| Discord + Facebook | Every day | 07:02 UTC+7 | `2 0 * * *` | Python checks weekday — Monday → weekly, else → daily |

---

## 5. Images (Weekly only)

| #   | Name        | Description                                          | File                          |
| --- | ----------- | ---------------------------------------------------- | ----------------------------- |
| 1   | Action Zone | Candlestick chart with EMA 200/12/26 + Action Zone   | `full-asset-image-candle.md`  |
| 2   | Onchain     | Line chart: Close price · Realized · STH · LTH · TMM | `full-asset-image-onchain.md` |

---

## 6. Data Sources

### Technical

| Value             | Source             | Method                                           |
| ----------------- | ------------------ | ------------------------------------------------ |
| Price & 24h/7d %  | Binance via `ccxt` | Daily open (00:00 UTC)                           |
| EMA 200 / 12 / 26 | `pandas_ta`        | Fetch 350 candles for complete EMA200 warmup     |
| ADX (14)          | `pandas_ta`        | >20 = trending 🟢 · ≤20 = ranging 🔴             |
| RSI (14)          | `pandas_ta`        | —                                                |
| Action Zone       | EMA12 vs EMA26     | Last sign change · 🟢 = EMA12 above · 🔴 = below |
| Key Levels (S/R)  | Pivot scan         | Swing highs/lows window=5                        |
| BOS               | Pivot scan         | SH/SL sequence                                   |

### Onchain

| Metric                   | Source                         | Notes                                      |
| ------------------------ | ------------------------------ | ------------------------------------------ |
| Realized Price (global)  | CoinMetrics Community API      | Derived: `price / MVRV`                    |
| MVRV (global)            | CoinMetrics Community API      | `CapMVRVCur`                               |
| NUPL                     | CoinMetrics Community API      | `1 − 1/MVRV`                               |
| Exchange Reserve + Flows | CoinMetrics Community API      | `SplyExNtv`, `FlowInExNtv`, `FlowOutExNtv` |
| STH / LTH Realized Price | btc.kaetkung.uk `/api/onchain` | Bearer `BTC_MONITOR_TOKEN`                 |
| True Market Mean (TMM)   | btc.kaetkung.uk `/api/onchain` | Bearer token                               |
| MVRV STH / LTH           | btc.kaetkung.uk `/api/onchain` | Bearer token                               |
| SOPR STH / LTH           | btc.kaetkung.uk `/api/onchain` | Bearer token                               |
| Supply in Profit %       | btc.kaetkung.uk `/api/onchain` | Bearer token                               |
| MVRV Z-Score             | btc.kaetkung.uk `/api/onchain` | `mvrv_z_score` key · Bearer token          |
| Fear & Greed             | alternative.me                 | `https://api.alternative.me/fng/`          |
| BTC Dominance            | CoinGecko                      | `GET /api/v3/global`                       |

### AI Read (Weekly only)

Claude (`claude-opus-4-7`) receives the last 120 daily candles (OHLCV) and relevant metrics, and outputs 4 lines:

```
Read1: [1-line insight on Realized / TMM / NUPL / Supply Profit]
Read2: [1-line insight on MVRV / Z-SCORE / SOPR]
Wave: [Elliott Wave call] · [1-line context]
Pattern: [chart pattern] · [brief note]
```

---

## 7. Per-Metric Thresholds

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

_Not financial advice_
