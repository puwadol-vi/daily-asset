import json
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

DIR        = Path(__file__).parent
CACHE_PATH = DIR / 'cache.json'
ET         = ZoneInfo('America/New_York')
K50        = 2 / 51
K100       = 2 / 101


def _expected_trading_date() -> date:
    """
    Returns the date of the most recently closed US trading session.
    At 7:10 AM UTC+7 = 8:10 PM ET previous day → session is closed.
    Skips weekends (Sat/Sun); holidays will show as ❌.
    """
    now = datetime.now(ET)
    # If it's a weekday and market has closed (after 4 PM ET)
    if now.weekday() < 5 and now.hour >= 16:
        return now.date()
    # Otherwise go back to find the last weekday
    d = now.date() - timedelta(days=1)
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d


def _load_cache() -> dict:
    return json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def _fetch_history(ticker: str, period: str) -> pd.DataFrame:
    h = yf.Ticker(ticker).history(period=period, interval='1d')
    if isinstance(h.columns, pd.MultiIndex):
        h.columns = h.columns.get_level_values(0)
    return h[h['Close'].notna()].copy()


def _fetch_latest(ticker: str) -> tuple:
    """
    Fetches only the most recent trading day via period='1d'.
    This endpoint is more up-to-date than period='5d'.
    Returns (close_price, session_date).
    """
    h = _fetch_history(ticker, period='1d')
    if h.empty:
        raise ValueError('no data for period=1d')
    return float(h['Close'].iloc[-1]), h.index[-1].date()


def _compute_status(price, price_prev, e50, e100, e50_prev, e100_prev) -> str:
    regime_bull = e50 > e100
    regime = '📈' if regime_bull else '📉'

    cross_e100_up   = price > e100 and price_prev <= e100_prev
    cross_e100_down = price < e100 and price_prev >= e100_prev
    cross_e50_up    = price > e50  and price_prev <= e50_prev
    cross_e50_down  = price < e50  and price_prev >= e50_prev

    if cross_e100_up:
        pos = '🟢↑'
    elif cross_e100_down:
        pos = '🟢↓'
    elif cross_e50_up:
        pos = '🟡↑'
    elif cross_e50_down:
        pos = '🟡↓'
    elif regime_bull:
        if price > e50:    pos = '🔵'
        elif price > e100: pos = '⚪'
        else:              pos = '🔴'
    else:
        if price < e50:    pos = '🔵'
        elif price < e100: pos = '⚪'
        else:              pos = '🔴'

    return f'{regime}{pos}'


def _apply_incremental(e50, e100, last_close, new_closes: list) -> tuple:
    """
    Incrementally applies EMA for each new close in order.
    Returns (e50, e100, e50_prev, e100_prev, price, price_prev).
    """
    e50_prev   = e50
    e100_prev  = e100
    price_prev = last_close

    for i, close_val in enumerate(new_closes):
        if i == len(new_closes) - 1:
            e50_prev   = e50
            e100_prev  = e100
            price_prev = last_close
        last_close = close_val
        e50  = e50  * (1 - K50)  + close_val * K50
        e100 = e100 * (1 - K100) + close_val * K100

    return e50, e100, e50_prev, e100_prev, last_close, price_prev


def _bootstrap(ticker: str, cache: dict) -> dict:
    """Full 1-year fetch to seed EMA — runs only when no cache entry exists."""
    h = _fetch_history(ticker, period='1y')
    if len(h) < 101:
        raise ValueError(f'not enough history ({len(h)} rows)')

    close    = h['Close']
    ema50_s  = ta.ema(close, 50)
    ema100_s = ta.ema(close, 100)

    price      = float(close.iloc[-1])
    price_prev = float(close.iloc[-2])
    e50        = float(ema50_s.iloc[-1])
    e100       = float(ema100_s.iloc[-1])
    e50_prev   = float(ema50_s.iloc[-2])
    e100_prev  = float(ema100_s.iloc[-2])
    date_str   = h.index[-1].strftime('%b %d, %Y')
    change_24h = (price / price_prev - 1) * 100
    status     = _compute_status(price, price_prev, e50, e100, e50_prev, e100_prev)

    cache[ticker] = {
        'date':       date_str,
        'close':      round(price, 2),
        'ema50':      round(e50, 4),
        'ema100':     round(e100, 4),
        'change_24h': round(change_24h, 2),
        'status':     status,
    }
    return {
        'date':       date_str,
        'price':      round(price, 2),
        'change_24h': round(change_24h, 2),
        'status':     status,
    }


def fetch_stock(ticker: str, cache: dict, expected: date) -> dict:
    expected_str = expected.strftime('%b %d, %Y')

    # Bootstrap if no cache — populates cache[ticker] then falls through to incremental
    if cache.get(ticker) is None:
        _bootstrap(ticker, cache)

    cached      = cache[ticker]
    cached_date = datetime.strptime(cached['date'], '%b %d, %Y').date()

    # Already up to date
    if cached_date == expected:
        return {
            'ticker':     ticker,
            'date':       cached['date'],
            'price':      cached['close'],
            'change_24h': cached['change_24h'],
            'status':     cached['status'],
        }

    # Need new data — try yfinance history first
    recent   = _fetch_history(ticker, period='5d')
    new_rows = sorted(
        [(idx.date(), float(c)) for idx, c in zip(recent.index, recent['Close'])
         if idx.date() > cached_date],
        key=lambda x: x[0],
    )

    has_expected = any(d == expected for d, _ in new_rows)

    if not has_expected:
        # period='5d' is stale — fall back to period='1d' (more up-to-date endpoint)
        latest_price, latest_date = _fetch_latest(ticker)
        if latest_date != expected:
            raise ValueError(f'latest data is {latest_date.strftime("%b %d, %Y")}, expected {expected_str}')
        # Keep any intermediate dates from history, append the latest day's price
        new_rows = [(d, c) for d, c in new_rows if d < expected]
        new_rows.append((expected, latest_price))
    else:
        # Only process up to expected date (ignore future dates if any)
        new_rows = [(d, c) for d, c in new_rows if d <= expected]

    e50, e100, e50_prev, e100_prev, price, price_prev = _apply_incremental(
        cached['ema50'], cached['ema100'], cached['close'],
        [c for _, c in new_rows],
    )

    change_24h = (price / price_prev - 1) * 100
    status     = _compute_status(price, price_prev, e50, e100, e50_prev, e100_prev)

    cache[ticker] = {
        'date':       expected_str,
        'close':      round(price, 2),
        'ema50':      round(e50, 4),
        'ema100':     round(e100, 4),
        'change_24h': round(change_24h, 2),
        'status':     status,
    }
    return {
        'ticker':     ticker,
        'date':       expected_str,
        'price':      round(price, 2),
        'change_24h': round(change_24h, 2),
        'status':     status,
    }


def fetch_all(stocks: list) -> list:
    cache    = _load_cache()
    expected = _expected_trading_date()
    results  = []
    for s in stocks:
        ticker = s['ticker']
        try:
            results.append(fetch_stock(ticker, cache, expected))
        except Exception as e:
            results.append({
                'ticker': ticker,
                'date':   None,
                'price':  None,
                'change_24h': None,
                'status': '❌',
                'error':  str(e),
            })
    _save_cache(cache)
    return results
