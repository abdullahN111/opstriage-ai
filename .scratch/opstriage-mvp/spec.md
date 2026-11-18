# OpsTriage AI — Feature Specification & Architecture Plan

## 1. Overview

**OpsTriage AI** is an end-to-end operations command center powered by the **Gemini API** (`google-genai` SDK with `gemini-4-hydrogen`) and **Google Workspace APIs** (**Gmail**, **Google Drive**, and **Google Sheets**).

When an **Inbound Inquiry** arrives, the **Triage Pipeline** autonomously:
1. **Classifies Intent & Priority** (`P0 - Critical` to `P3 - Low`, plus Intent Category & confidence).
2. **Extracts Key Entities** (sender details, organization, monetary amounts, deadlines, invoice/order IDs).
3. **Searches Google Drive SOPs** (`1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU`) for matching policy documents and citations.
4. **Logs a Tracking Row** into the **OpsTriage Tracking Google Sheet** (`1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek`) with status `Pending Approval`.
5. **Drafts a Policy-Grounded Response** citing the matched SOP clauses.

## 2. Three-Panel Web Command Center

- **Top Navigation Bar**:
  - Brand header & live connection status badge.
  - **Workspace Mode Toggle**: Instant switch between **1-Click Recruiter Sandbox Mode** (zero-login, pre-loaded with 6 realistic operational emails + custom email simulator + interactive live Sheet drawer) and **Live Google OAuth Mode** (connected to real Gmail, Drive folder `1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU`, and Sheet `1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek`).
  - **60-Second Demo Walkthrough Player**: Interactive guided demo & screen-recording showcase demonstrating an incoming email turning into a logged spreadsheet row and sent reply.
  - **Live KPI Counters**: Total Inquiries, P0/P1 Urgent Count, Avg Triage Latency, Sheet Rows Logged, and Resolved Count.
- **Left Panel — Categorized Inbox Queue**:
  - Filterable by Priority (`All`, `P0`, `P1`, `P2`, `P3`), Status (`Untriaged`, `Triaged / Needs Approval`, `Resolved`), and category search.
  - "+ Simulate / Fetch New Email" button and "Run AI Triage on All" batch button.
- **Center Panel — Real-Time Agent Execution Trace & Entity Inspector**:
  - Live step-by-step tool call timeline streamed via Server-Sent Events (SSE) with status spinners, latency badges (`ms`), expandable JSON arguments/results, and matched SOP policy excerpts.
  - Extracted Entity cards (Sender, Organization, Monetary Amount, Deadline, Reference IDs) + Live Google Sheet Row preview tab.
- **Right Panel — Human-in-the-Loop (HITL) Approval Drawer**:
  - Editable policy-grounded email draft with SOP citation pills.
  - Tone/Instruction Regenerate bar (e.g., *"Make firmer on SLA terms"*, *"Approve partial credit"*).
  - **1-Click "Approve, Send & Resolve"** button that sends the reply (via Gmail API in Live Mode or Sandbox Outbox) and updates the Google Sheet row status to `Resolved` with timestamp.

## 3. Technical Stack

- **Backend (`backend/`)**:
  - Python 3.14 + **FastAPI** + `uvicorn`
  - **Gemini API**: `google-genai` SDK using `gemini-4-hydrogen` via `client.interactions.create` (with automatic fallback to `client.models.generate_content` if needed by environment/SDK version).
  - **Google Workspace APIs**: `google-api-python-client`, `google-auth`, `google-auth-oauthlib` for OAuth 2.0 Web flow (`Gmail`, `Drive v3`, `Sheets v4`).
  - **Dual-Mode Workspace Adapter**: Seamless abstraction supporting both `sandbox` mode and `live` Google OAuth mode.
- **Frontend (`frontend/`)**:
  - **Next.js (App Router, TypeScript)** + **Tailwind CSS** + **Lucide React** icons.
