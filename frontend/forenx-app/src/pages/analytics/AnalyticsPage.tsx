import { Link } from "react-router-dom"
import {
  Activity,
  AlertCircle,
  BarChart3,
  Briefcase,
  FileText,
  FolderOpen,
  HardDrive,
  Link2,
  Loader2,
} from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useDashboardQuery } from "@/hooks/useDashboard"
import { formatCustodyAction } from "@/components/forensic/CustodyTimeline"
import { getErrorMessage } from "@/api/client"
import { formatBytes, formatDateTime } from "@/lib/utils"

const ANALYSIS_ORDER = [
  "hash",
  "keyword",
  "browser",
  "timeline",
  "metadata",
  "report",
  "ai",
] as const

function analysisLabel(type: string): string {
  return type.toUpperCase()
}

export default function AnalyticsPage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useDashboardQuery()

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading analytics…
      </div>
    )
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-6 w-6 text-danger" />}
        title="Could not load analytics"
        description={getErrorMessage(error)}
        action={
          <Button
            variant="secondary"
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            Try again
          </Button>
        }
      />
    )
  }

  const cards = [
    {
      label: "Total cases",
      value: String(data.total_cases),
      icon: Briefcase,
    },
    {
      label: "Open cases",
      value: String(data.open_cases),
      icon: FolderOpen,
    },
    {
      label: "Evidence items",
      value: String(data.total_evidence),
      icon: HardDrive,
    },
    {
      label: "Reports generated",
      value: String(data.reports_generated),
      icon: FileText,
    },
    {
      label: "Analysis runs",
      value: String(data.total_analysis_runs),
      icon: Activity,
    },
    {
      label: "Custody events",
      value: String(data.total_custody_events),
      icon: Link2,
    },
  ]

  const analysisRows = ANALYSIS_ORDER.map((type) => ({
    type,
    count: data.analysis_counts[type] ?? 0,
  }))
  const analysisMax = Math.max(1, ...analysisRows.map((row) => row.count))
  const custodyRows = Object.entries(data.custody_counts)
    .map(([action, count]) => ({ action, count }))
    .sort((a, b) => b.count - a.count)
  const evidenceTypeRows = Object.entries(data.evidence_type_counts)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
  const emptyPlatform =
    data.total_cases === 0 &&
    data.total_evidence === 0 &&
    data.total_analysis_runs === 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Live counts from stored case, evidence, analysis, custody, and report records. Opening this page does not run forensic analysis."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <Card key={card.label} className="p-5">
            <div className="flex items-center gap-2 text-text-muted">
              <card.icon className="h-4 w-4" />
              <p className="text-xs uppercase tracking-wider">{card.label}</p>
            </div>
            <p className="mt-2 font-display text-2xl font-semibold text-white">
              {card.value}
            </p>
          </Card>
        ))}
      </div>

      {emptyPlatform ? (
        <EmptyState
          icon={<BarChart3 className="h-6 w-6" />}
          title="Not enough data to generate analytics"
          description="Counts populate when cases, evidence, and analysis records exist. This view does not invent comparisons."
          action={
            <Button asChild variant="secondary">
              <Link to="/cases">Browse cases</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Analysis by type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {analysisRows.map((row) => (
                <div key={row.type}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="text-text-secondary">
                      {analysisLabel(row.type)}
                    </span>
                    <span className="font-medium text-white">{row.count}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{
                        width: `${Math.round((row.count / analysisMax) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Custody activity</CardTitle>
            </CardHeader>
            <CardContent>
              {custodyRows.length === 0 ? (
                <p className="text-sm text-text-muted">
                  No custody events recorded yet.
                </p>
              ) : (
                <ul className="space-y-2">
                  {custodyRows.map((row) => (
                    <li
                      key={row.action}
                      className="flex items-center justify-between gap-3 text-sm"
                    >
                      <span className="break-words text-text-secondary">
                        {formatCustodyAction(row.action)}
                      </span>
                      <span className="font-medium text-white">{row.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Evidence by type</CardTitle>
            </CardHeader>
            <CardContent>
              {evidenceTypeRows.length === 0 ? (
                <p className="text-sm text-text-muted">
                  No evidence registered yet.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {evidenceTypeRows.map((row) => (
                    <Badge key={row.type} variant="secondary">
                      {row.type}: {row.count}
                    </Badge>
                  ))}
                </div>
              )}
              <p className="mt-3 text-xs text-text-muted">
                Storage used: {formatBytes(data.storage_bytes)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent analysis</CardTitle>
            </CardHeader>
            <CardContent>
              {data.recent_analysis.length === 0 ? (
                <p className="text-sm text-text-muted">
                  No analysis activity recorded yet.
                </p>
              ) : (
                <ul className="space-y-3">
                  {data.recent_analysis.slice(0, 6).map((run) => (
                    <li key={run.id} className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">
                          {analysisLabel(run.analysis_type)}
                        </Badge>
                        <Badge
                          variant={
                            run.status === "success"
                              ? "success"
                              : run.status === "failed"
                                ? "danger"
                                : "secondary"
                          }
                        >
                          {run.status}
                        </Badge>
                      </div>
                      <p className="mt-1 break-words text-sm text-white">
                        {run.result_summary || "Analysis completed."}
                      </p>
                      <p className="mt-0.5 text-xs text-text-muted">
                        {[
                          run.evidence_filename,
                          run.created_at
                            ? formatDateTime(run.created_at)
                            : null,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
