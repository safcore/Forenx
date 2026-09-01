import { useState } from "react"
import { Download, FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { downloadEvidenceReport } from "@/api/evidence.api"
import { useGenerateEvidenceReportMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { EvidenceReportGenerationResult } from "@/types"

interface ReportGenerationSectionProps {
  evidenceId: string
}

const SECTION_LABELS: Array<{
  key: keyof EvidenceReportGenerationResult["sections"]
  label: string
}> = [
  { key: "reference_hash_comparison", label: "Reference Hash Comparison" },
  { key: "file_integrity_verification", label: "File Integrity Verification" },
  { key: "keyword_analysis", label: "Keyword Analysis" },
  { key: "browser_analysis", label: "Browser Analysis" },
  { key: "timeline_analysis", label: "Timeline Analysis" },
  { key: "metadata_analysis", label: "Metadata Analysis" },
]

export function ReportGenerationSection({
  evidenceId,
}: ReportGenerationSectionProps) {
  const [result, setResult] = useState<EvidenceReportGenerationResult | null>(
    null
  )
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const generateMutation = useGenerateEvidenceReportMutation(evidenceId)

  const handleGenerate = async () => {
    setSubmitError(null)
    setDownloadError(null)
    setResult(null)
    try {
      const report = await generateMutation.mutateAsync("both")
      setResult(report)
    } catch (err) {
      setSubmitError(getErrorMessage(err))
    }
  }

  const handleDownload = async () => {
    if (!result?.id) return
    setDownloadError(null)
    setDownloading(true)
    try {
      const prefer: "pdf" | "json" = result.has_pdf ? "pdf" : "json"
      const blob = await downloadEvidenceReport(result.id, prefer)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download =
        result.file_name ||
        `forenx-report.${prefer === "pdf" ? "pdf" : "json"}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setDownloadError(getErrorMessage(err))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Card id="report-generation" className="scroll-mt-24 lg:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="h-4 w-4 text-accent" />
          Forensic Report
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Generate a forensic report from stored case, evidence, custody, and
          analysis results. This does not re-run forensic analysis or modify
          acquisition hashes.
        </p>

        <div className="space-y-1 text-sm text-text-secondary">
          <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
            Includes
          </p>
          <ul className="list-inside list-disc space-y-0.5">
            <li>Case and evidence information</li>
            <li>Acquisition hashes</li>
            <li>Chain of custody</li>
            <li>Prior integrity / keyword / browser / timeline / metadata results</li>
          </ul>
        </div>

        <Button
          className="gap-2"
          disabled={generateMutation.isPending}
          aria-busy={generateMutation.isPending}
          onClick={() => void handleGenerate()}
        >
          {generateMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating Report…
            </>
          ) : (
            <>
              <FileText className="h-4 w-4" />
              Generate Report
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
            <div className="rounded-xl border border-accent/30 bg-accent/10 p-4">
              <p className="font-display text-lg font-semibold text-white">
                REPORT GENERATED
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {result.title || "Forensic report created successfully."}
              </p>
              <p className="mt-2 text-xs text-text-muted">
                Generated: {formatDateTime(result.generated_at)}
              </p>
            </div>

            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Format</p>
                <p className="mt-1 text-white uppercase">{result.format}</p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">File</p>
                <p className="mt-1 break-all text-white">
                  {result.file_name || "—"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Artifacts</p>
                <p className="mt-1 text-white">
                  {[
                    result.has_json ? "JSON" : null,
                    result.has_pdf ? "PDF" : null,
                  ]
                    .filter(Boolean)
                    .join(" + ") || "—"}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                Analysis coverage
              </p>
              {SECTION_LABELS.map(({ key, label }) => {
                const value = result.sections[key]
                const performed = !value.toLowerCase().includes("not performed")
                return (
                  <div
                    key={key}
                    className="flex items-start justify-between gap-4 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm"
                  >
                    <span className="text-text-secondary">{label}</span>
                    <Badge
                      variant="secondary"
                      className={cn(
                        "max-w-[60%] whitespace-normal text-right",
                        performed ? "text-white" : "text-text-muted"
                      )}
                    >
                      {value}
                    </Badge>
                  </div>
                )
              })}
              <div className="flex items-start justify-between gap-4 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <span className="text-text-secondary">AI-Assisted Investigation</span>
                <Badge variant="secondary" className="text-text-muted">
                  AI analysis not included.
                </Badge>
              </div>
            </div>

            <Button
              variant="secondary"
              className="gap-2"
              disabled={downloading}
              onClick={() => void handleDownload()}
            >
              {downloading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Preparing Download…
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Download Report
                </>
              )}
            </Button>
            {downloadError ? (
              <p className="text-sm text-danger" role="alert">
                {downloadError}
              </p>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
