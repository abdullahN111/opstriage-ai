# OpsTriage AI — Domain Glossary

Core domain terms used across the OpsTriage AI codebase, API contracts, and agent pipeline.

| Term | Definition | Avoid Synonyms |
| :--- | :--- | :--- |
| **Inbound Inquiry** | An incoming email message (from Gmail API in Live Mode or pre-loaded seed data in Recruiter Sandbox Mode) awaiting or undergoing triage. | Ticket, Message, Thread |
| **Triage Pipeline** | The 5-step autonomous Gemini agent workflow executed on an Inbound Inquiry: (1) Classify Intent & Priority, (2) Extract Entities, (3) Search Drive SOPs, (4) Log Tracking Row to Sheets, and (5) Draft Policy-Grounded Response. | Workflow, Job |
| **Intent Category** | The operational classification assigned to an Inbound Inquiry: `Billing & Refund`, `Vendor Invoice`, `SLA Escalation`, `Compliance & Security`, `HR & Onboarding`, or `General Operations`. | Tag, Label, Topic |
| **Priority Tier** | Urgency level assigned during triage: `P0 - Critical`, `P1 - High`, `P2 - Medium`, or `P3 - Low`. | Severity, Importance |
| **Extracted Entities** | Structured fields parsed from an Inbound Inquiry: `sender_name`, `sender_email`, `organization`, `monetary_amount`, `currency`, `deadline_iso`, `reference_ids`, and `key_summary`. | Metadata, Attributes |
| **SOP Document** | Standard Operating Procedure or policy document stored in the configured Google Drive folder (`1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU`) or Sandbox SOP store used to ground agent replies. | Knowledge Base Article, Wiki |
| **Agent Execution Trace** | Ordered sequence of step-by-step tool invocations (`classify_inquiry`, `extract_entities`, `search_drive_sops`, `log_sheet_row`, `draft_grounded_reply`) with timestamps, latency, inputs, and outputs streamed to the UI center panel. | Audit Log, Console Output |
| **Tracking Row** | A structured record appended to and updated in the OpsTriage Tracking Google Sheet (`1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek`) or Sandbox Sheet table. | Log Entry, Database Row |
| **Approval Drawer** | The Human-in-the-Loop (HITL) right-hand panel where an operator can edit the drafted reply, regenerate it with custom instructions, or click **Approve & Send** to dispatch the email and mark the Tracking Row `Resolved`. | Composer, Reply Box |
| **Workspace Mode** | The top-bar runtime toggle switching between `sandbox` (1-Click Recruiter Sandbox Mode with realistic inquiries, SOPs, and live in-app Sheet view) and `live` (Live Google OAuth Mode using real Gmail, Drive, and Sheets APIs). | Environment, Demo Mode |
