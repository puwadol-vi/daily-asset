#!/usr/bin/env python3
"""
Seed / recover btc_calc.csv.

  No CSV  → full init from history
  CSV exists but has gaps → fetch only missing slots and append

Labels use the same +1h slot convention as main.py:
  candle that opened at 00:00 ICT → written as slot '01:00'

Usage: venv/bin/python3 ema_bb_signal/seed.py
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

import ccxt
import pandas as pd
import ta

RUNTIME_DIR = Path(__file__).parent / 'runtime'
CALC_CSV    = RUNTIME_DIR / 'btc_calc.csv'
WARMUP      = 250


def _compute(df: pd.DataFrame) -> dict:
    df = df.copy().reset_index(drop=True)

    df['ema_200']   = ta.trend.ema_indicator(df['close'], window=200)
    ema_200_val     = float(df['ema_200'].iloc[-1])

    df['vol_ratio'] = (df['volume'] / df['volume'].rolling(20).mean()).round(5)

    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_basis']    = bb.bollinger_mavg()
    df['bb_upper']    = bb.bollinger_hband()
    df['bb_lower']    = bb.bollinger_lband()
    df['bb_distance'] = df['bb_upper'] - df['bb_basis']
    df['bb_ratio']    = (df['close'] - df['bb_basis']) / df['bb_distance']

    df['atr_14'] = ta.volatility.average_true_range(
        df['high'], df['low'], df['close'], window=14
    )

    last  = df.iloc[-1]
    close = round(float(last['close']), 2)

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
    }


def _fetch_raw(exchange, limit: int) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = (
        pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=7)
    ).dt.strftime('%Y-%m-%d %H:%M')
    return df[:-1].reset_index(drop=True)  # exclude forming + current slot (main.py handles current)


def init(exchange):
    print('[seed] No CSV found — full init...')
    df = _fetch_raw(exchange, WARMUP + 10)
    if len(df) < 20:
        print(f'[seed] Not enough data returned ({len(df)} rows) — aborting')
        return
    rows = [_compute(df.iloc[:i + 1].copy()) for i in range(20, len(df))]
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(CALC_CSV, index=False)
    print(f'[seed] Wrote {len(rows)} rows → last: {rows[-1]["datetime"]}')


def recover(exchange):
    df_csv  = pd.read_csv(CALC_CSV)
    last_dt = pd.Timestamp(df_csv['datetime'].iloc[-1])
    now_ict = pd.Timestamp.now('UTC').tz_localize(None) + pd.Timedelta(hours=7)
    # Slots to fill = between last_dt and the slot before the current one
    # (current slot is always computed by main.py after seed returns)
    missing = int((now_ict.floor('h') - pd.Timedelta(hours=1) - last_dt).total_seconds() / 3600)

    if missing <= 0:
        print(f'[seed] CSV is up to date (last: {last_dt})')
        return

    print(f'[seed] {missing} missing slot(s) since {last_dt} — fetching...')
    df_raw = _fetch_raw(exchange, WARMUP + missing + 5)

    if len(df_raw) < 20:
        print(f'[seed] Not enough data returned ({len(df_raw)} rows) — skipping')
        return

    existing_dts = set(df_csv['datetime'])
    new_indices  = [i for i, dt in enumerate(df_raw['datetime'])
                    if dt not in existing_dts and i >= 20]

    if not new_indices:
        print('[seed] Nothing new to append')
        return

    rows = [_compute(df_raw.iloc[:i + 1].copy()) for i in new_indices]
    pd.DataFrame(rows).to_csv(CALC_CSV, mode='a', header=False, index=False)
    print(f'[seed] Appended {len(rows)} row(s) → last: {rows[-1]["datetime"]}')


if __name__ == '__main__':
    exchange = ccxt.binance({'enableRateLimit': True})
    if CALC_CSV.exists():
        recover(exchange)
    else:
        init(exchange)
    print('[seed] Done')
