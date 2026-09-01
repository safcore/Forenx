import { useState } from "react"
import { Clock, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAnalyzeEvidenceTimelineMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { EvidenceTimelineAnalysisResult } from "@/types"

interface TimelineAnalysisSectionProps {
  evidenceId: string
}

function humanizeEventType(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function TimelineAnalysisSection({
  evidenceId,
}: TimelineAnalysisSectionProps) {
  const [result, setResult] = useState<EvidenceTimelineAnalysisResult | null>(
    null
  )
  const [submitError, setSubmitError] = useState<string | null>(null)

  const analyzeMutation = useAnalyzeEvidenceTimelineMutation(evidenceId)

  const handleAnalyze = async () => {
    setSubmitError(null)
    setResult(null)
    try {
      const analysis = await analyzeMutation.mutateAsync()
      setResult(analysis)
    } catch (err) {
      setSubmitError(getErrorMessage(err))
    }
  }

  const eventCount = result?.summary.total_events ?? 0
  const isEmpty =
    result &&
    (result.status === "empty" || eventCount === 0 || result.events.length === 0)

  return (
    <Card id="timeline-analysis" className="scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="h-4 w-4 text-accent" />
          Timeline Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Reconstruct chronological filesystem and metadata timestamps for this
          evidence. Events are ordered oldest to newest. This is separate from
          keyword search and browser analysis.
        </p>

        <Button
          className="gap-2"
          disabled={analyzeMutation.isPending}
          aria-busy={analyzeMutation.isPending}
          onClick={() => void handleAnalyze()}
        >
          {analyzeMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing Timeline…
            </>
          ) : (
            <>
              <Clock className="h-4 w-4" />
              Analyze Timeline
            </>
          )}
        </Button>

        {submitError ? (
          <p className="text-sm text-danger" role="alert">
            {submitError}
          </p>
        ) : null}

        {result ? (
          <div className="space-y-4">
            <div
              className={cn(
                "rounded-xl border p-4",
                isEmpty
                  ? "border-white/10 bg-white/[0.02]"
                  : "border-accent/30 bg-accent/10"
              )}
            >
              <p className="font-display text-lg font-semibold text-white">
                {isEmpty
                  ? "NO TIMELINE EVENTS FOUND"
                  : "TIMELINE ANALYSIS COMPLETE"}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {isEmpty
                  ? "No timeline events were found."
                  : result.message ||
                    "Timeline reconstruction completed successfully."}
              </p>
              {result.analyzed_at ? (
                <p className="mt-2 text-xs text-text-muted">
                  Analyzed: {formatDateTime(result.analyzed_at)}
                </p>
              ) : null}
            </div>

            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Timeline events</p>
                <p className="mt-1 text-white">{eventCount}</p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Oldest event</p>
                <p className="mt-1 text-white">
                  {result.summary.earliest_event
                    ? formatDateTime(result.summary.earliest_event)
                    : "—"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Newest event</p>
                <p className="mt-1 text-white">
                  {result.summary.latest_event
                    ? formatDateTime(result.summary.latest_event)
                    : "—"}
                </p>
              </div>
            </div>

            {Object.keys(result.summary.events_by_type).length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {Object.entries(result.summary.events_by_type).map(
                  ([type, count]) => (
                    <Badge key={type} variant="secondary">
                      {humanizeEventType(type)}: {count}
                    </Badge>
                  )
                )}
              </div>
            ) : null}

            {result.events.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                  Timeline events
                </p>
                {result.events.slice(0, 50).map((event) => (
                  <div
                    key={event.event_id || `${event.timestamp}-${event.event_type}`}
                    className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">
                        {humanizeEventType(event.event_type)}
                      </Badge>
                      <span className="text-xs text-text-muted">
                        {event.timestamp
                          ? formatDateTime(event.timestamp)
                          : "—"}
                      </span>
                      {event.source ? (
                        <span className="text-xs text-text-muted">
                          {event.source}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-white/90">{event.description}</p>
                  </div>
                ))}
                {result.events.length > 50 ? (
                  <p className="text-xs text-text-muted">
                    Showing first 50 of {result.events.length} returned events.
                  </p>
                ) : null}
                {result.events_truncated && result.events_total ? (
                  <p className="text-xs text-text-muted">
                    Backend truncated timeline to a safe limit (
                    {result.events.length} of {result.events_total}).
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
