import { useState } from "react"
import {
  AlertCircle,
  AlertTriangle,
  Link2,
  Loader2,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { HashDisplay } from "@/components/forensic/HashDisplay"
import { MetadataDisplay } from "@/components/forensic/MetadataDisplay"
import { getErrorMessage } from "@/api/client"
import { formatDateTime, cn } from "@/lib/utils"
import { useVerifyEvidenceCustodyChainMutation } from "@/hooks/useEvidence"
import type { CustodyEvent, CustodyChainVerificationResult } from "@/types"

const KNOWN_ACTION_LABELS: Record<string, string> = {
  evidence_uploaded: "Evidence Uploaded",
  evidence_hashed: "Evidence Hashed",
  evidence_accessed: "Evidence Accessed",
  evidence_acquired: "Evidence Acquired",
  evidence_registered: "Evidence Registered",
  evidence_verified: "Evidence Verified",
  evidence_examined: "Evidence Examined",
  evidence_analyzed: "Evidence Analyzed",
  evidence_exported: "Evidence Exported",
  evidence_transferred: "Evidence Transferred",
  evidence_closed: "Evidence Closed",
  ai_analysis_performed: "AI Analysis Performed",
}

export function formatCustodyAction(action: string): string {
  const normalized = action.trim().toLowerCase()
  if (KNOWN_ACTION_LABELS[normalized]) {
    return KNOWN_ACTION_LABELS[normalized]
  }
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatActor(event: CustodyEvent): string {
  if (event.actor_role && event.actor_id) {
    return `${event.actor_role} · ${event.actor_id}`
  }
  if (event.actor_role) return event.actor_role
  if (event.actor_id) return event.actor_id
  return "—"
}

interface CustodyTimelineProps {
  events: CustodyEvent[]
  brokenEventId?: string | null
}

export function CustodyTimeline({ events, brokenEventId }: CustodyTimelineProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        icon={<Link2 className="h-6 w-6" />}
        title="No chain-of-custody events recorded"
        description="Custody events will appear here once the backend records handling activity for this evidence."
      />
    )
  }

  return (
    <div className="relative space-y-4">
      <div
        aria-hidden
        className="absolute bottom-2 left-[1.125rem] top-2 w-px bg-white/10"
      />
      {events.map((event, index) => {
        const isBroken = Boolean(brokenEventId && event.event_id === brokenEventId)
        return (
          <div key={event.event_id || `${event.timestamp}-${index}`} className="relative pl-12">
            <div
              className={cn(
                "absolute left-3 top-5 h-3 w-3 rounded-full border-2 bg-background",
                isBroken ? "border-danger bg-danger animate-pulse" : "border-accent"
              )}
            />
            <Card
              className={cn(
                "p-4 sm:p-5 transition-colors",
                isBroken && "border-danger/60 bg-danger/[0.04] ring-1 ring-danger/40"
              )}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold text-white">
                      {formatCustodyAction(event.action)}
                    </h3>
                    {isBroken ? (
                      <Badge variant="danger" className="gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        Tampered / Broken Event
                      </Badge>
                    ) : null}
                    {event.source ? (
                      <Badge variant="secondary">{event.source}</Badge>
                    ) : null}
                    {typeof event.metadata?.verification_type === "string" ? (
                      <Badge variant="secondary">
                        {String(event.metadata.verification_type).replace(/_/g, " ")}
                      </Badge>
                    ) : null}
                    {typeof event.metadata?.analysis_type === "string" ? (
                      <Badge variant="secondary">
                        {String(event.metadata.analysis_type).replace(/_/g, " ")}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-text-muted">
                    {event.timestamp ? formatDateTime(event.timestamp) : "—"}
                  </p>
                </div>
                <p className="text-xs text-text-secondary">
                  Event #{index + 1}
                </p>
              </div>

            <div className="mt-4 space-y-3 text-sm">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                  Actor
                </p>
                <p className="mt-1 break-all font-mono text-xs text-white/90">
                  {formatActor(event)}
                </p>
              </div>

              {event.description ? (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                    Description
                  </p>
                  <p className="mt-1 text-sm text-text-secondary">
                    {event.description}
                  </p>
                </div>
              ) : null}

              <div className="grid gap-2 lg:grid-cols-2">
                <HashDisplay
                  label="Evidence SHA-256"
                  algorithm="Evidence SHA-256"
                  value={event.evidence_sha256 || null}
                />
                <HashDisplay
                  label="Event hash"
                  algorithm="Event hash"
                  value={event.event_hash || null}
                />
                {event.previous_event_hash ? (
                  <HashDisplay
                    label="Previous event hash"
                    algorithm="Previous event hash"
                    value={event.previous_event_hash}
                    className="lg:col-span-2"
                  />
                ) : null}
              </div>

              {event.metadata && Object.keys(event.metadata).length > 0 ? (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-muted">
                    Event metadata
                  </p>
                  <MetadataDisplay metadata={event.metadata} />
                </div>
              ) : null}
            </div>
          </Card>
          </div>
        )
      })}
    </div>
  )
}

interface CustodySectionProps {
  evidenceId: string
  isLoading: boolean
  isError: boolean
  error: unknown
  events: CustodyEvent[] | undefined
  onRetry: () => void
  isFetching: boolean
}

export function CustodySection({
  evidenceId,
  isLoading,
  isError,
  error,
  events,
  onRetry,
  isFetching,
}: CustodySectionProps) {
  const [verificationResult, setVerificationResult] =
    useState<CustodyChainVerificationResult | null>(null)
  const [verificationError, setVerificationError] = useState<string | null>(null)

  const verifyMutation = useVerifyEvidenceCustodyChainMutation(evidenceId)

  const handleVerifyChain = async () => {
    setVerificationError(null)
    try {
      const res = await verifyMutation.mutateAsync()
      setVerificationResult(res)
    } catch (err) {
      setVerificationError(getErrorMessage(err))
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-sm text-text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading chain of custody…
      </div>
    )
  }

  if (isError) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-6 w-6 text-danger" />}
        title="Could not load chain of custody"
        description={getErrorMessage(error)}
        action={
          <Button variant="secondary" onClick={onRetry} disabled={isFetching}>
            Try again
          </Button>
        }
      />
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-text-secondary">
          Read-only custody history for evidence{" "}
          <span className="font-mono text-xs text-white/90">{evidenceId}</span>.
          Events are shown oldest to newest.
        </p>

        <Button
          onClick={() => void handleVerifyChain()}
          disabled={verifyMutation.isPending}
          aria-busy={verifyMutation.isPending}
          className="gap-2 self-start sm:self-auto shrink-0"
        >
          {verifyMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Verifying chain…
            </>
          ) : (
            <>
              <ShieldCheck className="h-4 w-4" />
              Verify Custody Chain
            </>
          )}
        </Button>
      </div>

      {verificationError ? (
        <div
          className="flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger"
          role="alert"
        >
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Chain verification failed</p>
            <p className="mt-0.5 text-xs text-danger/90">{verificationError}</p>
          </div>
        </div>
      ) : null}

      {verificationResult ? (
        <div
          className={cn(
            "rounded-xl border p-4 sm:p-5 space-y-4",
            verificationResult.valid
              ? "border-success/30 bg-success/10"
              : "border-danger/30 bg-danger/10"
          )}
        >
          <div className="flex items-start gap-3">
            {verificationResult.valid ? (
              <ShieldCheck className="h-6 w-6 shrink-0 text-success mt-0.5" />
            ) : (
              <ShieldAlert className="h-6 w-6 shrink-0 text-danger mt-0.5" />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p
                  className={cn(
                    "font-display text-base font-semibold sm:text-lg",
                    verificationResult.valid ? "text-success" : "text-danger"
                  )}
                >
                  {verificationResult.valid
                    ? "CRYPTOGRAPHIC CHAIN INTACT"
                    : "TAMPERED / CHAIN BROKEN"}
                </p>
                <Badge
                  variant={verificationResult.valid ? "success" : "danger"}
                >
                  {verificationResult.status ||
                    (verificationResult.valid ? "valid" : "invalid")}
                </Badge>
                <Badge variant="secondary">
                  {verificationResult.event_count} event(s) checked
                </Badge>
              </div>

              <p className="mt-1 text-sm text-text-secondary">
                {verificationResult.message}
              </p>

              {verificationResult.broken_event_id ? (
                <div className="mt-3 rounded-lg border border-danger/40 bg-danger/15 p-3 text-xs">
                  <p className="font-semibold text-danger">
                    Broken Event Detected:
                  </p>
                  <p className="mt-1 font-mono text-white/90 break-all">
                    {verificationResult.broken_event_id}
                  </p>
                </div>
              ) : null}

              {verificationResult.warnings &&
              verificationResult.warnings.length > 0 ? (
                <div className="mt-3 space-y-1">
                  {verificationResult.warnings.map((w, idx) => (
                    <p
                      key={idx}
                      className="flex items-center gap-1.5 text-xs text-warning"
                    >
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                      {w}
                    </p>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          {(verificationResult.first_event || verificationResult.last_event) ? (
            <div className="grid gap-2 border-t border-white/[0.08] pt-3 lg:grid-cols-2">
              {verificationResult.first_event ? (
                <HashDisplay
                  label="Genesis Event Hash"
                  algorithm={`Genesis Event (${
                    verificationResult.first_event.timestamp
                      ? formatDateTime(verificationResult.first_event.timestamp)
                      : "initial"
                  })`}
                  value={verificationResult.first_event.event_hash}
                  truncate={false}
                />
              ) : null}
              {verificationResult.last_event ? (
                <HashDisplay
                  label="Latest Event Hash"
                  algorithm={`Latest Event (${
                    verificationResult.last_event.timestamp
                      ? formatDateTime(verificationResult.last_event.timestamp)
                      : "recent"
                  })`}
                  value={verificationResult.last_event.event_hash}
                  truncate={false}
                />
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <CustodyTimeline
        events={events ?? []}
        brokenEventId={verificationResult?.broken_event_id}
      />
    </div>
  )
}
