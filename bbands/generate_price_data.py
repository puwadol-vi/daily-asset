"""Fetch weekly OHLCV for a coin into bbands/data_{coin}_price.csv.

The only script in the pipeline that hits the exchange — generate_raw_data.py
and generate_process_data.py read this file, so re-tuning indicator math
never re-fetches. See bbands/plan.md section 9.8.
"""
import argparse
import ccxt
import pandas as pd
from pathlib import Path

from config import COINS

DIR = Path(__file__).parent
TIMEFRAME = '1w'


def fetch_all_ohlcv(symbol: str) -> list:
    exchange = ccxt.binance({'enableRateLimit': True})
    since = exchange.parse8601('2017-01-01T00:00:00Z')
    rows = []
    while True:
        batch = exchange.fetch_ohlcv(symbol, TIMEFRAME, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        last_ts = batch[-1][0]
        if last_ts == since or len(batch) < 1000:
            break
        since = last_ts + 1
    return rows


def build_dataframe(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
    df['close_date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.strftime('%Y-%m-%d')
    return df[['close_date', 'open', 'high', 'low', 'close', 'volume']]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--coin', choices=COINS, default='btc')
    args = parser.parse_args()

    df = build_dataframe(fetch_all_ohlcv(COINS[args.coin]))
    out = DIR / f'data_{args.coin}_price.csv'
    df.to_csv(out, index=False)
    print(f'Wrote {len(df)} rows to {out}')


if __name__ == '__main__':
    main()
