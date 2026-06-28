# Full Asset Status — Plan

Layout · Data Sources · Per-Asset Thresholds · Workflow

---

## 1. Post Layout — BTC Weekly

### Output Format

```
📊 BTC Weekly Status — [DATE e.g. Jun 28, 2026]

[🟢 BTC / 🔴 BTC] · $[PRICE]  ([+/-X.XX%] 7d)

📈 Technical
• EMA 200: [🟢/🔴]  |  ADX: [X.X] [🟢/🔴]  |  RSI: [X.X] [🔵/🟢/🟡/🔴]
• Action Zone: [🟢/🔴] $[CROSS PRICE] ([N] days ago)
• Key Levels: R $[RESISTANCE]  |  S $[SUPPORT]
• BOS: [HH/HL intact — N consecutive HHs / LH forming — first warning / BOS confirmed]

🔗 Onchain
Realized $[V]  ·  STH $[V]  ·  LTH $[V]  ·  TMM $[V]
MVRV [V] [🔵/🟢/🟡/🔴]  ·  STH [V]  ·  LTH [V]
SOPR  ·  STH [V]  ·  LTH [V]  ·  Supply Profit [X%]
F&G: [VALUE] [Label]  · Dom: [X.X%]
NUPL [V] [🔵/🟢/🟡/🔴]  ·  Reserve [VALUE][↓/↑] [±FLOW]

🤖 AI Read
• Wave: [call] · [1-line context]
• Pattern: [call]
```

### Example

```
📊 BTC Weekly Status — Jun 28, 2026

🔴 BTC · $61,200  (-4.30% 7d)

📈 Technical
• EMA 200: 🔴  |  ADX: 28.4 🟢  |  RSI: 38.2 🟢
• Action Zone: 🔴 $72,400 (45 days ago)
• Key Levels: R $68,000  |  S $58,500
• BOS: LH forming — first warning

🔗 Onchain
Realized $53,194  ·  STH $70,758  ·  LTH $49,768  ·  TMM $90,631
MVRV 1.12 🟢  ·  STH 0.88  ·  LTH 1.26
SOPR  ·  STH 0.990  ·  LTH 0.790  ·  Supply Profit 50.0%
F&G: 13 Extreme Fear  · Dom: 55.7%
NUPL 0.11 🟢  ·  Reserve 2.65M↑ +41

🤖 AI Read
• Wave: A-B-C correction · testing $58,500 S zone
• Pattern: Descending channel — lower highs since May top
```

---

## 2. Schedule

| Channel | Frequency | Time | Cron |
|---|---|---|---|
| Discord (both webhooks) | Weekly | Monday 07:02 UTC+7 | `2 0 * * 0` |
| Facebook Page (LNconnext) | Weekly | Monday 07:02 UTC+7 | `2 0 * * 0` |

---

## 3. Data Sources

### Technical

| Value | Source | Method |
|---|---|---|
| Price & 7d % | Binance via `ccxt` | Daily open (00:00 UTC). 7d % = (today_open ÷ open_8_days_ago − 1) × 100 |
| EMA 200 / 12 / 26 | `pandas_ta` | `ta.ema(close, N)`. Fetch 350 candles for complete EMA200 warmup |
| ADX (14) | `pandas_ta` | `ta.adx(H,L,C,14)`. >20 = trending 🟢 · ≤20 = ranging 🔴 |
| RSI (14) | `pandas_ta` | `ta.rsi(close, 14)` |
| Action Zone | `pandas_ta` | Last sign change of (EMA12 − EMA26). 🟢 = EMA12 above · 🔴 = below |
| Key Levels (S/R) | pivot scan | Swing highs/lows with window=5 |
| BOS | pivot scan | SH/SL sequence |

### Onchain

| Metric | Source | Notes |
|---|---|---|
| Realized Price (global) | CoinMetrics Community API (free) | Derived: `price / MVRV` |
| MVRV (global) | CoinMetrics Community API (free) | `CapMVRVCur` |
| NUPL | CoinMetrics Community API (free) | `1 − 1/MVRV` |
| Exchange Reserve + Flows | CoinMetrics Community API (free) | `SplyExNtv`, `FlowInExNtv`, `FlowOutExNtv` |
| STH / LTH Realized Price | btc.kaetkung.uk `/api/onchain` | Bearer token (`BTC_MONITOR_TOKEN`) |
| True Market Mean (TMM) | btc.kaetkung.uk `/api/onchain` | Bearer token |
| MVRV STH / LTH | btc.kaetkung.uk `/api/onchain` | Bearer token |
| SOPR STH / LTH | btc.kaetkung.uk `/api/onchain` | Bearer token |
| Supply in Profit % | btc.kaetkung.uk `/api/onchain` | Bearer token |
| Fear & Greed | alternative.me (free) | `https://api.alternative.me/fng/` |
| BTC Dominance | CoinGecko (free) | `GET /api/v3/global` |

### AI Read

Claude (`claude-opus-4-7`) receives the last 120 daily candles (OHLCV) and outputs:
- **Wave**: Elliott Wave position + 1-line context
- **Pattern**: Chart pattern name + brief note

---

## 4. Chart — Pixel Art (`generate_chart_btc.py`)

| Setting | Value |
|---|---|
| Canvas | 400 × 210 px → scaled 3× → **1200 × 630 px output** |
| Candles shown | 120 daily candles |
| Font scale | S=2 (3×5 → 6×10 px per character) |
| Candle width | 2 px body · 3 px slot |
| EMA 200 | Indigo dotted line · hidden if >5% outside candle range |
| EMA 12 | Green line |
| EMA 26 | Red line |
| Action zone | Filled area between EMA12/26 · 2×2 px cross marker at every cross |
| Header | Date (left) · "EMA 200" label (right, indigo) |

---

## 5. Facebook Posting (`run_full_btc.py`)

Two-step with Page Access Token (`FACEBOOK_PAGE_ID=760212033839028`):

```
Step 1: POST /{page-id}/photos
        data={'published': 'false', 'access_token': token}
        files={'source': <binary image>}
        → returns photo_id

Step 2: POST /{page-id}/feed
        json={'message': caption, 'attached_media': [{'media_fbid': photo_id}]}
        → creates feed post with image + caption (UTF-8 → emojis work)
```

**Required `.env` keys:**
```
FACEBOOK_PAGE_ID=760212033839028
FACEBOOK_PAGE_TOKEN=<Page Access Token from Graph API Explorer → LNconnext>
```

---

## 6. Per-Metric Thresholds

### MVRV

| 🔵 ADD | 🟢 HOLD | 🟡 WARN | 🔴 EXIT |
|---|---|---|---|
| < 1.0 | 1.0 – 2.0 | 2.0 – 3.5 | > 3.5 |

### NUPL

| 🔵 | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| < 0 | 0 – 0.5 | 0.5 – 0.75 | > 0.75 |

### RSI (14)

| < 30 | 30 – 70 | 70 – 80 | > 80 |
|---|---|---|---|
| 🔵 | 🟢 | 🟡 | 🔴 |

---

*Weekly · BTC only · Not financial advice*
