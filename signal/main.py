#!/usr/bin/env python3
"""
EMA/BB Signal Alert — run once per hour via cron.
Cron: 0 * * * * cd /path && venv/bin/python3 signal/main.py >> cron.log 2>&1
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

import ccxt
import pandas as pd
import ta
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / '.env')

RUNTIME_DIR = Path(__file__).parent / 'runtime'
CALC_CSV    = RUNTIME_DIR / 'btc_calc.csv'
CALC_WARMUP = 250

SETUP_JSON = Path(__file__).parent / 'setup.json'

_CALC_COLS = [
    'datetime', 'open', 'high', 'low', 'close', 'volume',
    'ema_200', 'ema_200_ratio',
    'bb_basis', 'bb_upper', 'bb_lower', 'bb_distance', 'bb_ratio',
    'vol_ratio', 'atr_14',
    'tenkan', 'kijun', 'senkou_a', 'senkou_b',
    'senkou_ratio', 'adx', 'tenkan_kijun',
]

def load_config() -> list:
    return json.loads(SETUP_JSON.read_text())


# ── indicators ────────────────────────────────────────────────────────────────

def compute(df: pd.DataFrame) -> dict:
    """Compute all indicators; return dict for the last row."""
    df = df.copy().reset_index(drop=True)

    # EMA 200
    df['ema_200']   = ta.trend.ema_indicator(df['close'], window=200)
    ema_200_val     = float(df['ema_200'].iloc[-1])

    # Volume ratio
    df['vol_ratio'] = (df['volume'] / df['volume'].rolling(20).mean()).round(5)

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_basis']    = bb.bollinger_mavg()
    df['bb_upper']    = bb.bollinger_hband()
    df['bb_lower']    = bb.bollinger_lband()
    df['bb_distance'] = df['bb_upper'] - df['bb_basis']
    df['bb_ratio']    = (df['close'] - df['bb_basis']) / df['bb_distance']

    # ATR
    df['atr_14'] = ta.volatility.average_true_range(
        df['high'], df['low'], df['close'], window=14
    )

    # Ichimoku (9, 26, 52)
    ich = ta.trend.IchimokuIndicator(df['high'], df['low'], window1=9, window2=26, window3=52, visual=False)
    df['tenkan'] = ich.ichimoku_conversion_line()
    df['kijun']  = ich.ichimoku_base_line()
    df['ichi_a'] = ich.ichimoku_a()
    df['ichi_b'] = ich.ichimoku_b()

    # ADX (14)
    df['adx'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()

    last  = df.iloc[-1]
    close = round(float(last['close']), 2)

    def _f(col, decimals=2):
        v = last.get(col)
        return round(float(v), decimals) if pd.notna(v) else None

    tenkan_v = _f('tenkan'); kijun_v = _f('kijun')
    ichi_a_v = _f('ichi_a'); ichi_b_v = _f('ichi_b')

    # senkou_ratio: (close - cloud_mid) / cloud_half  — >1 above cloud, <-1 below cloud
    if ichi_a_v is not None and ichi_b_v is not None:
        cloud_mid  = (ichi_a_v + ichi_b_v) / 2
        cloud_half = abs(ichi_a_v - ichi_b_v) / 2
        senkou_ratio = round((close - cloud_mid) / cloud_half, 4) if cloud_half > 0 else None
    else:
        senkou_ratio = None

    # tenkan_kijun: >1 = tenkan above kijun (bull), <1 = tenkan below kijun (bear)
    tenkan_kijun = round(tenkan_v / kijun_v, 5) if tenkan_v and kijun_v else None

    return {
        'datetime':      str(last['datetime']),
        'open':          round(float(last['open']),   2),
        'high':          round(float(last['high']),   2),
        'low':           round(float(last['low']),    2),
        'close':         close,
        'volume':        round(float(last['volume']), 5),
        'ema_200':       round(ema_200_val,            2),
        'ema_200_ratio': round(close / ema_200_val,    5) if ema_200_val else None,
        'bb_basis':      round(float(last['bb_basis']),    2),
        'bb_upper':      round(float(last['bb_upper']),    2),
        'bb_lower':      round(float(last['bb_lower']),    2),
        'bb_distance':   round(float(last['bb_distance']), 2),
        'bb_ratio':      round(float(last['bb_ratio']),    4),
        'vol_ratio':     round(float(last['vol_ratio']), 3) if pd.notna(last.get('vol_ratio')) else 0.0,
        'atr_14':        round(float(last['atr_14']), 2) if pd.notna(last.get('atr_14')) else None,
        'tenkan':        tenkan_v,
        'kijun':         kijun_v,
        'senkou_a':      ichi_a_v,
        'senkou_b':      ichi_b_v,
        'senkou_ratio':  senkou_ratio,
        'adx':           _f('adx', 1),
        'tenkan_kijun':  tenkan_kijun,
    }


# ── price fetch ───────────────────────────────────────────────────────────────

def make_exchange():
    return ccxt.binance({'enableRateLimit': True})


def current_candle_datetime() -> str:
    now = pd.Timestamp.now('UTC').tz_localize(None) + pd.Timedelta(hours=7)
    return (now - pd.Timedelta(hours=1)).floor('h').strftime('%Y-%m-%d %H:%M')


def csv_gap(candle_dt: str) -> int | None:
    """Hours between last CSV row and candle_dt. None = no CSV. 0 = already computed."""
    if not CALC_CSV.exists():
        return None
    df      = pd.read_csv(CALC_CSV, usecols=['datetime'])
    last_dt = pd.Timestamp(df['datetime'].iloc[-1])
    current = pd.Timestamp(candle_dt)
    return int((current - last_dt).total_seconds() / 3600)


def fetch_latest_1h(exchange) -> dict:
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=3)
    r = ohlcv[-2]  # last completed candle
    dt = (pd.Timestamp(r[0], unit='ms') + pd.Timedelta(hours=7)).strftime('%Y-%m-%d %H:%M')
    return {
        'timestamp': int(r[0]),
        'open':      round(float(r[1]), 5),
        'high':      round(float(r[2]), 5),
        'low':       round(float(r[3]), 5),
        'close':     round(float(r[4]), 5),
        'volume':    round(float(r[5]), 5),
        'datetime':  dt,
    }


def append_calc_row(row: dict):
    df_row = pd.DataFrame([{c: row.get(c) for c in _CALC_COLS}])
    df_row.to_csv(CALC_CSV, mode='a', header=False, index=False)


# ── signal check ──────────────────────────────────────────────────────────────

OPS = {'==': lambda a, b: a == b, '!=': lambda a, b: a != b,
       '>':  lambda a, b: a >  b, '>=': lambda a, b: a >= b,
       '<':  lambda a, b: a <  b, '<=': lambda a, b: a <= b}


# ── discord ───────────────────────────────────────────────────────────────────

def send_discord(msg: str, url: str):
    if not url:
        return
    try:
        r = requests.post(url, json={'content': msg}, timeout=10)
        if r.status_code not in (200, 204):
            print(f'[discord] HTTP {r.status_code}: {r.text[:200]}')
    except Exception as e:
        print(f'[discord] Error: {e}')


def _condition_line(col: str, op: str, val, calc_row: dict) -> str:
    actual = calc_row.get(col)
    met    = OPS[op](actual, val) if actual is not None else False
    ok     = '🟢' if met else '🔴'

    if col == 'ema_200_ratio':
        trend = '📈' if (actual or 0) > 1 else '📉'
        return f"  EMA   : {trend} ${calc_row.get('ema_200', 0):,.2f}"
    if col == 'bb_ratio':
        return f"  BB    : {ok} {actual:.4f}"
    if col == 'vol_ratio':
        return f"  Vol   : {ok} {actual:.2f}x"
    if col == 'senkou_ratio':
        return f"  Cloud : {ok} {actual:.4f}"
    if col == 'adx':
        return f"  ADX   : {ok} {actual:.1f}"
    if col == 'tenkan_kijun':
        t = calc_row.get('tenkan'); k = calc_row.get('kijun')
        t_str = f"T${t:,.0f}" if t else ''
        k_str = f"K${k:,.0f}" if k else ''
        return f"  TK    : {ok} {actual:.5f}  {t_str} {k_str}"
    return f"  {col} : {actual}  {ok}"


def _sl_tp(setup: dict, group: dict, calc_row: dict) -> tuple:
    """Returns (sl, tp, sl_pct_net, tp_pct_net) where net RR == rr_target exactly."""
    fee_rate = group.get('fee_rate', 0)
    slippage = group.get('slippage', 0)
    rt_fee   = fee_rate + (fee_rate + slippage)

    price   = calc_row['close']
    atr     = calc_row['atr_14'] or 0
    sl_dist = setup['sl_atr'] * atr

    sl_loss_net = sl_dist / price + rt_fee
    tp_gain_net = setup['rr_target'] * sl_loss_net
    tp_dist     = (tp_gain_net + rt_fee) * price

    if setup['side'] == 'LONG':
        sl = round(price - sl_dist, 2)
        tp = round(price + tp_dist, 2)
    else:
        sl = round(price + sl_dist, 2)
        tp = round(price - tp_dist, 2)

    return sl, tp, -(sl_loss_net * 100), +(tp_gain_net * 100)


def build_message(calc_row: dict, groups: list) -> str:
    price  = calc_row['close']
    atr    = calc_row['atr_14']
    dt     = (pd.Timestamp(calc_row['datetime']) + pd.Timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')

    lines = [
        '─' * 34,
        f"🕐 {dt}",
        f"💲 BTC/USDT — ${price:,.2f}",
    ]

    for group in groups:
        for setup in group['setups']:
            # Hide setup if key condition not met
            key_col = setup.get('key')
            if key_col:
                key_cond = next((c for c in setup['conditions'] if c[0] == key_col), None)
                if key_cond:
                    col, op, val = key_cond
                    actual = calc_row.get(col)
                    if actual is None or not OPS[op](actual, val):
                        continue

            is_hit     = all(OPS[op](calc_row.get(col), val)
                             for col, op, val in setup['conditions'])
            side_emoji = '📈' if setup['side'] == 'LONG' else '📉'
            badge      = '✅' if is_hit else '❌'
            sl, tp, sl_pct, tp_pct = _sl_tp(setup, group, calc_row)

            lines += [
                '',
                f"{side_emoji} {group['name']} - {setup['side']} {badge}",
                *[_condition_line(col, op, val, calc_row)
                  for col, op, val in setup['conditions']],
            ]
            if is_hit:
                lines += [
                    f"  SL : ${sl:,.2f}  ({sl_pct:.2f}%)",
                    f"  TP : ${tp:,.2f}  ({tp_pct:+.2f}%)",
                    f"💨 ATR : {atr:,.2f}" if pd.notna(atr) else "💨 ATR : n/a",
                ]

    lines.append('─' * 34)
    return '\n'.join(lines)


# ── main ─────────────────────────────────────────────────────────────────────

def _fetch_compute_write(exchange, candle_dt: str) -> dict:
    row_1h = fetch_latest_1h(exchange)
    print(f"[main] Fetched: {row_1h['datetime']}  close={row_1h['close']}")
    df = pd.read_csv(CALC_CSV).tail(CALC_WARMUP).reset_index(drop=True)
    df = pd.concat([df, pd.DataFrame([row_1h])], ignore_index=True)
    calc_row = compute(df)
    calc_row['datetime'] = candle_dt
    append_calc_row(calc_row)
    return calc_row


def run_once(exchange):
    candle_dt = current_candle_datetime()
    print(f"[main] Candle hour: {candle_dt}")

    gap = csv_gap(candle_dt)

    errors = 0
    try:
        if gap == 0:
            # Already computed this hour — read existing row, display only
            print(f"[main] {candle_dt} already in CSV — display only")
            calc_row = pd.read_csv(CALC_CSV).query(f'datetime == "{candle_dt}"').iloc[0].to_dict()
        elif gap == 1:
            # gap == 1: normal — compute new candle
            calc_row = _fetch_compute_write(exchange, candle_dt)
        else:
            # No CSV or gap in history — seed fills missing candles first
            reason = 'CSV missing' if gap is None else f'gap {gap}h'
            print(f'[main] {reason} — running seed.py...')
            subprocess.run([sys.executable, Path(__file__).parent / 'seed.py'], check=True)
            calc_row = pd.read_csv(CALC_CSV).query(f'datetime == "{candle_dt}"').iloc[0].to_dict()

        # Group setups by webhook env var, send each to its own channel
        from collections import defaultdict
        webhook_groups: dict = defaultdict(list)
        for g in load_config():
            env_key = g.get('webhook', 'EMA_BB_SIGNAL_WEBHOOK_URL')
            webhook_groups[env_key].append(g)

        for env_key, groups in webhook_groups.items():
            url = os.getenv(env_key, '')
            if url:
                send_discord(build_message(calc_row, groups), url)
    except Exception as e:
        errors = 1
        print(f'[main] ERROR: {e}')
        raise
    finally:
        log_url = os.getenv('DISCORD_LOG_URL')
        if log_url:
            dt_label = (pd.Timestamp(candle_dt) + pd.Timedelta(hours=1)).strftime('%b %-d, %Y %H:%M')
            requests.post(log_url, json={'content': f'🕐 {dt_label} {errors} error(s)'}, timeout=10)


if __name__ == '__main__':
    time.sleep(5)  # wait for Binance candle to be available after hour close
    exchange = make_exchange()
    run_once(exchange)
