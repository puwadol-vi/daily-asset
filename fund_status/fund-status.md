# Fund NAV Status

Daily Thai mutual fund NAV + key market indicator tracker. Posts to Discord and Google Calendar.

---

## 1. Overview

| Item     | Detail |
|----------|--------|
| Schedule | Cron on server |
| Ref date | Most recent completed business day in ICT (yesterday, skipping weekends) |
| Output 1 | Discord `DISCORD_WEBHOOK_URL` — error summary only |
| Output 2 | Google Calendar all-day event on **ref date** — full NAV message |

---

## 2. Groups & Sources

| Group | Source | Items |
|-------|--------|-------|
| SCB | Finnomena API | 16 funds |
| K | Finnomena API | 10 funds |
| Bualuang | Finnomena API | BGOLD |
| Gold | Yahoo Finance | Gold (GC=F) |
| Commodities | Yahoo Finance | Corn, Oil WTI, Soybean |
| Indices | Yahoo Finance | World index (ACWI) |
| FX | Yahoo Finance | Baht (THBUSD=X), Dollar index (DX-Y.NYB) |

---

## 3. Data Sources

| Source | Used for | How |
|--------|----------|-----|
| Finnomena API (proxied via Cloudflare Worker) | SCB, K, Bualuang funds | `GET /fn3/api/fund/v2/public/funds/{id}/latest` — fields: `value` (NAV), `d_change` (chg%), `date` |
| Yahoo Finance (`yfinance`) | Gold, Commodities, Indices, FX, **master funds** | `Ticker.history(period='5d')` — computes chg% from last 2 closes. GBp currency auto-divided by 100. |

---

## 4. Stale Data & Master Fund Logic

When a fund's data date is older than ref date, it is **stale**.

If the item has a `"master"` ticker in `funds.json`:
- Fetch master via yfinance
- If master date > feeder date → use master's NAV/chg%, show master ticker label
- If master is also stale (but fresher than feeder) → use master, show both label and master's date tag
- If master is not fresher than feeder → ignore master, show feeder's own stale data

---

## 5. Display Format

```
[Group]
🟢   +0.94%  SCBAXJ(E)
🟢   +0.53%  SCBBLOC(E)  (BCHS.L)
🔴   -0.96%  SCBCLEAN(E)  (ICLN) #Jun 17
🔴   -0.78%  SCBPGF(E) #Jun 16
❌ SCBAXJ(E)  HTTPSConn...
```

Rules:
- `🟢` positive · `🔴` negative · `⚪` zero/N/A · `❌` fetch error
- Change % right-aligned to 8 chars, no NAV shown
- Stale feeder (no master): `#Mon D` tag appended
- Fresh master used: `  (TICKER)` appended, no date tag
- Stale master used: `  (TICKER) #Mon D` appended
- Error: shows first 10 chars of error message

### Calendar event
- **Title:** `*📊 Fund NAV — Jun 18`
- **Date:** ref date (not today)
- **Description:** full message text

### Discord message
- Error summary only: `📅 Fund Status — Jun 18, 2026 — N error(s)` + list of errored funds

---

## 6. funds.json Structure

```json
{
  "groups": [
    {
      "name": "SCB",
      "source": "sec",
      "items": [
        { "display": "SCBAXJ(E)", "code": "SCBAXJ(E)" },
        { "display": "SCBBLOC(E)", "code": "SCBBLOC(E)", "master": "BCHS.L" }
      ]
    },
    {
      "name": "Gold",
      "source": "yahoo",
      "items": [
        { "display": "Gold", "ticker": "GC=F" }
      ]
    }
  ]
}
```

| Field | When | Meaning |
|-------|------|---------|
| `display` | always | Label shown in output |
| `code` | `source: sec` | Finnomena `short_code` |
| `ticker` | `source: yahoo` | Yahoo Finance symbol |
| `master` | optional | Yahoo ticker for master/underlying fund; used when feeder is stale |

---

## 7. Environment Variables

```
DISCORD_WEBHOOK_URL=
GOOGLE_SERVICE_ACCOUNT_FILE=fund-calendar-xxxx.json
GOOGLE_CALENDAR_ID=
```

Google Calendar uses **service account** auth (not OAuth token).

---

## 8. File Structure

```
fund_status/
  fund-status.md         ← this file
  funds.json             ← groups + items config
  fetch_funds.py         ← Finnomena + yfinance fetch, master fund logic
  run_fund_status.py     ← format + Discord + Calendar output
  fund-calendar-*.json   ← Google service account key
```

---

## 9. Dependencies

```
requests
yfinance
pandas
python-dotenv
google-api-python-client
google-auth
```
