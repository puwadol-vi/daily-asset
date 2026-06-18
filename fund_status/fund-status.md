# Fund NAV Status — Plan

Daily Thai mutual fund NAV + key market indicator tracker. Runs at **06:00 ICT**, posts to Discord and Google Calendar.

---

## 1. Overview

| Item        | Detail                                                           |
| ----------- | ---------------------------------------------------------------- |
| Schedule    | 06:00 ICT daily (`0 23 * * *` UTC = 06:00 next day ICT)          |
| Data: funds | SEC Thailand API — `api.sec.or.th`                               |
| Data: mkt   | Yahoo Finance — Gold, Oil, Corn, Soybean, DXY, World index, Baht |
| Data: bonds | Manual / FRED API — ML bonds, yield curve                        |
| Output 1    | Discord `DISCORD_WEBHOOK_URL` — log                              |
| Output 2    | Google Calendar all-day event — display                          |

---

## 2. Groups

Grouped by issuer / data source, sorted A→Z within each group.

| #   | Group         | Source                 | Items (count)                               |
| --- | ------------- | ---------------------- | ------------------------------------------- |
| 1   | SCB           | SEC Thailand API       | 16 funds                                    |
| 2   | K             | SEC Thailand API       | 10 funds                                    |
| 3   | Bualuang      | SEC Thailand API       | BGOLD                                       |
| 4   | Gold          | Yahoo Finance          | Gold (GC=F)                                 |
| 5   | Commodities   | Yahoo Finance + manual | Oil WTI, Corn, Soybean, Bloomberg commodity |
| 6   | Indices       | Yahoo Finance          | World index (^ACWI)                         |
| 7   | FX            | Yahoo Finance          | Baht, Dollar index                          |
| 8   | Bonds & Rates | Manual / FRED          | ML bonds, Intraday yield curve              |

---

## 3. Display Format

```
SCBGOLDE     🟢 +0.12%  3434.67
K-OIL        🔴 -4.10%  3554.55
Gold         🟢 +0.50%  3234.50
Baht         🔴 -0.20%    33.45
```

Rules:

- Display name left-padded to 14 chars
- `🟢` positive · `🔴` negative · `⚪` zero or N/A
- `+X.XX%` / `-X.XX%` / `N/A` — right-aligned 8 chars
- NAV / price appended after two spaces
- If the item's data date ≠ the header date → append `#Mon DD` (e.g. `#Jun 14`) to flag stale data
- Groups separated by blank line + `[Group Name]` header

---

## 4. Output

### Discord message

```
📊 Fund NAV — Jun 16, 2026

[Gold]
BGOLD          🟢 +0.30%  15.23
Gold           🟢 +0.50%  3234.50
KGDRMF         ⚪   N/A
SCBGOLDE       🟢 +0.12%  3434.67
SCBGOLDHE      🟢 +0.27%  2891.40 #Jun 14

[Energy]
K-OIL          🔴 -4.10%  3554.55
Oil WTI        🔴 -1.20%    73.40
SCBENERGYE     🔴 -0.02%  12345.67
...
```

### Google Calendar event

- **Title:** `📊 Fund NAV — Jun 16`
- **Type:** all-day event
- **Description:** same text as Discord message

---

## 5. Data Sources

| Source           | Groups                         | How                                                                             |
| ---------------- | ------------------------------ | ------------------------------------------------------------------------------- |
| SEC Thailand API | SCB, K, Bualuang               | `GET api.sec.or.th/FundFactsheet/fund/v1/info/nav/latest?proj_abbr_name=<code>` |
| Yahoo Finance    | Gold, Commodities, Indices, FX | `yfinance` · `ticker` field in JSON                                             |
| Manual / FRED    | Bonds & Rates                  | No fetch — display `⚪ N/A` as placeholder                                      |

SEC response fields used: `nav`, `nav_date`, `nav_chg_pct`

> If a fund returns no data (holiday / not yet published) → show `⚪ N/A`.

---

## 6. funds.json Structure

Top-level: `groups[]` — each group has `name`, `source` (`sec` / `yahoo` / `manual`), and `items[]`.

Per item:
| Field | Present when | Meaning |
|-------|-------------|---------|
| `display` | always | Label shown in output |
| `code` | `source: sec` | SEC `proj_abbr_name` (parentheses stripped) |
| `ticker` | `source: yahoo` | Yahoo Finance symbol |
| `source: "manual"` | item-level override | Skip fetch, show `⚪ N/A` |

---

## 7. File Structure

```
fund_status/
  fund-status.md       ← this file
  funds.json           ← all items, grouped by market
  fetch_funds.py       ← fetch NAV (SEC) + market data (yfinance)
  run_fund_status.py   ← main: fetch → format → Discord + Calendar
```

---

## 8. Environment Variables

Add to `.env`:

```
GOOGLE_CALENDAR_ID=primary
GOOGLE_TOKEN_FILE=token.json
GOOGLE_CREDENTIALS_FILE=credentials.json
```

> `DISCORD_WEBHOOK_URL` already in `.env`.

---

## 9. Cron Entry

```bash
# 06:00 ICT = 23:00 UTC (previous day)
0 23 * * * cd /home/ubuntu/daily-asset && /home/ubuntu/daily-asset/venv/bin/python3 fund_status/run_fund_status.py >> /home/ubuntu/daily-asset/cron.log 2>&1
```

---

## 10. Dependencies

```
requests
yfinance
python-dotenv
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```
