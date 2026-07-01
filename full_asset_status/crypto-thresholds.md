# Per-Metric Label Thresholds — by Asset

Each asset uses different numeric thresholds. Do not apply BTC numbers to ETH, SOL, BNB, or XRP.

---

## MVRV Ratio

| Asset | 🔵 ADD | 🟢 BUY | 🟡 WARN | 🔴 EXIT |
|---|---|---|---|---|
| BTC | < 1.0 | 1.0 – 2.0 | 2.0 – 3.5 | > 3.5 |
| ETH | < 1.0 | 1.0 – 2.0 | 2.0 – 2.8 | > 2.8 |
| SOL | < 1.0 | 1.0 – 2.0 | > 2.0 | > 3.0 |
| BNB | < 1.0 | 1.0 – 2.0 | > 2.0 | > 3.0 |
| XRP | < 1.0 | 1.0 – 2.0 | > 2.0 | > 3.0 |

> ETH overheats faster — EXIT at 2.8, not 3.5. SOL / BNB / XRP have fewer cycles — use direction (rising vs falling) more than fixed numbers; EXIT bars set lower as a precaution.

---

## Net Unrealized P/L (NUPL)

| Asset | 🔵 ADD | 🟢 BUY | 🟡 WARN | 🔴 EXIT | Notes |
|---|---|---|---|---|---|
| BTC | < 0 | 0 – 0.5 | 0.5 – 0.75 | > 0.75 | Hit 0.75+ right before Nov 2021 top ($69K) |
| ETH | < 0 | 0 – 0.5 | 0.5 – 0.73 | > 0.73 | ETH NUPL peaked ~0.73 in May 2021 |
| SOL | < 0 | 0 – 0.5 | > 0.5 | > 0.65 | Limited cycle history — use directionally |
| BNB | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Not reliable — skip. Use MVRV + SOPR + Reserve only. |
| XRP | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Not reliable — skip. Use MVRV + SOPR + Reserve only. |

---

## RSI (14) — Universal (all assets)

| Condition | Emoji |
|---|---|
| RSI < 30 (oversold, bouncing) | 🔵 ADD |
| RSI 30 – 70 (healthy range) | 🟢 OK |
| RSI 70 – 80 (overbought caution) | 🟡 WARN |
| RSI > 80 (extreme — expect pullback) | 🔴 HIGH |

> Same thresholds for all assets. Strong uptrends can hold RSI 60–80 for weeks; watch for RSI divergence (price HH + RSI LH = bearish).

---

## Exchange Reserve + Net Flow

| Condition | Label |
|---|---|
| Reserve declining + net outflow | 🟢 BUY |
| Reserve at multi-year low + price low | 🔵 ADD |
| Reserve rising gradually 2–4 weeks | 🟡 WARN |
| Reserve spike + large net inflow at highs | 🔴 EXIT |
| Reserve flat, flows balanced | ⚪ SKIP |

> Source: CoinMetrics community (`SplyExNtv`, `FlowInExNtv`, `FlowOutExNtv`). Net flow = inflow − outflow; negative = coins leaving exchanges (bullish). Reserve ↓ + net outflow together = strongest signal.

---

## Action Zone — EMA 12 / 26 Cross

| Condition | Label |
|---|---|
| EMA12 crosses above EMA26 | 🟢 |
| EMA12 crosses below EMA26 | 🔴 |

> Same threshold for all assets — label doesn't change until next cross. **Days count matters:** 3 days ago = fresh signal · 60 days ago = stale context.

---

## Realized Price — Context

| Condition | Meaning |
|---|---|
| Price well below Realized | 🔵 ADD — market in loss (historically rare) |
| Price at or just above Realized | 🟢 BUY — just turned profitable |
| Price 2–3× above Realized | 🟡 WARN — market well in profit |
| Price > 3× Realized | 🔴 EXIT zone — late cycle |

> Realized Price is displayed in the post as a raw value — no emoji label. Use this table to cross-check MVRV and confirm Wave / Pattern context.

---

## Onchain — What to Include Per Asset

| Asset | Technical + AI Read | Onchain metrics | Post Onchain Line |
|---|---|---|---|
| BTC / ETH | EMA200 · ADX · RSI · Action Zone · BOS · Wave · Pattern | Realized Price · MVRV · NUPL · Exchange Reserve + Flows | `Realized [V] · MVRV [V] 🟢` · `F&G [V] · Dom [X%]` · `NUPL [V] 🟢 · Reserve [V][↓/↑] [±FLOW]` |
| SOL | EMA200 · ADX · RSI · Action Zone · BOS · Wave · Pattern | Realized Price · MVRV · Reserve (NUPL: limited — skip) | `Realized [V] · MVRV [V] 🟢` · `F&G [V] · Dom [X%]` · `Reserve [V][↓/↑] [±FLOW]` |
| BNB / XRP | EMA200 · ADX · RSI · Action Zone · BOS | Realized Price · MVRV (direction) · Reserve (NUPL: ⚠️ skip) | `Realized [V] · MVRV [V] 🟢` · `F&G [V] · Dom [X%]` · `Reserve [V][↓/↑] [±FLOW]` |
| US Stocks | EMA200 · ADX · RSI · Action Zone · BOS · Wave · Pattern | N/A | No onchain line. |
