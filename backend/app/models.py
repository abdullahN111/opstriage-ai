from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


WorkspaceMode = Literal["sandbox", "live"]
PriorityTier = Literal["P0 - Critical", "P1 - High", "P2 - Medium", "P3 - Low"]
IntentCategory = Literal[
    "Billing & Refund",
    "Vendor Invoice",
    "SLA Escalation",
    "Compliance & Security",
    "HR & Onboarding",
    "General Operations",
]
InquiryStatus = Literal["Untriaged", "Triaging", "Needs Approval", "Resolved"]


class ExtractedEntities(BaseModel):
    sender_name: str = ""
    sender_email: str = ""
    organization: str = ""
    monetary_amount: Optional[float] = None
    currency: str = "USD"
    deadline_iso: Optional[str] = None
    reference_ids: List[str] = Field(default_factory=list)
    key_summary: str = ""


class SOPMatch(BaseModel):
    doc_id: str
    title: str
    drive_url: str
    matched_section: str
    policy_excerpt: str
    relevance_score: float = 0.95


class TraceStep(BaseModel):
    step_number: int
    tool_name: str
    title: str
    status: Literal["running", "completed", "error"]
    started_at: str
    duration_ms: int
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class TrackingRow(BaseModel):
    row_id: str
    sheet_row_number: int
    inquiry_id: str
    received_at: str
    sender_email: str
    organization: str
    subject: str
    intent_category: str
    priority_tier: str
    monetary_amount: str
    deadline: str
    matched_sop: str
    status: str  # "Pending Approval" | "Resolved"
    resolved_at: Optional[str] = None
    sheet_url: str


class InboundInquiry(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender_name: str
    sender_email: str
    organization: str
    received_at: str
    body: str
    status: InquiryStatus = "Untriaged"
    intent_category: Optional[IntentCategory] = None
    priority_tier: Optional[PriorityTier] = None
    confidence_score: Optional[float] = None
    classification_rationale: Optional[str] = None
    entities: Optional[ExtractedEntities] = None
    matched_sops: List[SOPMatch] = Field(default_factory=list)
    execution_trace: List[TraceStep] = Field(default_factory=list)
    tracking_row_id: Optional[str] = None
    sheet_row_number: Optional[int] = None
    draft_reply: Optional[str] = None
    sent_reply: Optional[str] = None
    ai_summary: Optional[str] = None
    resolved_at: Optional[str] = None
    triage_latency_ms: Optional[int] = None
    source_mode: WorkspaceMode = "sandbox"


class CreateInquiryRequest(BaseModel):
    subject: str
    sender_name: str
    sender_email: str
    organization: str = "External Partner"
    body: str


class RegenerateDraftRequest(BaseModel):
    instructions: str
    current_draft: Optional[str] = None


class ApproveAndSendRequest(BaseModel):
    final_reply_body: str
    reviewer_note: Optional[str] = "Approved via OpsTriage HITL Drawer"
