import { useState } from "react"
import { Globe, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAnalyzeEvidenceBrowserMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { EvidenceBrowserAnalysisResult } from "@/types"

interface BrowserAnalysisSectionProps {
  evidenceId: string
}

function totalArtifacts(result: EvidenceBrowserAnalysisResult): number {
  const s = result.summary
  return (
    s.history_count +
    s.download_count +
    s.bookmark_count +
    s.cookie_count +
    s.search_count +
    s.login_page_count
  )
}

export function BrowserAnalysisSection({ evidenceId }: BrowserAnalysisSectionProps) {
  const [result, setResult] = useState<EvidenceBrowserAnalysisResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const analyzeMutation = useAnalyzeEvidenceBrowserMutation(evidenceId)

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

  const artifactTotal = result ? totalArtifacts(result) : 0
  const isEmpty =
    result &&
    (result.status === "empty" || artifactTotal === 0)

  return (
    <Card id="browser-analysis" className="scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Globe className="h-4 w-4 text-accent" />
          Browser Artifact Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Analyze Chrome, Edge, or Firefox profile artifacts from the stored
          evidence. Cookie values and credentials are never returned. This is
          separate from hash verification and keyword search.
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
              Analyzing…
            </>
          ) : (
            <>
              <Globe className="h-4 w-4" />
              Analyze Browser Artifacts
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
                  ? "NO BROWSER ARTIFACTS FOUND"
                  : "BROWSER ANALYSIS COMPLETE"}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {isEmpty
                  ? "No browser artifacts were found."
                  : result.message ||
                    "Browser artifact analysis completed successfully."}
              </p>
              {result.analyzed_at ? (
                <p className="mt-2 text-xs text-text-muted">
                  Analyzed: {formatDateTime(result.analyzed_at)}
                </p>
              ) : null}
            </div>

            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Browser</p>
                <p className="mt-1 text-white">{result.browser || "—"}</p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">History</p>
                <p className="mt-1 text-white">
                  {result.summary.history_count} record
                  {result.summary.history_count === 1 ? "" : "s"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Downloads</p>
                <p className="mt-1 text-white">
                  {result.summary.download_count} record
                  {result.summary.download_count === 1 ? "" : "s"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Bookmarks</p>
                <p className="mt-1 text-white">
                  {result.summary.bookmark_count} record
                  {result.summary.bookmark_count === 1 ? "" : "s"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Cookie metadata</p>
                <p className="mt-1 text-white">
                  {result.summary.cookie_count} record
                  {result.summary.cookie_count === 1 ? "" : "s"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Searches</p>
                <p className="mt-1 text-white">
                  {result.summary.search_count} record
                  {result.summary.search_count === 1 ? "" : "s"}
                </p>
              </div>
            </div>

            {result.history.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                  Recent history sample
                </p>
                {result.history.slice(0, 8).map((item, index) => (
                  <div
                    key={`${item.url}-${index}`}
                    className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{item.domain || item.browser}</Badge>
                      {item.visit_time ? (
                        <span className="text-xs text-text-muted">
                          {formatDateTime(item.visit_time)}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 break-all text-white/90">
                      {item.title || item.url}
                    </p>
                    {item.title ? (
                      <p className="mt-1 break-all font-mono text-xs text-text-muted">
                        {item.url}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}

            {result.cookies.length > 0 ? (
              <p className="text-xs text-text-muted">
                Cookie metadata is shown without values. No passwords, JWTs, or
                session secrets are returned by this analysis.
              </p>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
