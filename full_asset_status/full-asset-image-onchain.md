# Onchain Price Levels Chart — Image Plan (New Image)

Close · Realized · STH · LTH · TMM — pixel art line chart

Used in **weekly posts only** as the second image alongside the candle chart.

---

## 1. Grid Specification

| Parameter     | Value                    | Notes                              |
| ------------- | ------------------------ | ---------------------------------- |
| Internal grid | `400 × 210 px`           | Same canvas as candle chart        |
| Scale         | `× 3 NEAREST`            | Hard pixel edges, no interpolation |
| Output        | `1200 × 630 px`          | Facebook OG · Discord embed        |
| Margins       | T:16 · L:8 · R:32 · B:26 | Same as candle chart               |
| Chart area    | `cw=360 · ch=168`        | cx=8, cy=16                        |
| Data points   | `120 daily candles`      | Same window as candle chart        |
| Style         | Line chart (no candles)  | One dot per day per line           |

---

## 2. Lines & Colors

| Line             | Color          | Hex       | Source field                        |
| ---------------- | -------------- | --------- | ----------------------------------- |
| Close price      | Bitcoin orange | `#F7931A` | `ohlcv_last_120[i]['close']`        |
| Realized Price   | Blue           | `#6366f1` | `realized_price` (cached daily)     |
| STH Realized     | Red            | `#ef4444` | `realized_price_sth` (cached daily) |
| LTH Realized     | Green          | `#22c55e` | `realized_price_lth` (cached daily) |
| True Market Mean | Light gray     | `#a0a0b0` | `true_market_mean` (cached daily)   |

---

## 3. Visual Elements — Draw Order

| #   | Element           | How drawn                                                                          |
| --- | ----------------- | ---------------------------------------------------------------------------------- |
| 0   | Header            | Left: `BTC ONCHAIN {DD Mon YYYY}` · Right: legend abbreviations in matching colors |
| 1   | Close price line  | Orange dot at slot col 1 · every slot                                              |
| 2   | Realized line     | Blue dot at slot col 1 · every slot · skip if null                                 |
| 3   | STH Realized line | Red dot at slot col 1 · every slot · skip if null                                  |
| 4   | LTH Realized line | Green dot at slot col 1 · every slot · skip if null                                |
| 5   | TMM line          | Light gray dot at slot col 1 · every slot · skip if null                           |
| 6   | Price labels      | Right of chart · auto step · pixel font · right-aligned                            |
| 7   | Month labels      | Below chart · first candle of each month                                           |

---

## 4. History Caching

Each daily run appends a snapshot to the shared `cache.json` (root level) under `'price_history'`:

```json
{
  "price_history": [
    {
      "date": "2026-07-01",
      "close": 58624.71,
      "realized": 51775.63,
      "sth": 69352.76,
      "lth": 49763.1,
      "tmm": 75835.7
    }
  ]
}
```

- Max entries: 60 days (rolling window, oldest dropped)
- Missing values stored as `null` → line has gap at that slot

---

## 5. Pixel Font

Same 3×5 bitmap font as `generate_chart_btc.py` (`S=2` scale factor).

---

## 6. Data Flow

```
run_full_btc.py (weekly mode)
│
├── data = fetch_btc.fetch_all()
├── cache_price_snapshot(data)        ← append to cache.json['price_history']
├── history = load_price_history()    ← last 120 entries from cache.json
│
├── img1 = generate_chart_btc.generate(data)        ← candle chart
├── img2 = generate_onchain_chart_btc.generate(history)  ← this chart
│
└── post_discord([img1, img2], caption)
    post_facebook([img1, img2], caption)
```

---

## 7. Reference Files

| File                            | Purpose                                         |
| ------------------------------- | ----------------------------------------------- |
| `full-asset-image-candle.md`    | Spec for the candle chart (old image)           |
| `generate_chart_btc.py`         | Candle chart implementation                     |
| `generate_onchain_chart_btc.py` | This chart (to be created)                      |
| `../cache.json`                 | Shared cache — `price_history` array lives here |
