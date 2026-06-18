# Daily Multi Asset Status — Plan

## 1. Emoji System

Format: `[REGIME][POSITION][DIR]`

| Part | Options | Meaning |
|---|---|---|
| REGIME | 📈 📉 | EMA50 > EMA100 = bull · EMA50 < EMA100 = bear |
| POSITION | 🔵 ⚪ 🔴 🟡 🟢 | price state (see below) |
| DIR | ↑ ↓ (suffix) | cross direction — only on cross day |

---

## 2. Position States

### Static (no cross today)

| Emoji | Condition | Note |
|---|---|---|
| 🔵 | price > EMA50 > EMA100  OR  price < EMA50 < EMA100 | Aligned with regime — price where expected |
| ⚪ | price between EMA50 and EMA100 | Transition zone |
| 🔴 | price < EMA100 < EMA50  OR  price > EMA100 > EMA50 | Diverged — price past BOTH EMAs against regime |

### Cross Events (today only — override static)

| Emoji | Signal | Risk |
|---|---|---|
| 🟡 | price crossed EMA50 | Fast signal — risky, may reverse |
| 🟢 | price crossed EMA100 | Slow signal — confirmed, sure trend |

---

## 3. Full State Table

### Bull Regime — 📈 (EMA50 > EMA100)

| Display | State | Trader Read |
|---|---|---|
| 📈🔵 | price > EMA50 > EMA100 | Clean bull, hold |
| 📈⚪ | EMA100 < price < EMA50 | Pulled back into support zone |
| 📈🔴 | price < EMA100 < EMA50 | Below key level — caution |
| 📈🟡↓ | crossed below EMA50 today | Fast warning — watch |
| 📈⚪ | day after 🟡↓, no further drop | Holding in support zone |
| 📈🟢↓ | crossed below EMA100 today | Confirmed breakdown |
| 📈🟡↑ | crossed above EMA50 today | Recovery — re-entry signal |
| 📈🔵 | day after 🟡↑, above EMA50 | Bull restored |
| 📈🟢↑ | crossed above EMA100 today | Full recovery confirmed |

### Bear Regime — 📉 (EMA50 < EMA100)

| Display | State | Trader Read |
|---|---|---|
| 📉🔵 | price < EMA50 < EMA100 | Clean bear, avoid / short |
| 📉⚪ | EMA50 < price < EMA100 | Testing resistance zone |
| 📉🔴 | price > EMA100 > EMA50 | Above key level — possible reversal |
| 📉🟡↑ | crossed above EMA50 today | Recovery attempt — risky, watch |
| 📉⚪ | day after 🟡↑, no further rise | Still in resistance zone |
| 📉🟢↑ | crossed above EMA100 today | Breakout — regime may flip soon |
| 📉🟡↓ | crossed below EMA50 today | Failed recovery |
| 📉🔵 | day after 🟡↓, below EMA50 | Bear restored |
| 📉🟢↓ | crossed below EMA100 today | Confirmed breakdown |

---

## 4. Trader Logic

**Bull regime — track BOTH cross directions:**
- 📈🟡↓ = pullback into EMA50 zone (healthy correction or start of reversal — watch)
- 📈🟢↓ = broke below EMA100 (stronger warning)
- 📈🟡↑ = re-crossed above EMA50 (re-entry signal after pullback) ← do not miss
- 📈🟢↑ = re-crossed above EMA100 (full bull confirmed again)

**Bear regime — focus on cross UP (but track both):**
- 📉🟡↑ = first recovery sign — risky, needs confirmation
- 📉🟢↑ = broke above EMA100 — strong signal, regime may flip
- 📉🟡↓ = failed recovery, bear continuing
- 📉🟢↓ = confirmed deeper bear

---

## 5. Template

```
📊 US Stock Status — [DATE]

[S] [TICKER]   $[PRICE]   [+/-X.X%]
[S] [TICKER]   $[PRICE]   [+/-X.X%]
[S] [TICKER]   $[PRICE]   [+/-X.X%]
...

🔵 aligned  ⚪ zone  🔴 diverged
🟡↑↓ EMA50 cross (fast)  🟢↑↓ EMA100 cross (slow)
📈 bull (E50>E100)  📉 bear (E50<E100)
```

---

## 6. Example

```
📊 US Stock Status — Jun 16, 2026

📈🔵  GOOG    $175.20   +1.2%
📈🔵  MSFT    $430.50   +0.8%
📈🟡↓ NVDA    $131.40   -0.3%
📈⚪  AMD     $162.80   +0.4%
📈🔴  AAPL    $198.00   -1.5%
📉🔵  NFLX    $658.00   -2.8%
📉⚪  META    $520.00   -1.1%
📉🟢↑ TSLA    $312.00   +3.2%

🔵 aligned  ⚪ zone  🔴 diverged
🟡↑↓ EMA50 cross (fast/risk)  🟢↑↓ EMA100 cross (slow/sure)
📈 bull (E50>E100)  📉 bear (E50<E100)
```

---

## 7. Data & Detection

**Per stock (daily close):**
```python
regime_bull     = ema50 > ema100
regime          = '📈' if regime_bull else '📉'

cross_e50_up    = (price > ema50)  and (price_prev <= ema50_prev)
cross_e50_down  = (price < ema50)  and (price_prev >= ema50_prev)
cross_e100_up   = (price > ema100) and (price_prev <= ema100_prev)
cross_e100_down = (price < ema100) and (price_prev >= ema100_prev)

# EMA100 cross takes priority over EMA50 cross
if cross_e100_up:    status = f'{regime}🟢↑'
elif cross_e100_down: status = f'{regime}🟢↓'
elif cross_e50_up:   status = f'{regime}🟡↑'
elif cross_e50_down: status = f'{regime}🟡↓'
else:
    if regime_bull:
        if price > ema50:    status = f'{regime}🔵'
        elif price > ema100: status = f'{regime}⚪'
        else:                status = f'{regime}🔴'
    else:
        if price < ema50:    status = f'{regime}🔵'
        elif price < ema100: status = f'{regime}⚪'
        else:                status = f'{regime}🔴'
```

**Data source:** Yahoo Finance (`yfinance`) · `ta.ema(close, 50)` · `ta.ema(close, 100)`
