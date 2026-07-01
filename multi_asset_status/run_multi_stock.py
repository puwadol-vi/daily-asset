import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))

load_dotenv(DIR.parent / '.env')

from fetch_stocks import fetch_all


def _fmt_price(price) -> str:
    return f'{price:,.2f}' if price is not None else 'N/A'


def _fmt_chg(chg) -> str:
    if chg is None:
        return 'N/A'
    return f'+{chg:.2f}%' if chg >= 0 else f'{chg:.2f}%'


def _pad_status(status: str) -> str:
    # Arrow chars (↑↓) are 1-wide; without arrow add a space to keep alignment
    return status if status[-1] in ('↑', '↓') else status + ' '


def main() -> None:
    stocks_config = json.loads((DIR / 'stocks.json').read_text())['stocks']
    results = fetch_all(stocks_config)

    # Use the most recent data date across all stocks (not the fetch date)
    dates = [r['date'] for r in results if r.get('date')]
    data_date = max(dates, key=lambda d: datetime.strptime(d, '%b %d, %Y')) if dates else 'N/A'

    lines = [f'📊 US Stock Status — {data_date}', '']
    for r in results:
        ticker = r['ticker'].ljust(6)
        if r.get('error'):
            lines.append(f'❌  {ticker}  {r["error"]}')
        else:
            s   = _pad_status(r['status'])
            chg = _fmt_chg(r['change_24h'])
            lines.append(f'{s} {ticker}  ${_fmt_price(r["price"])}   {chg}')

    lines += [
        '',
        '🔵 aligned  ⚪ zone  🔴 diverged',
        '🟡↑↓ EMA50 cross (fast)  🟢↑↓ EMA100 cross (slow)',
        '📈 bull (E50>E100)  📉 bear (E50<E100)',
    ]

    message = '\n'.join(lines)

    resp = requests.post(os.environ['MULTI_ASSET_WEBHOOK_URL'], json={'content': message})
    resp.raise_for_status()

    error_count = sum(1 for r in results if r.get('error'))
    log_url = os.environ.get('DISCORD_LOG_URL')
    if log_url:
        requests.post(log_url, json={'content': f'📅 Multi Asset Status — {data_date} — {error_count} error(s)'})

    print(f'\nPosted: {data_date}')


if __name__ == '__main__':
    main()
