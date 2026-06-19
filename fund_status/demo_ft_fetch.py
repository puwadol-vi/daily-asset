"""Demo: fetch BCHS:LSE (Invesco CoinShares Blockchain ETF) via yfinance."""
import yfinance as yf
import pandas
from datetime import date
from zoneinfo import ZoneInfo

ICT = ZoneInfo('Asia/Bangkok')


def fetch_lse(ticker_yahoo: str) -> dict:
    """Fetch latest price/change for an LSE ticker (Yahoo suffix .L, price in GBp)."""
    t = yf.Ticker(ticker_yahoo)
    h = t.history(period='5d', interval='1d')
    if isinstance(h.columns, pandas.MultiIndex):
        h.columns = h.columns.get_level_values(0)
    h = h[h['Close'].notna()]
    if len(h) < 2:
        return {'nav': None, 'chg_pct': None, 'date': None}
    price_gbx = float(h['Close'].iloc[-1])
    prev_gbx  = float(h['Close'].iloc[-2])
    price_gbp = price_gbx / 100          # GBp → GBP
    chg_pct   = (price_gbx / prev_gbx - 1) * 100
    row_date  = h.index[-1].date()
    return {
        'nav':     round(price_gbp, 4),
        'chg_pct': round(chg_pct, 2),
        'date':    row_date,
        'currency': 'GBP',
    }


if __name__ == '__main__':
    result = fetch_lse('BCHS.L')
    print(f"BCHS:LSE  (Invesco CoinShares Blockchain)")
    print(f"  date    : {result['date']}")
    print(f"  price   : {result['nav']} {result['currency']}")
    print(f"  change  : {result['chg_pct']:+.2f}%")
