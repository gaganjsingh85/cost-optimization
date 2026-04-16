# Azure + Microsoft 365 Cost Optimizer

An AI-powered FinOps dashboard that analyzes your Azure and Microsoft 365 spend, surfaces savings opportunities from Azure Advisor, identifies unused M365 licenses, and lets you chat with a Claude-powered assistant about your cloud costs.

![Version](https://img.shields.io/badge/version-1.2.0-blue) ![Python](https://img.shields.io/badge/python-3.11+-green) ![React](https://img.shields.io/badge/react-18-blue) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Table of Contents

- [What It Does](#what-it-does)
- [Pages](#pages)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Azure & M365 Setup](#azure--m365-setup)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Updating to a New Version](#updating-to-a-new-version)
- [Using the Dashboard](#using-the-dashboard)
- [Troubleshooting](#troubleshooting)
- [What's New in v1.2](#whats-new-in-v12)
- [Project Structure](#project-structure)
- [Security Notes](#security-notes)

---

## What It Does

- **Live cost analysis** — pulls real cost data from Azure Cost Management API, grouped by service, resource group, and location over 7/30/90 day windows.
- **Azure Advisor integration** — surfaces cost, security, performance, availability, and operational excellence recommendations with their potential annual savings.
- **VM right-sizing** — identifies oversized VMs and estimates monthly savings from downsizing.
- **M365 license optimization** — shows per-SKU license utilization, unused seats, inactive users (30-day activity), and monthly savings opportunities.
- **AI analysis** — Claude generates executive summaries, prioritized action plans, and quick wins from your data.
- **Chat assistant** — floating bottom-right agent with Claude tool use; ask questions like *"What's my top Azure cost service?"* or *"How many unused E5 licenses do I have?"* and Claude fetches the live data to answer.

---

## Pages

| Page | What It Shows |
|------|---------------|
| **Dashboard** | KPI cards (Azure spend, potential savings, M365 spend/savings), top recommendations, service cost chart, license overview |
| **Azure Advisor** | All Advisor recommendations with category/impact/search filters |
| **Cost Analysis** | Daily trend chart, cost by service, cost by resource group, detailed breakdown table |
| **M365 Licensing** | Per-SKU utilization table, spend distribution pie chart, optimization recommendations |
| **AI Analysis** | Run Claude analysis on Azure, M365, or both — returns executive summary + action plan |
| **Settings** | Configure Azure / M365 / Anthropic credentials |

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  React Frontend     │◄───────►│  FastAPI Backend     │
│  (port 3000)        │  HTTP   │  (port 8000)         │
└─────────────────────┘         └──────────┬───────────┘
                                           │
                     ┌─────────────────────┼─────────────────────┐
                     ▼                     ▼                     ▼
         ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐
         │  Azure APIs       │  │  MS Graph API     │  │  Anthropic API   │
         │  • Cost Mgmt      │  │  • Subscribed     │  │  • Claude        │
         │  • Advisor        │  │    SKUs           │  │    Sonnet 4.6    │
         │  • Compute        │  │  • Usage Reports  │  │                  │
         │  • Subscription   │  │                   │  │                  │
         └───────────────────┘  └───────────────────┘  └──────────────────┘
```

**Performance layer (v1.2):** Every expensive call is cached with per-key TTL + in-flight request dedup on both backend (server-side cache, 60s–10min TTLs) and frontend (30s response cache + concurrent request dedup). This prevents the Azure Cost Management 429 throttling that occurs when ~4 calls/minute are exceeded.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and **npm**
- An **Azure subscription** where you can create an App Registration
- A **Microsoft 365 tenant** with Global Admin access (to grant Graph API consent)
- An **Anthropic API key** (optional — enables AI Analysis and Chat Agent)

---

## Azure & M365 Setup

You need **two App Registrations** (or one registration with both Azure and Graph permissions). The instructions below assume two for clarity.

### Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **New registration**
2. Name it something like `cost-optimizer-azure` → **Register**
3. On the Overview page, copy:
   - **Application (client) ID** → this is your *Client ID* (NOT the Object ID)
   - **Directory (tenant) ID** → this is your *Tenant ID*
4. Go to **Certificates & secrets** → **New client secret** → pick an expiry → **Add**
5. **Copy the Value column immediately** (not the Secret ID). It's only shown once.
6. Go to your target **Subscription** → **Access control (IAM)** → **Add role assignment**:
   - Add role: **Reader**
   - Add role: **Cost Management Reader**
   - Assign both to your service principal (search for the app name you just created)

### Microsoft 365 App Registration

1. In the same tenant: **Microsoft Entra ID** → **App registrations** → **New registration**
2. Name it `cost-optimizer-m365` → **Register**
3. Copy the **Application (client) ID** and **Directory (tenant) ID**
4. **Certificates & secrets** → **New client secret** → copy the Value
5. **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**:
   - `Organization.Read.All`
   - `LicenseAssignment.ReadWrite.All`
   - `User.Read.All`
   - `Reports.Read.All`
6. Click **Grant admin consent for [tenant]** (requires Global Admin)

> **Tip:** You can use a single app registration for both Azure and M365 by combining the roles and Graph permissions above.

### Anthropic API Key (Optional)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. **Settings** → **API Keys** → **Create Key**
3. Copy the key (`sk-ant-...`) — you'll paste it into Settings later

---

## Installation

### 1. Clone or unzip the project

```bash
# If from zip
unzip azure-cost-optimizer-v1.2.zip
cd azure-cost-optimizer

# Or git clone
git clone <your-repo-url>
cd azure-cost-optimizer
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend setup

In a **second terminal**:

```bash
cd frontend
npm install
```

---

## Configuration

You have two options for providing credentials. Pick one.

### Option A: Use the Settings UI (recommended)

1. Start the app (see next section)
2. Open http://localhost:3000 → **Settings**
3. Fill in the Azure, M365, and Anthropic fields → click **Save**
4. Credentials are stored in `backend/config.json`

### Option B: Environment variables (.env file)

Create `backend/.env` with:

```env
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-secret-value
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

M365_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_SECRET=your-m365-secret-value

ANTHROPIC_API_KEY=sk-ant-api...
```

Values in `config.json` take precedence over `.env`.

---

## Running the App

> **Important for Windows users:** If you're running on Windows and your backend restarts in an infinite loop with messages like *"WatchFiles detected changes in venv\\Lib\\site-packages\\..."*, it's because uvicorn's file watcher is picking up changes in your virtual environment folder. Use the hardened startup command below (no-reload mode is most reliable).

### Terminal 1 — Backend

```bash
cd backend
venv\Scripts\activate   # or source venv/bin/activate

# Recommended — disables reload entirely (most reliable on Windows)
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# OR — reload enabled but with venv excluded
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "venv/*" --reload-exclude ".venv/*"
```

Backend runs at http://localhost:8000 — API docs at http://localhost:8000/docs

### Terminal 2 — Frontend

```bash
cd frontend
npm start
```

Frontend runs at http://localhost:3000.

On first launch:
1. A yellow banner appears prompting you to configure credentials
2. Click **Settings** → fill in the forms → **Save**
3. Navigate to the **Dashboard** — you should see live data within a few seconds

---

## Updating to a New Version

When you receive a new version (e.g. a patched zip or a specific set of fix files):

### Full version update

```bash
# 1. Stop both the backend and frontend (Ctrl+C in each terminal)

# 2. Back up your config
cp backend/config.json backend/config.json.bak

# 3. Replace files
#    - If you got a zip: unzip it over the existing project folder
#    - If you got individual files: copy each one to its corresponding path

# 4. Your config.json is preserved (not included in the zip by design)

# 5. Reinstall dependencies (only needed if requirements.txt or package.json changed)
cd backend
venv\Scripts\activate
pip install -r requirements.txt --upgrade

cd ../frontend
npm install

# 6. Restart both services (see "Running the App" above)
# 7. Hard-refresh the browser (Ctrl+Shift+R / Cmd+Shift+R)
```

### Partial update (single-file fix)

If you only got a handful of files to replace (e.g. targeted bug fix):

```bash
# 1. Stop both services (Ctrl+C in each terminal)

# 2. Copy each new file to its exact path, overwriting existing
#    Example paths for the v1.2 rate-limit fix:
#      backend/services/cache.py           (NEW file)
#      backend/services/azure_service.py
#      backend/services/m365_service.py
#      backend/routers/config_router.py
#      frontend/src/api/client.js
#      frontend/src/index.js

# 3. If requirements.txt was updated, run:
cd backend && pip install -r requirements.txt

# 4. If package.json was updated, run:
cd frontend && npm install

# 5. Restart backend and frontend

# 6. HARD-REFRESH the browser (Ctrl+Shift+R / Cmd+Shift+R)
#    Without this, the browser uses the old JS and nothing changes.
```

---

## Using the Dashboard

### First-time flow

1. **Settings** → enter Azure, M365, and Anthropic credentials
2. **Dashboard** — KPIs populate automatically
3. **Azure Advisor** — review recommendations, filter by Cost/High Impact for quick wins
4. **Cost Analysis** — drill into daily trend and per-service breakdown
5. **M365 Licensing** — find unused seats
6. **AI Analysis** — click **Full Combined Analysis** for Claude-generated executive summary + action plan
7. **Chat with Me** (bottom-right floating button) — ask natural-language questions

### Chat assistant examples

- *"What's my top Azure cost service this month?"*
- *"Show me high-impact Advisor recommendations I can fix this week"*
- *"How many unused Microsoft 365 E5 licenses do I have?"*
- *"What VMs can I right-size?"*
- *"Give me my combined potential monthly savings across Azure and M365"*

### Refresh behavior

Each page has a refresh button (circular arrow icon). Clicking it bypasses both the frontend cache (30s) and backend cache (60s–10min) and fetches fresh data. Otherwise, data auto-refreshes at cache expiry. This design is intentional — Azure Cost Management limits queries to ~4 calls/minute per subscription, so aggressive polling will trigger 429s.

---

## Troubleshooting

### Backend won't start / infinite reload loop on Windows

**Symptom:** Console spams *"WatchFiles detected changes in venv\\Lib\\site-packages\\..."* and `KeyboardInterrupt` tracebacks.

**Cause:** Something (OneDrive, antivirus, pip, an editor's file indexer) is touching files inside your `venv/` folder. Uvicorn's `--reload` picks those up and restarts endlessly.

**Fix:** Use one of:

```bash
# Option 1 — no reload (most reliable for Windows)
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Option 2 — reload with venv excluded
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "venv/*" --reload-exclude ".venv/*"

# Option 3 — move project out of OneDrive / Dropbox-synced folders
# OneDrive especially causes this. Use C:\projects\cost-optimizer instead.
```

### Dashboard shows em-dashes (—) in KPI cards

Usually means a backend call failed. Check:
1. The **banner above the KPIs** — it'll say exactly why (auth error, rate limited, no config, etc.)
2. The backend terminal output for the actual error
3. The **Data Status Banner** shows tailored fix hints for common error classes

### 429 Too Many Requests from Cost Management

Azure Cost Management allows ~4 calls/minute per subscription. v1.2 caches aggressively to stay under this limit. If you still hit it:

- The banner will show automatically and clear in ~60 seconds
- Don't mash the refresh button — wait for the retry-after window
- If persistent, another tool in your tenant may also be querying Cost Management — identify it via the `x-ms-ratelimit-*` headers

### "AADSTS700016: Application with identifier X was not found in directory Y"

Your Client ID and Tenant ID don't match. The app registration lives in a different tenant than the one you're authenticating against.

**Fix:** Go to your app registration's **Overview** page in Azure Portal. Copy **Application (client) ID** and **Directory (tenant) ID** *from that same app's Overview* and paste both into Settings.

### "AADSTS7000215: Invalid client secret provided"

The secret is wrong, expired, or you pasted the Secret ID instead of the Value.

**Fix:** Create a new secret in **Certificates & secrets**. Copy the **Value** column (not Secret ID) immediately — it's only shown once.

### "AuthorizationFailed: The client does not have authorization to perform action"

Your service principal is missing a role on the subscription.

**Fix:** Azure Portal → **Subscriptions** → your sub → **Access control (IAM)** → **Add role assignment** → add both **Reader** and **Cost Management Reader** to your service principal.

### Chat agent: "Client.__init__() got an unexpected keyword argument 'proxies'"

Older `anthropic` SDK is incompatible with newer `httpx` (≥0.28).

**Fix:**
```bash
cd backend
venv\Scripts\activate
pip install --upgrade anthropic
```

v1.2 requires `anthropic>=0.40.0`.

### "No module named 'six'"

Transitive dependency from `azure-mgmt-advisor` not auto-installed.

**Fix:**
```bash
pip install six
# or
pip install -r requirements.txt
```

### Frontend shows stale data after saving new credentials

All caches auto-invalidate on config save — but the browser may hold a cached page. **Hard-refresh** with Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (macOS).

### M365 licenses show "Unknown" names or $0 costs

The SKU isn't in the friendly-name/cost lookup table in `backend/services/m365_service.py`. Add it to the `SKU_FRIENDLY_NAMES` and `SKU_UNIT_COST` dicts.

---

## What's New in v1.2

### Performance fixes
- **Backend TTL cache** on every expensive call (cost 60s, Advisor 5min, M365 5min, subscription 10min, MSAL token ~55min)
- **Frontend in-flight request dedup** + 30s response cache — StrictMode double-fires now collapse to single requests
- **React.StrictMode removed** as belt-and-suspenders with the dedup
- **Cost Management 429 mitigation** — `x-ms-command-name: CostAnalysis` header added (per Microsoft Q&A guidance), single bounded retry honoring `x-ms-ratelimit-*-retry-after` headers
- **Consolidated cost queries** — 6 API calls reduced to 4 per refresh

### Correctness fixes
- Frontend field-name mismatches fixed (KPIs now read `friendly_name`, `enabled_units`, `consumed_units`, `unit_cost_estimate`)
- `'Subscription' object has no attribute 'tenant_id'` handled with `getattr` for SDK version variance
- Silent sample-data masking removed — every endpoint returns a `data_status` field
- New `DataStatusBanner` surfaces real errors with tailored fix hints

### New features
- Floating **Chat Agent** (Claude tool use) bottom-right
- **Subscription info header bar** with copy-to-clipboard on ID
- Cost-optimization themed **favicon**

---

## Project Structure

```
azure-cost-optimizer/
├── README.md                           ← this file
├── backend/
│   ├── main.py                         ← FastAPI entrypoint
│   ├── config.py                       ← config.json + .env loader
│   ├── requirements.txt
│   ├── config.json                     ← (created at runtime; gitignored)
│   ├── services/
│   │   ├── cache.py                    ← TTL cache + in-flight dedup
│   │   ├── azure_service.py            ← Azure Cost/Advisor/Compute/Subscription
│   │   ├── m365_service.py             ← MS Graph for licenses + usage
│   │   ├── claude_service.py           ← Claude analysis functions
│   │   └── chat_service.py             ← Claude chat agent w/ tool use
│   └── routers/
│       ├── config_router.py
│       ├── advisor_router.py
│       ├── costs_router.py
│       ├── m365_router.py
│       ├── subscription_router.py
│       ├── analyze_router.py
│       └── chat_router.py
└── frontend/
    ├── package.json
    ├── public/
    │   ├── index.html
    │   └── favicon.svg
    └── src/
        ├── index.js                    ← StrictMode removed
        ├── App.jsx
        ├── index.css
        ├── api/
        │   └── client.js               ← in-flight dedup + 30s cache
        ├── components/
        │   ├── Layout.jsx
        │   ├── Sidebar.jsx
        │   ├── SubscriptionBar.jsx
        │   ├── ChatAgent.jsx
        │   ├── DataStatusBanner.jsx
        │   ├── SavingsCard.jsx
        │   ├── RecommendationCard.jsx
        │   └── LoadingSpinner.jsx
        └── pages/
            ├── Dashboard.jsx
            ├── AzureAdvisor.jsx
            ├── CostAnalysis.jsx
            ├── M365Licensing.jsx
            ├── AIAnalysis.jsx
            └── Settings.jsx
```

---

## Security Notes

- **`backend/config.json` contains plaintext credentials.** It's excluded from the zip, but if you commit this repo to source control, add `config.json` and `.env` to `.gitignore`:

  ```gitignore
  backend/config.json
  backend/.env
  ```

- **Client secrets** granted to this app have broad read access to your Azure subscription and M365 tenant. Treat them like passwords. Rotate regularly. Set an expiry when creating them.

- **Frontend only talks to localhost:8000** by default. CORS is configured to allow `http://localhost:3000` only. If you deploy this, update the CORS config in `backend/main.py` and put the backend behind authentication.

- **Anthropic API key** is sent only to `api.anthropic.com`. Your Azure/M365 data passed to Claude for analysis leaves your network and is processed by Anthropic per their [terms of service](https://www.anthropic.com/legal/consumer-terms).

- This dashboard is for **internal use**. Don't expose it publicly without adding authentication, TLS, and a hardened secrets store (Azure Key Vault, AWS Secrets Manager, etc.).

---

## License

MIT — use it, fork it, modify it freely.

---

## Questions / Issues

This is an internal tool without a public issue tracker. If you're working from a distributed build:
- Check the **Troubleshooting** section above
- Check the browser DevTools Network tab for failed API calls
- Check the backend terminal for stack traces
- The `DataStatusBanner` on each page tells you exactly what went wrong