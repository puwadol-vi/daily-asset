"""
Snowball backtest V10 -- Multi (portfolio) money management. Same per-asset
SMC BOS/CHoCH entry/exit signals and leverage tiering as
generate_calc_csv_v10.py, reused verbatim (detect_structure(),
pick_scenario_dates(), liquidation_price(), the leverage-tier constants) --
the only thing this module changes is HOW MUCH is risked and out of WHICH
bank (snowball/PLAN.md):

  - ONE shared $2000 bank per scenario across all 5 assets, instead of each
    asset trading its own independent $2000 bank (generate_calc_csv_v10.py's
    model: margin = 50% of THAT asset's own bank).
  - Isolated position per asset -- a liquidation only debits/credits that
    one asset's own margin, never touches another asset's open position or
    bank balance.
  - Entry margin = pct[asset] * CURRENT PORTFOLIO TOTAL, where portfolio
    total = shared cash + every open asset's mark-to-market margin balance
    at this bar's close -- NOT a fraction of cash alone. BTC 20%,
    ETH/BNB/SOL/XRP 10% each. Worked example from PLAN.md: btc margin $220 +
    bnb margin $100 + cash $750 = $1070 total -> a fresh ETH entry uses
    10% * 1070 = $107.
  - Each asset keeps its own tradeable gate (date >= THAT asset's own
    auto-detected Scenario A/B start date, picked the same way
    generate_calc_csv_v10.py does it), just no longer paired 1:1 with a
    private bank -- the shared bank exists (sitting idle at $2000) from the
    display window's first row even before any asset's own gate opens.
  - Per bar, processed in a fixed order across the 5 assets -- liquidation
    checks first, then voluntary (small red CHoCH) exits, then entries
    (BTC -> ETH -> BNB -> SOL -> XRP) -- each step reading/writing the one
    shared bank immediately, so a later step in the same bar sees the
    already-updated cash (mirrors how a real shared account would behave).

Two scenarios (A, B) run as two fully independent $2000 portfolios, same
auto-detected start-date rule as the single-asset engine (kept per the
user's decision, see snowball/PLAN.md).

Backtest scope: BTC/ETH/BNB/SOL/XRP only. Gold (PAXG) and silver (XAG) are
named in PLAN.md for eventual live trading only -- no historical SMC
structure or backtest is computed for either here.

Usage:
    venv/bin/python3 snowball/generate_calc_multi.py
"""
from collections import defaultdict

import pandas as pd
import ta

from generate_calc_csv_v10 import (
    DISPLAY_END,
    HIGH_ADX_THRESHOLD,
    LEVERAGE_HIGH_ADX_GREEN_ZONE,
    LEVERAGE_LOW_ADX_GREEN_ZONE,
    RED_ZONE_LEVERAGE,
    STARTING_CAPITAL,
    detect_structure,
    fetch_ohlcv,
    liquidation_price,
    pick_scenario_dates,
)

MULTI_ASSETS = [
    {"key": "btc", "symbol": "BTC/USDT", "pct": 0.20},
    {"key": "eth", "symbol": "ETH/USDT", "pct": 0.10},
    {"key": "bnb", "symbol": "BNB/USDT", "pct": 0.10},
    {"key": "sol", "symbol": "SOL/USDT", "pct": 0.10},
    {"key": "xrp", "symbol": "XRP/USDT", "pct": 0.10},
]

OUTPUT_PATHS = {"a": "snowball/calc_multi_a.csv", "b": "snowball/calc_multi_b.csv"}


def prepare_asset(symbol: str):
    """Fetch + indicators + structure/CHoCH signals for one asset, same
    computation as generate_calc_csv_v10.py's generate_for_asset(). Returns
    the enriched df plus this asset's own auto-detected Scenario A/B start
    dates (derived straight from this same structure pass's
    small_green_choch column, not a separate re-scan)."""
    df = fetch_ohlcv(symbol)
    df["ema12"] = ta.trend.EMAIndicator(df["close"], window=12).ema_indicator()
    df["ema26"] = ta.trend.EMAIndicator(df["close"], window=26).ema_indicator()
    df["az_bullish"] = [
        None if pd.isna(e12) or pd.isna(e26) else bool(e12 >= e26)
        for e12, e26 in zip(df["ema12"], df["ema26"])
    ]
    adx_ind = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14)
    df["adx14"] = adx_ind.adx()

    structure = detect_structure(df)
    df["small_green_choch"] = structure["small_green_choch"]
    df["small_red_choch"] = structure["small_red_choch"]

    green_dates = df.loc[df["small_green_choch"], "date"].tolist()
    date_a, date_b = pick_scenario_dates(green_dates)
    return df, date_a, date_b


def run_portfolio(dates: list, asset_dfs: dict, start_dates: dict) -> dict:
    """One shared-bank, isolated-per-asset simulation across all 5 assets
    for a single scenario. `dates` is the common date axis (already aligned
    across all 5 assets); `asset_dfs[key]` is that asset's df reindexed onto
    it; `start_dates[key]` is that asset's own scenario start date."""
    n = len(dates)
    keys = [a["key"] for a in MULTI_ASSETS]
    pct = {a["key"]: a["pct"] for a in MULTI_ASSETS}

    closes = {k: asset_dfs[k]["close"].tolist() for k in keys}
    lows = {k: asset_dfs[k]["low"].tolist() for k in keys}
    adx14 = {k: asset_dfs[k]["adx14"].tolist() for k in keys}
    az_bullish = {k: asset_dfs[k]["az_bullish"].tolist() for k in keys}
    green = {k: asset_dfs[k]["small_green_choch"].tolist() for k in keys}
    red = {k: asset_dfs[k]["small_red_choch"].tolist() for k in keys}
    tradeable = {k: [d >= start_dates[k] for d in dates] for k in keys}

    out = {"cash": [None] * n, "total": [None] * n, "pnl": [None] * n, "pct_pnl": [None] * n}
    for k in keys:
        out.update({
            f"{k}_close": [None] * n, f"{k}_leverage": [None] * n, f"{k}_position_size": [None] * n,
            f"{k}_margin": [None] * n, f"{k}_liquidate_price": [None] * n, f"{k}_pct_liquidate": [None] * n,
            f"{k}_action": [""] * n,
        })

    positions = {k: None for k in keys}  # {"avg_entry","size","isolated_margin","leverage"} or None
    realized_total = STARTING_CAPITAL
    prev_total = STARTING_CAPITAL

    for i in range(n):
        action_parts = defaultdict(list)

        # --- 1. Liquidation checks, all assets (real risk from leverage,
        # checked every bar via the day's low -- takes priority over the
        # voluntary CHoCH exit below, same as the single-asset engine). ---
        for k in keys:
            position = positions[k]
            if position is None:
                continue
            liq_price = liquidation_price(position["avg_entry"], position["size"], position["isolated_margin"])
            if liq_price is not None and lows[k][i] <= liq_price:
                unrealized_at_liq = (liq_price - position["avg_entry"]) * position["size"]
                margin_balance_at_liq = position["isolated_margin"] + unrealized_at_liq
                realized_pnl = margin_balance_at_liq - position["isolated_margin"]
                realized_total += margin_balance_at_liq  # pay the (near-zero) closing value back into the shared bank
                action_parts[k].append(
                    f"** LIQUIDATION EVENT ** @ {liq_price:.2f} (margin wiped, realized "
                    f"{'+' if realized_pnl >= 0 else ''}{realized_pnl:.2f})"
                )
                positions[k] = None

        # --- 2. Voluntary exits (small red CHoCH), all assets. ---
        for k in keys:
            position = positions[k]
            if position is None or not red[k][i]:
                continue
            price = closes[k][i]
            notional = position["size"] * price
            cost = position["size"] * position["avg_entry"]
            realized_pnl = notional - cost
            margin_balance_at_exit = position["isolated_margin"] + realized_pnl
            realized_total += margin_balance_at_exit  # pay the full closing value back into the shared bank
            action_parts[k].append(
                f"EXIT @ {price:.2f} (small red CHoCH, realized "
                f"{'+' if realized_pnl >= 0 else ''}{realized_pnl:.2f})"
            )
            positions[k] = None

        # --- 3. Entries (small green CHoCH), BTC -> ETH -> BNB -> SOL -> XRP.
        # Margin = pct[asset] * CURRENT PORTFOLIO TOTAL (shared cash, already
        # updated by steps 1-2 above and any earlier entry this same bar,
        # plus every still-open asset's mark-to-market margin) -- this is
        # the money-management change from the single-asset engine's 50%-
        # of-its-own-bank rule (see module docstring). Leverage tier is the
        # unchanged 3-tier ADX/Action-Zone rule, using THAT asset's own
        # values at entry. ---
        for k in keys:
            if not (tradeable[k][i] and green[k][i] and positions[k] is None and realized_total > 0):
                continue
            price = closes[k][i]
            open_margin_sum = sum(
                positions[o]["isolated_margin"] + (closes[o][i] - positions[o]["avg_entry"]) * positions[o]["size"]
                for o in keys if positions[o] is not None
            )
            portfolio_total = realized_total + open_margin_sum
            entry_adx = adx14[k][i]
            adx_known = entry_adx is not None and not pd.isna(entry_adx)
            is_high_adx = adx_known and entry_adx >= HIGH_ADX_THRESHOLD
            zone_bullish = az_bullish[k][i]  # True/False/None (None during EMA warmup)
            if zone_bullish is False:
                lev = RED_ZONE_LEVERAGE            # action zone bearish -- 2x regardless of ADX
            elif is_high_adx:
                lev = LEVERAGE_HIGH_ADX_GREEN_ZONE  # ADX high + bullish (already-extended move)
            else:
                lev = LEVERAGE_LOW_ADX_GREEN_ZONE   # ADX low + bullish (or zone unknown, treat like green)
            margin = pct[k] * portfolio_total
            size = (margin * lev) / price
            positions[k] = {"avg_entry": price, "size": size, "isolated_margin": margin, "leverage": lev}
            realized_total -= margin  # draw the margin out of the shared bank
            adx_label = f"{entry_adx:.1f}" if adx_known else "n/a"
            zone_label = "green" if zone_bullish is True else ("red" if zone_bullish is False else "n/a")
            action_parts[k].append(
                f"ENTRY @ {price:.2f} (small green CHoCH, margin ${margin:.2f} "
                f"[{pct[k]*100:.0f}% of portfolio total ${portfolio_total:.2f}] @ {lev:.0f}x "
                f"[ADX {adx_label}, zone {zone_label}], {size:.6f} units)"
            )

        # --- 4. Recompute + record, all assets. ---
        margin_sum = 0.0
        for k in keys:
            position = positions[k]
            price = closes[k][i]
            out[f"{k}_close"][i] = price
            liq_price = pct_liquidate = None
            margin_balance = 0.0
            position_size_out = None
            if position:
                position_size_out = position["size"]
                liq_price = liquidation_price(position["avg_entry"], position["size"], position["isolated_margin"])
                margin_balance = position["isolated_margin"] + (price - position["avg_entry"]) * position["size"]
                pct_liquidate = ((liq_price - price) / price) * 100 if liq_price is not None else None
                out[f"{k}_leverage"][i] = position["leverage"]
            out[f"{k}_position_size"][i] = position_size_out
            out[f"{k}_margin"][i] = margin_balance if position else None
            out[f"{k}_liquidate_price"][i] = liq_price
            out[f"{k}_pct_liquidate"][i] = pct_liquidate
            out[f"{k}_action"][i] = " | ".join(action_parts[k])
            margin_sum += margin_balance

        total_amt = realized_total + margin_sum
        today_change = total_amt - prev_total
        pct_pnl = (today_change / prev_total) * 100 if prev_total != 0 else None
        out["cash"][i] = realized_total
        out["total"][i] = total_amt
        out["pnl"][i] = today_change
        out["pct_pnl"][i] = pct_pnl
        prev_total = total_amt

    return out


def generate_multi():
    print("Fetching + preparing all assets...")
    prepared = {}
    for a in MULTI_ASSETS:
        df, date_a, date_b = prepare_asset(a["symbol"])
        prepared[a["key"]] = {"df": df, "date_a": date_a, "date_b": date_b}
        print(f"  {a['symbol']}: A={date_a}  B={date_b}")

    # Align all 5 assets onto a common date axis -- expected to be a no-op
    # since all are Binance 1d USDT pairs with no trading-calendar gaps, but
    # checked (not assumed) since the shared-bank sim needs every asset's
    # row `i` to be the same calendar day.
    date_sets = [set(prepared[a["key"]]["df"]["date"]) for a in MULTI_ASSETS]
    common_dates = sorted(set.intersection(*date_sets))
    for a in MULTI_ASSETS:
        k = a["key"]
        full_len = len(prepared[k]["df"])
        prepared[k]["df"] = (
            prepared[k]["df"][prepared[k]["df"]["date"].isin(common_dates)].reset_index(drop=True)
        )
        dropped = full_len - len(prepared[k]["df"])
        if dropped:
            print(f"  WARNING: {k} dropped {dropped} date(s) not common to all 5 assets")

    for scenario_key, date_attr in (("a", "date_a"), ("b", "date_b")):
        start_dates = {a["key"]: prepared[a["key"]][date_attr] for a in MULTI_ASSETS}
        asset_dfs = {a["key"]: prepared[a["key"]]["df"] for a in MULTI_ASSETS}

        sim = run_portfolio(common_dates, asset_dfs, start_dates)
        out = pd.DataFrame({"date": common_dates, **sim})

        # Display window: a few days before the earliest asset's own
        # scenario start, for a clean chart edge, through DISPLAY_END --
        # same cushion convention as generate_calc_csv_v10.py.
        display_start = pd.to_datetime(min(start_dates.values())) - pd.Timedelta(days=6)
        out = out[
            (out["date"] >= display_start.date())
            & (out["date"] < pd.to_datetime(DISPLAY_END).date())
        ].reset_index(drop=True)

        numeric_cols = ["cash", "total", "pnl", "pct_pnl"]
        for a in MULTI_ASSETS:
            k = a["key"]
            numeric_cols += [f"{k}_close", f"{k}_leverage", f"{k}_margin",
                              f"{k}_liquidate_price", f"{k}_pct_liquidate"]
        for c in numeric_cols:
            out[c] = pd.to_numeric(out[c], errors="coerce").round(2)
        for a in MULTI_ASSETS:
            k = a["key"]
            out[f"{k}_position_size"] = pd.to_numeric(out[f"{k}_position_size"], errors="coerce").round(6)

        output_path = OUTPUT_PATHS[scenario_key]
        out.to_csv(output_path, index=False)
        print(f"\n=== Scenario {scenario_key.upper()} -> {output_path} ===")
        print(f"Wrote {len(out)} rows. Per-asset starts: "
              + ", ".join(f"{a['key']}={start_dates[a['key']]}" for a in MULTI_ASSETS))
        for a in MULTI_ASSETS:
            k = a["key"]
            action = out[f"{k}_action"]
            entries = action.str.contains("ENTRY @").sum()
            exits = action.str.contains("EXIT @").sum()
            liquidations = action.str.contains("LIQUIDATION EVENT").sum()
            print(f"  [{k}] entries={entries} exits={exits} liquidations={liquidations}")
        print(f"  final_total={out['total'].iloc[-1]:.2f}  final_cash={out['cash'].iloc[-1]:.2f}")


def main():
    generate_multi()


if __name__ == "__main__":
    main()
