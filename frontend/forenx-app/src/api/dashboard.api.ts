import { listCasesPaginated } from "@/api/cases.api"
import { listAccessibleEvidence } from "@/api/evidence.api"
import { listCustodyEvents, type CustodyListItem } from "@/api/custody.api"
import { listReports, type ReportListItem } from "@/api/reports.api"
import type { Case, CasePriority, Evidence } from "@/types"

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

/** Safely fetch all accessible cases across pages for complete metric calculation. */
async function fetchAllCases(): Promise<{ totalCount: number; cases: Case[] }> {
  const firstPage = await listCasesPaginated({ page: 1, page_size: 100 })
  let allCases = [...firstPage.results]
  const totalCount = firstPage.count

  if (totalCount > allCases.length) {
    const totalPages = Math.min(Math.ceil(totalCount / 100), 10)
    const subsequentPageNumbers: number[] = []
    for (let p = 2; p <= totalPages; p++) {
      subsequentPageNumbers.push(p)
    }
    const subsequentPages = await Promise.all(
      subsequentPageNumbers.map((p) =>
        listCasesPaginated({ page: p, page_size: 100 })
      )
    )
    for (const page of subsequentPages) {
      allCases = allCases.concat(page.results)
    }
  }

  return { totalCount, cases: allCases }
}

/**
 * Aggregates live platform metrics client-side by querying existing authenticated endpoints in parallel.
 * Replaces the nonexistent /api/dashboard/ endpoint with zero backend alterations.
 */
export async function getDashboardSummary(): Promise<DashboardSummary> {
  const [casesRes, evidenceRes, custodyRes, reportsRes] =
    await Promise.allSettled([
      fetchAllCases(),
      listAccessibleEvidence(),
      listCustodyEvents(),
      listReports(),
    ])

  // If all 4 requests fail (e.g. network outage or unauthenticated), throw to trigger error state
  const rejections = [casesRes, evidenceRes, custodyRes, reportsRes].filter(
    (r): r is PromiseRejectedResult => r.status === "rejected"
  )
  if (rejections.length === 4) {
    throw rejections[0].reason
  }

  const casesData =
    casesRes.status === "fulfilled"
      ? casesRes.value
      : { totalCount: 0, cases: [] }
  const evidenceList: Evidence[] =
    evidenceRes.status === "fulfilled" ? evidenceRes.value : []
  const custodyEvents: CustodyListItem[] =
    custodyRes.status === "fulfilled" ? custodyRes.value : []
  const reportsList: ReportListItem[] =
    reportsRes.status === "fulfilled" ? reportsRes.value : []

  const cases = casesData.cases
  const totalCases = casesData.totalCount

  // 1. Cases breakdown
  const openCases = cases.filter(
    (c) =>
      c.status === "open" ||
      c.status === "in_progress" ||
      c.status === "active"
  ).length
  const closedCases = cases.filter(
    (c) => c.status === "closed" || c.status === "archived"
  ).length

  const priorityCounts: Record<CasePriority, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  }
  for (const c of cases) {
    if (c.priority && priorityCounts[c.priority] !== undefined) {
      priorityCounts[c.priority]++
    } else {
      priorityCounts.medium++
    }
  }

  const recentCases = [...cases]
    .sort(
      (a, b) =>
        new Date(b.created_at || 0).getTime() -
        new Date(a.created_at || 0).getTime()
    )
    .slice(0, 5)

  // 2. Evidence breakdown
  const totalEvidence = evidenceList.length
  const storageBytes = evidenceList.reduce(
    (sum, ev) => sum + (Number(ev.file_size) || 0),
    0
  )

  const evidenceTypeCounts: Record<string, number> = {}
  for (const ev of evidenceList) {
    const ext = (
      ev.file_type ||
      ev.original_filename.split(".").pop() ||
      "unknown"
    ).toLowerCase()
    evidenceTypeCounts[ext] = (evidenceTypeCounts[ext] || 0) + 1
  }

  const recentEvidence: DashboardRecentEvidence[] = [...evidenceList]
    .sort(
      (a, b) =>
        new Date(b.created_at || b.acquisition_timestamp || 0).getTime() -
        new Date(a.created_at || a.acquisition_timestamp || 0).getTime()
    )
    .slice(0, 5)
    .map((ev) => ({
      id: ev.id,
      case_id: ev.case_id,
      original_filename: ev.original_filename,
      file_size: ev.file_size,
      created_at: ev.created_at || ev.acquisition_timestamp || "",
      acquisition_timestamp: ev.acquisition_timestamp,
    }))

  // 3. Reports breakdown
  const reportsGenerated = reportsList.length
  const recentReports: DashboardRecentReport[] = [...reportsList]
    .sort(
      (a, b) =>
        new Date(b.created_at || 0).getTime() -
        new Date(a.created_at || 0).getTime()
    )
    .slice(0, 5)
    .map((r) => ({
      id: r.id,
      report_id: r.report_id,
      title: r.title,
      case_title: r.case_title,
      evidence_filename: r.evidence_filename,
      created_at: r.created_at,
      generated_by_username: r.generated_by_username,
    }))

  // 4. Custody breakdown
  const totalCustodyEvents = custodyEvents.length
  const custodyCounts: Record<string, number> = {}
  for (const event of custodyEvents) {
    const action = event.action || "unknown"
    custodyCounts[action] = (custodyCounts[action] || 0) + 1
  }

  const recentCustody: DashboardRecentCustody[] = [...custodyEvents]
    .sort(
      (a, b) =>
        new Date(b.timestamp || 0).getTime() -
        new Date(a.timestamp || 0).getTime()
    )
    .slice(0, 5)
    .map((ev) => ({
      id: ev.id || ev.event_id,
      action: ev.action,
      actor_id: ev.actor_id,
      actor_role: ev.actor_role,
      timestamp: ev.timestamp,
      description: ev.description,
      evidence_filename: ev.evidence_filename,
      case_title: ev.case_title,
      metadata: ev.metadata,
    }))

  // 5. Analysis counts for AnalyticsPage (hash, keyword, browser, timeline, metadata, report, ai)
  const analysisCounts: Record<string, number> = {
    hash: 0,
    keyword: 0,
    browser: 0,
    timeline: 0,
    metadata: 0,
    report: reportsGenerated,
    ai: 0,
  }

  for (const event of custodyEvents) {
    const aType =
      typeof event.metadata?.analysis_type === "string"
        ? event.metadata.analysis_type.toLowerCase()
        : ""
    const vType =
      typeof event.metadata?.verification_type === "string"
        ? event.metadata.verification_type.toLowerCase()
        : ""
    const act = (event.action || "").toLowerCase()

    if (
      act === "evidence_verified" ||
      vType.includes("hash") ||
      vType.includes("integrity")
    ) {
      analysisCounts.hash++
    } else if (act === "ai_analysis_performed" || aType === "ai") {
      analysisCounts.ai++
    } else if (aType && analysisCounts[aType] !== undefined) {
      analysisCounts[aType]++
    }
  }

  const totalAnalysisRuns = Object.values(analysisCounts).reduce(
    (sum, val) => sum + val,
    0
  )

  // 6. Recent Analysis activity for Dashboard and Analytics
  const analysisEvents = custodyEvents.filter((ev) => {
    const act = (ev.action || "").toLowerCase()
    return (
      act === "evidence_analyzed" ||
      act === "evidence_verified" ||
      act === "ai_analysis_performed" ||
      act === "evidence_exported" ||
      Boolean(ev.metadata?.analysis_type)
    )
  })

  const recentAnalysis: DashboardRecentAnalysis[] = analysisEvents
    .sort(
      (a, b) =>
        new Date(b.timestamp || 0).getTime() -
        new Date(a.timestamp || 0).getTime()
    )
    .slice(0, 10)
    .map((ev) => {
      let type = "ANALYSIS"
      if (typeof ev.metadata?.analysis_type === "string") {
        type = ev.metadata.analysis_type.toUpperCase()
      } else if (ev.action === "evidence_verified") {
        type = "HASH"
      } else if (ev.action === "ai_analysis_performed") {
        type = "AI"
      } else if (ev.action === "evidence_exported") {
        type = "REPORT"
      }

      return {
        id: ev.id || ev.event_id,
        analysis_type: type,
        status: "success",
        result_summary:
          ev.description || `${type} analysis completed successfully.`,
        created_at: ev.timestamp,
        created_by_username:
          ev.actor_role || ev.actor_id || "investigator",
        evidence: ev.evidence,
        evidence_filename: ev.evidence_filename,
        case_title: ev.case_title,
      }
    })

  // 7. Timeline events for TimelinePage
  const explicitTimelineEvents = custodyEvents.filter((ev) => {
    const aType =
      typeof ev.metadata?.analysis_type === "string"
        ? ev.metadata.analysis_type.toLowerCase()
        : ""
    return (
      aType === "timeline" ||
      (ev.action || "").toLowerCase().includes("timeline")
    )
  })

  const timelineSource =
    explicitTimelineEvents.length > 0 ? explicitTimelineEvents : custodyEvents

  const recentTimeline: DashboardRecentAnalysis[] = timelineSource
    .sort(
      (a, b) =>
        new Date(b.timestamp || 0).getTime() -
        new Date(a.timestamp || 0).getTime()
    )
    .slice(0, 20)
    .map((ev) => ({
      id: ev.id || ev.event_id,
      analysis_type: "TIMELINE",
      status: "success",
      result_summary: ev.description || `Custody event: ${ev.action}`,
      created_at: ev.timestamp,
      created_by_username:
        ev.actor_role || ev.actor_id || "investigator",
      evidence: ev.evidence,
      evidence_filename: ev.evidence_filename,
      case_title: ev.case_title,
    }))

  return {
    total_cases: totalCases,
    open_cases: openCases,
    closed_cases: closedCases,
    total_evidence: totalEvidence,
    reports_generated: reportsGenerated,
    storage_bytes: storageBytes,
    priority_counts: priorityCounts,
    recent_cases: recentCases,
    recent_evidence: recentEvidence,
    recent_analysis: recentAnalysis,
    recent_timeline: recentTimeline,
    recent_custody: recentCustody,
    recent_reports: recentReports,
    total_analysis_runs: totalAnalysisRuns,
    total_custody_events: totalCustodyEvents,
    analysis_counts: analysisCounts,
    custody_counts: custodyCounts,
    evidence_type_counts: evidenceTypeCounts,
  }
}
