"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  Mail,
  FileText,
  Table,
  Send,
  CheckCircle2,
  Clock,
  RefreshCw,
  Play,
  ExternalLink,
  Search,
  Plus,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Check,
  Wand2,
  Circle,
  HelpCircle,
  Lock,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type WorkspaceMode = "sandbox" | "live";
type PriorityTier = "P0 - Critical" | "P1 - High" | "P2 - Medium" | "P3 - Low";
type InquiryStatus = "Untriaged" | "Triaging" | "Needs Approval" | "Resolved";

interface ExtractedEntities {
  sender_name: string;
  sender_email: string;
  organization: string;
  monetary_amount: number | null;
  currency: string;
  deadline_iso: string | null;
  reference_ids: string[];
  key_summary: string;
}

interface SOPMatch {
  doc_id: string;
  title: string;
  drive_url: string;
  matched_section: string;
  policy_excerpt: string;
  relevance_score: number;
}

interface TraceStep {
  step_number: number;
  tool_name: string;
  title: string;
  status: "running" | "completed" | "error";
  started_at: string;
  duration_ms: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  summary: string;
}

interface TrackingRow {
  row_id: string;
  sheet_row_number: number;
  inquiry_id: string;
  received_at: string;
  sender_email: string;
  organization: string;
  subject: string;
  intent_category: string;
  priority_tier: string;
  monetary_amount: string;
  deadline: string;
  matched_sop: string;
  status: string;
  resolved_at: string | null;
  sheet_url: string;
}

interface InboundInquiry {
  id: string;
  thread_id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  organization: string;
  received_at: string;
  body: string;
  status: InquiryStatus;
  intent_category?: string;
  priority_tier?: PriorityTier;
  confidence_score?: number;
  classification_rationale?: string;
  entities?: ExtractedEntities;
  matched_sops: SOPMatch[];
  execution_trace: TraceStep[];
  tracking_row_id?: string;
  sheet_row_number?: number;
  draft_reply?: string;
  sent_reply?: string;
  ai_summary?: string;
  resolved_at?: string;
  triage_latency_ms?: number;
  source_mode: WorkspaceMode;
}

interface KPIs {
  total_inquiries: number;
  untriaged_count: number;
  needs_approval_count: number;
  resolved_count: number;
  urgent_p0_p1_count: number;
  sheet_rows_logged: number;
  avg_triage_latency_ms: number;
}

function cleanEmailDisplay(raw?: string): string {
  if (!raw) return "";
  let text = raw;
  if (/<[a-z][\s\S]*>/i.test(text)) {
    text = text.replace(/<(script|style|head)[^>]*>[\s\S]*?<\/\1>/gi, "");
    text = text.replace(/<br\s*\/?>/gi, "\n");
    text = text.replace(
      /<\/?(p|div|tr|li|h[1-6]|table|blockquote)[^>]*>/gi,
      "\n",
    );
    text = text.replace(
      /<a\s+(?:[^>]*?\s+)?href=["']([^"']*)["'][^>]*>(.*?)<\/a>/gi,
      (_, href, label) => {
        const cleanLabel = label.replace(/<[^>]+>/g, "").trim();
        if (!cleanLabel || cleanLabel.toLowerCase() === href.toLowerCase()) {
          return href.length < 50 ? href : "[link]";
        }
        return `${cleanLabel} (${href.length < 60 ? href : "[link]"})`;
      },
    );
    text = text.replace(/<[^>]+>/g, " ");
  }
  text = text
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");

  const lines = text.split("\n").map((l) => l.trim());
  const cleanLines: string[] = [];
  for (const line of lines) {
    if (line) {
      if (
        (line.startsWith("http://") || line.startsWith("https://")) &&
        line.length > 80
      ) {
        cleanLines.push(line.slice(0, 60) + "... [link]");
      } else {
        cleanLines.push(line);
      }
    } else if (
      cleanLines.length > 0 &&
      cleanLines[cleanLines.length - 1] !== ""
    ) {
      cleanLines.push("");
    }
  }
  return cleanLines.join("\n").trim();
}

export default function OpsTriageCommandCenter() {
  const [mode, setMode] = useState<WorkspaceMode>("sandbox");
  const [oauthConnected, setOauthConnected] = useState(false);
  const [driveFolderUrl, setDriveFolderUrl] = useState(
    "https://drive.google.com/drive/u/0/folders/1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU",
  );
  const [sheetUrl, setSheetUrl] = useState(
    "https://docs.google.com/spreadsheets/d/1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek/edit#gid=0",
  );

  const [inquiries, setInquiries] = useState<InboundInquiry[]>([]);
  const [trackingRows, setTrackingRows] = useState<TrackingRow[]>([]);
  const [kpis, setKpis] = useState<KPIs>({
    total_inquiries: 5,
    untriaged_count: 3,
    needs_approval_count: 1,
    resolved_count: 1,
    urgent_p0_p1_count: 1,
    sheet_rows_logged: 2,
    avg_triage_latency_ms: 2150,
  });

  const [selectedId, setSelectedId] = useState<string>("inq-1001");
  const [statusFilter, setStatusFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>(
    {},
  );
  const [showOriginalEmail, setShowOriginalEmail] = useState<boolean>(true);

  // Right Drawer states
  const [editableDraft, setEditableDraft] = useState<string>("");
  const [regenPrompt, setRegenPrompt] = useState<string>("");
  const [isTriaging, setIsTriaging] = useState<boolean>(false);
  const [isRegenerating, setIsRegenerating] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isSummarizing, setIsSummarizing] = useState<boolean>(false);
  const [isSyncingGmail, setIsSyncingGmail] = useState<boolean>(false);
  const [summaryMap, setSummaryMap] = useState<Record<string, string>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals
  const [showSheetModal, setShowSheetModal] = useState<boolean>(false);
  const [showNewEmailModal, setShowNewEmailModal] = useState<boolean>(false);
  const [showGuideModal, setShowGuideModal] = useState<boolean>(false);
  const [adminEmail, setAdminEmail] = useState<string>("ak8757796@gmail.com");
  const [showAdminModal, setShowAdminModal] = useState<boolean>(false);
  const [adminPasskey, setAdminPasskey] = useState<string>("");
  const [adminPasskeyError, setAdminPasskeyError] = useState<string>("");
  const [isAdminUnlocked, setIsAdminUnlocked] = useState<boolean>(false);

  // New custom inquiry form
  const [newSubject, setNewSubject] = useState(
    "CRITICAL: Enterprise Invoice #INV-2026-9910 Overbilling ($18,200.00)",
  );
  const [newSenderName, setNewSenderName] = useState("Sophia Chen");
  const [newSenderEmail, setNewSenderEmail] = useState(
    "s.chen@nexus-robotics.ai",
  );
  const [newOrg, setNewOrg] = useState("Nexus Robotics Corp");
  const [newBody, setNewBody] = useState(
    "Hi Operations & Billing Team,\n\nWe noticed an unexpected duplicate wire charge of $18,200.00 USD on Invoice #INV-2026-9910 (Wire Ref #ACH-77123). Our fiscal quarter closes on 2026-11-20. Please issue a Credit Memo and initiate an expedited refund per our enterprise agreement.\n\nBest,\nSophia Chen\nVP Finance, Nexus Robotics Corp",
  );

  const selectedInquiry =
    inquiries.find((i) => i.id === selectedId) || inquiries[0] || null;

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 4000);
  }, []);

  const fetchAllData = useCallback(async () => {
    try {
      const [statusRes, inqRes, rowsRes] = await Promise.all([
        fetch(`${API_BASE}/api/status`),
        fetch(`${API_BASE}/api/inquiries`),
        fetch(`${API_BASE}/api/sheets/rows`),
      ]);
      if (statusRes.ok) {
        const st = await statusRes.json();
        setMode(st.mode);
        setOauthConnected(Boolean(st.oauth_connected));
        if (st.admin_email) setAdminEmail(st.admin_email);
        if (st.drive_folder_url) setDriveFolderUrl(st.drive_folder_url);
        if (st.sheets_tracker_url) setSheetUrl(st.sheets_tracker_url);
        if (st.kpis) setKpis(st.kpis);
      }
      if (inqRes.ok) {
        const data = await inqRes.json();
        const rawList: InboundInquiry[] = data.inquiries || [];
        const uniqueInquiries = Array.from(
          new Map(rawList.map((item) => [item.id, item])).values(),
        );
        setInquiries(uniqueInquiries);
        if (data.kpis) setKpis(data.kpis);
      }
      if (rowsRes.ok) {
        const rData = await rowsRes.json();
        const rawRows: TrackingRow[] = rData.rows || [];
        const uniqueRows = Array.from(
          new Map(rawRows.map((r) => [r.row_id, r])).values(),
        );
        setTrackingRows(uniqueRows);
      }
    } catch (err) {
      console.error("Failed to fetch OpsTriage state:", err);
    }
  }, []);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Handle Google OAuth callback parameters on return
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const isConnected =
        params.get("oauth") === "connected" || params.get("mode") === "live";
      const oauthErr = params.get("oauth") === "error";

      if (isConnected) {
        setIsAdminUnlocked(true);
        setMode("live");
        setOauthConnected(true);
        showToast(`Connected to Live Google Workspace (${adminEmail})`);
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname,
        );
        fetchAllData();
      } else if (oauthErr) {
        const reason =
          params.get("reason") || "OAuth authorization was denied or failed.";
        showToast(`OAuth Notice: ${reason}`);
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname,
        );
      }
    }
  }, [adminEmail, fetchAllData, showToast]);

  useEffect(() => {
    if (selectedInquiry) {
      setEditableDraft(
        selectedInquiry.sent_reply || selectedInquiry.draft_reply || "",
      );
    }
  }, [
    selectedInquiry?.id,
    selectedInquiry?.draft_reply,
    selectedInquiry?.sent_reply,
  ]);

  const handleToggleMode = async (targetMode: WorkspaceMode) => {
    if (targetMode === "live" && !oauthConnected && !isAdminUnlocked) {
      setShowAdminModal(true);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: targetMode }),
      });
      if (res.ok) {
        setMode(targetMode);
        await fetchAllData();
        showToast(
          targetMode === "sandbox"
            ? "Live Sandbox Mode active (pre-loaded enterprise inquiries)"
            : oauthConnected
              ? `Live Google Workspace active (${adminEmail})`
              : "Live Mode selected — click 'Connect Google' to authorize",
        );
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAdminVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdminPasskeyError("");
    try {
      const res = await fetch(`${API_BASE}/api/auth/admin/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passkey: adminPasskey }),
      });
      if (res.ok) {
        setIsAdminUnlocked(true);
        setShowAdminModal(false);
        setAdminPasskeyError("");
        showToast(
          `Administrator verified. Connecting Google for ${adminEmail}...`,
        );
        handleConnectGoogleOAuth();
      } else {
        const errData = await res.json().catch(() => null);
        const errMsg = errData?.detail || "Incorrect passkey.";
        setAdminPasskeyError(errMsg);
        showToast(errMsg);
      }
    } catch {
      const netErr = "Could not reach backend server on port 8000.";
      setAdminPasskeyError(netErr);
      showToast(netErr);
    }
  };

  const handleConnectGoogleOAuth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/google/url`);
      if (res.ok) {
        const { auth_url } = await res.json();
        window.location.href = auth_url;
      }
    } catch {
      showToast("Could not reach backend server on port 8000.");
    }
  };

  const handleRunTriage = async (inquiryId?: string) => {
    const targetId = inquiryId || selectedInquiry?.id;
    if (!targetId || isTriaging) return;

    setSelectedId(targetId);
    setIsTriaging(true);

    setInquiries((prev) =>
      prev.map((inq) =>
        inq.id === targetId
          ? { ...inq, status: "Triaging", execution_trace: [] }
          : inq,
      ),
    );

    try {
      const evtSource = new EventSource(
        `${API_BASE}/api/inquiries/${targetId}/triage/stream`,
      );

      const safetyTimer = setTimeout(async () => {
        try {
          evtSource.close();
        } catch {}
        setIsTriaging(false);
        await fetchAllData();
      }, 14000);

      evtSource.addEventListener("step.start", (e: MessageEvent) => {
        const step: TraceStep = JSON.parse(e.data);
        setInquiries((prev) =>
          prev.map((inq) => {
            if (inq.id !== targetId) return inq;
            const filtered = inq.execution_trace.filter(
              (s) => s.step_number !== step.step_number,
            );
            return { ...inq, execution_trace: [...filtered, step] };
          }),
        );
      });

      evtSource.addEventListener("step.completed", (e: MessageEvent) => {
        const step: TraceStep = JSON.parse(e.data);
        setInquiries((prev) =>
          prev.map((inq) => {
            if (inq.id !== targetId) return inq;
            const filtered = inq.execution_trace.filter(
              (s) => s.step_number !== step.step_number,
            );
            return { ...inq, execution_trace: [...filtered, step] };
          }),
        );
      });

      evtSource.addEventListener(
        "triage.completed",
        async (e: MessageEvent) => {
          clearTimeout(safetyTimer);
          const updatedInquiry: InboundInquiry = JSON.parse(e.data);
          setInquiries((prev) =>
            prev.map((inq) => (inq.id === targetId ? updatedInquiry : inq)),
          );
          setEditableDraft(updatedInquiry.draft_reply || "");
          evtSource.close();
          setIsTriaging(false);
          await fetchAllData();
          showToast(
            `Triage complete — Logged Row #${updatedInquiry.sheet_row_number} to Google Sheet`,
          );
        },
      );

      evtSource.onerror = async () => {
        clearTimeout(safetyTimer);
        evtSource.close();
        setIsTriaging(false);
        await fetchAllData();
      };
    } catch (err) {
      console.error(err);
      setIsTriaging(false);
    }
  };

  const handleRegenerateDraft = async () => {
    if (!selectedInquiry || !regenPrompt.trim() || isRegenerating) return;
    setIsRegenerating(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/inquiries/${selectedInquiry.id}/regenerate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            instructions: regenPrompt,
            current_draft: editableDraft,
          }),
        },
      );
      if (res.ok) {
        const data = await res.json();
        const updatedDraft = data.draft_reply || "";
        setEditableDraft(updatedDraft);
        setInquiries((prev) =>
          prev.map((i) =>
            i.id === selectedInquiry.id
              ? { ...i, draft_reply: updatedDraft }
              : i,
          ),
        );
        setRegenPrompt("");
        showToast("Email draft refined successfully.");
      } else {
        showToast("Could not refine draft.");
      }
    } catch {
      showToast("Refinement error. Please try again.");
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleApproveAndSend = async () => {
    if (!selectedInquiry || !editableDraft.trim() || isApproving) return;
    setIsApproving(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/inquiries/${selectedInquiry.id}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            final_reply_body: editableDraft,
          }),
        },
      );
      if (res.ok) {
        const data = await res.json();
        setInquiries((prev) =>
          prev.map((i) => (i.id === selectedInquiry.id ? data.inquiry : i)),
        );
        if (data.rows) setTrackingRows(data.rows);
        if (data.kpis) setKpis(data.kpis);
        showToast(
          `Email sent & Sheet Row #${
            selectedInquiry.sheet_row_number || 2
          } marked Resolved`,
        );
      }
    } finally {
      setIsApproving(false);
    }
  };

  const handleCreateCustomInquiry = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_BASE}/api/inquiries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject: newSubject,
        sender_name: newSenderName,
        sender_email: newSenderEmail,
        organization: newOrg,
        body: newBody,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      const created: InboundInquiry = data.inquiry;
      await fetchAllData();
      setSelectedId(created.id);
      setShowNewEmailModal(false);
      setTimeout(() => handleRunTriage(created.id), 250);
    }
  };

  const handleSummarizeEmail = async () => {
    if (!selectedInquiry || isSummarizing) return;
    setIsSummarizing(true);
    setShowOriginalEmail(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);
    try {
      const res = await fetch(
        `${API_BASE}/api/inquiries/${selectedInquiry.id}/summarize`,
        { method: "POST", signal: controller.signal },
      );
      if (res.ok) {
        const data = await res.json();
        const textSummary: string = data.summary || "";
        setSummaryMap((prev) => ({
          ...prev,
          [selectedInquiry.id]: textSummary,
        }));
        setInquiries((prev) =>
          prev.map((i) =>
            i.id === selectedInquiry.id ? { ...i, ai_summary: textSummary } : i,
          ),
        );
        showToast("Summary updated!");
      }
    } catch {
      showToast("Could not generate summary.");
    } finally {
      clearTimeout(timer);
      setIsSummarizing(false);
    }
  };

  const handleSyncGmail = async () => {
    if (isSyncingGmail) return;
    setIsSyncingGmail(true);
    try {
      const res = await fetch(`${API_BASE}/api/gmail/sync?limit=50`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        const rawList: InboundInquiry[] = data.inquiries || [];
        const uniqueInquiries = Array.from(
          new Map(rawList.map((item) => [item.id, item])).values(),
        );
        setInquiries(uniqueInquiries);
        if (data.kpis) setKpis(data.kpis);
        showToast(
          `Synced ${uniqueInquiries.length} emails from your Gmail inbox!`,
        );
      }
    } catch {
      showToast("Could not sync Gmail inbox.");
    } finally {
      setIsSyncingGmail(false);
    }
  };

  const handleResetSandbox = async () => {
    const res = await fetch(`${API_BASE}/api/sandbox/reset`, {
      method: "POST",
    });
    if (res.ok) {
      await fetchAllData();
      setSelectedId("inq-1001");
      showToast("Sandbox data reset.");
    }
  };

  const filteredInquiries = inquiries.filter((inq) => {
    const matchesStatus = statusFilter === "All" || inq.status === statusFilter;
    const matchesSearch =
      !searchQuery.trim() ||
      inq.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inq.organization.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inq.sender_email.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const priorityPill = (tier?: PriorityTier) => {
    if (!tier) return null;
    const short = tier.split(" - ")[0];
    const styles =
      short === "P0"
        ? "bg-red-500/15 text-red-400 border-red-500/30"
        : short === "P1"
          ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
          : "bg-slate-800 text-slate-300 border-slate-700";
    return (
      <span
        className={`text-[11px] font-medium px-1.5 py-0.5 rounded border ${styles}`}
      >
        {short}
      </span>
    );
  };

  return (
    <div className="h-screen flex flex-col bg-[#0b0f17] text-slate-100 overflow-hidden">
      {/* Subtle Toast */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-[9999] flex items-center gap-2 bg-slate-900 border border-slate-700 text-slate-100 px-4 py-2.5 rounded-lg shadow-2xl text-xs font-medium">
          <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* =====================================================================
          CLEAN SINGLE TOP BAR (Linear / Front Inspired)
      ===================================================================== */}
      <header className="h-14 border-b border-slate-800/80 bg-[#0f1522] px-5 flex items-center justify-between gap-4 shrink-0">
        {/* Left: Brand & Compact Live KPI Summary */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-sm tracking-tight text-white">
              OpsTriage AI
            </span>
          </div>

          {/* Inline Minimal KPI Bar */}
          <div className="hidden xl:flex items-center gap-4 text-xs text-slate-400 border-l border-slate-800 pl-6">
            <span>
              Queue:{" "}
              <strong className="text-slate-200">{kpis.total_inquiries}</strong>
            </span>
            <span>•</span>
            <span>
              Untriaged:{" "}
              <strong className="text-amber-400">{kpis.untriaged_count}</strong>
            </span>
            <span>•</span>
            <span>
              Needs Approval:{" "}
              <strong className="text-indigo-400">
                {kpis.needs_approval_count}
              </strong>
            </span>
            <span>•</span>
            <span>
              Resolved:{" "}
              <strong className="text-emerald-400">
                {kpis.resolved_count}
              </strong>
            </span>
            <span>•</span>
            <span>
              Avg Speed:{" "}
              <strong className="text-slate-200">
                {(kpis.avg_triage_latency_ms / 1000).toFixed(1)}s
              </strong>
            </span>
          </div>
        </div>

        {/* Right: Workspace Links, Sheet Drawer Button, and Mode Toggle */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowSheetModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 text-xs font-medium text-slate-200 transition"
          >
            <Table className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tracking Sheet ({kpis.sheet_rows_logged})</span>
          </button>

          <a
            href={driveFolderUrl}
            target="_blank"
            rel="noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-800/60 text-xs text-slate-400 hover:text-slate-200 transition"
          >
            <FileText className="w-3.5 h-3.5 text-sky-400" />
            <span>Drive SOPs</span>
            <ExternalLink className="w-3 h-3" />
          </a>

          {/* Sandbox vs Live OAuth Segmented Control */}
          <div className="flex items-center bg-slate-900 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={() => handleToggleMode("sandbox")}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                mode === "sandbox"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sandbox Mode
            </button>
            <button
              onClick={() => handleToggleMode("live")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition ${
                mode === "live"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  oauthConnected ? "bg-emerald-300" : "bg-amber-400"
                }`}
              />
              Live OAuth
            </button>
          </div>

          {mode === "live" && !oauthConnected && (
            <button
              onClick={handleConnectGoogleOAuth}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition"
            >
              Connect Google
            </button>
          )}

          <button
            onClick={() => setShowGuideModal(true)}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="How It Works / Step-by-Step Guide"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* =====================================================================
          THREE-PANEL WORKSPACE (Clean, Calm, Industry-Standard Layout)
      ===================================================================== */}
      <div className="flex-1 grid grid-cols-12 min-h-0">
        {/* -----------------------------------------------------------------
            PANEL 1 (3 COLS): INBOX QUEUE
        ----------------------------------------------------------------- */}
        <aside className="col-span-12 lg:col-span-3 border-r border-slate-800/80 bg-[#0d121c] flex flex-col min-h-0">
          <div className="p-3.5 border-b border-slate-800/80 space-y-2.5">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                1. Inbox Queue
              </h2>
              <div className="flex items-center gap-1">
                {mode === "live" ? (
                  <button
                    onClick={handleSyncGmail}
                    disabled={isSyncingGmail}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition disabled:opacity-50"
                    title="Sync up to 50 latest emails directly from your Gmail inbox"
                  >
                    <RefreshCw
                      className={`w-3 h-3 ${isSyncingGmail ? "animate-spin" : ""}`}
                    />
                    <span>
                      {isSyncingGmail ? "Syncing..." : "Sync Gmail (50)"}
                    </span>
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => setShowNewEmailModal(true)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      New Email
                    </button>
                    <button
                      onClick={handleResetSandbox}
                      className="p-1 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                      title="Reset Sample Data"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search emails..."
                className="w-full bg-slate-900 border border-slate-800 rounded-md pl-8 pr-3 py-1 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-slate-700"
              />
            </div>

            <div className="flex gap-1 text-[11px]">
              {["All", "Untriaged", "Needs Approval", "Resolved"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setStatusFilter(tab)}
                  className={`flex-1 py-1 rounded font-medium transition ${
                    statusFilter === tab
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab === "Needs Approval" ? "Approval" : tab}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/50">
            {filteredInquiries.map((inq) => {
              const active = selectedInquiry?.id === inq.id;
              return (
                <div
                  key={inq.id}
                  onClick={() => setSelectedId(inq.id)}
                  className={`p-3.5 cursor-pointer transition ${
                    active
                      ? "bg-slate-800/60 border-l-2 border-l-indigo-500"
                      : "hover:bg-slate-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-100 truncate">
                      {inq.organization}
                    </span>
                    <span
                      className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                        inq.status === "Resolved"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : inq.status === "Needs Approval"
                            ? "bg-indigo-500/15 text-indigo-300"
                            : "bg-amber-500/10 text-amber-300"
                      }`}
                    >
                      {inq.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-2 mb-2 leading-snug">
                    {inq.subject}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <div className="flex items-center gap-1.5">
                      {priorityPill(inq.priority_tier)}
                      {inq.intent_category && (
                        <span className="truncate max-w-[130px]">
                          {inq.intent_category}
                        </span>
                      )}
                    </div>
                    {inq.entities?.monetary_amount != null && (
                      <span className="font-mono text-slate-300">
                        ${inq.entities.monetary_amount.toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* -----------------------------------------------------------------
            PANEL 2 (5 COLS): EMAIL CONTEXT & AI AGENT TRACE
        ----------------------------------------------------------------- */}
        <main className="col-span-12 lg:col-span-5 border-r border-slate-800/80 bg-[#0b0f17] flex flex-col min-h-0">
          {selectedInquiry ? (
            <>
              {/* Top Action Header */}
              <div className="p-4 border-b border-slate-800/80 flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      2. AI Agent Triage
                    </span>
                    {priorityPill(selectedInquiry.priority_tier)}
                    {selectedInquiry.intent_category && (
                      <span className="text-xs text-indigo-300 font-medium">
                        • {selectedInquiry.intent_category}
                      </span>
                    )}
                  </div>
                  <h1 className="text-sm font-semibold text-white leading-snug">
                    {selectedInquiry.subject}
                  </h1>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedInquiry.sender_name} &lt;
                    {selectedInquiry.sender_email}&gt;
                  </p>
                </div>

                <button
                  onClick={() => handleRunTriage(selectedInquiry.id)}
                  disabled={isTriaging}
                  className="shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium shadow-sm transition"
                >
                  {isTriaging ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Running Triage...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      {selectedInquiry.status === "Untriaged"
                        ? "Run AI Triage"
                        : "Re-Run Triage"}
                    </>
                  )}
                </button>
              </div>

              {/* Scrollable Middle Workspace */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Incoming Email Card (Collapsible) */}
                <div className="bg-[#111726] border border-slate-800/90 rounded-lg overflow-hidden">
                  <div className="w-full px-3.5 py-2.5 flex items-center justify-between text-xs font-medium text-slate-300">
                    <button
                      onClick={() => setShowOriginalEmail(!showOriginalEmail)}
                      className="flex items-center gap-2 hover:text-white transition"
                    >
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      <span>Incoming Email Message</span>
                      {showOriginalEmail ? (
                        <ChevronDown className="w-4 h-4 text-slate-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-500" />
                      )}
                    </button>

                    <button
                      onClick={handleSummarizeEmail}
                      disabled={isSummarizing}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-[11px] font-medium transition disabled:opacity-50"
                      title="Generate a clear executive summary and explanation"
                    >
                      {isSummarizing ? (
                        <>
                          <RefreshCw className="w-3 h-3 text-indigo-400 animate-spin" />
                          <span>Summarizing...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3 text-indigo-400" />
                          <span>
                            {summaryMap[selectedInquiry.id] ||
                            selectedInquiry.ai_summary
                              ? "Re-Summarize"
                              : "Summarize & Explain"}
                          </span>
                        </>
                      )}
                    </button>
                  </div>

                  {showOriginalEmail && (
                    <div className="px-3.5 pb-3.5 pt-1 border-t border-slate-800/60 space-y-3">
                      {/* Highlighted AI Summary Callout in clear paragraph form */}
                      {(summaryMap[selectedInquiry.id] ||
                        selectedInquiry.ai_summary) && (
                        <div className="bg-indigo-950/40 border border-indigo-500/30 rounded-lg p-3 space-y-1.5">
                          <div className="flex items-center justify-between text-xs font-semibold text-indigo-300">
                            <span className="flex items-center gap-1.5">
                              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                              AI Email Summary & Explanation
                            </span>
                            <span className="text-[10px] text-slate-400 font-normal">
                              Gemini
                            </span>
                          </div>
                          <p className="text-xs text-indigo-100/90 leading-relaxed font-sans">
                            {summaryMap[selectedInquiry.id] ||
                              selectedInquiry.ai_summary}
                          </p>
                        </div>
                      )}

                      {/* Cleaned plain-text email body without HTML or link clutter */}
                      <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                        {cleanEmailDisplay(selectedInquiry.body)}
                      </pre>
                    </div>
                  )}
                </div>

                {/* Unified Extracted Key Details & SOP Card */}
                {selectedInquiry.entities && (
                  <div className="bg-[#111726] border border-slate-800/90 rounded-lg p-3.5 space-y-3">
                    <div className="text-xs font-medium text-slate-400">
                      Extracted Entities & Policy Grounding
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-xs">
                      <div>
                        <span className="text-slate-500 block text-[11px]">
                          Amount
                        </span>
                        <span className="font-mono font-semibold text-slate-100">
                          {selectedInquiry.entities.monetary_amount != null
                            ? `$${selectedInquiry.entities.monetary_amount.toLocaleString()} ${
                                selectedInquiry.entities.currency
                              }`
                            : "None"}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[11px]">
                          Deadline
                        </span>
                        <span className="font-mono text-slate-200">
                          {selectedInquiry.entities.deadline_iso ||
                            "Standard SLA"}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[11px]">
                          References
                        </span>
                        <span className="font-mono text-slate-200 truncate block">
                          {selectedInquiry.entities.reference_ids.join(", ") ||
                            "—"}
                        </span>
                      </div>
                    </div>

                    {selectedInquiry.matched_sops[0] && (
                      <div className="pt-2.5 border-t border-slate-800/80 text-xs">
                        <div className="flex items-center justify-between text-sky-400 font-medium mb-1">
                          <span>
                            Matched SOP: {selectedInquiry.matched_sops[0].title}
                          </span>
                          <a
                            href={selectedInquiry.matched_sops[0].drive_url}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:underline flex items-center gap-1 text-[11px]"
                          >
                            Drive <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          {selectedInquiry.matched_sops[0].policy_excerpt}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Clean 5-Step Agent Execution Checklist */}
                <div className="bg-[#111726] border border-slate-800/90 rounded-lg p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-400">
                      Agent Execution Steps (
                      {selectedInquiry.execution_trace.length}/5)
                    </span>
                    {selectedInquiry.triage_latency_ms && (
                      <span className="text-[11px] text-slate-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {(selectedInquiry.triage_latency_ms / 1000).toFixed(2)}s
                      </span>
                    )}
                  </div>

                  {selectedInquiry.execution_trace.length === 0 ? (
                    <div className="py-6 text-center space-y-2">
                      <p className="text-xs text-slate-400">
                        This email has not been triaged yet.
                      </p>
                      <button
                        onClick={() => handleRunTriage(selectedInquiry.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
                      >
                        <Play className="w-3 h-3 fill-current" />
                        Run 5-Step AI Triage
                      </button>
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-800/60">
                      {Array.from(
                        new Map(
                          selectedInquiry.execution_trace.map((s) => [
                            s.step_number,
                            s,
                          ]),
                        ).values(),
                      ).map((step) => {
                        const open = Boolean(expandedSteps[step.step_number]);
                        return (
                          <div
                            key={`step-${selectedInquiry.id}-${step.step_number}`}
                            className="py-2 first:pt-0 last:pb-0"
                          >
                            <div
                              onClick={() =>
                                setExpandedSteps((p) => ({
                                  ...p,
                                  [step.step_number]: !p[step.step_number],
                                }))
                              }
                              className="flex items-start justify-between gap-2 cursor-pointer group"
                            >
                              <div className="flex items-start gap-2.5 min-w-0">
                                {step.status === "running" ? (
                                  <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin mt-0.5 shrink-0" />
                                ) : (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                                )}
                                <div className="min-w-0">
                                  <div className="text-xs font-medium text-slate-200 group-hover:text-white">
                                    {step.step_number}. {step.title}
                                  </div>
                                  <div className="text-[11px] text-slate-400 truncate">
                                    {step.summary}
                                  </div>
                                </div>
                              </div>

                              <span className="text-[10px] text-slate-500 group-hover:text-slate-300 shrink-0">
                                {open ? "Hide JSON" : "JSON"}
                              </span>
                            </div>

                            {open && (
                              <pre className="mt-2 p-2.5 rounded bg-slate-950 border border-slate-800 text-[10px] font-mono text-slate-300 overflow-x-auto">
                                {JSON.stringify(step.output_payload, null, 2)}
                              </pre>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : null}
        </main>

        {/* -----------------------------------------------------------------
            PANEL 3 (4 COLS): HUMAN-IN-THE-LOOP APPROVAL & REPLY
        ----------------------------------------------------------------- */}
        <section className="col-span-12 lg:col-span-4 bg-[#0d121c] flex flex-col min-h-0">
          <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                3. Review & Approve Reply
              </h2>
              <p className="text-xs text-slate-300 mt-0.5">
                To: {selectedInquiry?.sender_email}
              </p>
            </div>
            {selectedInquiry?.sheet_row_number && (
              <button
                onClick={() => setShowSheetModal(true)}
                className="text-[11px] font-mono px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700"
              >
                Sheet Row #{selectedInquiry.sheet_row_number}
              </button>
            )}
          </div>

          {selectedInquiry ? (
            <div className="flex-1 flex flex-col p-4 space-y-3 overflow-y-auto">
              <div className="flex-1 flex flex-col min-h-[240px]">
                <textarea
                  value={editableDraft}
                  onChange={(e) => setEditableDraft(e.target.value)}
                  placeholder="Click 'Run AI Triage' in the center panel to draft a policy-grounded response..."
                  className="flex-1 w-full bg-[#111726] border border-slate-800 focus:border-indigo-500 rounded-lg p-3.5 text-xs text-slate-100 leading-relaxed resize-none focus:outline-none"
                />
              </div>

              {/* Simple 1-Line AI Refinement Input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={regenPrompt}
                  onChange={(e) => setRegenPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleRegenerateDraft();
                    }
                  }}
                  placeholder="Ask AI to refine (e.g. 'apologize sincerely', 'offer 15% discount', 'make it shorter')..."
                  className="flex-1 bg-[#111726] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={handleRegenerateDraft}
                  disabled={isRegenerating || !regenPrompt.trim()}
                  className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:opacity-40 text-xs font-medium text-white flex items-center gap-1.5 transition"
                >
                  <Wand2
                    className={`w-3.5 h-3.5 ${isRegenerating ? "animate-spin text-white" : "text-indigo-200"}`}
                  />
                  {isRegenerating ? "Refining..." : "Refine"}
                </button>
              </div>

              {/* Primary CTA: Approve, Send & Resolve */}
              <button
                onClick={handleApproveAndSend}
                disabled={isApproving || !editableDraft.trim()}
                className={`w-full py-2.5 px-4 rounded-lg font-semibold text-xs flex items-center justify-center gap-2 transition ${
                  selectedInquiry.status === "Resolved"
                    ? "bg-emerald-600/20 border border-emerald-500/40 text-emerald-300"
                    : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm"
                } disabled:opacity-40`}
              >
                {isApproving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Sending & Updating Sheet...
                  </>
                ) : selectedInquiry.status === "Resolved" ? (
                  <>
                    <Check className="w-4 h-4" />
                    Sent & Marked Resolved in Sheet
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    Approve, Send Email & Mark Resolved
                  </>
                )}
              </button>
            </div>
          ) : null}
        </section>
      </div>

      {/* =====================================================================
          MODAL: LIVE GOOGLE SHEET TRACKING LEDGER
      ===================================================================== */}
      {showSheetModal && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-[#0f1522] border border-slate-800 rounded-xl max-w-4xl w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Table className="w-4 h-4 text-emerald-400" />
                  OpsTriage Tracking Sheet Rows
                </h3>
                <p className="text-xs text-slate-400">
                  Every triaged email logs a row here; approving an email flips
                  its status to Resolved.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href={sheetUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                >
                  Open Real Google Sheet <ExternalLink className="w-3 h-3" />
                </a>
                <button
                  onClick={() => setShowSheetModal(false)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="border border-slate-800 rounded-lg overflow-hidden max-h-[60vh] overflow-y-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-900 text-slate-400 border-b border-slate-800 text-[11px]">
                    <th className="py-2.5 px-3">Row</th>
                    <th className="py-2.5 px-3">Organization</th>
                    <th className="py-2.5 px-3">Category & Priority</th>
                    <th className="py-2.5 px-3">Amount</th>
                    <th className="py-2.5 px-3">Matched SOP</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {trackingRows.map((row) => (
                    <tr key={row.row_id} className="hover:bg-slate-900/50">
                      <td className="py-2.5 px-3 font-mono text-slate-300">
                        #{row.sheet_row_number}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-white">
                        {row.organization}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {row.intent_category} (
                        {row.priority_tier.split(" - ")[0]})
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-200">
                        {row.monetary_amount}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 truncate max-w-[200px]">
                        {row.matched_sop}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                            row.status === "Resolved"
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "bg-amber-500/15 text-amber-300"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          MODAL: CREATE / SIMULATE NEW EMAIL
      ===================================================================== */}
      {showNewEmailModal && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-[#0f1522] border border-slate-800 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-white">
                Simulate Incoming Email
              </h3>
              <button
                onClick={() => setShowNewEmailModal(false)}
                className="text-xs text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>

            <form
              onSubmit={handleCreateCustomInquiry}
              className="space-y-3 text-xs"
            >
              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-slate-400 mb-1">
                    Sender Name
                  </label>
                  <input
                    type="text"
                    required
                    value={newSenderName}
                    onChange={(e) => setNewSenderName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">
                    Organization
                  </label>
                  <input
                    type="text"
                    required
                    value={newOrg}
                    onChange={(e) => setNewOrg(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Sender Email
                </label>
                <input
                  type="email"
                  required
                  value={newSenderEmail}
                  onChange={(e) => setNewSenderEmail(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Subject</label>
                <input
                  type="text"
                  required
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Message Body
                </label>
                <textarea
                  rows={4}
                  required
                  value={newBody}
                  onChange={(e) => setNewBody(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewEmailModal(false)}
                  className="px-3 py-2 rounded-lg bg-slate-800 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
                >
                  Add & Auto-Triage
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =====================================================================
          MODAL: QUICK 3-STEP USER GUIDE
      ===================================================================== */}
      {showGuideModal && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-[#0f1522] border border-slate-800 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-white">
                How to Test OpsTriage AI (3 Simple Steps)
              </h3>
              <button
                onClick={() => setShowGuideModal(false)}
                className="text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
            <ol className="space-y-3 text-slate-300 list-decimal list-inside leading-relaxed">
              <li>
                <strong className="text-white">
                  Pick an Email (Left Panel):
                </strong>{" "}
                Click any email marked{" "}
                <span className="text-amber-300">Untriaged</span> (or click{" "}
                <strong>+ New Email</strong> to create your own).
              </li>
              <li>
                <strong className="text-white">
                  Run AI Triage (Center Panel):
                </strong>{" "}
                Click <strong>Run AI Triage</strong>. Watch the 5 steps complete
                live: classifying priority, extracting dollar amounts/deadlines,
                matching a Google Drive SOP, logging a Google Sheet row, and
                drafting a reply.
              </li>
              <li>
                <strong className="text-white">
                  Approve & Send (Right Panel):
                </strong>{" "}
                Review or edit the drafted reply on the right, then click{" "}
                <strong className="text-emerald-400">
                  Approve, Send Email & Mark Resolved
                </strong>
                . Click <strong>Tracking Sheet</strong> in the top bar to see
                the row status flip to <em>Resolved</em>!
              </li>
            </ol>
          </div>
        </div>
      )}

      {/* =====================================================================
          MODAL: ADMIN OAUTH & PORTFOLIO PRIVACY PROTECTION
      ===================================================================== */}
      {showAdminModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f1522] border border-indigo-500/30 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl text-xs">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <Lock className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Administrator Access Required
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Live Google Workspace Mode Protection
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAdminModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-slate-300 space-y-2 leading-relaxed">
              <p>
                Live Mode connects to real-time Gmail, Drive SOPs, and Google
                Sheets for:
              </p>
              <div className="font-mono text-emerald-400 bg-black/40 px-2.5 py-1.5 rounded text-[11px] border border-emerald-500/20 flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>{adminEmail}</span>
              </div>
              <p className="text-[11px] text-slate-400">
                To protect private email security and prevent unintended inbox
                modifications on public portfolio deployments, Live OAuth is
                restricted strictly to the administrator.
              </p>
            </div>

            {/* Recruiter / Portfolio Visitor recommendation */}
            <div className="space-y-2">
              <button
                onClick={() => {
                  setShowAdminModal(false);
                  handleToggleMode("sandbox");
                }}
                className="w-full py-2.5 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center justify-center gap-2 transition"
              >
                <Sparkles className="w-3.5 h-3.5 text-white" />
                <span>Continue in Live Sandbox Mode (Recruiters)</span>
              </button>
              <p className="text-[10px] text-center text-slate-500">
                Sandbox Mode provides 100% full interactive AI triage, SOP
                matching, and refinement without exposing personal accounts.
              </p>
            </div>

            {/* Admin verification form */}
            <form
              onSubmit={handleAdminVerify}
              className="pt-3 border-t border-slate-800 space-y-2.5"
            >
              <label className="block text-[11px] font-medium text-slate-300">
                Project Owner Passkey:
              </label>

              {adminPasskeyError && (
                <div className="bg-rose-950/80 border border-rose-500/50 text-rose-200 px-3 py-2 rounded-lg text-[11px] flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-400 shrink-0" />
                  <span>{adminPasskeyError}</span>
                </div>
              )}

              <div className="flex gap-2">
                <input
                  type="password"
                  value={adminPasskey}
                  onChange={(e) => {
                    setAdminPasskey(e.target.value);
                    if (adminPasskeyError) setAdminPasskeyError("");
                  }}
                  placeholder="Enter passkey..."
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={!adminPasskey.trim()}
                  className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:opacity-40 text-xs font-medium text-white transition"
                >
                  Verify
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
