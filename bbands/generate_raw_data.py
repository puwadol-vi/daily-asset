"""Fetch BTC/USDT weekly candles and compute BBands BO [LuxAlgo] bull/bear
values for every (length, mult) combo into bbands/raw_data.csv.

See bbands/plan.md and bbands/script.txt for the indicator spec.
"""
import ccxt
import pandas as pd
import pandas_ta as ta
from pathlib import Path

DIR = Path(__file__).parent
OUT = DIR / 'raw_data.csv'

SYMBOL = 'BTC/USDT'
TIMEFRAME = '1w'
LENGTHS = [7, 8, 9, 10]
MULTS = [0.10, 0.15, 0.20, 0.25]


def fetch_all_ohlcv() -> list:
    exchange = ccxt.binance({'enableRateLimit': True})
    since = exchange.parse8601('2017-01-01T00:00:00Z')
    rows = []
    while True:
        batch = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=1000)
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
    return df


def bull_bear(close: pd.Series, length: int, mult: float) -> tuple[pd.Series, pd.Series]:
    """Vectorized form of the Pine for-loop: a rolling sum of the per-bar
    breakout distance / total distance, over the last `length` bars."""
    stdev = close.rolling(length).std(ddof=0) * mult
    ema = ta.ema(close, length=length)
    upper = ema + stdev
    lower = ema - stdev

    diff_upper = close - upper
    diff_lower = lower - close

    bull_num = diff_upper.clip(lower=0).rolling(length).sum()
    bull_den = diff_upper.abs().rolling(length).sum()
    bear_num = diff_lower.clip(lower=0).rolling(length).sum()
    bear_den = diff_lower.abs().rolling(length).sum()

    bull = (bull_num / bull_den * 100).where(bull_den > 0, 0)
    bear = (bear_num / bear_den * 100).where(bear_den > 0, 0)

    # Not enough history yet for band + rolling window to be meaningful.
    warmup = length * 2 - 1
    bull.iloc[:warmup] = float('nan')
    bear.iloc[:warmup] = float('nan')
    return bull, bear


def main() -> None:
    rows = fetch_all_ohlcv()
    df = build_dataframe(rows)

    out = pd.DataFrame({
        'close_date': df['close_date'],
        'open': df['open'],
        'high': df['high'],
        'low': df['low'],
        'close': df['close'],
        'volume': df['volume'],
    })
    for length in LENGTHS:
        for mult in MULTS:
            bull, bear = bull_bear(df['close'], length, mult)
            out[f'bull_{length}_{mult:.2f}'] = bull.round(4)
            out[f'bear_{length}_{mult:.2f}'] = bear.round(4)

    out.to_csv(OUT, index=False)
    print(f'Wrote {len(out)} rows to {OUT}')


if __name__ == '__main__':
    main()
