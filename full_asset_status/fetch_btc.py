import json
import numpy as np
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

DIR = Path(__file__).parent


def _fetch_ohlcv(limit: int = 250) -> list:
    import ccxt
    exchange = ccxt.binance({'enableRateLimit': True})
    return exchange.fetch_ohlcv('BTC/USDT', '1d', limit=limit)


def _coinmetrics() -> dict:
    """MVRV + exchange reserve/flows from CoinMetrics community (free, no key)."""
    start = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%d')
    end   = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
    r = requests.get(
        'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics',
        params={
            'assets':     'btc',
            'metrics':    'CapMVRVCur,SplyExNtv,FlowInExNtv,FlowOutExNtv',
            'start_time': start,
            'end_time':   end,
            'frequency':  '1d',
        },
        timeout=20,
    )
    r.raise_for_status()
    rows   = r.json()['data']
    latest = rows[-1]
    prev   = rows[-2] if len(rows) > 1 else rows[-1]

    def _f(row, key):
        v = row.get(key)
        return float(v) if v is not None else 0.0

    return {
        'mvrv':         _f(latest, 'CapMVRVCur'),
        'sply_ex':      _f(latest, 'SplyExNtv'),
        'sply_ex_prev': _f(prev,   'SplyExNtv'),
        'flow_in':      _f(latest, 'FlowInExNtv'),
        'flow_out':     _f(latest, 'FlowOutExNtv'),
    }


def _fear_greed() -> tuple[int, str]:
    r = requests.get('https://api.alternative.me/fng/', timeout=10)
    r.raise_for_status()
    d = r.json()['data'][0]
    return int(d['value']), d['value_classification']


def _btc_dominance() -> float:
    r = requests.get('https://api.coingecko.com/api/v3/global', timeout=10)
    r.raise_for_status()
    return float(r.json()['data']['market_cap_percentage']['btc'])


def _action_zone(ema12: pd.Series, ema26: pd.Series, close: pd.Series, ts: pd.Series):
    diff  = ema12 - ema26
    valid = diff.dropna()
    signs = np.sign(valid.values)
    changes = np.where(np.diff(signs) != 0)[0]

    if len(changes) == 0:
        zone = 'bullish' if float(diff.iloc[-1]) > 0 else 'bearish'
        return zone, float(close.iloc[-1]), 'unknown', 0

    cross_pos   = int(changes[-1]) + 1
    cross_orig  = int(valid.index[cross_pos])
    zone        = 'bullish' if valid.iloc[cross_pos] > 0 else 'bearish'
    cross_price = float(close.iloc[cross_orig])
    days        = len(close) - 1 - cross_orig
    cross_date  = datetime.fromtimestamp(
        int(ts.iloc[cross_orig]) / 1000, tz=timezone.utc
    ).strftime('%b %d, %Y')
    return zone, cross_price, cross_date, days


def _pivot_sr(close: pd.Series, price: float):
    roll_max = close.rolling(5, center=True).max()
    roll_min = close.rolling(5, center=True).min()
    ph = close[close == roll_max].dropna()
    pl = close[close == roll_min].dropna()
    r  = ph[ph > price]
    s  = pl[pl < price]
    return (float(r.min()) if len(r) else None,
            float(s.max()) if len(s) else None)


def _bos(close: pd.Series) -> str:
    roll_max = close.rolling(5, center=True).max()
    roll_min = close.rolling(5, center=True).min()
    sh = close[close == roll_max].dropna()
    sl = close[close == roll_min].dropna()
    price = float(close.iloc[-1])

    if len(sl) >= 1 and price < float(sl.iloc[-1]):
        return 'BOS confirmed'
    if len(sh) >= 2 and float(sh.iloc[-1]) < float(sh.iloc[-2]):
        return 'LH forming — first warning'

    sh_vals = sh.values[-5:]
    n_hh = 0
    for i in range(len(sh_vals) - 1, 0, -1):
        if sh_vals[i] > sh_vals[i - 1]:
            n_hh += 1
        else:
            break
    return f'HH/HL intact — {n_hh} consecutive HHs, no warning'


def fetch_all() -> dict:
    raw = _fetch_ohlcv(250)
    df  = pd.DataFrame(raw, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    close, high, low = df['close'], df['high'], df['low']

    ema200 = ta.ema(close, 200)
    ema12  = ta.ema(close, 12)
    ema26  = ta.ema(close, 26)
    adx_df = ta.adx(high, low, close, 14)
    rsi_s  = ta.rsi(close, 14)

    # Daily open = fixed reference price, doesn't drift during the day
    price_now  = float(df['open'].iloc[-1])
    price_prev = float(df['open'].iloc[-2])
    change_24h = (price_now / price_prev - 1) * 100

    action_zone, cross_price, cross_date, action_days = _action_zone(
        ema12, ema26, close, df['ts']
    )
    resistance, support = _pivot_sr(close, price_now)
    bos_status          = _bos(close)

    # CoinMetrics community: MVRV + exchange reserve/flows
    try:
        cm       = _coinmetrics()
        mvrv     = cm['mvrv']
        sply_ex  = cm['sply_ex']
        flow_in  = cm['flow_in']
        flow_out = cm['flow_out']
        ex_trend = 'rising' if sply_ex > cm['sply_ex_prev'] else 'declining'
    except Exception:
        mvrv     = 0.0
        sply_ex  = 0.0
        flow_in  = 0.0
        flow_out = 0.0
        ex_trend = 'declining'

    # Derived exactly from MVRV: Price / MVRV = Realized Price; 1 - 1/MVRV = NUPL
    realized_price = price_now / mvrv if mvrv else 0.0
    nupl           = 1 - 1 / mvrv    if mvrv else 0.0
    net_flow       = flow_in - flow_out  # negative = net outflow = bullish

    fg_value, fg_label = _fear_greed()

    # BTC dominance direction vs yesterday (cached under "btc" key)
    cache_path = DIR / 'cache.json'
    cache      = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    btc_cache  = cache.setdefault('btc', {})
    dom_today  = _btc_dominance()
    dom_prev   = btc_cache.get('dominance', {}).get('value', dom_today)
    btc_dom_dir = '↑' if dom_today >= dom_prev else '↓'
    btc_cache['dominance'] = {
        'value':   round(dom_today, 2),
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    }
    cache_path.write_text(json.dumps(cache, indent=2))

    tail60        = df.tail(60)
    ohlcv_last_60 = [
        {'open': float(r.open), 'high': float(r.high),
         'low': float(r.low), 'close': float(r.close), 'ts': int(r.ts)}
        for r in tail60.itertuples()
    ]
    ema200_series = [float(v) if pd.notna(v) else None for v in ema200.tail(60)]
    ema12_series  = [float(v) if pd.notna(v) else None for v in ema12.tail(60)]
    ema26_series  = [float(v) if pd.notna(v) else None for v in ema26.tail(60)]

    adx_col = next(c for c in adx_df.columns if c.startswith('ADX_'))
    adx_val = float(adx_df[adx_col].iloc[-1])

    candle_date = datetime.fromtimestamp(
        int(df['ts'].iloc[-1]) / 1000, tz=timezone.utc
    ).strftime('%b %d, %Y')

    return {
        'date':                   candle_date,
        'price':                  round(price_now, 2),
        'change_24h':             round(change_24h, 2),
        'ema200':                 round(float(ema200.iloc[-1]), 2),
        'above_ema200':           price_now > float(ema200.iloc[-1]),
        'adx':                    round(adx_val, 1),
        'adx_trending':           adx_val > 20,
        'rsi':                    round(float(rsi_s.iloc[-1]), 1),
        'action_zone':            action_zone,
        'action_cross_price':     round(cross_price, 2),
        'action_cross_date':      cross_date,
        'action_days':            action_days,
        'resistance':             round(resistance, 2) if resistance else None,
        'support':                round(support, 2) if support else None,
        'bos_status':             bos_status,
        'mvrv':                   round(mvrv, 2),
        'realized_price':         round(realized_price, 2),
        'nupl':                   round(nupl, 2),
        'fg_value':               fg_value,
        'fg_label':               fg_label,
        'btc_dominance':          round(dom_today, 1),
        'btc_dom_direction':      btc_dom_dir,
        'exchange_reserve':       sply_ex,
        'exchange_reserve_trend': ex_trend,
        'exchange_net_flow':      net_flow,
        'ohlcv_last_60':          ohlcv_last_60,
        'ema200_series':          ema200_series,
        'ema12_series':           ema12_series,
        'ema26_series':           ema26_series,
    }
