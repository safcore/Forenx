/** ForenX domain types — aligned with forensic engine + Django API */

export type UserRole =
  | "administrator"
  | "lead_investigator"
  | "investigator"
  | "analyst"
  | "auditor"
  | "viewer"

export interface User {
  /** Backend uses UUID strings; demo mode may use numeric ids. */
  id: string | number
  email: string
  username?: string
  first_name: string
  last_name: string
  role: UserRole
  avatar?: string | null
  department?: string | null
  phone?: string | null
  /** Mapped from backend `date_joined` when present. */
  created_at: string
  last_login?: string | null
  is_active?: boolean
}

export type CaseStatus = "open" | "active" | "closed" | "archived"

export type CasePriority = "low" | "medium" | "high" | "critical"

/** Case shape aligned with integrated Django CaseSerializer. */
export interface Case {
  id: string
  title: string
  description: string
  investigator: string
  investigator_username: string
  member_ids: string[]
  priority: CasePriority
  status: CaseStatus
  created_by: string
  created_at: string
  updated_at: string
}

export interface Evidence {
  id: string
  case_id: string
  case_title?: string
  original_filename: string
  file_size: number
  file_type: string
  mime_type: string
  md5: string
  sha1: string
  sha256: string
  metadata: Record<string, unknown>
  acquisition_timestamp: string
  uploaded_by: string
  storage_available: boolean
  created_at: string
  updated_at: string
}

/** POST /api/cases/<id>/evidence/ acquire pipeline response (sanitized). */
export interface EvidenceUploadResult {
  id: string
  case_id: string
  filename: string
  size: number
  hashes: {
    md5: string
    sha1: string
    sha256: string
  }
  metadata: Record<string, unknown>
  custody_event_id: string
  status: string
}

/** GET /api/evidence/<uuid>/custody/ — single custody event from backend chain. */
export interface CustodyEvent {
  event_id: string
  action: string
  actor_id: string
  actor_role: string
  source: string
  source_ip: string | null
  timestamp: string
  description: string
  evidence_sha256: string
  previous_event_hash: string | null
  event_hash: string
  metadata: Record<string, unknown>
}

/** GET /api/evidence/<uuid>/custody/ response payload (inside success envelope). */
export interface EvidenceCustodyChain {
  evidence_id: string
  events: CustodyEvent[]
  count: number
}

export type HashAlgorithm = "md5" | "sha1" | "sha256"

export interface HashVerificationRequest {
  evidence_id: number
  algorithm: HashAlgorithm
  expected_hash: string
}

export interface HashVerificationResult {
  evidence_id: number
  algorithm: HashAlgorithm
  expected_hash: string
  calculated_hash: string
  verified: boolean
  verified_at: string
}

/** POST /api/evidence/<uuid>/verify-hash/ — acquisition digest comparison. */
export interface EvidenceHashCompareResult {
  algorithm: HashAlgorithm
  match: boolean
}

export interface EvidenceIntegrityAlgorithmResult {
  acquisition_hash: string
  current_hash: string
  match: boolean
}

/** POST /api/evidence/<uuid>/verify-integrity/ — file-based integrity verification. */
export interface EvidenceIntegrityVerifyResult {
  verified_at: string
  overall_match: boolean
  algorithms: Partial<Record<HashAlgorithm, EvidenceIntegrityAlgorithmResult>>
}

/** POST /api/evidence/<uuid>/keywords/ — keyword search analysis result. */
export interface EvidenceKeywordMatch {
  keyword: string
  line_number?: number | null
  page_number?: number | null
  paragraph_number?: number | null
  matched_text: string
  context: string
  match_position?: number
  file_name?: string
}

export interface EvidenceKeywordSearchResult {
  file_name: string
  file_type: string
  status: string
  message: string
  keywords: string[]
  match_count: number
  matches: EvidenceKeywordMatch[]
  execution_time_ms: number
  timestamp: string
  searched_at: string
}

/** POST /api/evidence/<uuid>/browser/analyze/ — controlled browser artifact analysis. */
export interface BrowserArtifactSummary {
  browser?: string | null
  profile_name?: string | null
  history_count: number
  download_count: number
  bookmark_count: number
  cookie_count: number
  search_count: number
  login_page_count: number
  execution_time_ms?: number
  status?: string
  message?: string
}

export interface BrowserVisitArtifact {
  browser: string
  url: string
  title?: string | null
  visit_count?: number | null
  visit_time?: string | null
  domain?: string | null
}

export interface BrowserDownloadArtifact {
  browser: string
  source_url?: string | null
  downloaded_time?: string | null
  file_size?: number | null
  danger_status?: string | null
}

export interface BrowserBookmarkArtifact {
  browser: string
  title?: string | null
  url?: string | null
  created_time?: string | null
  folder?: string | null
}

export interface BrowserCookieArtifact {
  browser: string
  host?: string | null
  name?: string | null
  creation_time?: string | null
  last_access_time?: string | null
  expiration_time?: string | null
  secure?: boolean | null
  http_only?: boolean | null
}

export interface BrowserSearchArtifact {
  browser: string
  engine: string
  search_query: string
  visit_time?: string | null
  url?: string | null
}

export interface BrowserLoginPageArtifact {
  browser: string
  url: string
  visit_time?: string | null
  title?: string | null
}

export interface EvidenceBrowserAnalysisResult {
  browser: string
  profile_name?: string | null
  status: string
  message: string
  timestamp: string
  analyzed_at: string
  execution_time_ms: number
  history: BrowserVisitArtifact[]
  downloads: BrowserDownloadArtifact[]
  bookmarks: BrowserBookmarkArtifact[]
  cookies: BrowserCookieArtifact[]
  searches: BrowserSearchArtifact[]
  login_pages: BrowserLoginPageArtifact[]
  summary: BrowserArtifactSummary
}

/** POST /api/evidence/<uuid>/timeline/analyze/ — controlled timeline analysis. */
export interface TimelineEventRecord {
  event_id: string
  timestamp: string
  timestamp_original?: string
  timestamp_type?: string
  event_type: string
  source: string
  source_file?: string
  description: string
  artifact?: string
  confidence?: number
}

export interface TimelineAnalysisSummary {
  total_events: number
  events_by_type: Record<string, number>
  events_by_source: Record<string, number>
  earliest_event?: string | null
  latest_event?: string | null
  message?: string
}

export interface EvidenceTimelineAnalysisResult {
  status: string
  message: string
  source?: string
  generated_at?: string
  analyzed_at: string
  events: TimelineEventRecord[]
  summary: TimelineAnalysisSummary
  events_truncated?: boolean
  events_total?: number
  warnings?: string[]
}

/** POST /api/evidence/<uuid>/metadata/analyze/ — controlled deep metadata analysis. */
export interface EvidenceFilesystemMetadata {
  file_name?: string
  extension?: string
  mime_type?: string | null
  file_size?: number
  created_time?: string | null
  modified_time?: string | null
  accessed_time?: string | null
  readable?: boolean
  writable?: boolean
  hidden?: boolean
  sha256?: string | null
  status?: string
  message?: string
  timestamp?: string
}

export interface EvidenceImageMetadata {
  filename?: string
  extension?: string
  mime_type?: string | null
  file_size?: number
  width?: number | null
  height?: number | null
  camera_make?: string | null
  camera_model?: string | null
  software?: string | null
  date_taken?: string | null
  gps_latitude?: number | null
  gps_longitude?: number | null
  orientation?: number | null
  color_mode?: string | null
  status?: string
  message?: string
  timestamp?: string
}

export interface EvidencePdfMetadata {
  file_name?: string
  title?: string | null
  author?: string | null
  creator?: string | null
  producer?: string | null
  subject?: string | null
  keywords?: string | null
  creation_date?: string | null
  modification_date?: string | null
  page_count?: number | null
  encrypted?: boolean
  status?: string
  message?: string
  timestamp?: string
}

export interface EvidenceDocumentMetadata {
  file_name?: string
  title?: string | null
  author?: string | null
  company?: string | null
  last_modified_by?: string | null
  revision?: string | null
  created_date?: string | null
  modified_date?: string | null
  category?: string | null
  subject?: string | null
  status?: string
  message?: string
  timestamp?: string
}

export interface EvidenceMetadataAnalysisResult {
  status: string
  message: string
  timestamp?: string
  analyzed_at: string
  file_type: string
  file_name: string
  filesystem?: EvidenceFilesystemMetadata | null
  image?: EvidenceImageMetadata | null
  pdf?: EvidencePdfMetadata | null
  document?: EvidenceDocumentMetadata | null
  embedded_metadata_found: boolean
  metadata_fields_found: number
  metadata_categories: string[]
}

/** POST /api/evidence/<uuid>/report/ — controlled report generation. */
export interface EvidenceReportSectionStatus {
  reference_hash_comparison: string
  file_integrity_verification: string
  keyword_analysis: string
  browser_analysis: string
  timeline_analysis: string
  metadata_analysis: string
}

export interface EvidenceReportGenerationResult {
  id: string
  report_id: string
  report_type: string
  format: string
  title: string
  generated_at: string
  file_name: string
  has_json: boolean
  has_pdf: boolean
  download_url: string
  sections: EvidenceReportSectionStatus
  created_at: string
}

/** POST /api/evidence/<uuid>/ai-assist/ — advisory AI investigation. */
export interface EvidenceAIAssistResult {
  analysis_id: string
  status: string
  summary: string
  observations: string[]
  correlations: string[]
  potential_leads: string[]
  recommended_next_steps: string[]
  limitations: string[]
  question: string
  insufficient_context: boolean
  generated_at: string
  disclaimer: string
  advisory_only: boolean
  provider: string
  model: string
  confidence: string
}

export type CustodyAction =
  | "collected"
  | "received"
  | "transferred"
  | "analyzed"
  | "sealed"
  | "unsealed"
  | "exported"
  | "archived"
  | "accessed"
  | "verified"

export interface ChainOfCustodyEvent {
  id: number
  evidence_id: number
  event_number: number
  action: CustodyAction | string
  actor: User
  timestamp: string
  ip_address?: string | null
  notes?: string | null
  previous_hash?: string | null
  event_hash: string
  verification_status: "valid" | "invalid" | "pending"
  location?: string | null
}

export type TimelineEventType =
  | "file_created"
  | "file_modified"
  | "file_accessed"
  | "browser_visit"
  | "browser_download"
  | "browser_bookmark"
  | "browser_search"
  | "metadata_created"
  | "metadata_modified"
  | "unknown"

export interface TimelineEvent {
  id: number
  case_id?: number
  evidence_id?: number
  event_type: TimelineEventType
  timestamp: string
  source: string
  description: string
  confidence: number
  evidence_name?: string
  metadata?: Record<string, unknown>
}

export type ReportType = "summary" | "detailed" | "executive" | "technical"
export type ReportStatus = "draft" | "generating" | "ready" | "failed"

export interface Report {
  id: number
  case_id: number
  case_number?: string
  title: string
  type: ReportType
  status: ReportStatus
  created_by: User
  created_at: string
  completed_at?: string | null
  file_url?: string | null
  sections?: string[]
  findings_summary?: string
  limitations?: string
}

export interface Activity {
  id: number
  type: string
  message: string
  user?: User | null
  case_id?: number
  evidence_id?: number
  timestamp: string
}

export interface DashboardStats {
  total_cases: number
  open_cases: number
  closed_cases: number
  evidence_uploaded: number
  reports_generated: number
  storage_used: number
  storage_limit: number
  verified_hashes?: number
  custody_alerts?: number
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface KeywordSearchRequest {
  evidence_id: number
  keyword: string
  case_sensitive?: boolean
  whole_word?: boolean
  regex?: boolean
  unicode?: boolean
}

export interface KeywordMatch {
  line_number?: number
  context: string
  match: string
  offset?: number
}

export interface KeywordSearchResult {
  evidence_id: number
  keyword: string
  total_matches: number
  frequency: Record<string, number>
  matches: KeywordMatch[]
}

export interface BrowserArtifact {
  id: number
  evidence_id: number
  browser: "chrome" | "edge" | "firefox"
  artifact_type:
    | "history"
    | "download"
    | "bookmark"
    | "search"
    | "login_page"
    | "cookie_metadata"
  url?: string
  title?: string
  timestamp?: string
  host?: string
  cookie_name?: string
  secure?: boolean
  http_only?: boolean
  expires?: string
  /** Cookie VALUES must never be exposed */
}

export interface MetadataResult {
  evidence_id: number
  filesystem?: Record<string, unknown>
  image_exif?: Record<string, unknown>
  pdf?: Record<string, unknown>
  docx?: Record<string, unknown>
  extracted_at?: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiError {
  detail?: string
  message?: string
  [key: string]: unknown
}
