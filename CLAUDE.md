# Daily Asset — CLAUDE.md

Python project that runs scheduled market data jobs and posts results to Discord, Facebook, and Google Calendar.

---

## Modules

| Module               | Entry point                             | Output destination | Cron (UTC)   |
| -------------------- | --------------------------------------- | ------------------ | ------------ |
| `full_asset_status`  | `full_asset_status/run_full_btc.py`     | Discord + Facebook | `2 0 * * *`  |
| `multi_asset_status` | `multi_asset_status/run_multi_stock.py` | Discord            | `3 0 * * *`  |
| `fund_status`        | `fund_status/run_fund_status.py`        | Google Calendar    | `2 23 * * *` |
| `signal`             | `signal/main.py`                        | Discord            | `0 * * * *`  |

All times are UTC. Server runs UTC+0; target display time is 07:02 UTC+7 = 00:02 UTC.

---

## Logging — DISCORD_LOG_URL

Every module sends a log message to `DISCORD_LOG_URL` after it runs, regardless of success or failure. This is the single place to monitor all jobs.

### Log string formats

**full_asset_status**

```
Full Asset Status
Facebook: posted OK
https://www.facebook.com/<id>/posts/<id>
```

On Facebook error:

```
Full Asset Status
Facebook: ERROR 190 — Invalid OAuth access token.
```

**multi_asset_status**

```
📅 Multi Asset Status — Jun 30, 2026 — 0 error(s)
```

**fund_status**

```
📅 Fund Status — Jun 30, 2026 — 0 error(s)
```

**signal**

```
🕐 Jun 30, 2026 00:00 0 error(s)
```

---

## Environment Variables

File: `.env` (copy from `.env.example`)

```
# Shared logging
DISCORD_LOG_URL=          # All modules log here after each run

# full_asset_status
FULL_ASSET_WEBHOOK_URL=   # Discord channel for BTC status posts
BTC_MONITOR_TOKEN=        # Bearer token for btc.kaetkung.uk /api/onchain
ANTHROPIC_API_KEY=        # Claude API key (weekly AI read)
FACEBOOK_PAGE_ID=         # Canonical page ID: 61579068644495
FACEBOOK_PAGE_TOKEN=      # Permanent Page token (never expires — see below)

# multi_asset_status
MULTI_ASSET_WEBHOOK_URL=  # Discord channel for stock/asset status posts

# fund_status
GOOGLE_CALENDAR_ID=       # Google Calendar ID (user@gmail.com format)
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# signal
EMA_BB_SIGNAL_WEBHOOK_URL=       # Discord channel for EMA/BB signal alerts
```

---

## full_asset_status

### Mode detection

`run_full_btc.py` checks `datetime.weekday()` at runtime:

- Monday (`== 0`) → **Weekly** mode: 2 images (candle + onchain) + AI read
- Tue–Sun → **Daily** mode: text only, no images

### Facebook token

`FACEBOOK_PAGE_TOKEN` must be a **permanent Page access token** (never expires).

To get one: run `full_asset_status/get_facebook_token.py` — it walks through:

1. Short-lived User token (from Meta Graph API Explorer)
2. Long-lived User token (60 days, via App ID + App Secret)
3. Permanent Page token (never expires)

To inspect the current token: run `full_asset_status/inspect_facebook_token.py`.

Canonical page ID is `61579068644495` (`760212033839028` redirects to it).

### Data sources

| Data                                                     | Source                                                          |
| -------------------------------------------------------- | --------------------------------------------------------------- |
| Price, OHLCV                                             | Binance via `ccxt`                                              |
| EMA / ADX / RSI                                          | `pandas_ta` (350 candles fetched for EMA200 warmup)             |
| Realized, MVRV, NUPL                                     | CoinMetrics Community API                                       |
| STH/LTH Realized, TMM, SOPR, MVRV Z-Score, Supply Profit | btc.kaetkung.uk `/api/onchain` (Bearer `BTC_MONITOR_TOKEN`)     |
| Fear & Greed                                             | alternative.me                                                  |
| BTC Dominance                                            | CoinGecko                                                       |
| AI Read (weekly)                                         | Claude `claude-opus-4-7` — 4 lines: Read1, Read2, Wave, Pattern |

### Images (weekly only)

| #   | File                            | Description                                                                                                                   |
| --- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 1   | `generate_chart_btc.py`         | Candlestick chart with EMA 200 (blue) + Action Zone · 400×200 → 1200×600 px pixel art                                         |
| 2   | `generate_onchain_chart_btc.py` | Dot chart: BTC candles (orange) · Realized Price (blue) · STH (red) · LTH/green · TMM (gray) · 120 days · same pixel art spec |

Onchain history for chart #2 is cached in `onchain_chart_cache.json` (repo root, gitignored). Run `full_asset_status/seed.py` once to backfill 120 days of OHLCV + STH/LTH/TMM/realized.

### Plan / spec files

| File                           | Purpose                                                        |
| ------------------------------ | -------------------------------------------------------------- |
| `full-asset-status.md`         | Full spec: modes, layouts, schedule, data sources, thresholds  |
| `full-asset-status-display.md` | Condensed reference (source for `full_asset_status_plan.html`) |
| `full_asset_status_plan.html`  | Visual HTML reference — open in browser                        |
| `full-asset-image-candle.md`   | Pixel art spec for candle chart                                |
| `full-asset-image-onchain.md`  | Pixel art spec for onchain line chart                          |
| `crypto-thresholds.md`         | Per-asset MVRV/NUPL thresholds (BTC/ETH/SOL/BNB/XRP)           |

---

## signal (EMA/BB)

Runs every hour. Reads `signal/setup.json` for strategy configs (EMA200 ratio, volume ratio, BB ratio conditions). Posts alert to `EMA_BB_SIGNAL_WEBHOOK_URL` when a signal fires. Logs run summary to `DISCORD_LOG_URL`.

---

## Shared cache

| File                                        | Contents                                                              |
| ------------------------------------------- | --------------------------------------------------------------------- |
| `full_asset_status/cache.json`              | BTC dominance (prev/current) for direction arrow                      |
| `full_asset_status/onchain_chart_cache.csv` | 120-day OHLCV + RP/STH/LTH/TMM history for onchain chart (gitignored) |

Copy `onchain_chart_cache.csv` to the VPS to bootstrap history on a new machine.

---

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in .env values
bash setup_cron.sh   # registers all cron jobs
```
