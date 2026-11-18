# OpsTriage AI — Autonomous Google Workspace Operations Hub

**OpsTriage AI** is an end-to-end operations command center powered by the **Gemini API** (`google-genai` SDK with `gemini-4-hydrogen`) and **Google Workspace APIs** (**Gmail**, **Google Drive**, and **Google Sheets**).

When an incoming operational email arrives, the AI agent autonomously:
1. **Classifies Intent & Priority Tier** (`P0 - Critical` to `P3 - Low` across `Billing & Refund`, `SLA Escalation`, `Vendor Invoice`, `Compliance & Security`, `HR & Onboarding`, and `General Operations`).
2. **Extracts Structured Entities** (sender details, organization, monetary amounts, ISO deadlines, invoice/PO/incident reference IDs).
3. **Searches Google Drive SOPs** ([SOP/policy documents folder](https://drive.google.com/drive/u/0/folders/1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU)) for matching policy clauses.
4. **Logs a Structured Tracking Row** into the [OpsTriage tracking Google Sheet](https://docs.google.com/spreadsheets/d/1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek/edit?gid=0#gid=0).
5. **Drafts a Policy-Grounded Response** ready for 1-click Human-in-the-Loop approval, Gmail dispatch, and Sheet resolution.

---

## Architecture & Three-Panel Command Center

- **Top Bar**:
  - **Live Google OAuth Mode vs. 1-Click Recruiter Sandbox Mode** toggle.
  - Live KPI counters (Total Queue, P0/P1 Urgent Escalations, Avg Gemini Triage Speed, Sheet Rows Logged, Resolved Count).
  - Direct links to the configured Google Drive SOP folder and OpsTriage Tracking Sheet, plus a **60-Second Guided Demo Walkthrough**.
- **Left Panel — Categorized Inbox Queue**:
  - Status & keyword filters, Priority badges, Intent pills, and `+ Simulate Email` injector.
- **Center Panel — Real-Time Agent Execution Trace**:
  - Streams each tool call step-by-step via Server-Sent Events (SSE) with latency metrics (`ms`), expandable JSON input/output payloads, extracted entity cards, and an embedded **Live Sheet Ledger** tab.
- **Right Panel — Human-in-the-Loop (HITL) Approval Drawer**:
  - Editable policy-grounded draft, Gemini reviewer-guidance regeneration, and 1-click **Approve, Send Email & Mark Sheet Row Resolved**.

---

## Quick Start

### 1. Start the FastAPI Backend (`http://localhost:8000`)

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Start the Next.js Frontend (`http://localhost:3000`)

```powershell
cd frontend
npm install
npm run dev
```

### 3. Google Cloud OAuth Note (for Live Mode)

Ensure that `http://localhost:8000/api/auth/google/callback` is listed under **Authorized redirect URIs** in your Google Cloud OAuth 2.0 Client (`900102146177-83k8rt3o2k6l0nrafkocpuevmk1neb5q.apps.googleusercontent.com`), and that **Gmail API**, **Google Drive API**, and **Google Sheets API** are enabled in your Google Cloud project.
"# opstriage-ai" 
