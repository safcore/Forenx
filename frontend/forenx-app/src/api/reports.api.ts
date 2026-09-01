import apiClient from "@/api/client"
import { downloadEvidenceReport } from "@/api/evidence.api"

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

export interface ReportListItem {
  id: string
  case: string
  evidence: string
  case_title: string
  evidence_filename: string
  report_id: string
  report_type: string
  title: string
  has_json: boolean
  has_pdf: boolean
  generated_by: string
  generated_by_username: string
  created_at: string
}

function normalizeReportListItem(raw: Record<string, unknown>): ReportListItem {
  return {
    id: String(raw.id ?? ""),
    case: String(raw.case ?? ""),
    evidence: String(raw.evidence ?? ""),
    case_title: String(raw.case_title ?? ""),
    evidence_filename: String(raw.evidence_filename ?? ""),
    report_id: String(raw.report_id ?? ""),
    report_type: String(raw.report_type ?? ""),
    title: String(raw.title ?? ""),
    has_json: Boolean(raw.has_json),
    has_pdf: Boolean(raw.has_pdf),
    generated_by: String(raw.generated_by ?? ""),
    generated_by_username: String(raw.generated_by_username ?? ""),
    created_at: String(raw.created_at ?? ""),
  }
}

/** GET /api/reports/ — read-only list (does not generate reports). */
export async function listReports(): Promise<ReportListItem[]> {
  const { data } = await apiClient.get("/reports/")
  const payload = unwrapSuccess<unknown>(data)
  if (!Array.isArray(payload)) return []
  return payload.map((item) =>
    normalizeReportListItem(item as Record<string, unknown>)
  )
}

export { downloadEvidenceReport }
