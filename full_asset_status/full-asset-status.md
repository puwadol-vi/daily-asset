# Daily Asset Status — Post Plan

Layout · Data Sources · Per-Asset Thresholds · Daily Workflow

---

## 1. Post Text Layout — 1 Asset per Post

### Crypto — Layout (Facebook)

```
📊 BTC Daily Status — [DATE e.g. Jun 14, 2026]

[🟢 BTC / 🔴 BTC] · $[PRICE]  ([+/-X.XX%])

📈 Technical
• EMA 200: [🟢/🔴] $[EMA200]  |  ADX: [VALUE] [🟢/🔴]  |  RSI: [VALUE] [🔵/🟢/🟡/🔴]
• Action Zone: [🟢/🔴] $[CROSS PRICE] [CROSS DATE] ([N] days)
• Key Levels: R $[RESISTANCE]  |  S $[SUPPORT]
• BOS: [HH/HL intact / LH forming — first warning / BOS confirmed]

🤖 AI Read
• Wave: [Wave 3 push / W4 pullback / W5 warn / A-B-C correction / Unclear] · [X% to R $Y / on S $Z]
• Pattern: [Bull flag / Bear flag / Ascending triangle / Wedge / No clear pattern]

🔗 Onchain
Realized Price [V] · MVRV [V] [🟢/🟡/🔴]
F&G: [VALUE] [Extreme Fear/Fear/Neutral/Greed/Extreme Greed]  · [ASSET] Dom: [X.X%] [↑/↓]
Net Unrealized P/L [V] [🟢/🟡/🔴] · Reserve [VALUE][↓/↑] [NET±FLOW][↓/↑] [🟢/🔴]
```

> Price = daily open (00:00 UTC) · % = today open vs yesterday open
> Action Zone: 🟢 = EMA12 above EMA26 · 🔴 = below
> Reserve: VALUE = exchange reserve (e.g. 2.64M BTC) · ↓/↑ = reserve trend · NET FLOW = inflow−outflow

### Crypto — Example (BTC, Jun 14, 2026)

```
📊 BTC Daily Status — Jun 14, 2026

🟢 BTC · $105,200  (+2.8%)

📈 Technical
• EMA 200: 🟢 $72,400  |  ADX: 34.6 🟢  |  RSI: 58 🟢
• Action Zone: 🟢 $87,500  Apr 15, 2026 (60 days)
• Key Levels: R $112,000  |  S $98,500
• BOS: HH/HL intact — 3 consecutive HHs, no warning

🤖 AI Read
• Wave: Wave 3 push ongoing · held $98,500 HL on Jun 12 · 6.5% to R $112,000
• Pattern: Bull flag on EMA50 retest — tight consolidation after impulse leg

🔗 Onchain
Realized Price $62,800 · MVRV 1.68 🟢
F&G: 72 Greed  · BTC Dom: 54.2% ↑
Net Unrealized P/L 0.41 🟢 · Reserve 2.64M↓ -4.5K↓ 🟢
```

### US Stock — Layout (Facebook)

```
📊 [TICKER] Daily Status — [DATE e.g. Jun 14, 2026]

[🟢 TICKER / 🔴 TICKER] · $[PRICE]  ([+/-X.XX%])

📈 Technical
• EMA 200: [🟢/🔴] $[EMA200]  |  ADX: [VALUE] [🟢/🔴]  |  RSI: [VALUE] [🔵/🟢/🟡/🔴]
• Action Zone: [🟢/🔴] $[CROSS PRICE] [CROSS DATE] ([N] days)
• Key Levels: R $[RESISTANCE]  |  S $[SUPPORT]
• BOS: [HH/HL intact / LH forming — first warning / BOS confirmed]

🤖 AI Read
• Wave: [Wave 3 push / W4 pullback / W5 warn / A-B-C correction / Unclear] · [X% to R $Y / on S $Z]
• Pattern: [Bull flag / Bear flag / Ascending triangle / Wedge / No clear pattern]
```

> Price = after 4pm ET close · No onchain section for stocks

### US Stock — Example (NVDA, Jun 14, 2026)

```
📊 NVDA Daily Status — Jun 14, 2026

🟢 NVDA · $131.40  (+2.30%)

📈 Technical
• EMA 200: 🟢 $118.60  |  ADX: 28.4 🟢  |  RSI: 62 🟢
• Action Zone: 🟢 $124.80  May 22, 2026 (23 days)
• Key Levels: R $138.00  |  S $124.80
• BOS: HH/HL intact — no LH, 23-day clean uptrend

🤖 AI Read
• Wave: Wave 3 extension in progress · 5% gap to R $138.00
• Pattern: Ascending channel — higher highs and higher lows along EMA50
```

---

## 2. Data Sources

### Technical (all assets — stocks & crypto)

| Value | Source | How to Calc | What to Record |
|---|---|---|---|
| Price & % | Binance · `ccxt` | Daily candle open (00:00 UTC). % = (today_open ÷ yesterday_open − 1) × 100 | Open price in USD · % change open-to-open |
| EMA 200 | `pandas_ta` | `ta.ema(close, 200).iloc[-1]`. Is close above (🟢) or below (🔴)? | EMA200 value · 🟢/🔴 |
| ADX (14) | `pandas_ta` | `ta.adx(H,L,C,14)['ADX_14'].iloc[-1]`. >20 = trending 🟢 · ≤20 = ranging 🔴 | ADX value · 🟢/🔴 |
| RSI (14) | `pandas_ta` | `ta.rsi(close, 14).iloc[-1]`. See thresholds in Section 3. | RSI value · 🔵/🟢/🟡/🔴 |
| Action Zone (EMA 12/26 cross) | `pandas_ta` | Find last index where sign of (EMA12 − EMA26) changed. 🟢 = EMA12 crossed above · 🔴 = below. Cross price = close[cross_idx]. Days = today − cross. | 🟢/🔴 · Cross price · Cross date · Days since |
| Key Levels (S/R) | Python pivot scan | Scan swing highs/lows with window=2. Nearest swing high above price = Resistance. Nearest swing low below = Support. | Resistance price · Support price |
| BOS (Break of Structure) | Python pivot scan | SH[−1] > SH[−2] && SL[−1] > SL[−2] → HH/HL intact · SH[−1] < SH[−2] → LH forming · close below last SL → BOS confirmed | HH/HL intact · LH forming · BOS confirmed |

### AI Read (Claude judgment)

| Value | How to Assess | What to Record |
|---|---|---|
| Wave (Elliott Wave) | Inspect last 20–50 daily candles. Count 5-wave impulse (1–5) or 3-wave correction (A-B-C). W2 retraces 50–61.8% of W1 · W3 extends 1.618× W1 · W4 retraces ~38.2% of W3 · W5 at 100–161.8% extension. | Wave 3 push / W4 pullback / W5 warn / A-B-C correction / Unclear |
| Pattern (Chart Patterns) | Bull flag = sharp rally + tight consolidation · Ascending triangle = flat resistance + rising lows · Wedge = converging trendlines + RSI divergence. Claude confirms breakout validity and wave context. | Pattern name · or "No clear pattern" |

### Onchain Metrics (crypto only)

| Metric | Source | How to Get | What to Record |
|---|---|---|---|
| Realized Price | CoinMetrics Community API (free) | Derived: `Realized Price = Current Price / MVRV`. Use `CapMVRVCur` from CoinMetrics + open price. | Realized Price value (USD) |
| MVRV Ratio | CoinMetrics Community API (free) | `CapMrktCurUSD / CapRealUSD`. Thresholds differ by asset — see Section 3. | MVRV value · 🟢/🟡/🔴 |
| F&G Index | alternative.me (free API) | `https://api.alternative.me/fng/` → `value` + `value_classification`. 0–24 Extreme Fear · 25–49 Fear · 50 Neutral · 51–74 Greed · 75–100 Extreme Greed. | Value · Sentiment label |
| Dominance % | CoinGecko API (free) | `GET /api/v3/global` → `market_cap_percentage`. Compare to yesterday for ↑/↓. | Dom% · ↑/↓ |
| Net Unrealized P/L (NUPL) | CoinMetrics Community API | `(CapMrktCurUSD - CapRealUSD) / CapMrktCurUSD`. See thresholds in Section 3. | NUPL value · 🟢/🟡/🔴 |
| Exchange Reserve + Flows | CoinMetrics Community API | `SplyExNtv` (reserve) · `FlowInExNtv` (inflow) · `FlowOutExNtv` (outflow). Net flow = inflow − outflow. Negative = net outflow (bullish). | Reserve value + trend ↓/↑ · Net flow ± · 🟢/🔴 |

> **Timing:** Crypto at 07:00 UTC+7 = midnight UTC = daily candle close. US stocks: 07:00 UTC+7 is after 4pm ET close.
> **Onchain cadence:** Full read once per week. Daily: note only if a metric's label changed since last week.

> **Python Auto-Calc Stack:** `pip install ccxt pandas pandas_ta numpy`
> - **Fully auto:** EMA200 · ADX · RSI · Action Zone · Key Levels · BOS
> - **Partial auto + Claude confirms:** Pattern
> - **Claude judgment only:** Wave (requires visual count)

---

## 3. Per-Metric Label Thresholds — by Asset

### MVRV Ratio

| Asset | 🔵 ADD | 🟢 BUY | 🟡 WARN | 🔴 EXIT |
|---|---|---|---|---|
| BTC | < 1.0 | 1.0 – 2.0 | 2.0 – 3.5 | > 3.5 |
| ETH | < 1.0 | 1.0 – 2.0 | 2.0 – 2.8 | > 2.8 |
| SOL | < 1.0 | 1.0 – 2.0 | > 2.0 | > 3.0 |
| BNB | < 1.0 | 1.0 – 2.0 | > 2.0 | > 3.0 |
| XRP | < 1.0 | 1.0 – 2.0 | > 2.0 | > 3.0 |

> ETH overheats faster — EXIT at 2.8, not 3.5. SOL / BNB / XRP have fewer cycles — use direction (rising vs falling) more than fixed numbers.

### Net Unrealized P/L (NUPL)

| Asset | 🔵 ADD | 🟢 BUY | 🟡 WARN | 🔴 EXIT | Notes |
|---|---|---|---|---|---|
| BTC | < 0 | 0 – 0.5 | 0.5 – 0.75 | > 0.75 | Hit 0.75+ right before Nov 2021 top ($69K) |
| ETH | < 0 | 0 – 0.5 | 0.5 – 0.73 | > 0.73 | ETH NUPL peaked ~0.73 in May 2021 |
| SOL | < 0 | 0 – 0.5 | > 0.5 | > 0.65 | Limited cycle history — use directionally |
| BNB | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Not reliable — skip. Use MVRV + SOPR + Reserve only. |
| XRP | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Not reliable — skip. Use MVRV + SOPR + Reserve only. |

### RSI (14) — Universal

| Condition | Label |
|---|---|
| RSI < 30 (oversold, bouncing) | 🔵 ADD |
| RSI 30 – 70 (healthy range) | 🟢 OK |
| RSI 70 – 80 (overbought caution) | 🟡 WARN |
| RSI > 80 (extreme — expect pullback) | 🔴 HIGH |

> Same thresholds for all assets. Strong uptrends can hold RSI 60–80 for weeks; watch for RSI divergence (price HH + RSI LH = bearish).

### Exchange Reserve + Net Flow

| Condition | Label |
|---|---|
| Reserve declining + net outflow | 🟢 BUY |
| Reserve at multi-year low + price low | 🔵 ADD |
| Reserve rising gradually 2–4 weeks | 🟡 WARN |
| Reserve spike + large net inflow at highs | 🔴 EXIT |
| Reserve flat, flows balanced | ⚪ SKIP |

> Source: CoinMetrics (`SplyExNtv`, `FlowInExNtv`, `FlowOutExNtv`). Reserve ↓ + net outflow together = strongest signal.

### Action Zone — EMA 12/26 Cross

| Condition | Label |
|---|---|
| EMA12 crosses above EMA26 | 🟢 |
| EMA12 crosses below EMA26 | 🔴 |

> Label doesn't change until next cross. **Days count matters:** 3 days ago = fresh signal · 60 days ago = stale context.

### Realized Price — Context

| Condition | Meaning |
|---|---|
| Price well below Realized | 🔵 ADD — market in loss (historically rare) |
| Price at or just above Realized | 🟢 BUY — just turned profitable |
| Price 2–3× above Realized | 🟡 WARN — market well in profit |
| Price >3× Realized | 🔴 EXIT zone — late cycle |

> Realized Price is displayed in the post as a raw value — no emoji label. Use this table to cross-check MVRV and confirm Wave/Pattern context.

---

## 4. Onchain — What to Include Per Asset

| Asset | Technical + AI Read | Onchain metrics |
|---|---|---|
| BTC / ETH | EMA200 · ADX · RSI · Action Zone · BOS · Wave · Pattern | Realized Price · MVRV · NUPL · Reserve + Flows · F&G · Dom |
| SOL | EMA200 · ADX · RSI · Action Zone · BOS · Wave · Pattern | Realized Price · MVRV · Reserve (NUPL: skip) |
| BNB / XRP | EMA200 · ADX · RSI · Action Zone · BOS | Realized Price · MVRV direction · Reserve (NUPL: skip) |
| US Stocks | EMA200 · ADX · RSI · Action Zone · BOS · Wave · Pattern | N/A — no onchain line |

---

*Trading Strategy Reference · Daily Timeframe · Not financial advice*
