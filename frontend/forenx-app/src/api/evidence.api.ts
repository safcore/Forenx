import axios from "axios"
import apiClient from "@/api/client"
import type {
  CustodyEvent,
  Evidence,
  EvidenceCustodyChain,
  CustodyChainVerificationResult,
  EvidenceHashCompareResult,
  EvidenceIntegrityVerifyResult,
  EvidenceKeywordSearchResult,
  EvidenceBrowserAnalysisResult,
  EvidenceTimelineAnalysisResult,
  EvidenceMetadataAnalysisResult,
  EvidenceReportGenerationResult,
  EvidenceAIAssistResult,
  EvidenceUploadResult,
  HashAlgorithm,
} from "@/types"

/** Unwrap `{ success, data }` envelopes from integrated backend. */
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

const PATH_KEYS = new Set([
  "stored_path",
  "absolute_path",
  "evidence_path",
  "json_path",
  "pdf_path",
  "output_path",
  "path",
])

/** Strip internal path fields if present; backend serializers should omit them. */
function stripSensitivePaths(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(stripSensitivePaths)
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      if (PATH_KEYS.has(key) || key.endsWith("_path")) {
        continue
      }
      out[key] = stripSensitivePaths(item)
    }
    return out
  }
  return value
}

export function normalizeEvidence(raw: Record<string, unknown>): Evidence {
  const metadata =
    raw.metadata && typeof raw.metadata === "object"
      ? (stripSensitivePaths(raw.metadata) as Record<string, unknown>)
      : {}

  return {
    id: String(raw.id ?? ""),
    case_id: String(raw.case_id ?? ""),
    case_title: raw.case_title ? String(raw.case_title) : undefined,
    original_filename: String(raw.original_filename ?? raw.filename ?? ""),
    file_size: Number(raw.file_size ?? raw.size ?? 0),
    file_type: String(raw.file_type ?? ""),
    mime_type: String(raw.mime_type ?? ""),
    md5: String(raw.md5 ?? ""),
    sha1: String(raw.sha1 ?? ""),
    sha256: String(raw.sha256 ?? ""),
    metadata,
    acquisition_timestamp: String(
      raw.acquisition_timestamp ?? raw.created_at ?? ""
    ),
    uploaded_by: String(raw.uploaded_by ?? ""),
    storage_available: Boolean(raw.storage_available),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
  }
}

export function normalizeUploadResult(
  raw: Record<string, unknown>
): EvidenceUploadResult {
  const hashesRaw =
    raw.hashes && typeof raw.hashes === "object"
      ? (raw.hashes as Record<string, unknown>)
      : {}

  return {
    id: String(raw.id ?? ""),
    case_id: String(raw.case_id ?? ""),
    filename: String(raw.filename ?? raw.original_filename ?? ""),
    size: Number(raw.size ?? raw.file_size ?? 0),
    hashes: {
      md5: String(hashesRaw.md5 ?? raw.md5 ?? ""),
      sha1: String(hashesRaw.sha1 ?? raw.sha1 ?? ""),
      sha256: String(hashesRaw.sha256 ?? raw.sha256 ?? ""),
    },
    metadata:
      raw.metadata && typeof raw.metadata === "object"
        ? (stripSensitivePaths(raw.metadata) as Record<string, unknown>)
        : {},
    custody_event_id: String(raw.custody_event_id ?? ""),
    status: String(raw.status ?? "success"),
  }
}

export async function listEvidenceForCase(caseId: string): Promise<Evidence[]> {
  const { data } = await apiClient.get(`/cases/${caseId}/evidence/`)
  const items = unwrapSuccess<unknown[]>(data)
  if (!Array.isArray(items)) return []
  return items.map((item) =>
    normalizeEvidence(stripSensitivePaths(item) as Record<string, unknown>)
  )
}

/** GET /api/evidence/ — read-only inventory for accessible cases. */
export async function listAccessibleEvidence(): Promise<Evidence[]> {
  const { data } = await apiClient.get("/evidence/")
  const items = unwrapSuccess<unknown[]>(data)
  if (!Array.isArray(items)) return []
  return items.map((item) =>
    normalizeEvidence(stripSensitivePaths(item) as Record<string, unknown>)
  )
}

export async function uploadEvidenceForCase(
  caseId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<EvidenceUploadResult> {
  const form = new FormData()
  form.append("file", file)

  const { data } = await apiClient.post(`/cases/${caseId}/evidence/`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress(Math.round((event.loaded * 100) / event.total))
      }
    },
  })

  const payload = stripSensitivePaths(unwrapSuccess<Record<string, unknown>>(data))
  return normalizeUploadResult(payload as Record<string, unknown>)
}

/** GET /api/evidence/<uuid>/ — single evidence detail (read-only). */
export async function getEvidence(id: string): Promise<Evidence> {
  const { data } = await apiClient.get(`/evidence/${id}/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeEvidence(stripSensitivePaths(payload) as Record<string, unknown>)
}

export function normalizeCustodyEvent(raw: Record<string, unknown>): CustodyEvent {
  const metadata =
    raw.metadata && typeof raw.metadata === "object"
      ? (stripSensitivePaths(raw.metadata) as Record<string, unknown>)
      : {}

  const previousHash = raw.previous_event_hash
  return {
    event_id: String(raw.event_id ?? ""),
    action: String(raw.action ?? ""),
    actor_id: String(raw.actor_id ?? ""),
    actor_role: String(raw.actor_role ?? ""),
    source: String(raw.source ?? ""),
    source_ip:
      raw.source_ip === null || raw.source_ip === undefined
        ? null
        : String(raw.source_ip),
    timestamp: String(raw.timestamp ?? ""),
    description: String(raw.description ?? ""),
    evidence_sha256: String(raw.evidence_sha256 ?? ""),
    previous_event_hash:
      previousHash === null || previousHash === undefined || previousHash === ""
        ? null
        : String(previousHash),
    event_hash: String(raw.event_hash ?? ""),
    metadata,
  }
}

export function normalizeCustodyChain(raw: Record<string, unknown>): EvidenceCustodyChain {
  const eventsRaw = Array.isArray(raw.events) ? raw.events : []
  return {
    evidence_id: String(raw.evidence_id ?? ""),
    events: eventsRaw.map((item) =>
      normalizeCustodyEvent(stripSensitivePaths(item) as Record<string, unknown>)
    ),
    count: Number(raw.count ?? eventsRaw.length),
  }
}

/** GET /api/evidence/<uuid>/custody/ — read-only custody chain. */
export async function getEvidenceCustody(
  evidenceId: string
): Promise<EvidenceCustodyChain> {
  const { data } = await apiClient.get(`/evidence/${evidenceId}/custody/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeCustodyChain(stripSensitivePaths(payload) as Record<string, unknown>)
}

export function normalizeCustodyChainVerificationResult(
  raw: Record<string, unknown>
): CustodyChainVerificationResult {
  return {
    valid: Boolean(raw.valid),
    event_count: Number(raw.event_count ?? 0),
    first_event:
      raw.first_event && typeof raw.first_event === "object"
        ? normalizeCustodyEvent(
            stripSensitivePaths(raw.first_event) as Record<string, unknown>
          )
        : null,
    last_event:
      raw.last_event && typeof raw.last_event === "object"
        ? normalizeCustodyEvent(
            stripSensitivePaths(raw.last_event) as Record<string, unknown>
          )
        : null,
    broken_event_id: raw.broken_event_id ? String(raw.broken_event_id) : null,
    message: String(raw.message ?? ""),
    warnings: Array.isArray(raw.warnings) ? raw.warnings.map(String) : [],
    status: String(raw.status ?? ""),
  }
}

/** GET /api/evidence/<uuid>/custody/verify/ — cryptographic chain verification. */
export async function verifyEvidenceCustodyChain(
  evidenceId: string
): Promise<CustodyChainVerificationResult> {
  const { data } = await apiClient.get(`/evidence/${evidenceId}/custody/verify/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeCustodyChainVerificationResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}

export function normalizeHashCompareResult(
  raw: Record<string, unknown>
): EvidenceHashCompareResult {
  const algorithm = String(raw.algorithm ?? "sha256").toLowerCase()
  return {
    algorithm: algorithm as HashAlgorithm,
    match: Boolean(raw.match),
  }
}

/** POST /api/evidence/<uuid>/verify-hash/ — compare reference digest to acquisition hash. */
export async function verifyEvidenceHash(
  evidenceId: string,
  algorithm: HashAlgorithm,
  expectedHash: string
): Promise<EvidenceHashCompareResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/verify-hash/`, {
    algorithm,
    expected_hash: expectedHash.trim(),
  })
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeHashCompareResult(payload)
}

export function normalizeIntegrityVerifyResult(
  raw: Record<string, unknown>
): EvidenceIntegrityVerifyResult {
  const algorithmsRaw =
    raw.algorithms && typeof raw.algorithms === "object"
      ? (raw.algorithms as Record<string, unknown>)
      : {}
  const algorithms: EvidenceIntegrityVerifyResult["algorithms"] = {}

  for (const [key, value] of Object.entries(algorithmsRaw)) {
    if (!value || typeof value !== "object") continue
    const item = value as Record<string, unknown>
    const alg = key.toLowerCase()
    if (alg !== "md5" && alg !== "sha1" && alg !== "sha256") continue
    algorithms[alg] = {
      acquisition_hash: String(item.acquisition_hash ?? ""),
      current_hash: String(item.current_hash ?? ""),
      match: Boolean(item.match),
    }
  }

  return {
    verified_at: String(raw.verified_at ?? ""),
    overall_match: Boolean(raw.overall_match),
    algorithms,
  }
}

/** POST /api/evidence/<uuid>/verify-integrity/ — file-based integrity verification. */
export async function verifyEvidenceIntegrity(
  evidenceId: string
): Promise<EvidenceIntegrityVerifyResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/verify-integrity/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeIntegrityVerifyResult(payload)
}

export function normalizeKeywordSearchResult(
  raw: Record<string, unknown>
): EvidenceKeywordSearchResult {
  const matchesRaw = Array.isArray(raw.matches) ? raw.matches : []
  const matches = matchesRaw.map((item) => {
    const match = stripSensitivePaths(item) as Record<string, unknown>
    return {
      keyword: String(match.keyword ?? ""),
      line_number:
        match.line_number === null || match.line_number === undefined
          ? null
          : Number(match.line_number),
      page_number:
        match.page_number === null || match.page_number === undefined
          ? null
          : Number(match.page_number),
      paragraph_number:
        match.paragraph_number === null || match.paragraph_number === undefined
          ? null
          : Number(match.paragraph_number),
      matched_text: String(match.matched_text ?? ""),
      context: String(match.context ?? ""),
      match_position:
        match.match_position === undefined
          ? undefined
          : Number(match.match_position),
      file_name: match.file_name ? String(match.file_name) : undefined,
    }
  })

  return {
    file_name: String(raw.file_name ?? ""),
    file_type: String(raw.file_type ?? ""),
    status: String(raw.status ?? ""),
    message: String(raw.message ?? ""),
    keywords: Array.isArray(raw.keywords)
      ? raw.keywords.map((item) => String(item))
      : [],
    match_count: Number(raw.match_count ?? matches.length),
    matches,
    execution_time_ms: Number(raw.execution_time_ms ?? 0),
    timestamp: String(raw.timestamp ?? raw.searched_at ?? ""),
    searched_at: String(raw.searched_at ?? raw.timestamp ?? ""),
  }
}

/** POST /api/evidence/<uuid>/keywords/ — controlled keyword search analysis. */
export async function searchEvidenceKeywords(
  evidenceId: string,
  keywords: string[]
): Promise<EvidenceKeywordSearchResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/keywords/`, {
    keywords,
  })
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeKeywordSearchResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}

function asRecordList(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => stripSensitivePaths(item))
    .filter((item): item is Record<string, unknown> =>
      Boolean(item) && typeof item === "object" && !Array.isArray(item)
    )
}

export function normalizeBrowserAnalysisResult(
  raw: Record<string, unknown>
): EvidenceBrowserAnalysisResult {
  const summaryRaw =
    raw.summary && typeof raw.summary === "object"
      ? (raw.summary as Record<string, unknown>)
      : {}

  return {
    browser: String(raw.browser ?? summaryRaw.browser ?? "Unknown"),
    profile_name:
      raw.profile_name == null ? null : String(raw.profile_name),
    status: String(raw.status ?? summaryRaw.status ?? ""),
    message: String(raw.message ?? summaryRaw.message ?? ""),
    timestamp: String(raw.timestamp ?? raw.analyzed_at ?? ""),
    analyzed_at: String(raw.analyzed_at ?? raw.timestamp ?? ""),
    execution_time_ms: Number(raw.execution_time_ms ?? 0),
    history: asRecordList(raw.history).map((item) => ({
      browser: String(item.browser ?? ""),
      url: String(item.url ?? ""),
      title: item.title == null ? null : String(item.title),
      visit_count:
        item.visit_count == null ? null : Number(item.visit_count),
      visit_time: item.visit_time == null ? null : String(item.visit_time),
      domain: item.domain == null ? null : String(item.domain),
    })),
    downloads: asRecordList(raw.downloads).map((item) => ({
      browser: String(item.browser ?? ""),
      source_url: item.source_url == null ? null : String(item.source_url),
      downloaded_time:
        item.downloaded_time == null ? null : String(item.downloaded_time),
      file_size: item.file_size == null ? null : Number(item.file_size),
      danger_status:
        item.danger_status == null ? null : String(item.danger_status),
    })),
    bookmarks: asRecordList(raw.bookmarks).map((item) => ({
      browser: String(item.browser ?? ""),
      title: item.title == null ? null : String(item.title),
      url: item.url == null ? null : String(item.url),
      created_time:
        item.created_time == null ? null : String(item.created_time),
      folder: item.folder == null ? null : String(item.folder),
    })),
    cookies: asRecordList(raw.cookies).map((item) => ({
      browser: String(item.browser ?? ""),
      host: item.host == null ? null : String(item.host),
      name: item.name == null ? null : String(item.name),
      creation_time:
        item.creation_time == null ? null : String(item.creation_time),
      last_access_time:
        item.last_access_time == null ? null : String(item.last_access_time),
      expiration_time:
        item.expiration_time == null ? null : String(item.expiration_time),
      secure: item.secure == null ? null : Boolean(item.secure),
      http_only: item.http_only == null ? null : Boolean(item.http_only),
    })),
    searches: asRecordList(raw.searches).map((item) => ({
      browser: String(item.browser ?? ""),
      engine: String(item.engine ?? ""),
      search_query: String(item.search_query ?? ""),
      visit_time: item.visit_time == null ? null : String(item.visit_time),
      url: item.url == null ? null : String(item.url),
    })),
    login_pages: asRecordList(raw.login_pages).map((item) => ({
      browser: String(item.browser ?? ""),
      url: String(item.url ?? ""),
      visit_time: item.visit_time == null ? null : String(item.visit_time),
      title: item.title == null ? null : String(item.title),
    })),
    summary: {
      browser:
        summaryRaw.browser == null ? null : String(summaryRaw.browser),
      profile_name:
        summaryRaw.profile_name == null
          ? null
          : String(summaryRaw.profile_name),
      history_count: Number(summaryRaw.history_count ?? 0),
      download_count: Number(summaryRaw.download_count ?? 0),
      bookmark_count: Number(summaryRaw.bookmark_count ?? 0),
      cookie_count: Number(summaryRaw.cookie_count ?? 0),
      search_count: Number(summaryRaw.search_count ?? 0),
      login_page_count: Number(summaryRaw.login_page_count ?? 0),
      execution_time_ms: Number(summaryRaw.execution_time_ms ?? 0),
      status:
        summaryRaw.status == null ? undefined : String(summaryRaw.status),
      message:
        summaryRaw.message == null ? undefined : String(summaryRaw.message),
    },
  }
}

/**
 * POST /api/evidence/<uuid>/browser/analyze/
 * Explicit browser analysis. GET /browser/ is read-only.
 */
export async function analyzeEvidenceBrowser(
  evidenceId: string
): Promise<EvidenceBrowserAnalysisResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/browser/analyze/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeBrowserAnalysisResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}

export function normalizeTimelineAnalysisResult(
  raw: Record<string, unknown>
): EvidenceTimelineAnalysisResult {
  const summaryRaw =
    raw.summary && typeof raw.summary === "object"
      ? (raw.summary as Record<string, unknown>)
      : {}
  const eventsByType =
    summaryRaw.events_by_type && typeof summaryRaw.events_by_type === "object"
      ? (summaryRaw.events_by_type as Record<string, unknown>)
      : {}
  const eventsBySource =
    summaryRaw.events_by_source && typeof summaryRaw.events_by_source === "object"
      ? (summaryRaw.events_by_source as Record<string, unknown>)
      : {}

  const events = asRecordList(raw.events).map((item) => ({
    event_id: String(item.event_id ?? ""),
    timestamp: String(item.timestamp ?? ""),
    timestamp_original:
      item.timestamp_original == null
        ? undefined
        : String(item.timestamp_original),
    timestamp_type:
      item.timestamp_type == null ? undefined : String(item.timestamp_type),
    event_type: String(item.event_type ?? "unknown"),
    source: String(item.source ?? ""),
    source_file:
      item.source_file == null ? undefined : String(item.source_file),
    description: String(item.description ?? ""),
    artifact: item.artifact == null ? undefined : String(item.artifact),
    confidence:
      item.confidence == null ? undefined : Number(item.confidence),
  }))

  return {
    status: String(raw.status ?? ""),
    message: String(raw.message ?? summaryRaw.message ?? ""),
    source: raw.source == null ? undefined : String(raw.source),
    generated_at:
      raw.generated_at == null ? undefined : String(raw.generated_at),
    analyzed_at: String(raw.analyzed_at ?? raw.generated_at ?? ""),
    events,
    summary: {
      total_events: Number(summaryRaw.total_events ?? events.length),
      events_by_type: Object.fromEntries(
        Object.entries(eventsByType).map(([key, value]) => [key, Number(value)])
      ),
      events_by_source: Object.fromEntries(
        Object.entries(eventsBySource).map(([key, value]) => [
          key,
          Number(value),
        ])
      ),
      earliest_event:
        summaryRaw.earliest_event == null
          ? null
          : String(summaryRaw.earliest_event),
      latest_event:
        summaryRaw.latest_event == null
          ? null
          : String(summaryRaw.latest_event),
      message:
        summaryRaw.message == null ? undefined : String(summaryRaw.message),
    },
    events_truncated: Boolean(raw.events_truncated),
    events_total:
      raw.events_total == null ? undefined : Number(raw.events_total),
    warnings: Array.isArray(raw.warnings)
      ? raw.warnings.map((item) => String(item))
      : [],
  }
}

/**
 * POST /api/evidence/<uuid>/timeline/analyze/
 * Explicit timeline analysis. GET /timeline/ is read-only.
 */
export async function analyzeEvidenceTimeline(
  evidenceId: string
): Promise<EvidenceTimelineAnalysisResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/timeline/analyze/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeTimelineAnalysisResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}

function asOptionalRecord(
  value: unknown
): Record<string, unknown> | null | undefined {
  if (value == null) return value as null | undefined
  if (typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return null
}

function normalizeFilesystemMetadata(
  raw: Record<string, unknown> | null | undefined
): EvidenceMetadataAnalysisResult["filesystem"] {
  if (!raw) return raw
  return {
    file_name: raw.file_name == null ? undefined : String(raw.file_name),
    extension: raw.extension == null ? undefined : String(raw.extension),
    mime_type: raw.mime_type == null ? null : String(raw.mime_type),
    file_size: raw.file_size == null ? undefined : Number(raw.file_size),
    created_time:
      raw.created_time == null ? null : String(raw.created_time),
    modified_time:
      raw.modified_time == null ? null : String(raw.modified_time),
    accessed_time:
      raw.accessed_time == null ? null : String(raw.accessed_time),
    readable: raw.readable == null ? undefined : Boolean(raw.readable),
    writable: raw.writable == null ? undefined : Boolean(raw.writable),
    hidden: raw.hidden == null ? undefined : Boolean(raw.hidden),
    sha256: raw.sha256 == null ? null : String(raw.sha256),
    status: raw.status == null ? undefined : String(raw.status),
    message: raw.message == null ? undefined : String(raw.message),
    timestamp: raw.timestamp == null ? undefined : String(raw.timestamp),
  }
}

export function normalizeMetadataAnalysisResult(
  raw: Record<string, unknown>
): EvidenceMetadataAnalysisResult {
  const categories = Array.isArray(raw.metadata_categories)
    ? raw.metadata_categories.map((item) => String(item))
    : []

  return {
    status: String(raw.status ?? ""),
    message: String(raw.message ?? ""),
    timestamp: raw.timestamp == null ? undefined : String(raw.timestamp),
    analyzed_at: String(raw.analyzed_at ?? raw.timestamp ?? ""),
    file_type: String(raw.file_type ?? "filesystem"),
    file_name: String(raw.file_name ?? ""),
    filesystem: normalizeFilesystemMetadata(asOptionalRecord(raw.filesystem)),
    image: asOptionalRecord(raw.image) as EvidenceMetadataAnalysisResult["image"],
    pdf: asOptionalRecord(raw.pdf) as EvidenceMetadataAnalysisResult["pdf"],
    document: asOptionalRecord(
      raw.document
    ) as EvidenceMetadataAnalysisResult["document"],
    embedded_metadata_found: Boolean(raw.embedded_metadata_found),
    metadata_fields_found: Number(raw.metadata_fields_found ?? 0),
    metadata_categories: categories,
  }
}

/**
 * POST /api/evidence/<uuid>/metadata/analyze/
 * Explicit metadata analysis. GET /metadata/ is read-only and does not mutate acquisition data.
 */
export async function analyzeEvidenceMetadata(
  evidenceId: string
): Promise<EvidenceMetadataAnalysisResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/metadata/analyze/`)
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeMetadataAnalysisResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}

export function normalizeReportGenerationResult(
  raw: Record<string, unknown>
): EvidenceReportGenerationResult {
  const sectionsRaw =
    raw.sections && typeof raw.sections === "object"
      ? (raw.sections as Record<string, unknown>)
      : {}
  return {
    id: String(raw.id ?? ""),
    report_id: String(raw.report_id ?? ""),
    report_type: String(raw.report_type ?? ""),
    format: String(raw.format ?? raw.report_type ?? "json"),
    title: String(raw.title ?? ""),
    generated_at: String(raw.generated_at ?? raw.created_at ?? ""),
    file_name: String(raw.file_name ?? ""),
    has_json: Boolean(raw.has_json),
    has_pdf: Boolean(raw.has_pdf),
    download_url: String(raw.download_url ?? ""),
    sections: {
      reference_hash_comparison: String(
        sectionsRaw.reference_hash_comparison ?? "Not performed"
      ),
      file_integrity_verification: String(
        sectionsRaw.file_integrity_verification ?? "Not performed"
      ),
      keyword_analysis: String(
        sectionsRaw.keyword_analysis ?? "Not performed"
      ),
      browser_analysis: String(
        sectionsRaw.browser_analysis ?? "Not performed"
      ),
      timeline_analysis: String(
        sectionsRaw.timeline_analysis ?? "Not performed"
      ),
      metadata_analysis: String(
        sectionsRaw.metadata_analysis ?? "Not performed"
      ),
    },
    created_at: String(raw.created_at ?? raw.generated_at ?? ""),
  }
}

/**
 * POST /api/evidence/<uuid>/report/
 * Explicit forensic report generation from stored results only.
 */
export async function generateEvidenceReport(
  evidenceId: string,
  format: "json" | "pdf" | "both" = "both"
): Promise<EvidenceReportGenerationResult> {
  const { data } = await apiClient.post(`/evidence/${evidenceId}/report/`, {
    format,
  })
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeReportGenerationResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}

async function asDownloadBlob(error: unknown): Promise<never> {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    try {
      const text = await error.response.data.text()
      error.response.data = JSON.parse(text)
    } catch {
      // Keep original error if the blob is not JSON.
    }
  }
  throw error
}

/** Authenticated download helper for a generated report artifact. */
export async function downloadEvidenceReport(
  reportDbId: string,
  format: "json" | "pdf" = "pdf"
): Promise<Blob> {
  try {
    const { data } = await apiClient.get(
      `/reports/${reportDbId}/download/?format=${format}`,
      { responseType: "blob" }
    )
    return data as Blob
  } catch (error) {
    return asDownloadBlob(error)
  }
}

export interface EvidenceAnalysisHistoryItem {
  id: string
  case: string
  evidence: string
  analysis_type: string
  status: string
  started_at: string | null
  completed_at: string | null
  created_at: string | null
  created_by: string
  created_by_username: string
  result_summary: string
  error_message: string
}

/** GET /api/evidence/<uuid>/analysis-runs/ — read-only history. */
export async function listEvidenceAnalysisRuns(
  evidenceId: string
): Promise<EvidenceAnalysisHistoryItem[]> {
  const { data } = await apiClient.get(`/evidence/${evidenceId}/analysis-runs/`)
  const payload = unwrapSuccess<unknown>(data)
  if (!Array.isArray(payload)) return []
  return payload.map((item) => {
    const raw = item as Record<string, unknown>
    return {
      id: String(raw.id ?? ""),
      case: String(raw.case ?? ""),
      evidence: String(raw.evidence ?? ""),
      analysis_type: String(raw.analysis_type ?? ""),
      status: String(raw.status ?? ""),
      started_at: raw.started_at ? String(raw.started_at) : null,
      completed_at: raw.completed_at ? String(raw.completed_at) : null,
      created_at: raw.created_at ? String(raw.created_at) : null,
      created_by: String(raw.created_by ?? ""),
      created_by_username: String(raw.created_by_username ?? ""),
      result_summary: String(raw.result_summary ?? ""),
      error_message: String(raw.error_message ?? "").replace(
        /traceback[\s\S]*$/i,
        ""
      ),
    }
  })
}

export function normalizeAIAssistResult(
  raw: Record<string, unknown>
): EvidenceAIAssistResult {
  const asList = (value: unknown): string[] =>
    Array.isArray(value)
      ? value.map((item) => String(item)).filter(Boolean).slice(0, 20)
      : []

  return {
    analysis_id: String(raw.analysis_id ?? ""),
    status: String(raw.status ?? ""),
    summary: String(raw.summary ?? "").slice(0, 2000),
    observations: asList(raw.observations),
    correlations: asList(raw.correlations),
    potential_leads: asList(raw.potential_leads),
    recommended_next_steps: asList(raw.recommended_next_steps),
    limitations: asList(raw.limitations).slice(0, 10),
    question: String(raw.question ?? ""),
    insufficient_context: Boolean(raw.insufficient_context),
    generated_at: String(raw.generated_at ?? ""),
    disclaimer: String(
      raw.disclaimer ??
        "AI output is advisory and must be independently validated against the underlying forensic evidence."
    ),
    advisory_only: raw.advisory_only !== false,
    provider: String(raw.provider ?? ""),
    model: String(raw.model ?? ""),
    confidence: String(raw.confidence ?? "unknown"),
  }
}

/**
 * POST /api/evidence/<uuid>/ai-assist/
 * Explicit advisory AI investigation over stored forensic results.
 */
export async function assistEvidenceInvestigation(
  evidenceId: string,
  question?: string
): Promise<EvidenceAIAssistResult> {
  const body: Record<string, unknown> = { enabled: true }
  if (question !== undefined) {
    body.question = question
  }
  const { data } = await apiClient.post(
    `/evidence/${evidenceId}/ai-assist/`,
    body
  )
  const payload = unwrapSuccess<Record<string, unknown>>(data)
  return normalizeAIAssistResult(
    stripSensitivePaths(payload) as Record<string, unknown>
  )
}
