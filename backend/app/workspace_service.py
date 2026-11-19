import base64
import html
import json
import re
import threading
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Dict, Any

from .config import settings
from .models import (
    InboundInquiry,
    TrackingRow,
    SOPMatch,
    WorkspaceMode,
    CreateInquiryRequest,
)
from .seed_data import (
    SEED_SOP_DOCUMENTS,
    DRIVE_FOLDER_URL,
    SHEET_URL,
    get_initial_sandbox_data,
)

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False


class WorkspaceService:
    def __init__(self) -> None:
        self.mode: WorkspaceMode = "sandbox"
        self.sandbox_inquiries, self.sandbox_rows = get_initial_sandbox_data()
        self.live_inquiries: List[InboundInquiry] = []
        self.live_rows: List[TrackingRow] = []
        self._oauth_states: Dict[str, str] = {}
        self._sync_lock = threading.Lock()

    # ------------------------------------------------------------------
    # OAuth & Mode Management
    # ------------------------------------------------------------------
    def get_credentials(self) -> Optional[Any]:
        if getattr(self, "_cached_credentials", None) and self._cached_credentials.valid:
            return self._cached_credentials
        if not GOOGLE_LIBS_AVAILABLE:
            return None
        candidate_paths = [settings.TOKEN_PATH, Path("/tmp/token.json")]
        for tp in candidate_paths:
            if not tp.exists():
                continue
            try:
                creds = Credentials.from_authorized_user_file(
                    str(tp), settings.GOOGLE_SCOPES
                )
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    try:
                        tp.write_text(creds.to_json(), encoding="utf-8")
                    except Exception:
                        pass
                if creds and creds.valid:
                    self._cached_credentials = creds
                    return creds
            except Exception:
                continue
        return None

    def is_live_authenticated(self) -> bool:
        return self.get_credentials() is not None

    def get_auth_status(self) -> Dict[str, Any]:
        creds = self.get_credentials()
        return {
            "mode": self.mode,
            "oauth_connected": creds is not None,
            "admin_email": settings.ADMIN_EMAIL,
            "client_id_configured": bool(settings.GOOGLE_CLIENT_ID),
            "drive_folder_id": settings.GOOGLE_DRIVE_SOP_FOLDER_ID,
            "drive_folder_url": DRIVE_FOLDER_URL,
            "sheets_tracker_id": settings.GOOGLE_SHEETS_TRACKER_ID,
            "sheets_tracker_url": SHEET_URL,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }

    def set_mode(self, mode: WorkspaceMode) -> Dict[str, Any]:
        self.mode = mode
        return self.get_auth_status()

    def reset_sandbox(self) -> None:
        self.sandbox_inquiries, self.sandbox_rows = get_initial_sandbox_data()

    def build_oauth_authorization_url(self) -> str:
        if not GOOGLE_LIBS_AVAILABLE:
            raise RuntimeError("google-auth-oauthlib is not installed.")
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        flow.autogenerate_code_verifier = False
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            login_hint=settings.ADMIN_EMAIL,
        )
        return auth_url

    def handle_oauth_callback(self, code: str, state: Optional[str] = None) -> None:
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
            state=state,
        )
        flow.autogenerate_code_verifier = False
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Verify authorized email matches ADMIN_EMAIL to protect personal data on public URLs
        auth_email = ""
        try:
            gmail = build("gmail", "v1", credentials=creds)
            profile = gmail.users().getProfile(userId="me").execute()
            auth_email = profile.get("emailAddress", "")
        except Exception as exc:
            print(f"[WorkspaceService] Gmail profile check warning: {exc}")

        if settings.ADMIN_EMAIL and auth_email:
            if auth_email.lower().strip() != settings.ADMIN_EMAIL.lower().strip():
                raise PermissionError(
                    f"Access Denied: Live OAuth is strictly restricted to administrator ({settings.ADMIN_EMAIL}). "
                    f"Signed in as {auth_email}. Please explore OpsTriage AI in Live Sandbox Mode."
                )

        self._cached_credentials = creds
        saved = False
        for p in [settings.TOKEN_PATH, Path("/tmp/token.json")]:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(creds.to_json(), encoding="utf-8")
                saved = True
                break
            except Exception:
                continue
        self.mode = "live"
        # Pre-load live inbox so it is ready immediately
        try:
            self.sync_live_gmail_inbox(max_results=50)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Inquiries Management (Sandbox & Live Gmail)
    # ------------------------------------------------------------------
    def list_inquiries(self) -> List[InboundInquiry]:
        if self.mode == "live" and self.is_live_authenticated():
            if not self.live_inquiries:
                self.sync_live_gmail_inbox(max_results=50)
            return self.live_inquiries
        return self.sandbox_inquiries

    def get_inquiry(self, inquiry_id: str) -> Optional[InboundInquiry]:
        for inq in self.sandbox_inquiries + self.live_inquiries:
            if inq.id == inquiry_id:
                return inq
        return None

    def create_custom_inquiry(self, req: CreateInquiryRequest) -> InboundInquiry:
        target_list = (
            self.live_inquiries
            if (self.mode == "live" and self.is_live_authenticated())
            else self.sandbox_inquiries
        )
        new_num = 1001 + len(self.sandbox_inquiries) + len(self.live_inquiries)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inquiry = InboundInquiry(
            id=f"inq-{new_num}",
            thread_id=f"thr-{new_num}",
            subject=req.subject,
            sender_name=req.sender_name,
            sender_email=req.sender_email,
            organization=req.organization,
            received_at=now_iso,
            body=req.body,
            status="Untriaged",
            source_mode=self.mode,
        )
        target_list.insert(0, inquiry)
        return inquiry

    def sync_live_gmail_inbox(self, max_results: int = 50) -> List[InboundInquiry]:
        with self._sync_lock:
            creds = self.get_credentials()
            if not creds:
                return self.live_inquiries
            try:
                gmail = build("gmail", "v1", credentials=creds)
                results = (
                    gmail.users()
                    .messages()
                    .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
                    .execute()
                )
                messages = results.get("messages", [])
                existing_ids = {inq.id for inq in self.live_inquiries}

                for m in messages:
                    msg_id = f"gmail-{m['id']}"
                    if msg_id in existing_ids:
                        continue
                    existing_ids.add(msg_id)
                    msg_detail = (
                        gmail.users()
                        .messages()
                        .get(userId="me", id=m["id"], format="full")
                        .execute()
                    )
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in msg_detail.get("payload", {}).get("headers", [])
                    }
                    subject = headers.get("subject", "(No Subject)")
                    raw_from = headers.get("from", "Unknown Sender <unknown@example.com>")
                    sender_name, sender_email = self._parse_from_header(raw_from)
                    org = (
                        sender_email.split("@")[-1].split(".")[0].capitalize()
                        if "@" in sender_email
                        else "External"
                    )
                    body = self._extract_message_body(msg_detail.get("payload", {})) or msg_detail.get(
                        "snippet", ""
                    )
                    internal_ts = int(msg_detail.get("internalDate", "0")) / 1000.0
                    received_at = (
                        datetime.fromtimestamp(internal_ts, tz=timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        )
                        if internal_ts
                        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    )
                    if not any(x.id == msg_id for x in self.live_inquiries):
                        self.live_inquiries.append(
                            InboundInquiry(
                                id=msg_id,
                                thread_id=msg_detail.get("threadId", m["id"]),
                                subject=subject,
                                sender_name=sender_name,
                                sender_email=sender_email,
                                organization=org,
                                received_at=received_at,
                                body=body[:4000],
                                status="Untriaged",
                                source_mode="live",
                            )
                        )
            except Exception as exc:
                print(f"[WorkspaceService] Live Gmail sync warning: {exc}")
            # Deduplicate any existing entries by id
            deduped: Dict[str, InboundInquiry] = {}
            for item in self.live_inquiries:
                deduped[item.id] = item
            self.live_inquiries = list(deduped.values())
            # Sort newest received email first, matching real Gmail inbox view
            self.live_inquiries.sort(key=lambda x: x.received_at, reverse=True)
            return self.live_inquiries

    # ------------------------------------------------------------------
    # Google Drive SOP Search & Seeding
    # ------------------------------------------------------------------
    def search_drive_sops(
        self, intent_category: str, query_terms: str
    ) -> List[SOPMatch]:
        """Searches Live Google Drive folder when in Live Mode (falling back/enriching with seed SOPs)."""
        creds = self.get_credentials() if self.mode == "live" else None
        live_matches: List[SOPMatch] = []

        if creds:
            try:
                drive = build("drive", "v3", credentials=creds)
                q = f"'{settings.GOOGLE_DRIVE_SOP_FOLDER_ID}' in parents and trashed = false"
                res = (
                    drive.files()
                    .list(
                        q=q,
                        pageSize=20,
                        fields="files(id, name, mimeType, webViewLink)",
                    )
                    .execute()
                )
                files = res.get("files", [])
                if not files:
                    # Auto-seed the user's SOP Drive folder with our 5 default SOPs so Live Mode works immediately!
                    self.seed_drive_sops_to_live_folder()
                    res = (
                        drive.files()
                        .list(
                            q=q,
                            pageSize=20,
                            fields="files(id, name, mimeType, webViewLink)",
                        )
                        .execute()
                    )
                    files = res.get("files", [])

                query_words = [
                    w.lower()
                    for w in (intent_category + " " + query_terms).split()
                    if len(w) > 3
                ]
                for f in files:
                    fname = f.get("name", "")
                    score = 0.80
                    for w in query_words:
                        if w in fname.lower():
                            score = min(0.99, score + 0.06)
                    content_text = self._read_drive_file_text(drive, f)
                    for w in query_words:
                        if w in content_text.lower():
                            score = min(0.99, score + 0.03)
                    if score >= 0.83 or len(files) <= 2:
                        live_matches.append(
                            SOPMatch(
                                doc_id=f["id"],
                                title=fname,
                                drive_url=f.get("webViewLink", DRIVE_FOLDER_URL),
                                matched_section="Matched Live Google Drive SOP Document",
                                policy_excerpt=(content_text[:360].strip() or fname),
                                relevance_score=round(score, 2),
                            )
                        )
                live_matches.sort(key=lambda m: m.relevance_score, reverse=True)
                if live_matches:
                    return live_matches[:2]
            except Exception as exc:
                print(f"[WorkspaceService] Live Drive search fallback: {exc}")

        # Sandbox or fallback matching
        matched: List[SOPMatch] = []
        for doc in SEED_SOP_DOCUMENTS:
            if doc["category"].lower() == intent_category.lower():
                matched.append(
                    SOPMatch(
                        doc_id=doc["doc_id"],
                        title=doc["title"],
                        drive_url=doc["drive_url"],
                        matched_section=doc["matched_section"],
                        policy_excerpt=doc["policy_excerpt"],
                        relevance_score=0.97,
                    )
                )
        if not matched and intent_category.lower() != "general operations":
            # Only match top enterprise SOP if specifically an enterprise category without direct title match
            for doc in SEED_SOP_DOCUMENTS:
                if any(w in query_terms.lower() for w in doc["category"].lower().split()):
                    matched.append(
                        SOPMatch(
                            doc_id=doc["doc_id"],
                            title=doc["title"],
                            drive_url=doc["drive_url"],
                            matched_section=doc["matched_section"],
                            policy_excerpt=doc["policy_excerpt"],
                            relevance_score=0.85,
                        )
                    )
                    break
        return matched

    def seed_drive_sops_to_live_folder(self) -> List[Dict[str, str]]:
        """Uploads the 5 standard SOP markdown documents into the user's Google Drive folder if missing."""
        creds = self.get_credentials()
        if not creds:
            return []
        created: List[Dict[str, str]] = []
        try:
            drive = build("drive", "v3", credentials=creds)
            for doc in SEED_SOP_DOCUMENTS:
                metadata = {
                    "name": f"{doc['title']}.md",
                    "parents": [settings.GOOGLE_DRIVE_SOP_FOLDER_ID],
                    "mimeType": "text/markdown",
                }
                media = MediaInMemoryUpload(
                    doc["full_text"].encode("utf-8"),
                    mimetype="text/markdown",
                    resumable=False,
                )
                f = (
                    drive.files()
                    .create(
                        body=metadata,
                        media_body=media,
                        fields="id, name, webViewLink",
                    )
                    .execute()
                )
                created.append(f)
        except Exception as exc:
            print(f"[WorkspaceService] Failed to seed Drive SOPs: {exc}")
        return created

    # ------------------------------------------------------------------
    # Google Sheets Tracking Row Logging & Resolution
    # ------------------------------------------------------------------
    def list_tracking_rows(self) -> List[TrackingRow]:
        if self.mode == "live" and self.is_live_authenticated():
            return self.live_rows or self.sandbox_rows
        return self.sandbox_rows

    def append_tracking_row(
        self, inquiry: InboundInquiry, matched_sop_title: str
    ) -> TrackingRow:
        target_rows = (
            self.live_rows
            if (self.mode == "live" and self.is_live_authenticated())
            else self.sandbox_rows
        )
        # Check if row already exists for inquiry
        for existing in target_rows:
            if existing.inquiry_id == inquiry.id:
                existing.intent_category = inquiry.intent_category or "General Operations"
                existing.priority_tier = inquiry.priority_tier or "P2 - Medium"
                existing.matched_sop = matched_sop_title
                existing.status = "Pending Approval"
                return existing

        row_num = len(target_rows) + 2
        row_id = f"ROW-{row_num - 1:03d}"
        amt_str = (
            f"${inquiry.entities.monetary_amount:,.2f} {inquiry.entities.currency}"
            if (inquiry.entities and inquiry.entities.monetary_amount is not None)
            else "N/A"
        )
        deadline_str = (
            inquiry.entities.deadline_iso
            if (inquiry.entities and inquiry.entities.deadline_iso)
            else "Standard SLA"
        )

        row = TrackingRow(
            row_id=row_id,
            sheet_row_number=row_num,
            inquiry_id=inquiry.id,
            received_at=inquiry.received_at,
            sender_email=inquiry.sender_email,
            organization=inquiry.organization,
            subject=inquiry.subject,
            intent_category=inquiry.intent_category or "General Operations",
            priority_tier=inquiry.priority_tier or "P2 - Medium",
            monetary_amount=amt_str,
            deadline=deadline_str,
            matched_sop=matched_sop_title,
            status="Pending Approval",
            resolved_at=None,
            sheet_url=SHEET_URL,
        )

        # If Live Mode with valid credentials, write directly to Google Sheet!
        creds = self.get_credentials() if self.mode == "live" else None
        if creds:
            try:
                sheets = build("sheets", "v4", credentials=creds)
                self._ensure_sheet_headers(sheets)
                values = [
                    [
                        row.row_id,
                        row.inquiry_id,
                        row.received_at,
                        row.sender_email,
                        row.organization,
                        row.subject,
                        row.intent_category,
                        row.priority_tier,
                        row.monetary_amount,
                        row.deadline,
                        row.matched_sop,
                        row.status,
                        row.resolved_at or "",
                    ]
                ]
                append_res = (
                    sheets.spreadsheets()
                    .values()
                    .append(
                        spreadsheetId=settings.GOOGLE_SHEETS_TRACKER_ID,
                        range="A1",
                        valueInputOption="USER_ENTERED",
                        insertDataOption="INSERT_ROWS",
                        body={"values": values},
                    )
                    .execute()
                )
                updated_range = append_res.get("updates", {}).get("updatedRange", "")
                if "!" in updated_range:
                    cell_part = updated_range.split("!")[-1].split(":")[0]
                    digits = "".join(ch for ch in cell_part if ch.isdigit())
                    if digits:
                        row.sheet_row_number = int(digits)
            except Exception as exc:
                print(f"[WorkspaceService] Live Sheets append warning: {exc}")

        target_rows.insert(0, row)
        inquiry.tracking_row_id = row.row_id
        inquiry.sheet_row_number = row.sheet_row_number
        return row

    def mark_resolved_and_send_email(
        self, inquiry: InboundInquiry, final_reply_body: str
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inquiry.sent_reply = final_reply_body
        inquiry.draft_reply = final_reply_body
        inquiry.status = "Resolved"
        inquiry.resolved_at = now_iso

        # Update tracking row in memory
        for r in self.sandbox_rows + self.live_rows:
            if r.inquiry_id == inquiry.id or r.row_id == inquiry.tracking_row_id:
                r.status = "Resolved"
                r.resolved_at = now_iso

        gmail_sent = False
        sheets_updated = False
        creds = self.get_credentials() if self.mode == "live" else None

        if creds:
            # 1. Send reply via Gmail API
            try:
                gmail = build("gmail", "v1", credentials=creds)
                mime_msg = MIMEText(final_reply_body)
                mime_msg["to"] = inquiry.sender_email
                mime_msg["subject"] = (
                    inquiry.subject
                    if inquiry.subject.lower().startswith("re:")
                    else f"Re: {inquiry.subject}"
                )
                raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
                send_body: Dict[str, Any] = {"raw": raw_bytes}
                if inquiry.thread_id and not inquiry.thread_id.startswith("thr-"):
                    send_body["threadId"] = inquiry.thread_id
                gmail.users().messages().send(userId="me", body=send_body).execute()
                gmail_sent = True
            except Exception as exc:
                print(f"[WorkspaceService] Live Gmail send warning: {exc}")

            # 2. Update Status & Resolved_At columns in Google Sheet
            if inquiry.sheet_row_number:
                try:
                    sheets = build("sheets", "v4", credentials=creds)
                    range_target = f"L{inquiry.sheet_row_number}:M{inquiry.sheet_row_number}"
                    sheets.spreadsheets().values().update(
                        spreadsheetId=settings.GOOGLE_SHEETS_TRACKER_ID,
                        range=range_target,
                        valueInputOption="USER_ENTERED",
                        body={"values": [["Resolved", now_iso]]},
                    ).execute()
                    sheets_updated = True
                except Exception as exc:
                    print(f"[WorkspaceService] Live Sheets status update warning: {exc}")

        return {
            "inquiry_id": inquiry.id,
            "status": "Resolved",
            "resolved_at": now_iso,
            "mode": self.mode,
            "gmail_dispatched": gmail_sent or (self.mode == "sandbox"),
            "sheet_row_updated": sheets_updated or (self.mode == "sandbox"),
            "sheet_row_number": inquiry.sheet_row_number,
            "sheet_url": SHEET_URL,
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    def _ensure_sheet_headers(self, sheets_service: Any) -> None:
        try:
            res = (
                sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=settings.GOOGLE_SHEETS_TRACKER_ID, range="A1:M1")
                .execute()
            )
            if not res.get("values"):
                headers = [
                    [
                        "Row ID",
                        "Inquiry ID",
                        "Received At",
                        "Sender Email",
                        "Organization",
                        "Subject",
                        "Intent Category",
                        "Priority Tier",
                        "Monetary Amount",
                        "Deadline",
                        "Matched SOP",
                        "Status",
                        "Resolved At",
                    ]
                ]
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=settings.GOOGLE_SHEETS_TRACKER_ID,
                    range="A1:M1",
                    valueInputOption="USER_ENTERED",
                    body={"values": headers},
                ).execute()
        except Exception:
            pass

    @staticmethod
    def _read_drive_file_text(drive_service: Any, file_meta: Dict[str, Any]) -> str:
        fid = file_meta["id"]
        mime = file_meta.get("mimeType", "")
        try:
            if mime == "application/vnd.google-apps.document":
                raw = (
                    drive_service.files()
                    .export(fileId=fid, mimeType="text/plain")
                    .execute()
                )
            else:
                raw = drive_service.files().get_media(fileId=fid).execute()
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="ignore")
            return str(raw)
        except Exception:
            return file_meta.get("name", "")

    @staticmethod
    def _parse_from_header(raw_from: str) -> tuple[str, str]:
        if "<" in raw_from and ">" in raw_from:
            name = raw_from.split("<")[0].strip().strip('"')
            email = raw_from.split("<")[1].split(">")[0].strip()
            return (name or email, email)
        return (raw_from.strip(), raw_from.strip())

    @classmethod
    def _find_part_by_mime(cls, payload: Dict[str, Any], target_mime: str) -> str:
        if payload.get("mimeType") == target_mime and payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        for part in payload.get("parts", []):
            res = cls._find_part_by_mime(part, target_mime)
            if res:
                return res
        return ""

    @staticmethod
    def _clean_text(raw: str) -> str:
        if not raw:
            return ""
        text = raw
        # If text contains HTML tags
        if "<" in text and ">" in text:
            # Strip script, style, and head blocks
            text = re.sub(r"<(script|style|head)[^>]*>[\s\S]*?</\1>", "", text, flags=re.IGNORECASE)
            # Convert breaks and paragraphs to line breaks
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</?(p|div|tr|li|h[1-6]|blockquote|table)[^>]*>", "\n", text, flags=re.IGNORECASE)
            # Simplify hyperlinks: <a href="url">text</a> -> text
            def link_replace(match):
                href = match.group(1).strip()
                label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                if not label or label.lower() == href.lower():
                    # If label is just the raw link, keep it clean or truncate if massive tracking link
                    return href if len(href) < 60 else "[link]"
                if len(href) > 70 or any(k in href.lower() for k in ["track", "click", "token", "utm_"]):
                    return label
                return f"{label} ({href})"
            text = re.sub(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', link_replace, text, flags=re.IGNORECASE | re.DOTALL)
            # Strip any remaining tags
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(text)

        # Clean unicode spaces
        text = text.replace("\xa0", " ").replace("&nbsp;", " ")
        # Clean up lines and excessive blank lines or massive tracking URLs
        lines = [l.strip() for l in text.splitlines()]
        clean_lines = []
        for line in lines:
            if line:
                # If an entire line is a single giant URL > 90 characters
                if (line.startswith("http://") or line.startswith("https://")) and len(line) > 85:
                    clean_lines.append(line[:65] + "... [link]")
                else:
                    clean_lines.append(line)
            elif clean_lines and clean_lines[-1] != "":
                clean_lines.append("")
        return "\n".join(clean_lines).strip()

    @classmethod
    def _extract_message_body(cls, payload: Dict[str, Any]) -> str:
        # 1. Look for text/plain in parts tree first
        plain_text = cls._find_part_by_mime(payload, "text/plain")
        if plain_text and len(plain_text.strip()) > 5:
            return cls._clean_text(plain_text)

        # 2. Look for text/html in parts tree
        html_text = cls._find_part_by_mime(payload, "text/html")
        if html_text:
            return cls._clean_text(html_text)

        # 3. Fallback: check top-level body data
        if "body" in payload and payload["body"].get("data"):
            data = payload["body"]["data"]
            raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            return cls._clean_text(raw)

        return ""


workspace_service = WorkspaceService()
