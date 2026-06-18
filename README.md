# Daily Asset — Claude Code Guide

## Project Overview

**Pixel Chart Diary** — a Facebook page that posts daily asset status updates.
Two automated post creators run daily and publish to Discord (and future Facebook).

---

## Post Creator 1: Full BTC Status

**File:** `full_asset_status/run_full_btc.py`

**What it does:**
1. Fetches BTC OHLCV + EMA data (`fetch_btc.py`)
2. Generates a pixel art chart image — EMA 200/12/26 overlaid on 60-day candles (`generate_chart_btc.py`)
3. Builds a partial message with pre-computed labels (`prompt_btc.py`)
4. Calls **Claude API** (`claude-opus-4-7`) to generate Wave + Pattern analysis lines
5. Posts image + text together to Discord via webhook

**Key files:**
- `fetch_btc.py` — data fetching
- `prompt_btc.py` — prompt builder + message assembler
- `generate_chart_btc.py` — pixel art chart generator
- `cache.json` — local cache (auto-created)

**Env vars needed:** `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`

---

## Post Creator 2: Multi Stock Status

**File:** `multi_asset_status/run_multi_stock.py`

**What it does:**
1. Reads stock list from `stocks.json`
2. Fetches price + EMA data for each stock (`fetch_stocks.py`)
3. Builds a text-only status message with emoji regime/position system
4. Posts to Discord via webhook

**Emoji system:**
- `[REGIME][POSITION][DIR]` format
- `📈/📉` = bull/bear regime (EMA50 vs EMA100)
- `🔵` aligned · `⚪` zone · `🔴` diverged
- `🟡` EMA50 cross (fast) · `🟢` EMA100 cross (slow)
- `↑↓` = cross direction suffix (cross day only)

**Key files:**
- `fetch_stocks.py` — data fetching
- `stocks.json` — stock ticker list

**Env vars needed:** `DISCORD_WEBHOOK_URL`

---

## Facebook Page

**Page name:** Pixel Chart Diary
**Content:** Daily BTC pixel chart + US stock EMA status posts
