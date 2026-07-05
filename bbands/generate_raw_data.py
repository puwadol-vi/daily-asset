"""Compute BBands BO [LuxAlgo] bull/bear values for every (length, mult)
combo from bbands/data_{coin}_price.csv into bbands/data_{coin}_raw.csv.

No network access — run generate_price_data.py first. See bbands/plan.md
and bbands/script.txt for the indicator spec.
"""
import argparse
import pandas as pd
import pandas_ta as ta
from pathlib import Path

from config import COINS, LENGTHS, MULTS

DIR = Path(__file__).parent


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
    parser = argparse.ArgumentParser()
    parser.add_argument('--coin', choices=COINS, default='btc')
    args = parser.parse_args()

    price_path = DIR / f'data_{args.coin}_price.csv'
    df = pd.read_csv(price_path)

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

    out_path = DIR / f'data_{args.coin}_raw.csv'
    out.to_csv(out_path, index=False)
    print(f'Wrote {len(out)} rows to {out_path}')


if __name__ == '__main__':
    main()
