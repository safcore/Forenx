import { useParams, Link, useNavigate } from "react-router-dom"
import {
  ArrowLeft,
  HardDrive,
  Clock,
  Link2,
  FileText,
  Activity,
  AlertCircle,
  Loader2,
} from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/common/EmptyState"
import { useCaseQuery } from "@/hooks/useCases"
import { useEvidenceQuery } from "@/hooks/useEvidence"
import { formatCaseRef } from "@/api/cases.api"
import { getErrorMessage } from "@/api/client"
import { formatDate } from "@/lib/utils"

const tabs = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "evidence", label: "Evidence", icon: HardDrive, path: "evidence" },
  { id: "timeline", label: "Timeline", icon: Clock, path: "timeline" },
  { id: "custody", label: "Chain of Custody", icon: Link2, path: "custody" },
  { id: "reports", label: "Reports", icon: FileText, path: "reports" },
]

/**
 * Minimal case overview for Phase 3.
 * Evidence / timeline / custody / reports tabs navigate to existing shells only.
 */
export default function CaseDetailPage() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { data: caseData, isLoading, isError, error, refetch } = useCaseQuery(caseId)
  const {
    data: evidenceList,
    isLoading: evidenceLoading,
    isError: evidenceError,
  } = useEvidenceQuery(caseId)

  const evidenceCount = evidenceList?.length ?? 0

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading case…
      </div>
    )
  }

  if (isError || !caseData) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/cases")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Cases
        </Button>
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Case not found"
          description={
            isError
              ? getErrorMessage(error)
              : "This case may not exist or you may not have permission to view it."
          }
          action={
            <div className="flex gap-2">
              {isError ? (
                <Button variant="secondary" onClick={() => void refetch()}>
                  Retry
                </Button>
              ) : null}
              <Button variant="secondary" onClick={() => navigate("/cases")}>
                Back to cases
              </Button>
            </div>
          }
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        to="/cases"
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to cases
      </Link>

      <PageHeader
        title={caseData.title}
        description={formatCaseRef(caseData.id)}
        actions={
          <div className="flex gap-2">
            <Badge variant="default">{caseData.status.replace("_", " ")}</Badge>
            <Badge variant="warning">{caseData.priority}</Badge>
          </div>
        }
      />

      <div className="flex flex-wrap gap-1 border-b border-white/[0.06] pb-px">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => {
              if (t.path) navigate(`/cases/${caseId}/${t.path}`)
            }}
            className={`flex items-center gap-2 rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors ${
              t.id === "overview"
                ? "border-b-2 border-accent text-accent"
                : "text-text-secondary hover:text-white"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-text-secondary">
              {caseData.description?.trim()
                ? caseData.description
                : "No description provided."}
            </p>
            <p className="text-xs text-text-muted">
              Evidence upload, listing, and detail views are available from the
              Evidence tab. Timeline, custody, and reports remain out of scope.
            </p>
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-white">Evidence</p>
                  <p className="mt-1 text-xs text-text-muted">
                    {evidenceLoading
                      ? "Loading evidence count…"
                      : evidenceError
                        ? "Could not load evidence count."
                        : evidenceCount === 0
                          ? "No evidence collected for this case yet."
                          : `${evidenceCount} evidence item${evidenceCount === 1 ? "" : "s"} collected.`}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-2"
                  onClick={() => navigate(`/cases/${caseId}/evidence`)}
                >
                  <HardDrive className="h-4 w-4" />
                  {evidenceCount === 0 ? "Upload evidence" : "View evidence"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-text-muted">Investigator</span>
              <span className="text-right text-white">
                {caseData.investigator_username || "—"}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-text-muted">Evidence items</span>
              <span className="text-right text-white">
                {evidenceLoading ? "…" : evidenceCount}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-text-muted">Case ID</span>
              <span className="break-all font-mono text-xs text-white">
                {caseData.id}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Created</span>
              <span className="text-white">
                {caseData.created_at
                  ? formatDate(caseData.created_at)
                  : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Updated</span>
              <span className="text-white">
                {caseData.updated_at
                  ? formatDate(caseData.updated_at)
                  : "—"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
