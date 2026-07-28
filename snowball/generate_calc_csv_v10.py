"""
Snowball backtest V10 -- Smart Money Concepts (SMC) BOS/CHoCH, raw data
generator + baked simulation. One calc_<asset>.csv per asset (BTC/ETH/BNB/
SOL/XRP), same engine, each with its own 2 auto-detected scenario start dates.

Ports the swing-structure engine from snowball/trade/smc.txt (LuxAlgo's
"Smart Money Concepts" Pine Script indicator) to Python -- NOT the price-%
zigzag used by V8/V9. Two structure detectors run side by side, each fully
independent (own leg state, own pivot levels, own trend bias), differing
only in their fractal confirmation window:

  - BIG   ("swing" in the original indicator) -- BIG_SIZE = 50 bars.
  - SMALL ("internal" in the original indicator) -- SMALL_SIZE = 5 bars,
    matching the Pine source's own hardcoded `getCurrentStructure(5,...)`
    call (not user-configurable there either).

Structure detection (leg/pivot), faithful to smc.txt's leg()/getCurrentStructure():
  A bar `size` bars back is confirmed as a swing HIGH once none of the
  `size` bars since have made a higher high (`high[size] > highest(size)`
  becomes true `size` bars later) -- and symmetrically for a swing LOW.
  This is a forward-confirming fractal, NOT a %-move zigzag: confirmation
  always lags the actual peak/trough by exactly `size` bars, deterministically
  (unlike V8/V9's zigzag, whose lag varies with how fast price reverses).
  Each newly confirmed pivot is labeled HH/LH (high vs. the previous
  confirmed high) or HL/LL (low vs. the previous confirmed low) -- same
  labeling convention as V8/V9, and same choice to leave the very first
  pivot of each kind unlabeled (no prior to compare against).

BOS/CHoCH (faithful to smc.txt's displayStructure()): each structure tracks
a running trend bias. When close crosses back above the structure's current
pivot-high level (and that level hasn't already been crossed since it was
set): label CHoCH if the bias was bearish (a reversal), or BOS if the bias
was already bullish (a continuation) -- then bias flips/stays bullish, and
the level is marked crossed (so it can't refire until a fresh pivot high
resets it). Symmetric for crossing below the pivot-low level (bearish
CHoCH/BOS). SMALL's crossings additionally require its pivot level to
differ from BIG's current pivot level at that moment (smc.txt's
`extraCondition` -- suppresses a redundant SMALL break announcement when
it's literally sitting on the same price level as BIG's).

Strategy (this repo's own addition -- smc.txt is just the structure
detector, it has no position logic of its own):
  - Entry / re-entry: ISOLATED MARGIN = 50% of the current bank (realized),
    every time SMALL fires a bullish CHoCH ("small green CHoCH") while flat.
    Leverage is dynamic, a 3-tier rule chosen at entry from that bar's ADX14
    and Action Zone (EMA12/EMA26) state -- money-management findings
    validated across all 5 assets/10 scenarios via re-simulation, not just
    bucket-level snapshots (see plan.md): (1) Action zone bearish at entry
    -> 2x, REGARDLESS of ADX -- this is the single biggest improvement
    found: red-zone entries underperform at both ADX levels, and because
    margin is 50% of the compounding bank, a liquidation in this bucket
    does outsized damage to every later entry's size, not just that one
    trade. (Earlier versions of this rule only cut ADX<22+red, leaving
    ADX>=22+red at 5x -- re-simulation showed extending the cut to ALL
    red-zone entries improves final totals in 8/10 cases, some
    dramatically, at the cost of one asset/scenario where a red-zone entry
    happened to be an outsized winner.) (2) Action zone bullish + ADX14 >=
    HIGH_ADX_THRESHOLD (an already-extended move) -> 5x. (3) Action zone
    bullish (or unavailable, e.g. during EMA warmup) + ADX14 < threshold ->
    10x -- this bucket's win rate matched the ADX-high/bullish bucket, so
    it keeps the aggressive tier. Notional = margin*leverage/price, real
    liquidation risk via MMR=0 (same model as V5-V7).
  - Exit: full close the moment SMALL fires a bearish CHoCH ("small red
    CHoCH") while in a position -- OR a real liquidation if price hits the
    liquidation level first (checked every bar via the day's low,
    independent of whether a CHoCH has fired yet).
  - No compounding within a cycle -- a single position per cycle, never
    added to, never partially reduced. Bank-fraction sizing IS how gains (or
    losses) compound ACROSS cycles, since each new entry's margin is 50% of
    whatever the bank currently holds. BIG's own BOS/CHoCH and SMALL's BOS
    events are computed and logged for reference/charting only; they do not
    drive any position action.

Two scenarios run in parallel per asset, sharing the identical structure/
BOS/CHoCH signals (computed once) but each with its own independent bank +
position state, gated to only start trading from its own start date -- so
they can diverge in position state (e.g. one open, one flat) from that
point on. Scenario start dates are auto-detected per asset (not hand-picked)
by the same rule verified against BTC's original hand-picked dates
(2022-07-07 / 2023-01-08, reproduced exactly by this rule):
  - SCENARIO A: the first small green CHoCH on/after CUTOFF_A (2022-07-01).
  - SCENARIO B: the first small green CHoCH on/after CUTOFF_B (2023-01-01).
Each scenario's own realized/total/margin/... columns are prefixed a_/b_.

Usage:
    venv/bin/python3 snowball/generate_calc_csv_v10.py
"""
import ccxt
import pandas as pd
import ta

TIMEFRAME = "1d"
DISPLAY_END = "2025-10-01"
FETCH_START = "2022-01-01"           # ~6mo warmup so BIG_SIZE=50 has time to cycle before CUTOFF_A
CUTOFF_A = "2022-07-01"              # scenario A = first small green CHoCH on/after this date
CUTOFF_B = "2023-01-01"              # scenario B = first small green CHoCH on/after this date

BIG_SIZE = 50                        # "swing" structure -- smc.txt's swingsLengthInput default
SMALL_SIZE = 5                       # "internal" structure -- smc.txt's hardcoded getCurrentStructure(5,...)

STARTING_CAPITAL = 2000.0            # starting bank for each scenario
MARGIN_FRACTION = 0.5                # each entry's isolated margin = 50% of the current bank
HIGH_ADX_THRESHOLD = 22.0            # >= this at entry, WHEN zone is bullish -> reduced leverage (plan.md section 4)
RED_ZONE_LEVERAGE = 2.0              # action zone bearish at entry, REGARDLESS of ADX -- validated across
                                      # all 5 assets/10 scenarios to be the biggest single improvement (plan.md)
LEVERAGE_HIGH_ADX_GREEN_ZONE = 5.0    # ADX high + action zone bullish -- already-extended move, still bullish context
LEVERAGE_LOW_ADX_GREEN_ZONE = 10.0    # ADX low + action zone bullish -- best-performing bucket, keep 10x
MMR = 0.0                            # maintenance margin rate, same simplification as V5-V7

ASSETS = [
    {"symbol": "BTC/USDT", "output": "snowball/calc_btc.csv"},
    {"symbol": "ETH/USDT", "output": "snowball/calc_eth.csv"},
    {"symbol": "BNB/USDT", "output": "snowball/calc_bnb.csv"},
    {"symbol": "SOL/USDT", "output": "snowball/calc_sol.csv"},
    {"symbol": "XRP/USDT", "output": "snowball/calc_xrp.csv"},
]

BULLISH_LEG, BEARISH_LEG = 1, 0
BULLISH, BEARISH = 1, -1


def liquidation_price(avg_entry, size, isolated_margin):
    if size is None or size <= 0 or isolated_margin <= 0:
        return None
    return (avg_entry * size - isolated_margin) / (size * (1 - MMR))


def fetch_ohlcv(symbol: str) -> pd.DataFrame:
    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601(f"{FETCH_START}T00:00:00Z")
    rows = []
    while True:
        batch = exchange.fetch_ohlcv(symbol, TIMEFRAME, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms").dt.date
    df = df.drop(columns=["ts"]).drop_duplicates(subset="date").reset_index(drop=True)
    return df


class Structure:
    """One independent leg/pivot/trend state machine (BIG or SMALL)."""
    def __init__(self, size):
        self.size = size
        self.leg = BEARISH_LEG        # smc.txt: var leg = 0
        self.pivot_high = {"level": None, "crossed": False}
        self.pivot_low = {"level": None, "crossed": False}
        self.trend = 0                # 0 = no established bias yet, else BULLISH/BEARISH


def detect_small_green_choch_dates(df: pd.DataFrame) -> list:
    """Lightweight structure-only pass (no position sim) -- returns the list
    of dates where SMALL registers a bullish CHoCH, used to auto-pick each
    scenario's start date (see module docstring)."""
    n = len(df)
    highs, lows, closes = df["high"].tolist(), df["low"].tolist(), df["close"].tolist()
    roll_high = {
        BIG_SIZE: df["high"].rolling(BIG_SIZE, min_periods=BIG_SIZE).max().tolist(),
        SMALL_SIZE: df["high"].rolling(SMALL_SIZE, min_periods=SMALL_SIZE).max().tolist(),
    }
    roll_low = {
        BIG_SIZE: df["low"].rolling(BIG_SIZE, min_periods=BIG_SIZE).min().tolist(),
        SMALL_SIZE: df["low"].rolling(SMALL_SIZE, min_periods=SMALL_SIZE).min().tolist(),
    }
    big, small = Structure(BIG_SIZE), Structure(SMALL_SIZE)
    green_dates = []

    for i in range(n):
        for st, size in ((big, BIG_SIZE), (small, SMALL_SIZE)):
            if i >= size:
                rh, rl = roll_high[size][i], roll_low[size][i]
                new_leg_high = rh is not None and highs[i - size] > rh
                new_leg_low = rl is not None and lows[i - size] < rl
                prev_leg = st.leg
                if new_leg_high:
                    st.leg = BEARISH_LEG
                elif new_leg_low:
                    st.leg = BULLISH_LEG
                if st.leg != prev_leg:
                    idx = i - size
                    if st.leg == BULLISH_LEG:
                        st.pivot_low["level"] = lows[idx]
                        st.pivot_low["crossed"] = False
                    else:
                        st.pivot_high["level"] = highs[idx]
                        st.pivot_high["crossed"] = False

        price = closes[i]
        prev_price = closes[i - 1] if i > 0 else None
        if i > 0 and small.pivot_high["level"] is not None and not small.pivot_high["crossed"]:
            extra = True
            if big.pivot_high["level"] is not None:
                extra = small.pivot_high["level"] != big.pivot_high["level"]
            if price > small.pivot_high["level"] and prev_price <= small.pivot_high["level"] and extra:
                if small.trend == BEARISH:
                    green_dates.append(df["date"].iloc[i])
                small.pivot_high["crossed"] = True
                small.trend = BULLISH
        if i > 0 and small.pivot_low["level"] is not None and not small.pivot_low["crossed"]:
            extra = True
            if big.pivot_low["level"] is not None:
                extra = small.pivot_low["level"] != big.pivot_low["level"]
            if price < small.pivot_low["level"] and prev_price >= small.pivot_low["level"] and extra:
                small.pivot_low["crossed"] = True
                small.trend = BEARISH

    return green_dates


def pick_scenario_dates(green_dates: list) -> tuple:
    cutoff_a = pd.to_datetime(CUTOFF_A).date()
    cutoff_b = pd.to_datetime(CUTOFF_B).date()
    after_a = [d for d in green_dates if d >= cutoff_a]
    after_b = [d for d in green_dates if d >= cutoff_b]
    date_a = after_a[0] if after_a else green_dates[0]
    date_b = after_b[0] if after_b else (after_a[1] if len(after_a) > 1 else date_a)
    return date_a, date_b


def detect_structure(df: pd.DataFrame) -> dict:
    """Runs the BIG/SMALL leg -> pivot -> BOS/CHoCH detection across the
    whole range of df (smc.txt's leg()/getCurrentStructure()/displayStructure(),
    same algorithm as detect_small_green_choch_dates() but keeping every
    column needed for charting, plus the full per-bar small_green_choch/
    small_red_choch boolean series -- the literal entry/exit triggers).
    Pulled out of run_simulation() so both the single-asset engine (its own
    bank/position sim, steps 3-5 below) and the multi-asset portfolio engine
    (generate_calc_multi.py's shared-bank sim) can drive their own strategy
    logic off the identical structure/CHoCH signals, computed once."""
    n = len(df)
    highs = df["high"].tolist()
    lows = df["low"].tolist()
    closes = df["close"].tolist()

    roll_high = {
        BIG_SIZE: df["high"].rolling(BIG_SIZE, min_periods=BIG_SIZE).max().tolist(),
        SMALL_SIZE: df["high"].rolling(SMALL_SIZE, min_periods=SMALL_SIZE).max().tolist(),
    }
    roll_low = {
        BIG_SIZE: df["low"].rolling(BIG_SIZE, min_periods=BIG_SIZE).min().tolist(),
        SMALL_SIZE: df["low"].rolling(SMALL_SIZE, min_periods=SMALL_SIZE).min().tolist(),
    }

    out = {
        "big_swing_high": [None] * n, "big_swing_low": [None] * n, "big_pivot_label": [None] * n,
        "small_swing_high": [None] * n, "small_swing_low": [None] * n, "small_pivot_label": [None] * n,
        "big_break": [None] * n, "small_break": [None] * n,
        "structure_action": [""] * n,
        "small_green_choch": [False] * n, "small_red_choch": [False] * n,
    }

    big = Structure(BIG_SIZE)
    small = Structure(SMALL_SIZE)

    for i in range(n):
        action_parts = []

        # --- 1. Advance leg/pivot detection for both structures ---
        for st, swing_high_col, swing_low_col, label_col, prefix in (
            (big, "big_swing_high", "big_swing_low", "big_pivot_label", "BIG"),
            (small, "small_swing_high", "small_swing_low", "small_pivot_label", "SMALL"),
        ):
            size = st.size
            if i >= size:
                rh, rl = roll_high[size][i], roll_low[size][i]
                new_leg_high = rh is not None and highs[i - size] > rh
                new_leg_low = rl is not None and lows[i - size] < rl
                prev_leg = st.leg
                if new_leg_high:
                    st.leg = BEARISH_LEG
                elif new_leg_low:
                    st.leg = BULLISH_LEG
                if st.leg != prev_leg:
                    idx = i - size
                    if st.leg == BULLISH_LEG:
                        price = lows[idx]
                        label = None
                        if st.pivot_low["level"] is not None:
                            label = "HL" if price > st.pivot_low["level"] else "LL"
                        st.pivot_low["level"] = price
                        st.pivot_low["crossed"] = False
                        out[swing_low_col][idx] = price
                        if label:
                            out[label_col][idx] = label
                            action_parts.append(f"{prefix} {label} confirmed @ {price:.2f}")
                    else:
                        price = highs[idx]
                        label = None
                        if st.pivot_high["level"] is not None:
                            label = "HH" if price > st.pivot_high["level"] else "LH"
                        st.pivot_high["level"] = price
                        st.pivot_high["crossed"] = False
                        out[swing_high_col][idx] = price
                        if label:
                            out[label_col][idx] = label
                            action_parts.append(f"{prefix} {label} confirmed @ {price:.2f}")

        # --- 2. BOS/CHoCH checks -- BIG first, then SMALL (SMALL's
        # extraCondition needs BIG's CURRENT levels, already updated above) ---
        price = closes[i]
        prev_price = closes[i - 1] if i > 0 else None

        for st, is_small, prefix, break_col in (
            (big, False, "BIG", "big_break"), (small, True, "SMALL", "small_break")
        ):
            ph, pl = st.pivot_high, st.pivot_low
            if i > 0 and ph["level"] is not None and not ph["crossed"]:
                extra = True
                if is_small and big.pivot_high["level"] is not None:
                    extra = ph["level"] != big.pivot_high["level"]
                crossover = price > ph["level"] and prev_price <= ph["level"]
                if crossover and extra:
                    tag = "CHOCH" if st.trend == BEARISH else "BOS"
                    ph["crossed"] = True
                    st.trend = BULLISH
                    out[break_col][i] = f"BULL_{tag}"
                    action_parts.append(f"{prefix} BULL {tag} @ {price:.2f} (level {ph['level']:.2f})")
                    if is_small and tag == "CHOCH":
                        out["small_green_choch"][i] = True
            if i > 0 and pl["level"] is not None and not pl["crossed"]:
                extra = True
                if is_small and big.pivot_low["level"] is not None:
                    extra = pl["level"] != big.pivot_low["level"]
                crossunder = price < pl["level"] and prev_price >= pl["level"]
                if crossunder and extra:
                    tag = "CHOCH" if st.trend == BULLISH else "BOS"
                    pl["crossed"] = True
                    st.trend = BEARISH
                    out[break_col][i] = f"BEAR_{tag}"
                    action_parts.append(f"{prefix} BEAR {tag} @ {price:.2f} (level {pl['level']:.2f})")
                    if is_small and tag == "CHOCH":
                        out["small_red_choch"][i] = True

        out["structure_action"][i] = " | ".join(action_parts)

    return out


def run_simulation(df: pd.DataFrame, scenarios: list) -> dict:
    n = len(df)
    lows = df["low"].tolist()
    closes = df["close"].tolist()
    adx14 = df["adx14"].tolist()
    az_bullish = df["az_bullish"].tolist()
    # Structure detection (BIG/SMALL) runs across the whole fetched range,
    # including the pre-scenario-A warmup -- it needs that history to have
    # real pivots ready by the first displayed bar. Each SCENARIO's own
    # strategy must NOT trade before ITS OWN start_date though, or its realized
    # ledger would already reflect trades nobody can see in the displayed CSV
    # (this was the actual bug in the single-scenario version: realized showed
    # -5309.68 on the very first visible row because 2022 trades had already
    # happened, off-screen, before the old single DISPLAY_START).
    for sc in scenarios:
        sc["tradeable"] = (df["date"] >= sc["start_date"]).tolist()
        sc["position"] = None       # {"avg_entry","size","isolated_margin","leverage"} or None
        # realized is a real cash ledger, not a pure PnL total: starts holding
        # the full starting capital, ENTRY draws the margin OUT (50% of
        # whatever the bank currently holds), EXIT/LIQUIDATION pays the
        # position's full closing margin_balance back IN -- so `total` never
        # jumps at an entry/exit, it just relabels which bucket the same
        # dollar is sitting in.
        sc["realized_total"] = STARTING_CAPITAL
        sc["prev_total"] = STARTING_CAPITAL

    structure = detect_structure(df)
    small_green_choch_arr = structure.pop("small_green_choch")
    small_red_choch_arr = structure.pop("small_red_choch")
    out = structure
    for sc in scenarios:
        k = sc["key"]
        out.update({
            f"{k}_liquidate_price": [None] * n, f"{k}_pct_liquidate": [None] * n,
            f"{k}_leverage": [None] * n, f"{k}_position_size": [None] * n, f"{k}_notional": [None] * n,
            f"{k}_total": [None] * n, f"{k}_pnl": [None] * n, f"{k}_pct_pnl": [None] * n,
            f"{k}_margin": [None] * n, f"{k}_position": [None] * n,
            f"{k}_unrealized": [None] * n, f"{k}_realized": [None] * n,
            f"{k}_action": [""] * n,
        })

    for i in range(n):
        small_green_choch = small_green_choch_arr[i]
        small_red_choch = small_red_choch_arr[i]
        price = closes[i]

        # --- 3-5. Per-scenario position sim: liquidation check, CHoCH entry/
        # exit, then recompute + record (same field conventions as V7). Each
        # scenario has its own position/bank state and its own tradeable gate. ---
        for sc in scenarios:
            k = sc["key"]
            sc_action_parts = []
            position = sc["position"]
            realized_total = sc["realized_total"]

            # Liquidation check -- real risk from leverage, checked every
            # bar via the day's low. Takes priority over the voluntary CHoCH
            # exit below.
            liquidated = False
            if position is not None:
                liq_price = liquidation_price(position["avg_entry"], position["size"], position["isolated_margin"])
                if liq_price is not None and lows[i] <= liq_price:
                    unrealized_at_liq = (liq_price - position["avg_entry"]) * position["size"]
                    margin_balance_at_liq = position["isolated_margin"] + unrealized_at_liq
                    realized_pnl = margin_balance_at_liq - position["isolated_margin"]
                    realized_total += margin_balance_at_liq  # pay the (near-zero) closing value back into the bank
                    sc_action_parts.append(
                        f"** LIQUIDATION EVENT ** @ {liq_price:.2f} (margin wiped, realized "
                        f"{'+' if realized_pnl >= 0 else ''}{realized_pnl:.2f})"
                    )
                    position = None
                    liquidated = True

            # Strategy: entry on small green CHoCH, exit on small red CHoCH.
            # Margin = 50% of the current bank, leverage picked from this
            # bar's ADX14. Only tradeable from this scenario's own
            # start_date onward.
            if not liquidated and small_red_choch and position is not None:
                notional = position["size"] * price
                cost = position["size"] * position["avg_entry"]
                realized_pnl = notional - cost
                margin_balance_at_exit = position["isolated_margin"] + realized_pnl
                realized_total += margin_balance_at_exit  # pay the full closing value back into the bank
                sc_action_parts.append(
                    f"EXIT @ {price:.2f} (small red CHoCH, realized "
                    f"{'+' if realized_pnl >= 0 else ''}{realized_pnl:.2f})"
                )
                position = None

            if sc["tradeable"][i] and small_green_choch and position is None and realized_total > 0:
                entry_adx = adx14[i]
                adx_known = entry_adx is not None and not pd.isna(entry_adx)
                is_high_adx = adx_known and entry_adx >= HIGH_ADX_THRESHOLD
                zone_bullish = az_bullish[i]  # True/False/None (None during EMA warmup)
                if zone_bullish is False:
                    lev = RED_ZONE_LEVERAGE            # action zone bearish -- 2x regardless of ADX
                elif is_high_adx:
                    lev = LEVERAGE_HIGH_ADX_GREEN_ZONE  # ADX high + bullish (already-extended move)
                else:
                    lev = LEVERAGE_LOW_ADX_GREEN_ZONE   # ADX low + bullish (or zone unknown, treat like green)
                margin = MARGIN_FRACTION * realized_total
                size = (margin * lev) / price
                position = {"avg_entry": price, "size": size, "isolated_margin": margin, "leverage": lev}
                realized_total -= margin  # draw the margin out of the bank
                adx_label = f"{entry_adx:.1f}" if adx_known else "n/a"
                zone_label = "green" if zone_bullish is True else ("red" if zone_bullish is False else "n/a")
                sc_action_parts.append(
                    f"ENTRY @ {price:.2f} (small green CHoCH, margin ${margin:.2f} "
                    f"[{MARGIN_FRACTION*100:.0f}% of bank] @ {lev:.0f}x [ADX {adx_label}, zone {zone_label}], "
                    f"{size:.6f} units)"
                )

            # Recompute + record
            liq_price = pct_liquidate = None
            notional_amt = margin_balance = position_clean = unrealized_amt = 0.0
            position_size_out = None
            if position:
                position_size_out = position["size"]
                liq_price = liquidation_price(position["avg_entry"], position["size"], position["isolated_margin"])
                notional_amt = position["size"] * price
                margin_balance = position["isolated_margin"] + (price - position["avg_entry"]) * position["size"]
                position_clean = notional_amt / position["leverage"]
                unrealized_amt = margin_balance - position_clean
                pct_liquidate = ((liq_price - price) / price) * 100 if liq_price is not None else None

            total_amt = margin_balance + realized_total
            today_change = total_amt - sc["prev_total"]
            pct_pnl = (today_change / sc["prev_total"]) * 100 if sc["prev_total"] != 0 else None

            leverage_total = (notional_amt / total_amt) if (notional_amt and total_amt) else None

            out[f"{k}_liquidate_price"][i] = liq_price
            out[f"{k}_pct_liquidate"][i] = pct_liquidate
            out[f"{k}_leverage"][i] = leverage_total
            out[f"{k}_position_size"][i] = position_size_out
            out[f"{k}_notional"][i] = notional_amt or None
            out[f"{k}_total"][i] = total_amt
            out[f"{k}_pnl"][i] = today_change
            out[f"{k}_pct_pnl"][i] = pct_pnl
            out[f"{k}_margin"][i] = margin_balance
            out[f"{k}_position"][i] = position_clean
            out[f"{k}_unrealized"][i] = unrealized_amt if position else None
            out[f"{k}_realized"][i] = realized_total
            out[f"{k}_action"][i] = " | ".join(sc_action_parts)

            sc["position"] = position
            sc["realized_total"] = realized_total
            sc["prev_total"] = total_amt

    return out


def generate_for_asset(symbol: str, output_path: str):
    df = fetch_ohlcv(symbol)
    df["pct_change"] = df["close"].pct_change() * 100
    # Action Zone (chart reference only, not wired into the SMC strategy) --
    # same EMA12/EMA26 bullish/bearish zone convention as V4-V7. az_bullish is
    # precomputed here too (not left for the JS to compare) -- index.html only
    # reads and displays, it does not calculate.
    df["ema12"] = ta.trend.EMAIndicator(df["close"], window=12).ema_indicator()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema26"] = ta.trend.EMAIndicator(df["close"], window=26).ema_indicator()
    df["az_bullish"] = [
        None if pd.isna(e12) or pd.isna(e26) else bool(e12 >= e26)
        for e12, e26 in zip(df["ema12"], df["ema26"])
    ]
    # Raw ADX/+DI/-DI (chart reference only, not wired into the strategy --
    # unlike V6/V7 this isn't used for any regime/leverage decision here).
    adx_ind = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14)
    df["adx14"] = adx_ind.adx()
    df["di_plus"] = adx_ind.adx_pos()
    df["di_minus"] = adx_ind.adx_neg()

    green_dates = detect_small_green_choch_dates(df)
    date_a, date_b = pick_scenario_dates(green_dates)
    scenarios = [
        {"key": "a", "label": f"A: from {date_a.isoformat()}", "start_date": date_a},
        {"key": "b", "label": f"B: from {date_b.isoformat()}", "start_date": date_b},
    ]

    sim = run_simulation(df, scenarios)
    for key, values in sim.items():
        df[key] = values

    scenario_cols = []
    for sc in scenarios:
        k = sc["key"]
        scenario_cols += [
            f"{k}_liquidate_price", f"{k}_pct_liquidate", f"{k}_leverage", f"{k}_position_size",
            f"{k}_notional", f"{k}_total", f"{k}_pnl", f"{k}_pct_pnl", f"{k}_margin",
            f"{k}_position", f"{k}_unrealized", f"{k}_realized", f"{k}_action",
        ]

    out_cols = [
        "date", "open", "high", "low", "close", "volume", "pct_change", "ema12", "ema20", "ema26", "az_bullish",
        "adx14", "di_plus", "di_minus",
        "big_swing_high", "big_swing_low", "big_pivot_label", "big_break",
        "small_swing_high", "small_swing_low", "small_pivot_label", "small_break", "structure_action",
    ] + scenario_cols
    out = df[out_cols].copy()

    # Display window: a few days before Scenario A's start, for a clean chart
    # edge, through DISPLAY_END.
    display_start = pd.to_datetime(date_a) - pd.Timedelta(days=6)
    out = out[
        (out["date"] >= display_start.date())
        & (out["date"] < pd.to_datetime(DISPLAY_END).date())
    ].reset_index(drop=True)

    numeric_scenario_cols = [c for c in scenario_cols if not c.endswith("_action")]
    for c in (["open", "high", "low", "close", "volume", "pct_change", "ema12", "ema20", "ema26",
               "adx14", "di_plus", "di_minus",
               "big_swing_high", "big_swing_low", "small_swing_high", "small_swing_low"]
              + [c for c in numeric_scenario_cols if not c.endswith("_position_size")]):
        out[c] = pd.to_numeric(out[c], errors="coerce").round(2)
    for sc in scenarios:
        out[f"{sc['key']}_position_size"] = pd.to_numeric(out[f"{sc['key']}_position_size"], errors="coerce").round(6)

    out.to_csv(output_path, index=False)
    print(f"\n=== {symbol} -> {output_path} ===")
    print(f"Wrote {len(out)} rows. Scenario A start={date_a}  Scenario B start={date_b}")

    structure_action = out["structure_action"]
    small_bull_choch = (structure_action.str.contains("SMALL BULL CHOCH")).sum()
    small_bear_choch = (structure_action.str.contains("SMALL BEAR CHOCH")).sum()
    print(f"SMALL bull_choch={small_bull_choch} bear_choch={small_bear_choch}")

    for sc in scenarios:
        k, action = sc["key"], out[f"{sc['key']}_action"]
        entries = (action.str.contains("ENTRY @")).sum()
        exits = (action.str.contains("EXIT @")).sum()
        liquidations = (action.str.contains("LIQUIDATION EVENT")).sum()
        print(f"[{k}] start={sc['start_date']} entries={entries} exits={exits} "
              f"liquidations={liquidations} final_total={out[f'{k}_total'].iloc[-1]:.2f}")


def main():
    for asset in ASSETS:
        generate_for_asset(asset["symbol"], asset["output"])


if __name__ == "__main__":
    main()
