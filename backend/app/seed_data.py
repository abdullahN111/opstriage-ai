from typing import List, Dict, Any
from .models import InboundInquiry, SOPMatch, ExtractedEntities, TraceStep, TrackingRow
from .config import settings

DRIVE_FOLDER_URL = f"https://drive.google.com/drive/u/0/folders/{settings.GOOGLE_DRIVE_SOP_FOLDER_ID}"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SHEETS_TRACKER_ID}/edit#gid=0"


SEED_SOP_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "doc_id": "sop-billing-001",
        "title": "SOP-01: Enterprise Billing, Overcharge & Refund Policy (v4.2)",
        "category": "Billing & Refund",
        "drive_url": DRIVE_FOLDER_URL,
        "matched_section": "Section 3.2 — Duplicate Charge & Credit Memo SLA",
        "policy_excerpt": (
            "Duplicate ACH/Wire or card billings under $25,000 USD are eligible for immediate automated credit memo "
            "issuance and 48-hour refund settlement once the invoice ID and payment reference are verified. "
            "Refunds between $10,000 and $25,000 require Controller notification in the OpsTriage Sheet."
        ),
        "full_text": (
            "# SOP-01: Enterprise Billing, Overcharge & Refund Policy (v4.2)\n\n"
            "## Section 3.2 — Duplicate Charge & Credit Memo SLA\n"
            "- Duplicate billings under $25,000 USD qualify for expedited 48-hour reversal upon verification of Invoice ID.\n"
            "- Always provide a Credit Memo Reference (`CM-2026-XXXX`) in the customer response.\n"
            "- Confirm that no service interruption will occur during billing reconciliation."
        ),
    },
    {
        "doc_id": "sop-sla-002",
        "title": "SOP-02: P0 Production Outage & SLA Credit Escalation Playbook",
        "category": "SLA Escalation",
        "drive_url": DRIVE_FOLDER_URL,
        "matched_section": "Section 1.4 — Enterprise 99.99% Uptime SLA & Service Credit Tiers",
        "policy_excerpt": (
            "If an Enterprise Tier customer experiences >15 minutes of regional API degradation (HTTP 502/504), "
            "classify as P0 - Critical. Acknowledge within 15 minutes, provide the incident RCA timeline (24h), "
            "and pre-authorize a 10% monthly service credit under Master Services Agreement Clause 8.1."
        ),
        "full_text": (
            "# SOP-02: P0 Production Outage & SLA Credit Escalation Playbook\n\n"
            "## Section 1.4 — Enterprise 99.99% Uptime SLA & Service Credit Tiers\n"
            "- 15–45 mins downtime: 10% monthly service credit applied to next billing cycle.\n"
            "- Incident Commander must deliver Preliminary RCA within 24 hours of restoration."
        ),
    },
    {
        "doc_id": "sop-vendor-003",
        "title": "SOP-03: Accounts Payable & Net-30 Vendor Invoice Processing",
        "category": "Vendor Invoice",
        "drive_url": DRIVE_FOLDER_URL,
        "matched_section": "Section 2.1 — PO Matching & Net-30 Wire Disbursement Rules",
        "policy_excerpt": (
            "Vendor invoices referencing an approved Purchase Order (PO-XXXX) under $50,000 are queued for "
            "Friday ACH/Wire batch runs. If a vendor flags an overdue invoice <7 days past due, issue immediate "
            "same-day expedited ACH and send remittance confirmation."
        ),
        "full_text": (
            "# SOP-03: Accounts Payable & Net-30 Vendor Invoice Processing\n\n"
            "## Section 2.1 — PO Matching & Net-30 Wire Disbursement Rules\n"
            "- Verify 3-way match: Purchase Order ID, Invoice ID, and W-9 on file.\n"
            "- Overdue vendor balances with valid PO numbers are prioritized for next-business-day ACH release."
        ),
    },
    {
        "doc_id": "sop-sec-004",
        "title": "SOP-04: GDPR / SOC2 Data Processing Addendum & Security Review SOP",
        "category": "Compliance & Security",
        "drive_url": DRIVE_FOLDER_URL,
        "matched_section": "Section 4.1 — Standard SOC2 Type II Report & Signed DPA Distribution",
        "policy_excerpt": (
            "Enterprise customers requesting SOC2 Type II attestation, Penetration Test executive summaries, or "
            "countersigned GDPR Data Processing Addendums (DPA) under an active NDA receive package access within "
            "1 business day via the Trust Portal link."
        ),
        "full_text": (
            "# SOP-04: GDPR / SOC2 Data Processing Addendum & Security Review SOP\n\n"
            "## Section 4.1 — Standard SOC2 Type II Report & Signed DPA Distribution\n"
            "- Confirm active Mutual NDA or MSA before releasing SOC2 Type II bridge letters.\n"
            "- Standard GDPR Articles 28/32 DPA templates require zero custom legal redlines."
        ),
    },
    {
        "doc_id": "sop-hr-005",
        "title": "SOP-05: Contractor Access Provisioning & Hardware Stipend Policy",
        "category": "HR & Onboarding",
        "drive_url": DRIVE_FOLDER_URL,
        "matched_section": "Section 2.3 — Engineering Contractor SSO & Equipment Reimbursement",
        "policy_excerpt": (
            "Approved engineering contractors receive Okta SSO + GitHub org access 48 hours prior to start date "
            "and up to $1,800 USD hardware/security key reimbursement upon receipt submission."
        ),
        "full_text": (
            "# SOP-05: Contractor Access Provisioning & Hardware Stipend Policy\n\n"
            "## Section 2.3 — Engineering Contractor SSO & Equipment Reimbursement\n"
            "- Provision Okta SSO, Google Workspace, and GitHub least-privilege roles 48h before start.\n"
            "- Hardware stipend cap is $1,800 USD reimbursable on the first invoice cycle."
        ),
    },
]


def get_initial_sandbox_data() -> tuple[List[InboundInquiry], List[TrackingRow]]:
    inquiries: List[InboundInquiry] = [
        InboundInquiry(
            id="inq-1001",
            thread_id="thr-1001",
            subject="URGENT: Duplicate ACH Charge on Invoice #INV-2026-8841 ($14,500.00)",
            sender_name="Elena Rostova",
            sender_email="elena.rostova@vanguard-logistics.io",
            organization="Vanguard Global Logistics",
            received_at="2026-11-16T10:12:00Z",
            body=(
                "Hi Ops & Billing Team,\n\n"
                "Our treasury system flagged that Vanguard Global Logistics was debited twice via ACH this morning "
                "for our Q4 Enterprise Platform subscription on Invoice #INV-2026-8841.\n\n"
                "Each debit was $14,500.00 USD (total $29,000.00 pulled, reference #ACH-992014-B). "
                "We have our monthly close deadline on 2026-11-18 and need the duplicate $14,500.00 refunded "
                "along with a formal Credit Memo immediately.\n\n"
                "Best regards,\n"
                "Elena Rostova\n"
                "VP of Finance, Vanguard Global Logistics"
            ),
            status="Needs Approval",
            ai_summary=(
                "Elena Rostova from Vanguard Global Logistics is requesting an immediate reversal for a duplicate "
                "$14,500.00 ACH debit on Invoice #INV-2026-8841 before their November 18 financial close. "
                "Operations must issue Credit Memo #CM-2026-8841 and queue priority settlement per SOP-01 Section 3.2."
            ),
            intent_category="Billing & Refund",
            priority_tier="P1 - High",
            confidence_score=0.98,
            classification_rationale=(
                "Verified duplicate ACH billing of $14,500.00 USD with a hard financial close deadline of 2026-11-18."
            ),
            entities=ExtractedEntities(
                sender_name="Elena Rostova",
                sender_email="elena.rostova@vanguard-logistics.io",
                organization="Vanguard Global Logistics",
                monetary_amount=14500.00,
                currency="USD",
                deadline_iso="2026-11-18",
                reference_ids=["INV-2026-8841", "ACH-992014-B"],
                key_summary="Duplicate ACH debit of $14,500.00 USD on Invoice #INV-2026-8841; requires Credit Memo and refund before 2026-11-18 close.",
            ),
            matched_sops=[
                SOPMatch(
                    doc_id="sop-billing-001",
                    title="SOP-01: Enterprise Billing, Overcharge & Refund Policy (v4.2)",
                    drive_url=DRIVE_FOLDER_URL,
                    matched_section="Section 3.2 — Duplicate Charge & Credit Memo SLA",
                    policy_excerpt=SEED_SOP_DOCUMENTS[0]["policy_excerpt"],
                    relevance_score=0.97,
                )
            ],
            execution_trace=[
                TraceStep(
                    step_number=1,
                    tool_name="classify_inquiry",
                    title="Classify Intent & Priority Tier",
                    status="completed",
                    started_at="10:12:02.110",
                    duration_ms=420,
                    input_payload={"subject": "URGENT: Duplicate ACH Charge on Invoice #INV-2026-8841 ($14,500.00)"},
                    output_payload={
                        "intent_category": "Billing & Refund",
                        "priority_tier": "P1 - High",
                        "confidence_score": 0.98,
                    },
                    summary="Classified as Billing & Refund (P1 - High, 98% confidence)",
                ),
                TraceStep(
                    step_number=2,
                    tool_name="extract_entities",
                    title="Extract Financial & Temporal Entities",
                    status="completed",
                    started_at="10:12:02.530",
                    duration_ms=510,
                    input_payload={"sender": "elena.rostova@vanguard-logistics.io"},
                    output_payload={
                        "organization": "Vanguard Global Logistics",
                        "monetary_amount": 14500.00,
                        "currency": "USD",
                        "deadline_iso": "2026-11-18",
                        "reference_ids": ["INV-2026-8841", "ACH-992014-B"],
                    },
                    summary="Extracted $14,500.00 USD, deadline 2026-11-18, refs INV-2026-8841 & ACH-992014-B",
                ),
                TraceStep(
                    step_number=3,
                    tool_name="search_drive_sops",
                    title="Search Google Drive SOP Folder",
                    status="completed",
                    started_at="10:12:03.040",
                    duration_ms=380,
                    input_payload={
                        "drive_folder_id": settings.GOOGLE_DRIVE_SOP_FOLDER_ID,
                        "query": "Duplicate ACH charge credit memo refund SLA",
                    },
                    output_payload={
                        "matched_doc": "SOP-01: Enterprise Billing, Overcharge & Refund Policy (v4.2)",
                        "section": "Section 3.2 — Duplicate Charge & Credit Memo SLA",
                        "relevance_score": 0.97,
                    },
                    summary="Matched SOP-01 Section 3.2 (48-hour expedited reversal under $25,000 USD)",
                ),
                TraceStep(
                    step_number=4,
                    tool_name="log_sheet_row",
                    title="Append Tracking Row to OpsTriage Sheet",
                    status="completed",
                    started_at="10:12:03.420",
                    duration_ms=340,
                    input_payload={
                        "spreadsheet_id": settings.GOOGLE_SHEETS_TRACKER_ID,
                        "range": "Tracker!A:M",
                        "status": "Pending Approval",
                    },
                    output_payload={"row_id": "ROW-001", "sheet_row_number": 2, "status": "Pending Approval"},
                    summary="Logged Row #2 in OpsTriage Tracking Sheet (Status: Pending Approval)",
                ),
                TraceStep(
                    step_number=5,
                    tool_name="draft_grounded_reply",
                    title="Draft Policy-Grounded Response",
                    status="completed",
                    started_at="10:12:03.760",
                    duration_ms=640,
                    input_payload={"sop_citation": "SOP-01 Section 3.2", "credit_memo_id": "CM-2026-8841"},
                    output_payload={"draft_ready": True, "word_count": 138},
                    summary="Generated response grounded in SOP-01 Section 3.2 with Credit Memo #CM-2026-8841",
                ),
            ],
            tracking_row_id="ROW-001",
            sheet_row_number=2,
            draft_reply=(
                "Hi Elena,\n\n"
                "Thank you for flagging this immediately. We have verified the duplicate ACH debit of $14,500.00 USD "
                "(Reference #ACH-992014-B) against Invoice #INV-2026-8841 for Vanguard Global Logistics.\n\n"
                "Per our Enterprise Billing Policy (SOP-01, Section 3.2), duplicate charges under $25,000 USD qualify "
                "for expedited 48-hour settlement:\n"
                "1. Credit Memo Issued: #CM-2026-8841 for $14,500.00 USD.\n"
                "2. ACH Reversal Initiated: The $14,500.00 USD refund has been queued for priority settlement and will "
                "clear your account prior to your November 18, 2026 close deadline.\n"
                "3. Controller Notification: Logged in our OpsTriage ledger (Row #2) with zero impact to your active Q4 subscription.\n\n"
                "Please let us know if your treasury team needs the signed PDF Credit Memo attached separately.\n\n"
                "Best regards,\n"
                "OpsTriage Autonomous Operations Team"
            ),
            triage_latency_ms=2290,
            source_mode="sandbox",
        ),
        InboundInquiry(
            id="inq-1002",
            thread_id="thr-1002",
            subject="P0 ESCALATION: US-East Webhook Gateway 504 Timeouts (SLA Breach)",
            sender_name="Marcus Vance",
            sender_email="mvance@AetherPay-Corp.com",
            organization="AetherPay Financial",
            received_at="2026-11-16T10:28:00Z",
            body=(
                "Team,\n\n"
                "Our production checkout cluster experienced 27 minutes of HTTP 504 gateway timeouts on your "
                "US-East webhook ingestion endpoint between 09:15 UTC and 09:42 UTC today (Incident Ticket #INC-7741).\n\n"
                "Under our Enterprise MSA ($48,000/month commitment), this exceeds the 99.99% uptime SLA threshold. "
                "We require:\n"
                "1) Written confirmation of our 10% monthly SLA service credit ($4,800.00 USD), and\n"
                "2) A formal Root Cause Analysis (RCA) delivery deadline by tomorrow 2026-11-17.\n\n"
                "Marcus Vance\n"
                "Head of Platform Reliability, AetherPay Financial"
            ),
            status="Untriaged",
            source_mode="sandbox",
            ai_summary=(
                "Marcus Vance from AetherPay Financial has escalated a 27-minute gateway outage exceeding their 99.99% Enterprise SLA. "
                "The customer is requesting an authorized 10% monthly service credit of $4,800.00 and an incident Root Cause Analysis report by tomorrow."
            ),
        ),
        InboundInquiry(
            id="inq-1003",
            thread_id="thr-1003",
            subject="Overdue Net-30 Wire Request — CloudScale GPU Cluster PO-2026-441 ($32,400.00)",
            sender_name="Priya Nair",
            sender_email="ar@cloudscale-infra.ai",
            organization="CloudScale Infrastructure Inc.",
            received_at="2026-11-16T09:45:00Z",
            body=(
                "Hello Accounts Payable,\n\n"
                "Following up on Invoice #CSI-9082 for $32,400.00 USD covering reserved H200 inference capacity "
                "under approved Purchase Order #PO-2026-441.\n\n"
                "The Net-30 due date was November 13, 2026 (3 days past due). Please confirm when the ACH/Wire "
                "disbursement will be released before our quarter-end audit cutoff on 2026-11-20.\n\n"
                "Thank you,\n"
                "Priya Nair | Accounts Receivable Lead\n"
                "CloudScale Infrastructure Inc."
            ),
            status="Untriaged",
            source_mode="sandbox",
            ai_summary=(
                "Priya Nair from CloudScale Infrastructure is requesting urgent wire disbursement for a 3-day overdue "
                "$32,400.00 GPU compute invoice under approved Purchase Order #PO-2026-441. "
                "Under SOP-03 Section 2.1, overdue vendor balances with valid PO matching qualify for expedited ACH release."
            ),
        ),
        InboundInquiry(
            id="inq-1004",
            thread_id="thr-1004",
            subject="Urgent Security Review: SOC2 Type II + Countersigned GDPR DPA Needed for Procurement",
            sender_name="Dr. Lukas Weber",
            sender_email="l.weber@helvetia-medtech.ch",
            organization="Helvetia MedTech AG",
            received_at="2026-11-16T08:50:00Z",
            body=(
                "Good morning Security & Legal Operations,\n\n"
                "We are in the final stage of signing our $85,000.00 annual Enterprise license (Deal Ref #SF-55192, "
                "Mutual NDA #NDA-2026-309 already signed).\n\n"
                "Our DPO requires your latest SOC2 Type II attestation report and a countersigned standard GDPR "
                "Data Processing Addendum (DPA) by 2026-11-19 so we can release the countersigned order form.\n\n"
                "Kind regards,\n"
                "Dr. Lukas Weber\n"
                "Chief Information Security Officer, Helvetia MedTech AG"
            ),
            status="Untriaged",
            source_mode="sandbox",
            ai_summary=(
                "Dr. Lukas Weber from Helvetia MedTech is requesting their DPO compliance package containing SOC2 Type II reports "
                "and a countersigned GDPR Data Processing Addendum to finalize an $85,000 procurement contract ahead of November 19."
            ),
        ),
        InboundInquiry(
            id="inq-1005",
            thread_id="thr-1005",
            subject="Contractor Onboarding & $1,650 Workstation Reimbursement — Start Date Nov 19",
            sender_name="Devon Brooks",
            sender_email="devon.brooks@BrooksSecConsulting.dev",
            organization="Brooks Security Consulting",
            received_at="2026-11-16T08:15:00Z",
            body=(
                "Hi People Ops,\n\n"
                "I'm starting my Senior Staff Security Engineer contract on November 19, 2026 (Contract #CTR-2026-118). "
                "Could you confirm when my Okta SSO + GitHub access will be provisioned, and verify approval for my "
                "$1,650.00 USD workstation + YubiKey hardware receipt reimbursement?\n\n"
                "Thanks!\n"
                "Devon Brooks"
            ),
            status="Resolved",
            ai_summary=(
                "Devon Brooks is requesting Okta and GitHub org access ahead of their November 19 contract start date, "
                "alongside a $1,650 workstation expense reimbursement. Under SOP-05, contractor access has been pre-scheduled and the stipend was approved."
            ),
            intent_category="HR & Onboarding",
            priority_tier="P2 - Medium",
            confidence_score=0.96,
            classification_rationale="Standard contractor SSO onboarding and hardware reimbursement ($1,650 <= $1,800 SOP cap).",
            entities=ExtractedEntities(
                sender_name="Devon Brooks",
                sender_email="devon.brooks@BrooksSecConsulting.dev",
                organization="Brooks Security Consulting",
                monetary_amount=1650.00,
                currency="USD",
                deadline_iso="2026-11-19",
                reference_ids=["CTR-2026-118"],
                key_summary="Contractor Okta/GitHub provisioning before 2026-11-19 start date and $1,650.00 hardware reimbursement.",
            ),
            matched_sops=[
                SOPMatch(
                    doc_id="sop-hr-005",
                    title="SOP-05: Contractor Access Provisioning & Hardware Stipend Policy",
                    drive_url=DRIVE_FOLDER_URL,
                    matched_section="Section 2.3 — Engineering Contractor SSO & Equipment Reimbursement",
                    policy_excerpt=SEED_SOP_DOCUMENTS[4]["policy_excerpt"],
                    relevance_score=0.96,
                )
            ],
            execution_trace=[
                TraceStep(
                    step_number=1,
                    tool_name="classify_inquiry",
                    title="Classify Intent & Priority Tier",
                    status="completed",
                    started_at="08:15:04.100",
                    duration_ms=390,
                    input_payload={"subject": "Contractor Onboarding & $1,650 Workstation Reimbursement"},
                    output_payload={"intent_category": "HR & Onboarding", "priority_tier": "P2 - Medium"},
                    summary="Classified as HR & Onboarding (P2 - Medium, 96% confidence)",
                ),
                TraceStep(
                    step_number=2,
                    tool_name="extract_entities",
                    title="Extract Financial & Temporal Entities",
                    status="completed",
                    started_at="08:15:04.490",
                    duration_ms=440,
                    input_payload={"sender": "devon.brooks@BrooksSecConsulting.dev"},
                    output_payload={"monetary_amount": 1650.0, "deadline_iso": "2026-11-19", "reference_ids": ["CTR-2026-118"]},
                    summary="Extracted $1,650.00 USD stipend request and start date 2026-11-19",
                ),
                TraceStep(
                    step_number=3,
                    tool_name="search_drive_sops",
                    title="Search Google Drive SOP Folder",
                    status="completed",
                    started_at="08:15:04.930",
                    duration_ms=350,
                    input_payload={"query": "Contractor SSO GitHub hardware stipend reimbursement"},
                    output_payload={"matched_doc": "SOP-05: Contractor Access Provisioning & Hardware Stipend Policy"},
                    summary="Matched SOP-05 Section 2.3 ($1,800 cap, 48h prior SSO provisioning)",
                ),
                TraceStep(
                    step_number=4,
                    tool_name="log_sheet_row",
                    title="Append Tracking Row to OpsTriage Sheet",
                    status="completed",
                    started_at="08:15:05.280",
                    duration_ms=310,
                    input_payload={"row_id": "ROW-002"},
                    output_payload={"row_id": "ROW-002", "sheet_row_number": 3, "status": "Resolved"},
                    summary="Logged Row #3 in OpsTriage Tracking Sheet (Status: Resolved)",
                ),
                TraceStep(
                    step_number=5,
                    tool_name="draft_grounded_reply",
                    title="Draft Policy-Grounded Response",
                    status="completed",
                    started_at="08:15:05.590",
                    duration_ms=520,
                    input_payload={"sop_citation": "SOP-05 Section 2.3"},
                    output_payload={"draft_ready": True},
                    summary="Drafted approval confirmation grounded in SOP-05 Section 2.3",
                ),
            ],
            tracking_row_id="ROW-002",
            sheet_row_number=3,
            draft_reply=(
                "Hi Devon,\n\n"
                "Welcome aboard! Per SOP-05 (Section 2.3 — Engineering Contractor SSO & Equipment Reimbursement):\n"
                "1. Access Provisioning: Your Okta SSO, Google Workspace, and GitHub invites are scheduled to activate on November 17, 2026 (48 hours prior to your November 19 start date).\n"
                "2. Hardware Reimbursement: Your $1,650.00 USD workstation + YubiKey expense is within our $1,800.00 USD contractor cap under Contract #CTR-2026-118 and has been approved for your first invoice cycle.\n\n"
                "Best regards,\n"
                "OpsTriage People Operations"
            ),
            sent_reply=(
                "Hi Devon,\n\n"
                "Welcome aboard! Per SOP-05 (Section 2.3 — Engineering Contractor SSO & Equipment Reimbursement):\n"
                "1. Access Provisioning: Your Okta SSO, Google Workspace, and GitHub invites are scheduled to activate on November 17, 2026 (48 hours prior to your November 19 start date).\n"
                "2. Hardware Reimbursement: Your $1,650.00 USD workstation + YubiKey expense is within our $1,800.00 USD contractor cap under Contract #CTR-2026-118 and has been approved for your first invoice cycle.\n\n"
                "Best regards,\n"
                "OpsTriage People Operations"
            ),
            resolved_at="2026-11-16T08:18:12Z",
            triage_latency_ms=2010,
            source_mode="sandbox",
        ),
        InboundInquiry(
            id="inq-1006",
            thread_id="thr-1006",
            subject="Annual Vendor Compliance: Updated W-9 & Direct Deposit Authorization",
            sender_name="Sarah Jenkins",
            sender_email="sjenkins@meridian-partners.com",
            organization="Meridian Capital Partners",
            received_at="2026-11-16T07:30:00Z",
            body=(
                "Dear Operations & Vendor Management,\n\n"
                "As part of our annual FY2027 fiscal compliance audit, Meridian Capital Partners requires an updated countersigned "
                "W-9 form and confirmed ACH direct deposit instructions for our vendor ledger (Vendor Ref #VND-9920).\n\n"
                "Please provide the standard tax package prior to our December 1 vendor cutoff so ongoing monthly disbursements "
                "remain uninterrupted.\n\n"
                "Sincerely,\n"
                "Sarah Jenkins\n"
                "Vendor Management Lead, Meridian Capital Partners"
            ),
            status="Untriaged",
            source_mode="sandbox",
            ai_summary=(
                "Sarah Jenkins from Meridian Capital Partners is requesting an updated W-9 tax form and direct deposit instructions "
                "for their annual FY2027 vendor compliance review before December 1. Operations can dispatch the standard verified tax package under general SLA."
            ),
        ),
    ]

    tracking_rows: List[TrackingRow] = [
        TrackingRow(
            row_id="ROW-001",
            sheet_row_number=2,
            inquiry_id="inq-1001",
            received_at="2026-11-16T10:12:00Z",
            sender_email="elena.rostova@vanguard-logistics.io",
            organization="Vanguard Global Logistics",
            subject="URGENT: Duplicate ACH Charge on Invoice #INV-2026-8841 ($14,500.00)",
            intent_category="Billing & Refund",
            priority_tier="P1 - High",
            monetary_amount="$14,500.00 USD",
            deadline="2026-11-18",
            matched_sop="SOP-01: Enterprise Billing, Overcharge & Refund Policy (v4.2)",
            status="Pending Approval",
            resolved_at=None,
            sheet_url=SHEET_URL,
        ),
        TrackingRow(
            row_id="ROW-002",
            sheet_row_number=3,
            inquiry_id="inq-1005",
            received_at="2026-11-16T08:15:00Z",
            sender_email="devon.brooks@BrooksSecConsulting.dev",
            organization="Brooks Security Consulting",
            subject="Contractor Onboarding & $1,650 Workstation Reimbursement — Start Date Nov 19",
            intent_category="HR & Onboarding",
            priority_tier="P2 - Medium",
            monetary_amount="$1,650.00 USD",
            deadline="2026-11-19",
            matched_sop="SOP-05: Contractor Access Provisioning & Hardware Stipend Policy",
            status="Resolved",
            resolved_at="2026-11-16T08:18:12Z",
            sheet_url=SHEET_URL,
        ),
    ]

    return inquiries, tracking_rows
