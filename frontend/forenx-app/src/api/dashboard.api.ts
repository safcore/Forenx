import apiClient from "@/api/client"
import { normalizeCase } from "@/api/cases.api"
import type { Case, CasePriority } from "@/types"

function unwrapSuccess<T>(payload: unknown): T {
  if (
    payload &&
    typeof payload === "object" &&
    "success" in payload &&
    "data" in payload
  ) {
    return (payload as { data: T }).data
  }
  return payload as T
}

export interface DashboardRecentEvidence {
  id: string
  case_id: string
  original_filename: string
  file_size: number
  created_at: string
  acquisition_timestamp?: string
}

export interface DashboardRecentAnalysis {
  id: string
  analysis_type: string
  status: string
  result_summary: string
  created_at: string | null
  created_by_username: string
  evidence: string
  evidence_filename?: string
  case_title?: string
}

export interface DashboardRecentCustody {
  id: string
  action: string
  actor_id: string
  actor_role: string
  timestamp: string | null
  description: string
  evidence_filename?: string
  case_title?: string
  metadata?: Record<string, unknown>
}

export interface DashboardRecentReport {
  id: string
  report_id: string
  title: string
  case_title?: string
  evidence_filename?: string
  created_at: string
  generated_by_username?: string
}

export interface DashboardSummary {
  total_cases: number
  open_cases: number
  closed_cases: number
  total_evidence: number
  reports_generated: number
  storage_bytes: number
  priority_counts: Record<CasePriority, number>
  recent_cases: Case[]
  recent_evidence: DashboardRecentEvidence[]
  recent_analysis: DashboardRecentAnalysis[]
  recent_timeline: DashboardRecentAnalysis[]
  recent_custody: DashboardRecentCustody[]
  recent_reports: DashboardRecentReport[]
  total_analysis_runs: number
  total_custody_events: number
  analysis_counts: Record<string, number>
  custody_counts: Record<string, number>
  evidence_type_counts: Record<string, number>
}

function normalizeEvidenceRow(raw: Record<string, unknown>): DashboardRecentEvidence {
  return {
    id: String(raw.id ?? ""),
    case_id: String(raw.case_id ?? raw.case ?? ""),
    original_filename: String(raw.original_filename ?? ""),
    file_size: Number(raw.file_size ?? 0),
    created_at: String(raw.created_at ?? ""),
    acquisition_timestamp: raw.acquisition_timestamp
      ? String(raw.acquisition_timestamp)
      : undefined,
  }
}

function normalizeAnalysisRow(raw: Record<string, unknown>): DashboardRecentAnalysis {
  return {
    id: String(raw.id ?? ""),
    analysis_type: String(raw.analysis_type ?? ""),
    status: String(raw.status ?? ""),
    result_summary: String(raw.result_summary ?? ""),
    created_at: raw.created_at ? String(raw.created_at) : null,
    created_by_username: String(raw.created_by_username ?? ""),
    evidence: String(raw.evidence ?? ""),
    evidence_filename: raw.evidence_filename
      ? String(raw.evidence_filename)
      : undefined,
    case_title: raw.case_title ? String(raw.case_title) : undefined,
  }
}

function normalizeCustodyRow(raw: Record<string, unknown>): DashboardRecentCustody {
  return {
    id: String(raw.id ?? ""),
    action: String(raw.action ?? ""),
    actor_id: String(raw.actor_id ?? ""),
    actor_role: String(raw.actor_role ?? ""),
    timestamp: raw.timestamp ? String(raw.timestamp) : null,
    description: String(raw.description ?? ""),
    evidence_filename: raw.evidence_filename
      ? String(raw.evidence_filename)
      : undefined,
    case_title: raw.case_title ? String(raw.case_title) : undefined,
    metadata:
      raw.metadata && typeof raw.metadata === "object"
        ? (raw.metadata as Record<string, unknown>)
        : undefined,
  }
}

function asCountMap(raw: unknown): Record<string, number> {
  if (!raw || typeof raw !== "object") return {}
  const out: Record<string, number> = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    out[key] = Number(value ?? 0)
  }
  return out
}

function normalizeReportRow(raw: Record<string, unknown>): DashboardRecentReport {
  return {
    id: String(raw.id ?? ""),
    report_id: String(raw.report_id ?? ""),
    title: String(raw.title ?? ""),
    case_title: raw.case_title ? String(raw.case_title) : undefined,
    evidence_filename: raw.evidence_filename
      ? String(raw.evidence_filename)
      : undefined,
    created_at: String(raw.created_at ?? ""),
    generated_by_username: raw.generated_by_username
      ? String(raw.generated_by_username)
      : undefined,
  }
}

/** GET /api/dashboard/ — read-only live aggregates. */
export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await apiClient.get("/dashboard/")
  const raw = unwrapSuccess<Record<string, unknown>>(data)
  const priorityRaw =
    (raw.priority_counts as Record<string, number> | undefined) ?? {}

  return {
    total_cases: Number(raw.total_cases ?? 0),
    open_cases: Number(raw.open_cases ?? 0),
    closed_cases: Number(raw.closed_cases ?? 0),
    total_evidence: Number(raw.total_evidence ?? 0),
    reports_generated: Number(raw.reports_generated ?? 0),
    total_analysis_runs: Number(raw.total_analysis_runs ?? 0),
    total_custody_events: Number(raw.total_custody_events ?? 0),
    storage_bytes: Number(raw.storage_bytes ?? 0),
    priority_counts: {
      critical: Number(priorityRaw.critical ?? 0),
      high: Number(priorityRaw.high ?? 0),
      medium: Number(priorityRaw.medium ?? 0),
      low: Number(priorityRaw.low ?? 0),
    },
    analysis_counts: asCountMap(raw.analysis_counts),
    custody_counts: asCountMap(raw.custody_counts),
    evidence_type_counts: asCountMap(raw.evidence_type_counts),
    recent_cases: Array.isArray(raw.recent_cases)
      ? raw.recent_cases.map((item) =>
          normalizeCase(item as Record<string, unknown>)
        )
      : [],
    recent_evidence: Array.isArray(raw.recent_evidence)
      ? raw.recent_evidence.map((item) =>
          normalizeEvidenceRow(item as Record<string, unknown>)
        )
      : [],
    recent_analysis: Array.isArray(raw.recent_analysis)
      ? raw.recent_analysis.map((item) =>
          normalizeAnalysisRow(item as Record<string, unknown>)
        )
      : [],
    recent_timeline: Array.isArray(raw.recent_timeline)
      ? raw.recent_timeline.map((item) =>
          normalizeAnalysisRow(item as Record<string, unknown>)
        )
      : [],
    recent_custody: Array.isArray(raw.recent_custody)
      ? raw.recent_custody.map((item) =>
          normalizeCustodyRow(item as Record<string, unknown>)
        )
      : [],
    recent_reports: Array.isArray(raw.recent_reports)
      ? raw.recent_reports.map((item) =>
          normalizeReportRow(item as Record<string, unknown>)
        )
      : [],
  }
}
