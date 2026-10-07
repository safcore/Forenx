import apiClient from "@/api/client"

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

export interface CustodyListItem {
  id: string
  event_id: string
  action: string
  actor_id: string
  actor_role: string
  source: string
  timestamp: string | null
  description: string
  evidence: string
  evidence_filename?: string
  case: string
  case_title?: string
  metadata?: Record<string, unknown>
  evidence_sha256?: string
}

function normalizeCustodyListItem(raw: Record<string, unknown>): CustodyListItem {
  return {
    id: String(raw.id ?? raw.event_id ?? ""),
    event_id: String(raw.event_id ?? ""),
    action: String(raw.action ?? ""),
    actor_id: String(raw.actor_id ?? ""),
    actor_role: String(raw.actor_role ?? ""),
    source: String(raw.source ?? ""),
    timestamp: raw.timestamp ? String(raw.timestamp) : null,
    description: String(raw.description ?? ""),
    evidence: String(raw.evidence ?? ""),
    evidence_filename: raw.evidence_filename
      ? String(raw.evidence_filename)
      : undefined,
    case: String(raw.case ?? ""),
    case_title: raw.case_title ? String(raw.case_title) : undefined,
    metadata:
      raw.metadata && typeof raw.metadata === "object"
        ? (raw.metadata as Record<string, unknown>)
        : undefined,
    evidence_sha256: raw.evidence_sha256
      ? String(raw.evidence_sha256)
      : undefined,
  }
}

/** GET /api/custody/ — read-only list. Does not create custody events. */
export async function listCustodyEvents(
  caseId?: string
): Promise<CustodyListItem[]> {
  const { data } = await apiClient.get("/custody/", {
    params: caseId ? { case_id: caseId } : undefined,
  })
  const payload = unwrapSuccess<unknown>(data)
  if (!Array.isArray(payload)) return []
  return payload.map((item) =>
    normalizeCustodyListItem(item as Record<string, unknown>)
  )
}

/** GET /api/custody/verify/ — verify cryptographic custody chain integrity. */
export async function verifyCustodyChain(caseId?: string): Promise<{
  valid: boolean
  status: "VALID" | "INVALID"
  message: string
  event_count: number
  verified_chains: number
  broken_chains: Array<Record<string, unknown>>
}> {
  const { data } = await apiClient.get("/custody/verify/", {
    params: caseId ? { case_id: caseId } : undefined,
  })
  return unwrapSuccess(data)
}
