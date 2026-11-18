from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel

from .config import settings
from .models import (
    WorkspaceMode,
    CreateInquiryRequest,
    RegenerateDraftRequest,
    ApproveAndSendRequest,
)
from .seed_data import SEED_SOP_DOCUMENTS
from .workspace_service import workspace_service
from .agent_pipeline import agent_pipeline

app = FastAPI(
    title="OpsTriage AI — Autonomous Operations Hub API",
    version="1.0.0",
    description="Gemini API + Google Workspace (Gmail, Drive, Sheets) End-to-End Inbox Operations Triage",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetModeRequest(BaseModel):
    mode: WorkspaceMode


class AdminVerifyRequest(BaseModel):
    passkey: str


@app.post("/api/auth/admin/verify")
def verify_admin(req: AdminVerifyRequest) -> Dict[str, Any]:
    if req.passkey == settings.ADMIN_PASSKEY:
        return {
            "authorized": True,
            "admin_email": settings.ADMIN_EMAIL,
            "message": f"Administrator verified as {settings.ADMIN_EMAIL}",
        }
    raise HTTPException(status_code=401, detail="Invalid admin passkey")


def _compute_kpis() -> Dict[str, Any]:
    inquiries = workspace_service.list_inquiries()
    rows = workspace_service.list_tracking_rows()
    total = len(inquiries)
    untriaged = sum(1 for i in inquiries if i.status == "Untriaged")
    needs_approval = sum(1 for i in inquiries if i.status == "Needs Approval")
    resolved = sum(1 for i in inquiries if i.status == "Resolved")
    urgent_p0_p1 = sum(
        1
        for i in inquiries
        if i.priority_tier in ("P0 - Critical", "P1 - High") and i.status != "Resolved"
    )
    latencies = [i.triage_latency_ms for i in inquiries if i.triage_latency_ms]
    avg_latency_ms = int(sum(latencies) / len(latencies)) if latencies else 2150
    return {
        "total_inquiries": total,
        "untriaged_count": untriaged,
        "needs_approval_count": needs_approval,
        "resolved_count": resolved,
        "urgent_p0_p1_count": urgent_p0_p1,
        "sheet_rows_logged": len(rows),
        "avg_triage_latency_ms": avg_latency_ms,
    }


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_key_configured": bool(settings.GEMINI_API_KEY),
        **workspace_service.get_auth_status(),
    }


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    return {
        **workspace_service.get_auth_status(),
        "gemini_model": settings.GEMINI_MODEL,
        "kpis": _compute_kpis(),
    }


@app.post("/api/mode")
def set_workspace_mode(req: SetModeRequest) -> Dict[str, Any]:
    status = workspace_service.set_mode(req.mode)
    return {
        **status,
        "kpis": _compute_kpis(),
    }


@app.post("/api/sandbox/reset")
def reset_sandbox() -> Dict[str, Any]:
    workspace_service.reset_sandbox()
    return {
        "status": "reset",
        "inquiries": [i.model_dump() for i in workspace_service.list_inquiries()],
        "rows": [r.model_dump() for r in workspace_service.list_tracking_rows()],
        "kpis": _compute_kpis(),
    }


@app.get("/api/auth/google/url")
def get_google_oauth_url() -> Dict[str, str]:
    url = workspace_service.build_oauth_authorization_url()
    return {"auth_url": url}


@app.get("/api/auth/google/callback")
def google_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    base_frontend = settings.FRONTEND_URL.rstrip("/")
    if error or not code:
        return RedirectResponse(
            url=f"{base_frontend}/?oauth=error&reason={error or 'missing_code'}"
        )
    try:
        workspace_service.handle_oauth_callback(code=code, state=state)
        return RedirectResponse(url=f"{base_frontend}/?mode=live&oauth=connected")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f"{base_frontend}/?oauth=error&reason={str(exc)[:120]}"
        )


@app.post("/api/drive/seed-sops")
def seed_drive_sops() -> Dict[str, Any]:
    created = workspace_service.seed_drive_sops_to_live_folder()
    return {"created_count": len(created), "files": created}


@app.get("/api/sops")
def list_sops() -> Dict[str, Any]:
    return {
        "drive_folder_id": settings.GOOGLE_DRIVE_SOP_FOLDER_ID,
        "sops": SEED_SOP_DOCUMENTS,
    }


@app.get("/api/inquiries")
def list_inquiries() -> Dict[str, Any]:
    inquiries = workspace_service.list_inquiries()
    return {
        "mode": workspace_service.mode,
        "inquiries": [i.model_dump() for i in inquiries],
        "kpis": _compute_kpis(),
    }


@app.post("/api/inquiries")
def create_inquiry(req: CreateInquiryRequest) -> Dict[str, Any]:
    inquiry = workspace_service.create_custom_inquiry(req)
    return {
        "inquiry": inquiry.model_dump(),
        "kpis": _compute_kpis(),
    }


@app.post("/api/gmail/sync")
def sync_gmail(limit: int = 50) -> Dict[str, Any]:
    inquiries = workspace_service.sync_live_gmail_inbox(max_results=limit)
    return {
        "synced_count": len(inquiries),
        "inquiries": [i.model_dump() for i in inquiries],
        "kpis": _compute_kpis(),
    }


@app.get("/api/inquiries/{inquiry_id}/triage/stream")
async def stream_triage(inquiry_id: str):
    inquiry = workspace_service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    return StreamingResponse(
        agent_pipeline.stream_triage_execution(inquiry),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/inquiries/{inquiry_id}/triage")
async def run_triage_sync(inquiry_id: str) -> Dict[str, Any]:
    inquiry = workspace_service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    async for _ in agent_pipeline.stream_triage_execution(inquiry):
        pass

    return {
        "inquiry": inquiry.model_dump(),
        "kpis": _compute_kpis(),
    }


@app.post("/api/inquiries/{inquiry_id}/summarize")
def summarize_inquiry(inquiry_id: str) -> Dict[str, Any]:
    inquiry = workspace_service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    summary = agent_pipeline.summarize_inquiry(inquiry)
    return {
        "inquiry_id": inquiry.id,
        "summary": summary,
        "inquiry": inquiry.model_dump(),
    }


@app.post("/api/inquiries/{inquiry_id}/regenerate")
def regenerate_reply(inquiry_id: str, req: RegenerateDraftRequest) -> Dict[str, Any]:
    inquiry = workspace_service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    new_draft = agent_pipeline.regenerate_draft(
        inquiry, req.instructions, req.current_draft
    )
    return {
        "inquiry_id": inquiry.id,
        "draft_reply": new_draft,
        "inquiry": inquiry.model_dump(),
    }


@app.post("/api/inquiries/{inquiry_id}/approve")
def approve_and_send(inquiry_id: str, req: ApproveAndSendRequest) -> Dict[str, Any]:
    inquiry = workspace_service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    resolution = workspace_service.mark_resolved_and_send_email(
        inquiry, req.final_reply_body
    )
    return {
        "resolution": resolution,
        "inquiry": inquiry.model_dump(),
        "rows": [r.model_dump() for r in workspace_service.list_tracking_rows()],
        "kpis": _compute_kpis(),
    }


@app.get("/api/sheets/rows")
def get_sheet_rows() -> Dict[str, Any]:
    rows = workspace_service.list_tracking_rows()
    return {
        "spreadsheet_id": settings.GOOGLE_SHEETS_TRACKER_ID,
        "rows": [r.model_dump() for r in rows],
    }
