# 02: Gemini Agent Triage Pipeline & SSE Execution Trace Streaming

Status: resolved

## Scope
- Implement the 5-step Gemini Triage Pipeline using `google-genai` (`gemini-4-hydrogen`):
  1. `classify_inquiry`: Intent category, Priority Tier (`P0`–`P3`), confidence, and rationale.
  2. `extract_entities`: Sender details, organization, monetary amount, currency, deadline, reference IDs, and key summary.
  3. `search_drive_sops`: Search Google Drive folder `1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU` (or Sandbox SOP store) and extract matching policy clauses.
  4. `log_sheet_row`: Append/update structured tracking row in Google Sheet `1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek` (or Sandbox Sheet store).
  5. `draft_grounded_reply`: Generate a policy-grounded email response citing the matched SOP.
- Stream each step in real time over Server-Sent Events (`/api/inquiries/{id}/triage/stream`) for the center-panel Agent Execution Trace.
