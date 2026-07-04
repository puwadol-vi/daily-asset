"""Convert bbands/raw_data.csv into an 8-bit weekly signal mask per
(length, mult) combo -> bbands/process_data.csv.

Bit legend (see bbands/plan.md section 3):
  0 green_go_pos   G_last==0 and G_this>0
  1 red_go_pos     R_last==0 and R_this>0
  2 cross_up       G_last<R_last and G_this>R_this
  3 cross_down     G_last>R_last and G_this<R_this
  4 red_peak       R_last>R_this
  5 green_peak     G_last>G_this
  6 green_go_zero  G_last>0 and G_this==0
  7 red_go_zero    R_last>0 and R_this==0
"""
import pandas as pd
from pathlib import Path

DIR = Path(__file__).parent
IN = DIR / 'raw_data.csv'
OUT = DIR / 'process_data.csv'

LENGTHS = [7, 8, 9, 10]
MULTS = [0.10, 0.15, 0.20, 0.25]

BIT_GREEN_GO_POS = 1 << 0
BIT_RED_GO_POS = 1 << 1
BIT_CROSS_UP = 1 << 2
BIT_CROSS_DOWN = 1 << 3
BIT_RED_PEAK = 1 << 4
BIT_GREEN_PEAK = 1 << 5
BIT_GREEN_GO_ZERO = 1 << 6
BIT_RED_GO_ZERO = 1 << 7


def combo_mask(g: pd.Series, r: pd.Series) -> pd.Series:
    g_last, r_last = g.shift(1), r.shift(1)
    valid = g.notna() & r.notna() & g_last.notna() & r_last.notna()

    mask = pd.Series(0, index=g.index, dtype='Int64')
    mask += ((g_last == 0) & (g > 0)) * BIT_GREEN_GO_POS
    mask += ((r_last == 0) & (r > 0)) * BIT_RED_GO_POS
    mask += ((g_last < r_last) & (g > r)) * BIT_CROSS_UP
    mask += ((g_last > r_last) & (g < r)) * BIT_CROSS_DOWN
    mask += (r_last > r) * BIT_RED_PEAK
    mask += (g_last > g) * BIT_GREEN_PEAK
    mask += ((g_last > 0) & (g == 0)) * BIT_GREEN_GO_ZERO
    mask += ((r_last > 0) & (r == 0)) * BIT_RED_GO_ZERO

    return mask.where(valid, other=pd.NA)


def main() -> None:
    df = pd.read_csv(IN)
    out = pd.DataFrame({'date': df['close_date']})
    for length in LENGTHS:
        for mult in MULTS:
            g = df[f'bull_{length}_{mult:.2f}']
            r = df[f'bear_{length}_{mult:.2f}']
            out[f'{length}_{mult:.2f}'] = combo_mask(g, r)

    out.to_csv(OUT, index=False)
    print(f'Wrote {len(out)} rows to {OUT}')


if __name__ == '__main__':
    main()
