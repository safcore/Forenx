import { History, Loader2, AlertCircle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/common/EmptyState"
import { useEvidenceAnalysisHistoryQuery } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime, sanitizeInvestigatorText } from "@/lib/utils"

interface AnalysisHistorySectionProps {
  evidenceId: string
}

const TYPE_LABELS: Record<string, string> = {
  hash: "HASH",
  keyword: "KEYWORD",
  browser: "BROWSER",
  timeline: "TIMELINE",
  metadata: "METADATA",
  report: "REPORT",
  ai: "AI",
  custody: "CUSTODY",
}

function statusVariant(
  status: string
): "success" | "danger" | "warning" | "secondary" {
  if (status === "success") return "success"
  if (status === "failed") return "danger"
  if (status === "running" || status === "pending") return "warning"
  return "secondary"
}

export function AnalysisHistorySection({
  evidenceId,
}: AnalysisHistorySectionProps) {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useEvidenceAnalysisHistoryQuery(evidenceId)

  return (
    <Card id="analysis-history" className="scroll-mt-24 lg:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="h-4 w-4 text-accent" />
          Analysis History
          {data ? (
            <Badge variant="secondary">{data.length} run(s)</Badge>
          ) : null}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading analysis history…
          </div>
        ) : null}

        {isError ? (
          <EmptyState
            icon={<AlertCircle className="h-6 w-6 text-danger" />}
            title="Could not load analysis history"
            description={getErrorMessage(error)}
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void refetch()}
                disabled={isFetching}
              >
                Try again
              </Button>
            }
          />
        ) : null}

        {!isLoading && !isError && data && data.length === 0 ? (
          <EmptyState
            icon={<History className="h-6 w-6" />}
            title="No analysis history"
            description="Explicit forensic actions on this evidence will appear here. Opening this page does not run analysis."
          />
        ) : null}

        {!isLoading && !isError && data && data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-text-muted">
                  <th className="py-2 pr-3 font-medium">Type</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 pr-3 font-medium">Actor</th>
                  <th className="py-2 pr-3 font-medium">Timestamp</th>
                  <th className="py-2 font-medium">Summary</th>
                </tr>
              </thead>
              <tbody>
                {data.map((run) => (
                  <tr
                    key={run.id}
                    className="border-b border-white/[0.04] align-top"
                  >
                    <td className="py-3 pr-3">
                      <Badge variant="secondary">
                        {TYPE_LABELS[run.analysis_type] ??
                          run.analysis_type.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-3 pr-3">
                      <Badge variant={statusVariant(run.status)}>
                        {run.status}
                      </Badge>
                    </td>
                    <td className="py-3 pr-3 text-text-secondary">
                      {run.created_by_username || run.created_by || "—"}
                    </td>
                    <td className="py-3 pr-3 text-text-muted">
                      {run.created_at
                        ? formatDateTime(run.created_at)
                        : "—"}
                    </td>
                    <td className="py-3 break-words text-text-secondary">
                      {sanitizeInvestigatorText(
                        run.result_summary || run.error_message,
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
