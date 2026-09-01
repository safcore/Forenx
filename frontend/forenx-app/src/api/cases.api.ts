import apiClient from "@/api/client"
import type { Case, CasePriority, CaseStatus } from "@/types"

export interface CaseListParams {
  search?: string
  status?: CaseStatus
  priority?: CasePriority
}

export interface CreateCasePayload {
  title: string
  description?: string
  priority?: CasePriority
  status?: CaseStatus
  investigator?: string
  member_ids?: string[]
}

/** Normalize one CaseSerializer payload into the frontend Case type. */
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
    priority: (raw.priority as CasePriority) || "medium",
    status: (raw.status as CaseStatus) || "open",
    created_by: String(raw.created_by ?? ""),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
  }
}

function asCaseList(data: unknown): Case[] {
  if (Array.isArray(data)) {
    return data.map((item) => normalizeCase(item as Record<string, unknown>))
  }
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>
    // Defensive: support unexpected paginated wrappers
    if (Array.isArray(obj.results)) {
      return obj.results.map((item) =>
        normalizeCase(item as Record<string, unknown>)
      )
    }
  }
  return []
}

export async function listCases(params?: CaseListParams): Promise<Case[]> {
  const { data } = await apiClient.get("/cases/", { params })
  return asCaseList(data)
}

export async function getCase(id: string): Promise<Case> {
  const { data } = await apiClient.get(`/cases/${id}/`)
  return normalizeCase(data as Record<string, unknown>)
}

export async function createCase(payload: CreateCasePayload): Promise<Case> {
  const body: Record<string, unknown> = {
    title: payload.title,
  }
  if (payload.description != null) body.description = payload.description
  if (payload.priority) body.priority = payload.priority
  if (payload.status) body.status = payload.status
  if (payload.investigator) body.investigator = payload.investigator
  if (payload.member_ids?.length) body.member_ids = payload.member_ids

  const { data } = await apiClient.post("/cases/", body)
  return normalizeCase(data as Record<string, unknown>)
}

export async function updateCase(
  id: string,
  payload: Partial<CreateCasePayload>
): Promise<Case> {
  const { data } = await apiClient.patch(`/cases/${id}/`, payload)
  return normalizeCase(data as Record<string, unknown>)
}

/** Short display reference — backend has no case_number field. */
export function formatCaseRef(id: string): string {
  if (!id) return "—"
  return id.slice(0, 8).toUpperCase()
}
