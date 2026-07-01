import csv
import os
import numpy as np
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

DIR           = Path(__file__).parent
ONCHAIN_CACHE = DIR / 'onchain_chart_cache.csv'
_CSV_FIELDS   = ['date', 'open', 'high', 'low', 'close', 'realized', 'sth', 'lth', 'tmm',
                 'ema200', 'ema12', 'ema26']
_NUMERIC      = ('open', 'high', 'low', 'close', 'realized', 'sth', 'lth', 'tmm',
                 'ema200', 'ema12', 'ema26')


def _fetch_ohlcv(limit: int = 3) -> list:
    import ccxt
    exchange = ccxt.binance({'enableRateLimit': True})
    return exchange.fetch_ohlcv('BTC/USDT', '1d', limit=limit)


def _coinmetrics_mvrv() -> float:
    """Latest MVRV from CoinMetrics community API (free, no key)."""
    start = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%d')
    end   = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
    r = requests.get(
        'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics',
        params={
            'assets':     'btc',
            'metrics':    'CapMVRVCur',
            'start_time': start,
            'end_time':   end,
            'frequency':  '1d',
        },
        timeout=20,
    )
    r.raise_for_status()
    rows = r.json()['data']
    v    = rows[-1].get('CapMVRVCur')
    return float(v) if v is not None else 0.0


def _fear_greed() -> tuple[int, str]:
    r = requests.get('https://api.alternative.me/fng/', timeout=10)
    r.raise_for_status()
    d = r.json()['data'][0]
    return int(d['value']), d['value_classification']


def _btc_monitor(token: str | None) -> dict:
    """STH/LTH realized prices, cohort MVRV, SOPR, supply profit from btc.kaetkung.uk."""
    _empty = {
        'realized_price_sth':   None,
        'realized_price_lth':   None,
        'true_market_mean':     None,
        'mvrv_sth':             None,
        'mvrv_lth':             None,
        'mvrv_z_score':         None,
        'sopr_sth':             None,
        'sopr_lth':             None,
        'supply_in_profit_pct': None,
    }
    if not token:
        return _empty
    r = requests.get(
        'https://btc.kaetkung.uk/api/onchain',
        headers={'Authorization': f'Bearer {token}'},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json().get('metrics', {})

    def _v(key):
        v = data.get(key, {}).get('value')
        return round(float(v), 2) if v is not None else None

    return {
        'realized_price_sth':   _v('realized_price_sth'),
        'realized_price_lth':   _v('realized_price_lth'),
        'true_market_mean':     _v('true_market_mean'),
        'mvrv_sth':             _v('mvrv_sth'),
        'mvrv_lth':             _v('mvrv_lth'),
        'mvrv_z_score':         _v('mvrv_z_score'),
        'sopr_sth':             _v('sopr_sth'),
        'sopr_lth':             _v('sopr_lth'),
        'supply_in_profit_pct': _v('supply_in_profit_pct'),
    }


def _btc_dominance() -> float:
    r = requests.get('https://api.coingecko.com/api/v3/global', timeout=10)
    r.raise_for_status()
    return float(r.json()['data']['market_cap_percentage']['btc'])


def _action_zone_from_cache(history: list, ema12_today: float, ema26_today: float,
                             close_today: float) -> tuple:
    """Find last EMA12/26 crossover from cached series + today's computed values."""
    e12s = [e.get('ema12') for e in history] + [ema12_today]
    e26s = [e.get('ema26') for e in history] + [ema26_today]
    cls  = [e.get('close') for e in history] + [close_today]

    n = len(e12s)
    for i in range(n - 1, 0, -1):
        e12c, e26c = e12s[i],   e26s[i]
        e12p, e26p = e12s[i-1], e26s[i-1]
        if None in (e12c, e26c, e12p, e26p):
            continue
        if (e12c > e26c) != (e12p > e26p):
            zone        = 'bullish' if e12c > e26c else 'bearish'
            cross_price = cls[i] if cls[i] is not None else close_today
            return zone, round(cross_price, 2), n - 1 - i

    last_e12 = next((v for v in reversed(e12s) if v is not None), None)
    last_e26 = next((v for v in reversed(e26s) if v is not None), None)
    zone = 'bullish' if (last_e12 and last_e26 and last_e12 > last_e26) else 'bearish'
    return zone, round(close_today, 2), 0


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


# ── Cache I/O ─────────────────────────────────────────────────────────────────

def _read_csv() -> list:
    if not ONCHAIN_CACHE.exists():
        return []
    with ONCHAIN_CACHE.open(newline='') as f:
        rows = list(csv.DictReader(f))
    result = []
    for row in rows:
        entry = {'date': row['date']}
        for k in _NUMERIC:
            v = row.get(k, '')
            entry[k] = float(v) if v else None
        result.append(entry)
    return result


def _write_csv(history: list) -> None:
    with ONCHAIN_CACHE.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        w.writeheader()
        for row in history:
            w.writerow({k: ('' if row.get(k) is None else row.get(k)) for k in _CSV_FIELDS})


def cache_price_snapshot(data: dict) -> None:
    """Append today's entry to onchain_chart_cache.csv (rolling 120)."""
    history = _read_csv()

    try:
        iso_date = datetime.strptime(data['date'], '%b %d, %Y').strftime('%Y-%m-%d')
    except Exception:
        iso_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    history = [e for e in history if e.get('date') != iso_date]
    history.append({
        'date':     iso_date,
        'open':     data.get('_open'),
        'high':     data.get('_high'),
        'low':      data.get('_low'),
        'close':    data.get('_close'),
        'realized': data.get('realized_price'),
        'sth':      data.get('realized_price_sth'),
        'lth':      data.get('realized_price_lth'),
        'tmm':      data.get('true_market_mean'),
        'ema200':   data.get('ema200'),
        'ema12':    data.get('_ema12'),
        'ema26':    data.get('_ema26'),
    })
    history.sort(key=lambda e: e.get('date', ''))
    _write_csv(history[-120:])


def load_price_history() -> list:
    """Load last 120 entries from onchain_chart_cache.csv."""
    return _read_csv()[-120:]


# ── Main fetch ────────────────────────────────────────────────────────────────

def fetch_all() -> dict:
    """Fetch today's candle only; use CSV cache for all historical computation."""
    history = load_price_history()

    # ── 1. Fetch today's candle from Binance ──────────────────────────────────
    raw        = _fetch_ohlcv(3)
    ts_today   = int(raw[-1][0])
    open_today = float(raw[-1][1])
    high_today = float(raw[-1][2])
    low_today  = float(raw[-1][3])
    close_today = float(raw[-1][4])

    # Reference price = daily open (stable, doesn't drift intraday)
    price_now = open_today

    # Changes from cached open prices
    price_prev   = history[-1]['open']  if history                else price_now
    price_7d_ago = history[-7]['open']  if len(history) >= 7      else price_now
    change_24h   = (price_now / price_prev   - 1) * 100 if price_prev   else 0.0
    change_7d    = (price_now / price_7d_ago - 1) * 100 if price_7d_ago else 0.0

    # ── 2. EMAs: incremental from last cached value ───────────────────────────
    k200 = 2 / 201
    k12  = 2 / 13
    k26  = 2 / 27
    prev200 = next((e['ema200'] for e in reversed(history) if e.get('ema200')), close_today)
    prev12  = next((e['ema12']  for e in reversed(history) if e.get('ema12')),  close_today)
    prev26  = next((e['ema26']  for e in reversed(history) if e.get('ema26')),  close_today)
    ema200 = round(close_today * k200 + prev200 * (1 - k200), 2)
    ema12  = round(close_today * k12  + prev12  * (1 - k12),  2)
    ema26  = round(close_today * k26  + prev26  * (1 - k26),  2)

    # ── 3. Technical indicators from cache closes ─────────────────────────────
    cache_closes = [e['close'] for e in history if e.get('close') is not None]
    cache_highs  = [e['high']  for e in history if e.get('high')  is not None]
    cache_lows   = [e['low']   for e in history if e.get('low')   is not None]

    all_closes = pd.Series(cache_closes + [close_today])
    all_highs  = pd.Series(cache_highs  + [high_today])
    all_lows   = pd.Series(cache_lows   + [low_today])

    rsi_val = float(ta.rsi(all_closes, 14).iloc[-1])
    adx_df  = ta.adx(all_highs, all_lows, all_closes, 14)
    adx_col = next(c for c in adx_df.columns if c.startswith('ADX_'))
    adx_val = float(adx_df[adx_col].iloc[-1])

    action_zone, cross_price, action_days = _action_zone_from_cache(
        history, ema12, ema26, close_today
    )
    resistance, support = _pivot_sr(all_closes, price_now)
    bos_status          = _bos(all_closes)

    # ── 4. Onchain APIs ───────────────────────────────────────────────────────
    try:
        mvrv = _coinmetrics_mvrv()
    except Exception:
        mvrv = 0.0

    realized_price = price_now / mvrv if mvrv else 0.0
    nupl           = 1 - 1 / mvrv    if mvrv else 0.0

    fg_value, _ = _fear_greed()

    try:
        bm = _btc_monitor(os.environ.get('BTC_MONITOR_TOKEN'))
    except Exception:
        bm = {k: None for k in ['realized_price_sth', 'realized_price_lth', 'true_market_mean',
                                 'mvrv_sth', 'mvrv_lth', 'mvrv_z_score',
                                 'sopr_sth', 'sopr_lth', 'supply_in_profit_pct']}

    dom_today = _btc_dominance()

    candle_date = datetime.fromtimestamp(ts_today / 1000, tz=timezone.utc).strftime('%b %d, %Y')

    return {
        'date':                   candle_date,
        'price':                  round(price_now, 2),
        'change_24h':             round(change_24h, 2),
        'change_7d':              round(change_7d, 2),
        'ema200':                 ema200,
        'above_ema200':           price_now > ema200,
        'adx':                    round(adx_val, 1),
        'adx_trending':           adx_val > 20,
        'rsi':                    round(rsi_val, 1),
        'action_zone':            action_zone,
        'action_cross_price':     cross_price,
        'action_days':            action_days,
        'resistance':             round(resistance, 2) if resistance else None,
        'support':                round(support, 2)    if support    else None,
        'bos_status':             bos_status,
        'mvrv':                   round(mvrv, 2),
        'realized_price':         round(realized_price, 2),
        'nupl':                   round(nupl, 2),
        'fg_value':               fg_value,
        'btc_dominance':          round(dom_today, 1),
        # for cache_price_snapshot
        '_open':   open_today,
        '_high':   high_today,
        '_low':    low_today,
        '_close':  close_today,
        '_ema12':  ema12,
        '_ema26':  ema26,
        # for AI (weekly)
        'ohlcv_last_120': (
            [{'open': e['open'], 'high': e['high'], 'low': e['low'],
              'close': e['close'], 'date': e['date']}
             for e in history]
            + [{'open': open_today, 'high': high_today, 'low': low_today,
                'close': close_today, 'date': candle_date}]
        )[-120:],
        # btc.kaetkung.uk onchain
        'realized_price_sth':   bm['realized_price_sth'],
        'realized_price_lth':   bm['realized_price_lth'],
        'true_market_mean':     bm['true_market_mean'],
        'mvrv_sth':             bm['mvrv_sth'],
        'mvrv_lth':             bm['mvrv_lth'],
        'mvrv_z_score':         bm['mvrv_z_score'],
        'sopr_sth':             bm['sopr_sth'],
        'sopr_lth':             bm['sopr_lth'],
        'supply_in_profit_pct': bm['supply_in_profit_pct'],
    }
