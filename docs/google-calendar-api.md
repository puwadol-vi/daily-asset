# Google Calendar — Create Events

Two ways to create events on Google Calendar.

|                  | Option A — Python + cron          | Option B — Claude MCP          |
| ---------------- | --------------------------------- | ------------------------------ |
| Setup            | Google Cloud project + OAuth once | OAuth once (Claude handles it) |
| Daily automation | ✅ runs without Claude            | ❌ needs Claude each time      |
| One-off tasks    | ❌ manual script run              | ✅ just prompt Claude          |
| Best for         | Daily auto-log (post tracker)     | Manual / on-demand events      |

---

## Option A — Python + cron (OAuth 2.0 + Google Cloud Project)

### Step 1 — Create Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. **New Project** → name it (e.g. `pixel-chart-diary`) → **Create**

### Step 2 — Enable Google Calendar API

1. **APIs & Services** → **Library**
2. Search **"Google Calendar API"** → **Enable**

### Step 3 — Create OAuth 2.0 Credentials

1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
2. Application type: **Desktop app**
3. **Create** → **Download JSON**
4. Save as `credentials.json` in project root

### Step 4 — Add to .env

```
GOOGLE_CALENDAR_ID=primary
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
```

Add to `.gitignore`:

```
credentials.json
token.json
```

### Step 5 — Install dependencies

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dotenv
```

### Step 6 — OAuth first run (one time only)

Run this once — browser opens → log in → approve → `token.json` saved automatically:

```bash
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/calendar'])
creds = flow.run_local_server(port=0)
open('token.json','w').write(creds.to_json())
print('Done — token.json saved')
"
```

### Step 7 — create_calendar_event.py

```python
import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv(Path(__file__).parent.parent / '.env')

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_service():
    token_file = os.environ['GOOGLE_TOKEN_FILE']
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        open(token_file, 'w').write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def create_event(title: str, date: str, description: str = '') -> str:
    service = get_service()
    event = {
        'summary': title,
        'description': description,
        'start': {'date': date},
        'end':   {'date': date},
    }
    result = service.events().insert(
        calendarId=os.environ['GOOGLE_CALENDAR_ID'],
        body=event
    ).execute()
    return result.get('htmlLink')


if __name__ == '__main__':
    from datetime import date
    link = create_event(
        title='📊 BTC Chart Posted',
        date=date.today().isoformat(),
        description='Daily BTC pixel chart posted to Discord and Facebook.'
    )
    print(f'Created: {link}')
```

### Step 8 — Add to cron

Run at 07:05 every day (after the post scripts finish):

```bash
crontab -e
```

```
5 0 * * * cd /path/to/daily-asset && python full_asset_status/create_calendar_event.py
```

> After the first `token.json` is saved, cron runs every day with no browser, no Claude.

---

## Option B — Claude MCP

No Google Cloud project needed. Claude handles the API directly.

**Setup (one time):**

1. Tell Claude: _"authenticate Google Calendar"_
2. Claude gives you a URL → open in browser → approve
3. Copy the callback URL from the address bar → paste back to Claude
4. Done — Claude can now create events anytime

**Daily use:**

```
You:   "create event: BTC posted today"
Claude: creates event on your Google Calendar instantly
```

**Example prompts:**

- "Create all-day event: BTC Status Posted, today"
- "Create task: review onchain metrics, Jun 20, 9am Bangkok time"
- "Add event every Monday: weekly asset review"

> Claude MCP requires Claude to be in the conversation each time — not suitable for fully automated daily cron jobs.
