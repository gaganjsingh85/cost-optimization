# Azure Cost Optimizer

An AI-powered agent that connects to your Azure environment and Microsoft 365 tenant to identify real cost savings opportunities. Uses Claude (claude-sonnet-4-6) to analyze Azure Advisor recommendations, actual spend data, and M365 license usage — then delivers a consolidated, prioritized action plan.

---

## What It Does

| Module | Data Source | Output |
|--------|------------|--------|
| Azure Advisor | Azure Advisor API | Recommendations across Cost, Security, HA, Performance |
| Cost Analysis | Azure Cost Management API | 30/60/90-day spend by service, resource group, location |
| M365 Licensing | Microsoft Graph API | License utilization, inactive users, over-provisioning |
| AI Analysis | Claude claude-sonnet-4-6 | Executive summary, ranked savings, 30/60/90-day plan |

> **Works without real credentials.** The app ships with rich sample data so you can explore the full UI before connecting to live Azure/M365.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

---

## Local Setup — Step by Step

### 1. Clone / extract the project

```
azure-cost-optimizer/
├── backend/
└── frontend/
```

### 2. Set up the Python backend

```bash
cd azure-cost-optimizer/backend

# Create a virtual environment
python -m venv venv

# Activate it
# macOS / Linux:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Create a .env file

Copy the example and fill in your credentials. The app also lets you enter credentials via the Settings UI.

```bash
cp .env.example .env
# Then edit .env with your actual values
```

### 4. Start the backend

```bash
# From the backend/ directory, with venv active:
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

Verify it works: open http://localhost:8000/api/health — should return `{"status":"ok"}`

Interactive API docs: http://localhost:8000/docs

---

### 5. Set up the React frontend

Open a **new terminal**:

```bash
cd azure-cost-optimizer/frontend

npm install
```

### 6. Start the frontend

```bash
npm start
```

Your browser will open automatically at **http://localhost:3000**

---

## Connecting to Azure & M365

### Option A — Settings UI (recommended)

1. Open http://localhost:3000
2. Click **Settings** in the left sidebar
3. Fill in your Azure Service Principal credentials
4. Fill in your M365 / Graph API credentials
5. Enter your Anthropic API Key
6. Click **Save Configuration**

### Option B — Environment variables (.env file)

Edit `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...

# Azure Service Principal
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-client-secret-value
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# M365 Graph API
M365_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_SECRET=your-m365-client-secret
```

Restart the backend after editing .env.

---

## Azure Service Principal Setup

You need an Azure Service Principal with read access to your subscription.

### Create the Service Principal

```bash
# Login to Azure CLI
az login

# Create a service principal with Reader role
az ad sp create-for-rbac \
  --name "azure-cost-optimizer" \
  --role "Reader" \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
  --sdk-auth
```

This outputs:
```json
{
  "clientId": "...",        <- AZURE_CLIENT_ID
  "clientSecret": "...",    <- AZURE_CLIENT_SECRET
  "tenantId": "...",        <- AZURE_TENANT_ID
  "subscriptionId": "..."   <- AZURE_SUBSCRIPTION_ID
}
```

### Required Azure Roles

| Role | Purpose |
|------|---------|
| Reader | Read subscription resources |
| Cost Management Reader | Access billing and cost data |

Add Cost Management Reader if needed:
```bash
az role assignment create \
  --assignee YOUR_CLIENT_ID \
  --role "Cost Management Reader" \
  --scope /subscriptions/YOUR_SUBSCRIPTION_ID
```

---

## M365 / Graph API Setup

### Register an App in Azure AD

1. Go to **Azure Portal → Azure Active Directory → App registrations → New registration**
2. Name: `m365-cost-optimizer`
3. Supported account types: Accounts in this organizational directory only
4. Click **Register**

### Add API Permissions (Application permissions — not delegated)

Go to **API permissions → Add a permission → Microsoft Graph → Application permissions**:

| Permission | Purpose |
|-----------|---------|
| `Reports.Read.All` | Usage reports (Teams, Exchange, SharePoint) |
| `Organization.Read.All` | License and subscription data |
| `Directory.Read.All` | User and license details |

Click **Grant admin consent** (requires Global Admin).

### Create a Client Secret

Go to **Certificates & secrets → New client secret**. Copy the value — it's only shown once.

Note your:
- **Application (client) ID** → M365_CLIENT_ID
- **Directory (tenant) ID** → M365_TENANT_ID
- **Client secret value** → M365_CLIENT_SECRET

---

## Getting an Anthropic API Key

1. Sign in at https://console.anthropic.com
2. Go to **API Keys → Create Key**
3. Copy the key (starts with `sk-ant-`)

The AI Analysis features require a valid key. All other pages (Azure Advisor, Cost Analysis, M365 Licensing) work without it.

---

## Running Without Real Credentials (Demo Mode)

The app automatically returns sample data when credentials are not configured or when API calls fail. You'll see a `sample_data: true` indicator in the raw API responses.

**Demo mode gives you:**
- 8 sample Azure Advisor recommendations (Cost, Security, HA, Performance)
- 30-day cost breakdown across sample services and resource groups
- Sample M365 license data with realistic utilization patterns
- AI analysis works if you provide an Anthropic API key (it will analyze the sample data)

---

## Application Pages

### Dashboard
High-level overview: total spend, savings potential, top recommendations, cost-by-service chart, M365 license summary table.

### Azure Advisor
Full list of Azure Advisor recommendations. Filter by category (Cost, Security, High Availability, Performance, Operational Excellence) and impact level (High, Medium, Low). Search by name.

### Cost Analysis
Period-selectable (7/30/90 days) cost charts: daily trend, breakdown by service, breakdown by resource group. Sortable data table with percentage breakdowns.

### M365 Licensing
License utilization progress bars (green >80%, yellow 50–80%, red <50% utilized). Spend distribution pie chart. Actionable recommendations to downgrade or reclaim unused licenses.

### AI Analysis
One-click analysis buttons that send all collected data to Claude. Returns:
- Executive summary with total savings opportunity
- Ranked savings opportunities with effort estimates
- M365 license-specific recommendations
- 30 / 60 / 90-day action plan

### Settings
Configure all credentials with masked display. Connection status cards show live green/red indicators. Test connection before saving.

---

## API Reference

With the backend running, visit http://localhost:8000/docs for the full interactive API reference.

Key endpoints:

```
GET  /api/health                    Health check
GET  /api/config                    Config status (masked)
POST /api/config                    Save credentials
GET  /api/advisor/recommendations   Azure Advisor recs (?category=Cost)
GET  /api/advisor/summary           Summary by category
GET  /api/costs/summary             Cost data (?days=30)
GET  /api/costs/breakdown           Detailed breakdown
GET  /api/m365/licenses             License utilization
GET  /api/m365/summary              Full M365 summary + recommendations
POST /api/analyze/azure             Claude analysis of Azure spend
POST /api/analyze/m365              Claude analysis of M365 licensing
POST /api/analyze/full              Combined full analysis
```

---

## Troubleshooting

### Backend won't start
```
ModuleNotFoundError: No module named 'fastapi'
```
Make sure your virtual environment is **activated** before running `pip install` and `python main.py`.

### CORS error in browser
Verify the backend is running on port 8000. The frontend is hardcoded to `http://localhost:8000`. Check the browser console for the exact error.

### Azure API returns 403
The Service Principal is missing the **Cost Management Reader** role. Add it via:
```bash
az role assignment create --assignee CLIENT_ID --role "Cost Management Reader" --scope /subscriptions/SUB_ID
```

### M365 Graph returns 403
Admin consent has not been granted for the app permissions. A Global Admin must click **Grant admin consent** in the Azure AD app registration.

### Claude analysis returns generic text
Check that `ANTHROPIC_API_KEY` is set and valid. Verify at http://localhost:8000/api/config — `has_anthropic` should be `true`.

### npm install fails
Make sure you're using Node.js 18+. Run `node --version` to check.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, React Router v6, Tailwind CSS, Recharts, Lucide React, Axios |
| Backend | Python, FastAPI, Uvicorn |
| AI | Anthropic Claude (claude-sonnet-4-6) |
| Azure | azure-identity, azure-mgmt-advisor, azure-mgmt-costmanagement, azure-mgmt-compute |
| M365 | MSAL, Microsoft Graph REST API |
