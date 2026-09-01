import { Link } from "react-router-dom"
import { AlertCircle, Clock, Loader2 } from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { useDashboardQuery } from "@/hooks/useDashboard"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"

export default function TimelinePage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useDashboardQuery()

  const timelineRuns =
    data?.recent_timeline ??
    (data?.recent_analysis ?? []).filter(
      (run) => run.analysis_type.toLowerCase() === "timeline"
    )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Timeline"
        description="Stored timeline AnalysisRun results only. Opening this page does not reconstruct timestamps or call timeline analysis."
      />

      {isLoading ? (
        <div className="flex min-h-[30vh] items-center justify-center gap-2 text-sm text-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading stored timeline activity…
        </div>
      ) : null}

      {isError ? (
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Could not load timeline activity"
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
      ) : null}

      {!isLoading && !isError && timelineRuns.length === 0 ? (
        <EmptyState
          icon={<Clock className="h-6 w-6" />}
          title="No timeline events found."
          description="Run Analyze Timeline from an evidence detail page. This overview lists stored analysis results only."
          action={
            <Button asChild variant="secondary">
              <Link to="/cases">Browse cases</Link>
            </Button>
          }
        />
      ) : null}

      {!isLoading && !isError && timelineRuns.length > 0 ? (
        <Card>
          <CardContent className="space-y-3 p-4">
            {timelineRuns.map((run) => (
              <div
                key={run.id}
                className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">TIMELINE</Badge>
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
                <p className="mt-2 break-words text-sm text-white">
                  {run.result_summary || "Timeline analysis completed."}
                </p>
                <p className="mt-1 break-words text-xs text-text-muted">
                  {[
                    run.evidence_filename,
                    run.case_title,
                    run.created_by_username,
                    run.created_at ? formatDateTime(run.created_at) : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                {run.evidence ? (
                  <Link
                    to={`/evidence/${run.evidence}`}
                    className="mt-2 inline-block text-xs text-accent hover:underline"
                  >
                    Open evidence
                  </Link>
                ) : null}
              </div>
            ))}
            <p className="text-xs text-text-muted">
              Stored analysis results. New reconstruction requires Analyze
              Timeline on an evidence detail page.
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
