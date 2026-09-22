import apiClient from "@/api/client"
import type { Case, CasePriority, CaseStatus } from "@/types"

export interface CaseListParams {
  search?: string
  status?: CaseStatus
  priority?: CasePriority
  ordering?: string
  page?: number
  page_size?: number
}

export interface CreateCasePayload {
  title: string
  description?: string
  priority?: CasePriority
  status?: CaseStatus
  investigator?: string
  member_ids?: string[]
}

export interface PaginatedCases {
  count: number
  next: string | null
  previous: string | null
  results: Case[]
}

/**
 * Maps frontend lowercase priority to backend Django uppercase choices.
 * low -> LOW, medium -> MEDIUM, high -> HIGH, critical -> CRITICAL
 */
export function toBackendPriority(
  priority?: string
): "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | undefined {
  if (!priority) return undefined
  const p = priority.trim().toLowerCase()
  switch (p) {
    case "low":
      return "LOW"
    case "medium":
      return "MEDIUM"
    case "high":
      return "HIGH"
    case "critical":
      return "CRITICAL"
    default:
      return priority.toUpperCase() as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  }
}

/**
 * Maps frontend lowercase status to backend Django uppercase choices.
 * open -> OPEN, in_progress / active -> IN_PROGRESS, closed / archived -> CLOSED
 */
export function toBackendStatus(
  status?: string
): "OPEN" | "IN_PROGRESS" | "CLOSED" | undefined {
  if (!status) return undefined
  const s = status.trim().toLowerCase()
  switch (s) {
    case "open":
      return "OPEN"
    case "active":
    case "in_progress":
    case "in progress":
      return "IN_PROGRESS"
    case "closed":
    case "archived":
      return "CLOSED"
    default:
      return status.toUpperCase() as "OPEN" | "IN_PROGRESS" | "CLOSED"
  }
}

/**
 * Maps backend uppercase priority to frontend lowercase type.
 * LOW -> low, MEDIUM -> medium, HIGH -> high, CRITICAL -> critical
 */
export function toFrontendPriority(priority?: unknown): CasePriority {
  const p = String(priority ?? "").trim().toUpperCase()
  switch (p) {
    case "LOW":
      return "low"
    case "MEDIUM":
      return "medium"
    case "HIGH":
      return "high"
    case "CRITICAL":
      return "critical"
    default:
      return "medium"
  }
}

/**
 * Maps backend uppercase status to frontend lowercase type.
 * OPEN -> open, IN_PROGRESS -> in_progress, CLOSED -> closed
 */
export function toFrontendStatus(status?: unknown): CaseStatus {
  const s = String(status ?? "").trim().toUpperCase()
  switch (s) {
    case "OPEN":
      return "open"
    case "IN_PROGRESS":
      return "in_progress"
    case "CLOSED":
      return "closed"
    default:
      return "open"
  }
}

/** Normalize one CaseSerializer payload from Django into the frontend Case type. */
export function normalizeCase(raw: Record<string, unknown>): Case {
  const memberIds = Array.isArray(raw.member_ids)
    ? raw.member_ids.map((id) => String(id))
    : []

  return {
    id: String(raw.id ?? ""),
    title: String(raw.title ?? ""),
    description: String(raw.description ?? ""),
    investigator: String(raw.investigator ?? ""),
    investigator_username: String(raw.investigator_username ?? ""),
    member_ids: memberIds,
    priority: toFrontendPriority(raw.priority),
    status: toFrontendStatus(raw.status),
    created_by: String(raw.created_by ?? ""),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
  }
}

/** Unpack DRF paginated or raw array response into Case[] list. */
function asCaseList(data: unknown): Case[] {
  if (Array.isArray(data)) {
    return data.map((item) => normalizeCase(item as Record<string, unknown>))
  }
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>
    if (Array.isArray(obj.results)) {
      return obj.results.map((item) =>
        normalizeCase(item as Record<string, unknown>)
      )
    }
  }
  return []
}

/** Unpack DRF paginated response preserving count, next, previous metadata. */
export function normalizePaginatedCases(data: unknown): PaginatedCases {
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>
    if (Array.isArray(obj.results)) {
      return {
        count: Number(obj.count ?? obj.results.length),
        next: obj.next ? String(obj.next) : null,
        previous: obj.previous ? String(obj.previous) : null,
        results: obj.results.map((item) =>
          normalizeCase(item as Record<string, unknown>)
        ),
      }
    }
  }
  if (Array.isArray(data)) {
    const results = data.map((item) =>
      normalizeCase(item as Record<string, unknown>)
    )
    return {
      count: results.length,
      next: null,
      previous: null,
      results,
    }
  }
  return { count: 0, next: null, previous: null, results: [] }
}

/**
 * Serializes frontend CaseListParams into query params with uppercase Django choices.
 * e.g. status=open -> status=OPEN, priority=high -> priority=HIGH
 */
export function serializeCaseListParams(
  params?: CaseListParams
): Record<string, string | number> | undefined {
  if (!params) return undefined

  const query: Record<string, string | number> = {}

  if (params.search?.trim()) {
    query.search = params.search.trim()
  }

  if (params.status) {
    const backendStatus = toBackendStatus(params.status)
    if (backendStatus) {
      query.status = backendStatus
    }
  }

  if (params.priority) {
    const backendPriority = toBackendPriority(params.priority)
    if (backendPriority) {
      query.priority = backendPriority
    }
  }

  if (params.ordering?.trim()) {
    query.ordering = params.ordering.trim()
  }

  if (typeof params.page === "number" && params.page > 0) {
    query.page = params.page
  }

  if (typeof params.page_size === "number" && params.page_size > 0) {
    query.page_size = params.page_size
  }

  return Object.keys(query).length > 0 ? query : undefined
}

/** GET /api/cases/ — returns Case[] (unwrapped from DRF results). */
export async function listCases(params?: CaseListParams): Promise<Case[]> {
  const queryParams = serializeCaseListParams(params)
  const { data } = await apiClient.get("/cases/", { params: queryParams })
  return asCaseList(data)
}

/** GET /api/cases/ — returns full paginated envelope { count, next, previous, results }. */
export async function listCasesPaginated(
  params?: CaseListParams
): Promise<PaginatedCases> {
  const queryParams = serializeCaseListParams(params)
  const { data } = await apiClient.get("/cases/", { params: queryParams })
  return normalizePaginatedCases(data)
}

/** GET /api/cases/<id>/ — retrieve one case with normalized lowercase choices. */
export async function getCase(id: string): Promise<Case> {
  const { data } = await apiClient.get(`/cases/${id}/`)
  return normalizeCase(data as Record<string, unknown>)
}

/** POST /api/cases/ — creates case with normalized uppercase choices for backend. */
export async function createCase(payload: CreateCasePayload): Promise<Case> {
  const body: Record<string, unknown> = {
    title: payload.title.trim(),
  }
  if (payload.description != null) {
    body.description = payload.description
  }
  if (payload.priority) {
    body.priority = toBackendPriority(payload.priority)
  }
  if (payload.status) {
    body.status = toBackendStatus(payload.status)
  }
  if (payload.investigator) {
    body.investigator = payload.investigator
  }
  if (payload.member_ids?.length) {
    body.member_ids = payload.member_ids
  }

  const { data } = await apiClient.post("/cases/", body)
  return normalizeCase(data as Record<string, unknown>)
}

/** PATCH /api/cases/<id>/ — updates case with normalized uppercase choices for backend. */
export async function updateCase(
  id: string,
  payload: Partial<CreateCasePayload>
): Promise<Case> {
  const body: Record<string, unknown> = {}

  if (payload.title !== undefined) {
    body.title = payload.title.trim()
  }
  if (payload.description !== undefined) {
    body.description = payload.description
  }
  if (payload.priority !== undefined) {
    body.priority = toBackendPriority(payload.priority)
  }
  if (payload.status !== undefined) {
    body.status = toBackendStatus(payload.status)
  }
  if (payload.investigator !== undefined) {
    body.investigator = payload.investigator
  }
  if (payload.member_ids !== undefined) {
    body.member_ids = payload.member_ids
  }

  const { data } = await apiClient.patch(`/cases/${id}/`, body)
  return normalizeCase(data as Record<string, unknown>)
}

/** DELETE /api/cases/<id>/ — delete case by id. */
export async function deleteCase(id: string): Promise<void> {
  await apiClient.delete(`/cases/${id}/`)
}

/** Short display reference — backend has no case_number field. */
export function formatCaseRef(id: string): string {
  if (!id) return "—"
  return id.slice(0, 8).toUpperCase()
}
