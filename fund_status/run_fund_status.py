import json
import os
import sys
import requests
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))
load_dotenv(DIR.parent / '.env')

from fetch_funds import fetch_all, expected_date

SCOPES = ['https://www.googleapis.com/auth/calendar']


# ── formatting ────────────────────────────────────────────────────────────────

def _emoji(chg_pct) -> str:
    if chg_pct is None: return '⚪'
    if chg_pct > 0:     return '🟢'
    if chg_pct < 0:     return '🔴'
    return '⚪'


def _fmt_chg(chg_pct) -> str:
    if chg_pct is None:
        return 'N/A'
    return f'{chg_pct:+.2f}%'


def _fmt_nav(nav) -> str:
    if nav is None:
        return ''
    if nav < 1:
        return f'{nav:.4f}'
    return f'{nav:,.2f}'


def _stale(item_date: date | None, ref: date) -> str:
    # Only flag when data is OLDER than expected (truly stale), not when fresher
    if item_date is None or item_date >= ref:
        return ''
    return f' #{item_date.strftime("%b %-d")}'


def _fmt_line(item: dict, ref: date) -> str:
    emoji = _emoji(item['chg_pct'])
    chg   = _fmt_chg(item['chg_pct']).rjust(8)
    price = f'  {_fmt_nav(item["nav"])}' if item['nav'] is not None else ''
    name  = f'  {item["display"]}'
    stale = _stale(item.get('date'), ref)
    if item.get('error'):
        return f'❌ {item["display"]}  {item["error"][:40]}'
    return f'{emoji} {chg}{price}{name}{stale}'


def build_message(groups: list, ref: date) -> str:
    lines  = []
    for group in groups:
        if not group['items']:
            continue
        lines.append(f'[{group["name"]}]')
        for item in group['items']:
            lines.append(_fmt_line(item, ref))
    return '\n'.join(lines).rstrip()


# ── outputs ───────────────────────────────────────────────────────────────────


def post_discord(groups: list, ref: date) -> None:
    error_items = [
        item
        for g in groups
        for item in g['items']
        if item.get('error')
    ]
    lines = [f'📅 Fund Status — {ref.strftime("%b %-d, %Y")} — {len(error_items)} error(s)']
    for item in error_items:
        lines.append(f'❌ {item["display"]}  {item["error"]}')
    url = os.environ['DISCORD_WEBHOOK_URL']
    resp = requests.post(url, json={'content': '\n'.join(lines)})
    if not resp.ok:
        raise RuntimeError(f'Discord {resp.status_code}: {resp.text}')


def post_calendar(message: str, ref: date) -> None:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        os.environ['GOOGLE_SERVICE_ACCOUNT_FILE'],
        scopes=SCOPES,
    )
    service = build('calendar', 'v3', credentials=creds)

    today = datetime.now(ZoneInfo('Asia/Bangkok')).date()
    title = f'*📊 Fund NAV — {ref.strftime("%b %-d")}'
    event = {
        'summary':     title,
        'description': message,
        'start':       {'date': today.isoformat()},
        'end':         {'date': today.isoformat()},
    }
    result = service.events().insert(
        calendarId=os.environ['GOOGLE_CALENDAR_ID'],
        body=event,
    ).execute()
    return result


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    config = json.loads((DIR / 'funds.json').read_text())
    ref    = expected_date()

    groups  = fetch_all(config['groups'])
    message = build_message(groups, ref)

    if os.environ.get('DISCORD_WEBHOOK_URL'):
        post_discord(groups, ref)
        print('Discord: OK')

    if os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE') and os.environ.get('GOOGLE_CALENDAR_ID'):
        result = post_calendar(message, ref)
        print(f'Calendar: OK')
        print(f'  id:     {result.get("id")}')
        print(f'  status: {result.get("status")}')
        print(f'  link:   {result.get("htmlLink")}')
    else:
        print('Calendar: skipped (GOOGLE_SERVICE_ACCOUNT_FILE / GOOGLE_CALENDAR_ID not set)')

    print(f'\nPosted: {ref}')


if __name__ == '__main__':
    main()
