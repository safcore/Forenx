import { Link, useParams } from "react-router-dom"
import { AlertCircle, Link2, Loader2 } from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  formatCustodyAction,
} from "@/components/forensic/CustodyTimeline"
import { useCustodyListQuery } from "@/hooks/useCustody"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"

function actionVariant(
  action: string
): "success" | "warning" | "default" | "secondary" {
  const normalized = action.trim().toLowerCase()
  if (normalized === "evidence_verified") return "success"
  if (normalized === "evidence_analyzed") return "default"
  if (normalized === "evidence_exported") return "warning"
  if (normalized === "ai_analysis_performed") return "secondary"
  return "secondary"
}

export default function CustodyPage() {
  const { caseId } = useParams<{ caseId?: string }>()
  const { data, isLoading, isError, error, refetch, isFetching } =
    useCustodyListQuery(caseId)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Chain of Custody"
        description="Read-only ledger of recorded handling events. Opening or refreshing this page does not create custody events."
      />

      {isLoading ? (
        <div className="flex min-h-[30vh] items-center justify-center gap-2 text-sm text-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading custody events…
        </div>
      ) : null}

      {isError ? (
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Could not load custody events"
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

      {!isLoading && !isError && data && data.length === 0 ? (
        <EmptyState
          icon={<Link2 className="h-6 w-6" />}
          title="No custody events recorded"
          description="Custody events appear after evidence upload and explicit forensic actions. Viewing this page is read-only."
        />
      ) : null}

      {!isLoading && !isError && data && data.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Link2 className="h-4 w-4 text-accent" />
              Recorded events
              <Badge variant="secondary">{data.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-text-muted">
                    <th className="px-4 py-3 font-medium">Action</th>
                    <th className="px-4 py-3 font-medium">Actor</th>
                    <th className="px-4 py-3 font-medium">Timestamp</th>
                    <th className="px-4 py-3 font-medium">Evidence / Case</th>
                    <th className="px-4 py-3 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((event) => {
                    const verification =
                      typeof event.metadata?.verification_type === "string"
                        ? String(event.metadata.verification_type)
                        : null
                    const analysisType =
                      typeof event.metadata?.analysis_type === "string"
                        ? String(event.metadata.analysis_type)
                        : null
                    return (
                      <tr
                        key={event.id || event.event_id}
                        className="border-b border-white/[0.04] align-top"
                      >
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <Badge variant={actionVariant(event.action)}>
                              {formatCustodyAction(event.action)}
                            </Badge>
                            {verification ? (
                              <Badge variant="secondary">
                                {verification.replace(/_/g, " ")}
                              </Badge>
                            ) : null}
                            {analysisType ? (
                              <Badge variant="secondary">
                                {analysisType.replace(/_/g, " ")}
                              </Badge>
                            ) : null}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-text-secondary">
                          <p className="break-all">
                            {event.actor_role || event.actor_id || "—"}
                          </p>
                          {event.actor_role && event.actor_id ? (
                            <p className="mt-0.5 break-all font-mono text-xs text-text-muted">
                              {event.actor_id}
                            </p>
                          ) : null}
                        </td>
                        <td className="px-4 py-3 text-text-muted">
                          {event.timestamp
                            ? formatDateTime(event.timestamp)
                            : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <p className="break-words text-white">
                            {event.evidence_filename || "Evidence"}
                          </p>
                          <p className="mt-0.5 break-words text-xs text-text-muted">
                            {event.case_title || event.case}
                          </p>
                          {event.evidence ? (
                            <Link
                              to={`/evidence/${event.evidence}`}
                              className="mt-1 inline-block text-xs text-accent hover:underline"
                            >
                              Open evidence
                            </Link>
                          ) : null}
                        </td>
                        <td className="px-4 py-3 break-words text-text-secondary">
                          {event.description || "—"}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
