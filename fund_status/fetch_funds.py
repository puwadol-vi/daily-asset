import pandas
import requests
import yfinance as yf
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

ICT = ZoneInfo('Asia/Bangkok')

FINNOMENA_LIST   = 'https://www.finnomena.com/fn3/api/fund/public/list'
FINNOMENA_LATEST = 'https://www.finnomena.com/fn3/api/fund/v2/public/funds/{id}/latest'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Origin': 'https://www.finnomena.com',
    'Referer': 'https://www.finnomena.com/',
    'Connection': 'keep-alive',
}

_fund_map: dict[str, str] = {}   # short_code → fund_id
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        _session.get('https://www.finnomena.com/', timeout=10)
    return _session


def expected_date() -> date:
    """Most recent completed business day in ICT time."""
    d = datetime.now(ICT).date() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _load_fund_map() -> None:
    global _fund_map
    if _fund_map:
        return
    resp = _get_session().get(FINNOMENA_LIST, timeout=15)
    resp.raise_for_status()
    _fund_map = {f['short_code']: f['id'] for f in resp.json() if f.get('short_code')}


def _fetch_fund(code: str) -> dict:
    _load_fund_map()
    fund_id = _fund_map.get(code)
    if not fund_id:
        raise ValueError(f'not found in Finnomena: {code}')
    resp = _get_session().get(FINNOMENA_LATEST.format(id=fund_id), timeout=10)
    resp.raise_for_status()
    d = resp.json().get('data', {})
    raw_date = d.get('date', '')
    return {
        'nav':     round(float(d['value']), 2) if d.get('value') is not None else None,
        'chg_pct': round(float(d['d_change']), 2) if d.get('d_change') is not None else None,
        'date':    datetime.fromisoformat(raw_date.replace('Z', '+00:00')).date() if raw_date else None,
    }


def _fetch_yahoo(ticker: str) -> dict:
    h = yf.Ticker(ticker).history(period='5d', interval='1d')
    if isinstance(h.columns, pandas.MultiIndex):
        h.columns = h.columns.get_level_values(0)
    h = h[h['Close'].notna()]
    if len(h) < 2:
        return {'nav': None, 'chg_pct': None, 'date': None}
    price   = float(h['Close'].iloc[-1])
    prev    = float(h['Close'].iloc[-2])
    chg_pct = (price / prev - 1) * 100
    return {
        'nav':     round(price, 2),
        'chg_pct': round(chg_pct, 2),
        'date':    h.index[-1].date(),
    }


def _fetch_item(item: dict, group_source: str) -> dict:
    src     = item.get('source') or group_source
    display = item['display']
    if src == 'manual':
        return {'display': display, 'nav': None, 'chg_pct': None, 'date': None, 'error': None}
    try:
        if src == 'sec':
            result = _fetch_fund(item['code'])
        else:
            result = _fetch_yahoo(item['ticker'])
        return {'display': display, **result, 'error': None}
    except Exception as e:
        return {'display': display, 'nav': None, 'chg_pct': None, 'date': None, 'error': str(e)}


def fetch_all(groups: list) -> list:
    """Returns [{name, items: [{display, nav, chg_pct, date, error}]}]."""
    return [
        {
            'name':  g['name'],
            'items': [_fetch_item(item, g['source']) for item in g['items']],
        }
        for g in groups
    ]
