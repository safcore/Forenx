import { useState } from "react"
import { useParams, Link, useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "react-hot-toast"
import {
  ArrowLeft,
  HardDrive,
  Clock,
  Link2,
  FileText,
  Activity,
  AlertCircle,
  Loader2,
  Lock,
} from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/common/EmptyState"
import { useCaseQuery } from "@/hooks/useCases"
import { useEvidenceQuery } from "@/hooks/useEvidence"
import { formatCaseRef, closeCase } from "@/api/cases.api"
import { getErrorMessage } from "@/api/client"
import { formatDate } from "@/lib/utils"

const tabs = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "evidence", label: "Evidence", icon: HardDrive, path: "evidence" },
  { id: "timeline", label: "Timeline", icon: Clock, path: "timeline" },
  { id: "custody", label: "Chain of Custody", icon: Link2, path: "custody" },
  { id: "reports", label: "Reports", icon: FileText, path: "reports" },
]

export default function CaseDetailPage() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showCloseModal, setShowCloseModal] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  const { data: caseData, isLoading, isError, error, refetch } = useCaseQuery(caseId)
  const {
    data: evidenceList,
    isLoading: evidenceLoading,
    isError: evidenceError,
  } = useEvidenceQuery(caseId)

  const evidenceCount = evidenceList?.length ?? 0

  const handleCloseCase = async () => {
    if (!caseId) return
    setIsClosing(true)
    try {
      await closeCase(caseId)
      toast.success("Case closed successfully. Evidence and custody records preserved.")
      queryClient.invalidateQueries({ queryKey: ["case", caseId] })
      queryClient.invalidateQueries({ queryKey: ["cases"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] })
      await refetch()
      setShowCloseModal(false)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsClosing(false)
    }
  }

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

  const isClosed = caseData.status.toLowerCase() === "closed"

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
          <div className="flex items-center gap-2">
            <Badge variant={isClosed ? "success" : "default"}>
              {caseData.status.replace("_", " ")}
            </Badge>
            <Badge variant="warning">{caseData.priority}</Badge>
            {!isClosed && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowCloseModal(true)}
                className="gap-1.5 ml-2 border-white/10 hover:border-danger/40 hover:text-danger transition-colors"
              >
                <Lock className="h-3.5 w-3.5" />
                Close Case
              </Button>
            )}
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
              Select Evidence, Timeline, Chain of Custody, or Reports above to work
              with this case.
            </p>

            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">Evidence collection</p>
                  <p className="text-xs text-text-muted">
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
              <span className="text-right text-white font-medium">
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
            <div className="flex justify-between">
              <span className="text-text-muted">Status</span>
              <span className="text-white capitalize">
                {caseData.status.replace("_", " ")}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Close Case Confirmation Modal */}
      {showCloseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#141414] p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-warning mb-4">
              <div className="rounded-xl border border-warning/20 bg-warning/10 p-2.5">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold text-white">Close Investigation Case</h3>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed mb-6">
              Are you sure you want to transition case <strong className="text-white">{caseData.title}</strong> to <strong className="text-white">CLOSED</strong> status?
              <br /><br />
              All collected evidence, cryptographic hashes, timeline events, and chain-of-custody records will remain completely intact and accessible.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setShowCloseModal(false)}
                disabled={isClosing}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                onClick={handleCloseCase}
                disabled={isClosing}
                className="bg-danger hover:bg-danger/80 text-white"
              >
                {isClosing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Closing Case…
                  </>
                ) : (
                  "Confirm Close"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
