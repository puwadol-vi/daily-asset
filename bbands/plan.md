# BBands BO [LuxAlgo] — Backtest Tool

A browser-based backtester for the BBands BO [LuxAlgo] indicator on weekly BTC/ETH candles, with an optional Nadaraya-Watson Envelope overlay. Everything runs client-side in `bbands/index.html` — no server, no build step. Open it via a local HTTP server (browsers block `fetch()` of local files opened via `file://`):

## 1. What it does

- Simulates a long/short/hedge trading strategy driven by the BBands BO indicator's green/red lines, over the full weekly history of BTC/USDT or ETH/USDT.
- Lets you pick the indicator's `Length`/`Mult`, which of 3 entry rules and 4 exit rules to use, and which side(s) to trade — then instantly shows the resulting trade list, equity curve stats, and drawdown.
- Optionally overlays the Nadaraya-Watson Envelope [LuxAlgo] on the price chart (display only — it doesn't drive entries/exits).

## 2. Header controls

| Control                  | What it does                                                                                                                                                                                                   |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Chart Type**           | `Candle` / `Heikin-Ashi` / `Line` — how the price panel renders. Doesn't affect the indicator math, which always uses real `close`.                                                                            |
| **Select Coin**          | `BTC/USDT` or `ETH/USDT`. Switches which trio of `data_{coin}_*.csv` files is loaded.                                                                                                                          |
| **Indicator** (dropdown) | Toggle which indicators are drawn. **BBands BO [LuxAlgo]** is locked on (it drives the backtest, so it can't be turned off). **Nadaraya-Watson Envelope [LuxAlgo]** is optional, overlaid on the candle chart. |
| **View Plan**            | This page.                                                                                                                                                                                                     |

## 3. Backtest controls

| Control             | What it does                                                                                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Length**          | BBands BO lookback, 7–14.                                                                                                                                                |
| **Mult**            | BBands BO stdev multiplier, 0.10–0.30.                                                                                                                                   |
| **Entry Rule**      | Which of the 3 entry conditions opens a position (see §5 for what each one means).                                                                                       |
| **Exit Rule**       | Which of the 4 exit conditions closes a position.                                                                                                                        |
| **Side**            | `Long only`, `Short only`, or `Both (hedge)` — hedge mode runs long and short as two fully independent books (own capital, own trades), not a single reversing position. |
| **Initial Capital** | Starting capital for the compounding equity curve (100% of capital in/out per trade, no fees/slippage).                                                                  |

## 4. Reading the chart

Three stacked panels, sharing one x-axis, price/value axis on the **right**:

1. **Price panel** — candles (or Heikin-Ashi/line), log-scale price axis, plus the Nadaraya-Watson envelope if selected.
2. **BBands BO panel** — the green (`bull`) and red (`bear`) lines, 0–100, with a dashed midline at 50.
3. **Volume panel** — up/down colored bars (no axis labels, per request).

Other chart behavior:

- **Mouse wheel** pans left/right through history (doesn't zoom).
- **Hover** shows a dotted crosshair (TradingView-style): a vertical line through all 3 panels, a horizontal line on whichever panel you're over, plus a price/value label on the right axis and a date label on the bottom axis.
- **Trade markers** — thin vertical bands drawn on every panel at each trade's entry/exit bar: 🟢 entry long, 🔵 exit long, 🔴 entry short, 🟡 exit short.

## 5. Results

- **Stat cards** — Trades, Win Rate, Total Return, Max Drawdown, Final Capital. Split into a Long card + Short card when Side = Both.
- **Order table** — one row per closed trade: entry date/price, exit date/price, % change, capital before/after that trade, and running % drawdown.

## 6. Indicator reference

### BBands BO [LuxAlgo] (`bbands/script.txt`)

For a given `length`/`mult`, weekly close (`src`):

```
stdev = ta.stdev(src, length) * mult
ema   = ta.ema(src, length)
upper = ema + stdev
lower = ema - stdev

# rolling window i = 0..length-1 (this bar back to length-1 bars ago)
bull_num += max(src[i] - upper[i], 0);  bull_den += abs(src[i] - upper[i])
bear_num += max(lower[i] - src[i], 0);  bear_den += abs(lower[i] - src[i])

bull = bull_num / bull_den * 100   # green line, 0-100
bear = bear_num / bear_den * 100   # red line,   0-100
```

`bull`/`bear` are 0 when no bar in the window broke the respective band.

### The 8 primitives behind Entry/Exit Rule

Every entry/exit rule (long and its short mirror) reduces to one of 8 weekly booleans. `G` = bull (green), `R` = bear (red); `_last`/`_this` = previous/current week.

| bit | primitive       | condition                             |
| --- | --------------- | ------------------------------------- |
| 0   | `green_go_pos`  | `G_last == 0 and G_this > 0`          |
| 1   | `red_go_pos`    | `R_last == 0 and R_this > 0`          |
| 2   | `cross_up`      | `G_last < R_last and G_this > R_this` |
| 3   | `cross_down`    | `G_last > R_last and G_this < R_this` |
| 4   | `red_peak`      | `R_last > R_this`                     |
| 5   | `green_peak`    | `G_last > G_this`                     |
| 6   | `green_go_zero` | `G_last > 0 and G_this == 0`          |
| 7   | `red_go_zero`   | `R_last > 0 and R_this == 0`          |

### What each Entry/Exit Rule # means

|                                             | Long            | Short (mirror) |
| ------------------------------------------- | --------------- | -------------- |
| **Entry** #1 — Momentum flips from zero     | `green_go_pos`  | `red_go_pos`   |
| **Entry** #2 — Line crosses over            | `cross_up`      | `cross_down`   |
| **Entry** #3 — Opposing line peaks          | `red_peak`      | `green_peak`   |
| **Exit** #1 — Own line peaks                | `green_peak`    | `red_peak`     |
| **Exit** #2 — Line crosses back             | `cross_down`    | `cross_up`     |
| **Exit** #3 — Own line returns to zero      | `green_go_zero` | `red_go_zero`  |
| **Exit** #4 — Opposing line flips from zero | `red_go_pos`    | `green_go_pos` |

**Position state machine, per week:** if a position is open and its exit-rule bit fires, close at that week's close (recording the trade); immediately after, if the entry-rule bit also fires that same week, a new position opens right away (same-week re-entry is allowed). In hedge mode (`Side = Both`), the long and short books run this independently and never interact.

### Nadaraya-Watson Envelope [LuxAlgo] (`bbands/Nadaraya-Watson.txt`)

Display-only overlay, **precomputed in Python** (fixed bandwidth=8, mult=3 — the script's defaults) into `nw_upper`/`nw_lower` columns of `data_{coin}_raw.csv`; the browser just draws them, no client-side math. It implements the script's _repainting_ fit (its default mode): a Gaussian kernel-weighted regression over the last min(500, n) bars. The script's non-repainting "endpoint method" needs ~1000 bars of warm-up — more history than our weekly datasets (~460–1300 bars) have, so it's not used. Because the full multi-year BTC/ETH price range (4-figure to 5-figure prices) sits inside one fitting window, the band comes out wide — that's a faithful reproduction of the indicator's behavior on this dataset, not a bug.

## 7. Data pipeline (regenerating the CSVs)

Three stages, one script each, run per coin:

```
data_{coin}_price.csv     # raw OHLCV only, straight from ccxt
data_{coin}_raw.csv       # + bull/bear per (length,mult) combo, + nw_upper/nw_lower
data_{coin}_process.csv   # 8-bit signal mask per combo (bit table above)
```

```bash
python3 generate_price_data.py --coin btc      # only script that hits the exchange
python3 generate_raw_data.py --coin btc        # no network — reads data_btc_price.csv
python3 generate_process_data.py --coin btc    # no network — reads data_btc_raw.csv
```

Re-tuning the indicator math (e.g. changing `LENGTHS`/`MULTS`/`NW_BANDWIDTH`/`NW_MULT` in `config.py`) only needs the last two steps — no re-fetch, no rate-limit risk. Repeat with `--coin eth` for ETH.

## 8. File layout

```
bbands/
  index.html                  # the tool itself
  plan.md                     # this file
  script.txt                  # BBands BO [LuxAlgo] Pine source
  Nadaraya-Watson.txt          # Nadaraya-Watson Envelope [LuxAlgo] Pine source
  config.py                   # COINS, LENGTHS, MULTS, NW_BANDWIDTH, NW_MULT
  generate_price_data.py       # ccxt weekly OHLCV -> data_{coin}_price.csv
  generate_raw_data.py         # -> data_{coin}_raw.csv (bull/bear + nw_upper/nw_lower)
  generate_process_data.py     # -> data_{coin}_process.csv (signal bitmask)
  data_btc_price.csv / data_btc_raw.csv / data_btc_process.csv
  data_eth_price.csv / data_eth_raw.csv / data_eth_process.csv
```
