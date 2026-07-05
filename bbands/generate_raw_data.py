"""Compute BBands BO [LuxAlgo] bull/bear values for every (length, mult)
combo, plus the Nadaraya-Watson Envelope [LuxAlgo] band (fixed params),
from bbands/data_{coin}_price.csv into bbands/data_{coin}_raw.csv.

No network access — run generate_price_data.py first. See bbands/plan.md,
bbands/script.txt, and bbands/Nadaraya-Watson.txt for the indicator specs.
"""
import argparse
import numpy as np
import pandas as pd
import pandas_ta as ta
from pathlib import Path

from config import COINS, LENGTHS, MULTS, NW_BANDWIDTH, NW_MULT

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


def nadaraya_watson(close: pd.Series, bandwidth: float, mult: float) -> tuple[pd.Series, pd.Series]:
    """Repainting fit (script default): Gaussian kernel-weighted regression
    over the last min(500, n) bars. See bbands/Nadaraya-Watson.txt."""
    values = close.to_numpy()
    n = len(values)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    if n == 0:
        return pd.Series(upper, index=close.index), pd.Series(lower, index=close.index)

    window = min(500, n)
    start = n - window
    window_vals = values[start:]
    idx = np.arange(window)
    diff = idx[:, None] - idx[None, :]
    weights = np.exp(-(diff ** 2) / (bandwidth ** 2 * 2))
    nwe = (weights @ window_vals) / weights.sum(axis=1)
    sae = np.abs(window_vals - nwe).mean() * mult

    upper[start:] = nwe + sae
    lower[start:] = nwe - sae
    return pd.Series(upper, index=close.index), pd.Series(lower, index=close.index)


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

    nw_upper, nw_lower = nadaraya_watson(df['close'], NW_BANDWIDTH, NW_MULT)
    out['nw_upper'] = nw_upper.round(4)
    out['nw_lower'] = nw_lower.round(4)

    out_path = DIR / f'data_{args.coin}_raw.csv'
    out.to_csv(out_path, index=False)
    print(f'Wrote {len(out)} rows to {out_path}')


if __name__ == '__main__':
    main()
