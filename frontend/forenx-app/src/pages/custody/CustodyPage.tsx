import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  AlertCircle,
  AlertTriangle,
  Link2,
  Loader2,
  ShieldCheck,
  X,
} from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatCustodyAction } from "@/components/forensic/CustodyTimeline"
import { useCustodyListQuery } from "@/hooks/useCustody"
import { verifyCustodyChain } from "@/api/custody.api"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import { toast } from "react-hot-toast"

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

interface VerificationResultState {
  valid: boolean
  status: "VALID" | "INVALID"
  message: string
  event_count: number
  verified_chains: number
  broken_chains: Array<Record<string, unknown>>
}

export default function CustodyPage() {
  const { caseId } = useParams<{ caseId?: string }>()
  const { data, isLoading, isError, error, refetch, isFetching } =
    useCustodyListQuery(caseId)

  const [isVerifying, setIsVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<VerificationResultState | null>(null)

  const handleVerify = async () => {
    setIsVerifying(true)
    try {
      const result = await verifyCustodyChain(caseId)
      setVerifyResult(result)
      if (result.valid) {
        toast.success("Custody chain verification passed: VALID")
      } else {
        toast.error("Custody chain verification failed: INVALID")
      }
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsVerifying(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Chain of Custody"
        description="Read-only ledger of recorded handling events. Opening or refreshing this page does not create custody events."
        actions={
          <Button
            variant="default"
            size="sm"
            onClick={handleVerify}
            disabled={isVerifying}
            className="gap-2"
          >
            {isVerifying ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Verifying Chain…
              </>
            ) : (
              <>
                <ShieldCheck className="h-4 w-4" />
                Verify Custody Chain
              </>
            )}
          </Button>
        }
      />

      {/* Verification Result Banner */}
      {verifyResult && (
        <div
          className={`relative rounded-xl border p-4 transition-all ${
            verifyResult.valid
              ? "border-success/30 bg-success/10 text-white"
              : "border-danger/30 bg-danger/10 text-white"
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              {verifyResult.valid ? (
                <ShieldCheck className="h-5 w-5 text-success shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold tracking-wide">
                    {verifyResult.status}:
                  </span>
                  <span
                    className={
                      verifyResult.valid ? "text-success font-medium" : "text-danger font-medium"
                    }
                  >
                    {verifyResult.message}
                  </span>
                </div>
                <p className="mt-1 text-xs text-text-secondary">
                  {verifyResult.valid
                    ? `Cryptographic chain intact. Verified ${verifyResult.verified_chains} evidence ledger${
                        verifyResult.verified_chains === 1 ? "" : "s"
                      } across ${verifyResult.event_count} recorded custody event${
                        verifyResult.event_count === 1 ? "" : "s"
                      }.`
                    : `Chain integrity failure detected in ${verifyResult.broken_chains.length} evidence ledger(s). Cryptographic hash linkage mismatch.`}
                </p>
              </div>
            </div>
            <button
              onClick={() => setVerifyResult(null)}
              className="text-text-muted hover:text-white transition-colors"
              aria-label="Dismiss banner"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

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
