# Pixel Art Chart — Image Plan

Action Zone (EMA 12/26) · EMA 200 · Asset+date label · Cross marker · Pixel price/month labels

---

## 1. Grid Specification

| Parameter | Value | Notes |
|---|---|---|
| Internal grid | `200 × 105 px` | Drawing canvas |
| Scale | `× 6 NEAREST` | Hard pixel edges, no interpolation |
| Output | `1200 × 630 px` | Facebook OG · Discord embed |
| Margins | T:8 · L:4 · R:20 · B:13 | R:20 for price labels · B:13 for month labels |
| Chart area | `cw=176 · ch=84` | cx=4, cy=8 |
| Candle slot | `3 px` (2 body + 1 gap) | 58 candles × 3 = 174 px → centered in 176 px |
| Candles shown | `58` daily | ≈ 2 months |

---

## 2. Color Palette

| Element | Color | Hex |
|---|---|---|
| Background | Near black | `#0d0d0d` |
| All candle bodies | Bitcoin orange (up & down same) | `#F7931A` |
| All candle wicks | Darker orange (up & down same) | `#b86c10` |
| EMA 200 | Indigo · dotted every 2nd slot | `#6366f1` |
| EMA 12 | Green · every slot col 0 | `#22c55e` |
| EMA 26 | Red · every slot col 1 | `#ef4444` |
| Action zone fill (bull) | Solid dark green fill | `rgb(16,39,24)` |
| Action zone fill (bear) | Solid dark red fill | `rgb(45,21,21)` |
| Cross marker (bull) | Green 2×2 dot above candle high | `rgb(34,197,94)` |
| Cross marker (bear) | Red 2×2 dot below candle low | `rgb(239,68,68)` |
| Asset+date label | Dim gray pixel font · top-left | `rgb(74,74,90)` |
| Price labels | Dim gray pixel font · right side | `rgb(74,74,90)` |
| Month labels | Dimmer gray pixel font · bottom | `rgb(58,58,74)` |

---

## 3. Visual Elements — Draw Order

| # | Element | How drawn | Data field |
|---|---|---|---|
| 0 | Asset + date label | Top-left inside top margin (y=1) · pixel font · e.g. `BTC 16JUN2026` | last `ts` from `ohlcv_last_60` |
| 1 | Background | Fill entire grid `rgb(13,13,13)` | — |
| 2 | Action zone fill | Vertical 2px solid band per slot between EMA12 and EMA26. Dark green if bull · dark red if bear. | `ema12_series · ema26_series` |
| 3 | Candles | Wick 1px col 0 (darker orange) · Body 2px cols 0–1 (bitcoin orange) · min body 1px · same color up & down | `ohlcv_last_60` |
| 2.5 | Cross marker | One 2×2 dot at most recent EMA12/26 crossover candle. Green dot 3px above high (bull cross) · Red dot 2px below low (bear cross). | `ema12_series · ema26_series · ohlcv_last_60` |
| 4 | EMA 200 | 1px dot at slot col 1 · every other slot (sparse dotted) | `ema200_series` |
| 5 | EMA 12 | 1px dot at slot col 0 · every slot | `ema12_series` |
| 6 | EMA 26 | 1px dot at slot col 1 · every slot | `ema26_series` |
| 7 | Price labels | Right of chart · every **4000 USD** · pixel font 3×5 · right-aligned · skip if <7px from prev label | `pmin / pmax` from ohlcv + all EMA series |
| 8 | Month labels | Below chart · first candle of each month · month name only (JAN/FEB…) · pixel font 3×5 · hide if <8px from chart edge | timestamps in `ohlcv_last_60` |

---

## 4. Pixel Font — 3 × 5 Bitmap

| Property | Value |
|---|---|
| Glyph size | 3 px wide · 5 px tall |
| Char spacing | 1 px gap between chars → 4 px per char total |
| "100K" width | 4 chars × 4 − 1 = `15 px` → fits in 20 px right margin |
| "JUN" width | 3 chars × 4 − 1 = `11 px` → centered under month boundary candle |
| Chars defined | 0–9 · A B C D E F G J K L M N O P R S T U V Y |
| Price format | `NNK` or `NNNK` — e.g. `96K`, `100K`, `104K` · step = 4000 USD |
| Date format | 3-letter month name — `APR`, `MAY`, `JUN` |

**Candle anatomy:**
- Wick — 1px wide (col 0) · full high→low · darker orange `#b86c10`
- Body — 2px wide (cols 0–1) · open→close · bitcoin orange `#F7931A` · same up & down
- Gap — col 2 · empty · separates next candle

---

## 5. Data Mapping — fetch\_btc.py → generate\_chart\_btc.py

| fetch\_btc.py field | Type | Used for |
|---|---|---|
| `ohlcv_last_60` | list[dict] · 60 items · {open,high,low,close,ts} | Candlesticks · price scale · price labels |
| `ema200_series` | list[float] · 60 values | EMA 200 indigo dotted line |
| `ema12_series` | list[float] · 60 values | EMA 12 green line · action zone top/bottom |
| `ema26_series` | list[float] · 60 values | EMA 26 red line · action zone top/bottom |

> `fetch_btc.py` fetches **250 candles** to compute accurate EMA200. Slices last 60 for display.
> EMA12 and EMA26 pre-computed across all 250 candles, last 60 values stored in `ema12_series` and `ema26_series`.

---

## 6. Shared Data Flow

```
run_full_btc.py
│
├── data = fetch_btc.fetch_all()
│     └── OHLCV: Binance/ccxt · price = daily open
│         Onchain: CoinMetrics community (MVRV, exchange reserve/flows)
│         F&G: alternative.me · BTC Dom: CoinGecko
│         includes: ohlcv_last_60, ema200/12/26_series + all other fields
│
├── img_path = generate_chart_btc.generate(data)
│     uses: ohlcv_last_60, ema200_series, ema12_series, ema26_series
│     → pixel art PNG 1200×630
│
├── system_p, user_msg, partial = prompt_btc.build_prompt(data)
│     uses: price, change_24h, ema200, adx, rsi, action_zone,
│           bos_status, mvrv, realized_price, nupl,
│           exchange_reserve, exchange_net_flow,
│           fg_value, btc_dominance,
│           ohlcv_last_60  ← Wave/Pattern analysis
│
├── discord_msg = claude_api(system_p, user_msg) → assemble(partial, ai_read)
│
└── post_discord(discord_msg, img_path)
      → one multipart POST · image appears above text in Discord
```
