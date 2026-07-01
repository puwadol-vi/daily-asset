import json
import os
import sys
import requests
from datetime import date, timedelta
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
    if item.get('error'):
        return f'❌ {item["display"]}  {item["error"][:10]}'

    is_stale = item.get('date') and item['date'] < ref
    if is_stale and item.get('master_code'):
        chg_pct     = item.get('master_chg_pct')
        nav         = item.get('master_nav')
        master_date = item.get('master_date')
        stale_tag   = _stale(master_date, ref)
        suffix      = f'  ({item["master_code"]}){stale_tag}'
    else:
        chg_pct = item['chg_pct']
        nav     = item['nav']
        suffix  = _stale(item.get('date'), ref)


    emoji = _emoji(chg_pct)
    chg   = _fmt_chg(chg_pct).rjust(8)
    name  = f'  {item["display"]}'
    return f'{emoji} {chg}{name}{suffix}'


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


def post_log(groups: list, ref: date) -> None:
    error_items = [
        item
        for g in groups
        for item in g['items']
        if item.get('error')
    ]
    lines = [f'📅 Fund Status — {ref.strftime("%b %-d, %Y")} — {len(error_items)} error(s)']
    for item in error_items:
        lines.append(f'❌ {item["display"]}  {item["error"]}')
    url = os.environ['DISCORD_LOG_URL']
    resp = requests.post(url, json={'content': '\n'.join(lines)})
    if not resp.ok:
        raise RuntimeError(f'Discord {resp.status_code}: {resp.text}')


def is_holiday(groups: list, ref: date) -> bool:
    """
    Assume ref was a public holiday if ALL fetched items with dates
    are older than ref — no external holiday API needed.
    """
    dated = [
        item for g in groups for item in g['items']
        if item.get('date') and not item.get('error')
    ]
    if not dated:
        return False
    return all(item['date'] < ref for item in dated)


def post_calendar(message: str, ref: date) -> None:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        os.environ['GOOGLE_SERVICE_ACCOUNT_FILE'],
        scopes=SCOPES,
    )
    service = build('calendar', 'v3', credentials=creds)
    cal_id = os.environ['GOOGLE_CALENDAR_ID']
    title  = f'*📊 Fund NAV — {ref.strftime("%b %-d")}'

    # Duplicate guard — skip if event already exists for this date
    existing = service.events().list(
        calendarId=cal_id,
        timeMin=f'{ref.isoformat()}T00:00:00Z',
        timeMax=f'{(ref + timedelta(days=1)).isoformat()}T00:00:00Z',
        singleEvents=True,
    ).execute()
    for ev in existing.get('items', []):
        if ev.get('summary') == title:
            print(f'Calendar: event already exists for {ref} — skip')
            return None

    event = {
        'summary':     title,
        'description': message,
        'start':       {'date': ref.isoformat()},
        'end':         {'date': ref.isoformat()},
    }
    result = service.events().insert(calendarId=cal_id, body=event).execute()
    return result


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    config = json.loads((DIR / 'funds.json').read_text())
    ref    = expected_date()

    groups  = fetch_all(config['groups'], ref)
    message = build_message(groups, ref)

    if is_holiday(groups, ref):
        print(f'Holiday detected on {ref} (all data stale) — skip')
        return

    # Log — failure does NOT block calendar
    if os.environ.get('DISCORD_LOG_URL'):
        try:
            post_log(groups, ref)
            print('Log: OK')
        except Exception as e:
            print(f'Log: ERROR — {e}')

    # Calendar
    if os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE') and os.environ.get('GOOGLE_CALENDAR_ID'):
        try:
            result = post_calendar(message, ref)
            if result:
                print(f'Calendar: OK  id={result.get("id")}')
        except Exception as e:
            print(f'Calendar: ERROR — {e}')
    else:
        print('Calendar: skipped (GOOGLE_SERVICE_ACCOUNT_FILE / GOOGLE_CALENDAR_ID not set)')

    print(f'\nPosted: {ref}')


if __name__ == '__main__':
    main()
