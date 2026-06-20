# PixelSheetDiary — Google Sheets as a Backend Platform

> **Tagline:** Turn any Google Sheet into a web app. No backend. No auth. Just paste your Sheet ID.

**URL Pattern:** `PixelSheetDiary for [Purpose]`

---

## 1. Core Goal

Build an ultra-lightweight web application that uses dynamically provided Google Sheets as a free, serverless backend. Key design constraint is **zero friction**:

- No database setup required
- No user authentication or registration
- No user-side developer configuration (no API keys)

---

## 2. URL Routing Structure

| URL                                | Purpose                                                 |
| ---------------------------------- | ------------------------------------------------------- |
| `xxxx.com/sheet/`                  | Landing page — product description and onboarding steps |
| `xxxx.com/sheet/<google-sheet-id>` | App workspace populated with data from that sheet ID    |

---

## 3. Feature Tiers

### Tier 1 — View Only (Read)

- **User action:** Set Google Sheet sharing to "Anyone with the link → Viewer"
- **App behavior:** Frontend reads via Google's public `gviz/tq` endpoint (no API key required). Re-fetches on interval to stay in sync with manual edits.

### Tier 2 — Editable (Write)

- **User action (2 steps):**
  1. "Anyone with the link" → Viewer (same as Tier 1)
  2. Share explicitly with `<DEPLOYER_GOOGLE_ACCOUNT>` → Editor
- **App behavior:** Shows a "+" button. On click, a dialog with an input form appears. On submit, frontend POSTs to the Master Apps Script Web App, which appends a new row to the user's sheet.
- **Why it works:** Apps Script runs as `<DEPLOYER_GOOGLE_ACCOUNT>` ("Execute as: Me") with "Anyone" access. It already has editor rights via the shared account — no user OAuth needed.

---

## 4. Tech Stack

| Layer    | Technology                                                             |
| -------- | ---------------------------------------------------------------------- |
| Frontend | Next.js (App Router) + React + Tailwind CSS                            |
| Hosting  | Vercel / Cloudflare Pages                                              |
| Read     | Google Sheets `gviz/tq` public JSON endpoint                           |
| Write    | Google Apps Script Web App (1 master script, write-proxy microservice) |

---

## 5. Google Apps Script Setup

- **Runs as:** `<DEPLOYER_GOOGLE_ACCOUNT>` (Me)
- **Access:** Anyone (no sign-in required)
- **Receives POST:** `{ sheetId, values: [...] }`
- **Action:** `SpreadsheetApp.openById(sheetId).getActiveSheet().appendRow(values)`
- **Config:** Deployed URL stored as `NEXT_PUBLIC_APPS_SCRIPT_URL` env var

---

## 6. Constraints & Security

- **Abuse protection:** `SpreadsheetApp.openById()` throws if `<DEPLOYER_GOOGLE_ACCOUNT>` is not an editor — bad actors with random sheet IDs fail automatically
- **Rate limits:** Google Apps Script daily quotas apply — acceptable for demo/small-scale use
- **gviz/tq parsing:** Response is wrapped in a callback prefix (e.g. `/*O_o*/\ngoogle.visualization.Query...`) that must be stripped before JSON parsing

---

## 7. Possible Purposes

| Category     | Verticals                                                                                      |
| ------------ | ---------------------------------------------------------------------------------------------- |
| **Finance**  | Income & Expense · Investment Portfolio · Net Worth · Subscription Tracker · Freelance Billing |
| **Health**   | Body Metrics · Workout Log · Sleep Tracker · Medication Log                                    |
| **Work**     | Timesheet · Project Milestones · Sales Pipeline · Client History                               |
| **Learning** | Habit Tracker · Book Log · Study Hours                                                         |
| **Life**     | Car Maintenance · Home Repairs · Travel Log                                                    |

Finance

- Income & Expense (budgeting)
- Investment portfolio log
- Net worth tracker
- Subscription tracker
- Freelance invoice / client billing

Health & Body

- Weight / body metrics log
- Workout log
- Sleep tracker
- Medication log
- Calorie / water intake

Work & Productivity

- Daily timesheet
- Project milestone log
- Sales pipeline / lead tracker
- Client contact history
- Standup / work journal

Learning & Habits

- Habit tracker
- Book / reading log
- Study hours log
- Language learning progress

Life & Home

- Car maintenance log
- Plant care log
- Home repair log
- Travel log / trip record
