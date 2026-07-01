# Pixel Art Chart — Image Plan

Action Zone (EMA 12/26) · EMA 200 · Asset+date label · Cross markers · Pixel price/month labels

---

## 1. Grid Specification

| Parameter     | Value                    | Notes                                                               |
| ------------- | ------------------------ | ------------------------------------------------------------------- |
| Internal grid | `400 × 210 px`           | Drawing canvas                                                      |
| Scale         | `× 3 NEAREST`            | Hard pixel edges, no interpolation                                  |
| Output        | `1200 × 630 px`          | Facebook OG · Discord embed                                         |
| Margins       | T:16 · L:8 · R:32 · B:26 | R:32 for price labels ("100K" = 30px + 2px) · B:26 for month labels |
| Chart area    | `cw=360 · ch=168`        | cx=8, cy=16                                                         |
| Candle slot   | `3 px` (2 body + 1 gap)  | 120 candles × 3 = 360 px → exactly fills cw                         |
| Candles shown | `120` daily              | ≈ 4 months                                                          |

---

## 2. Color Palette

| Element                  | Color                            | Hex               |
| ------------------------ | -------------------------------- | ----------------- |
| Background               | Near black                       | `#0d0d0d`         |
| All candle bodies        | Bitcoin orange (up & down same)  | `#F7931A`         |
| All candle wicks         | Darker orange (up & down same)   | `#b86c10`         |
| EMA 200                  | Indigo · dotted every 2nd slot   | `#6366f1`         |
| EMA 12                   | Green · every slot col 0         | `#22c55e`         |
| EMA 26                   | Red · every slot col 1           | `#ef4444`         |
| Action zone fill (bull)  | Solid dark green fill            | `rgb(16,39,24)`   |
| Action zone fill (bear)  | Solid dark red fill              | `rgb(45,21,21)`   |
| Cross marker (bull)      | Green 2×2 dot above candle high  | `rgb(34,197,94)`  |
| Cross marker (bear)      | Red 2×2 dot below candle low     | `rgb(239,68,68)`  |
| Asset+date label         | Dim gray pixel font · top-left   | `rgb(74,74,90)`   |
| EMA 200 header indicator | Indigo pixel font · top-right    | `rgb(99,102,241)` |
| Price labels             | Dim gray pixel font · right side | `rgb(74,74,90)`   |
| Price tick               | Dark gray 2px tick               | `rgb(34,34,34)`   |
| Month labels             | Dimmer gray pixel font · bottom  | `rgb(58,58,74)`   |
| Month tick               | Darker gray 3px tick             | `rgb(41,41,51)`   |

---

## 3. Visual Elements — Draw Order

| #   | Element          | How drawn                                                                                                                                 | Data field                                     |
| --- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| 0   | Header labels    | Left: `BTC 29JUN2026` at (cx+1, y=2) · Right: `EMA 200` in indigo at (cx+cw-1, y=2)                                                       | last `ts` from `ohlcv_last_120`                |
| 1   | Action zone fill | Vertical 2px solid band per slot between EMA12 and EMA26. Dark green `rgb(16,39,24)` if bull · dark red `rgb(45,21,21)` if bear.          | `ema12_series · ema26_series`                  |
| 2   | Candles          | Wick 1px col 0 (darker orange) · Body 2px cols 0–1 (bitcoin orange) · min body 1px · same color up & down                                 | `ohlcv_last_120`                               |
| 2.5 | Cross markers    | 2×2 dot at **every** EMA12/26 crossover in 120-candle window. Green dot 3px above high (bull cross) · Red dot 2px below low (bear cross). | `ema12_series · ema26_series · ohlcv_last_120` |
| 3   | EMA 200          | 1px dot at slot col 1 · every other slot (sparse dotted) · clipped if >5% outside candle range                                            | `ema200_series`                                |
| 4   | EMA 12           | 1px dot at slot col 0 · every slot                                                                                                        | `ema12_series`                                 |
| 5   | EMA 26           | 1px dot at slot col 1 · every slot                                                                                                        | `ema26_series`                                 |
| 6   | Price labels     | Right of chart · every **4000 USD** · pixel font · right-aligned at (GRID_W-2, y-5) · skip if <(font_height+gap) from prev label          | `pmin / pmax` from ohlcv + all EMA series      |
| 7   | Month labels     | Below chart · first candle of each month · month name only (JAN/FEB…) · pixel font · hide if <11px from chart edge                        | timestamps in `ohlcv_last_120`                 |

---

## 4. Pixel Font — 3 × 5 Bitmap

| Property      | Value                                                                         |
| ------------- | ----------------------------------------------------------------------------- |
| Glyph size    | 3 px wide · 5 px tall                                                         |
| Scale factor  | `S = 2` → each pixel rendered as a 2×2 block                                  |
| Char spacing  | 1 px gap between chars → 4 px per char (×S = 8 px rendered)                   |
| "100K" width  | 4 chars × 4 − 1 = `15 px` (×S = 30 px) → fits in 32 px right margin           |
| "JUN" width   | 3 chars × 4 − 1 = `11 px` (×S = 22 px) → centered under month boundary candle |
| Chars defined | 0–9 · A B C D E F G J K L M N O P R S T U V Y                                 |
| Price format  | `NNK` or `NNNK` — e.g. `96K`, `100K`, `104K` · step = 4000 USD                |
| Date format   | `DDMMMYYYY` — e.g. `29JUN2026`                                                |

**Candle anatomy:**

- Wick — 1px wide (col 0) · full high→low · darker orange `#b86c10`
- Body — 2px wide (cols 0–1) · open→close · bitcoin orange `#F7931A` · same up & down
- Gap — col 2 · empty · separates next candle

---

## 5. Data Mapping — fetch_btc.py → generate_chart_btc.py

| fetch_btc.py field | Type                                              | Used for                                   |
| ------------------ | ------------------------------------------------- | ------------------------------------------ |
| `ohlcv_last_120`   | list[dict] · 120 items · {open,high,low,close,ts} | Candlesticks · price scale · price labels  |
| `ema200_series`    | list[float] · 120 values                          | EMA 200 indigo dotted line                 |
| `ema12_series`     | list[float] · 120 values                          | EMA 12 green line · action zone top/bottom |
| `ema26_series`     | list[float] · 120 values                          | EMA 26 red line · action zone top/bottom   |

> `fetch_btc.py` fetches **350 candles** (200 warmup + 120 chart + buffer) to compute accurate EMA200. Slices last 120 for display.
> EMA12 and EMA26 pre-computed across all candles; last 120 values stored in `ema12_series` and `ema26_series`.

---

## 6. Cache

Shared cache file at repo root: `../cache.json`

- `btc.dominance` — BTC dominance direction vs yesterday
- `price_history` — daily snapshots (close, realized, sth, lth, tmm) for onchain chart

---

## 7. Shared Data Flow

```
run_full_btc.py
│
├── data = fetch_btc.fetch_all()
│     └── OHLCV: Binance/ccxt · price = daily open
│         Onchain: CoinMetrics community (MVRV, exchange reserve/flows)
│         F&G: alternative.me · BTC Dom: CoinGecko
│         btc.kaetkung.uk: STH/LTH realized, MVRV/SOPR cohorts, supply profit
│         includes: ohlcv_last_120, ema200/12/26_series + all other fields
│
├── img_path = generate_chart_btc.generate(data)
│     uses: ohlcv_last_120, ema200_series, ema12_series, ema26_series
│     → pixel art PNG 1200×600
│
├── system_p, user_msg, partial = prompt_btc.build_prompt(data)
│     uses: price, change_7d, ema200, adx, rsi, action_zone,
│           bos_status, mvrv, realized_price, nupl,
│           realized_price_sth/lth, true_market_mean,
│           mvrv_sth/lth, sopr_sth/lth, supply_in_profit_pct,
│           exchange_reserve, exchange_net_flow,
│           fg_value, btc_dominance,
│           ohlcv_last_120  ← Wave/Pattern analysis
│
├── discord_msg = claude_api(system_p, user_msg) → assemble(partial, ai_read)
│
└── post_discord(discord_msg, img_path) + post_facebook(img_path, discord_msg)
      → Discord: multipart POST · image above text
      → Facebook: upload photo unpublished → create feed post with attachment
```
