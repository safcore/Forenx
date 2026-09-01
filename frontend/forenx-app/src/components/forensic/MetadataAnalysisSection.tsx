import { useState } from "react"
import { FileSearch, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAnalyzeEvidenceMetadataMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatBytes, formatDateTime } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { EvidenceMetadataAnalysisResult } from "@/types"

interface MetadataAnalysisSectionProps {
  evidenceId: string
}

const DISPLAY_FIELD_LIMIT = 40

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function flattenFields(
  section: Record<string, unknown> | null | undefined,
  prefix: string
): Array<{ key: string; value: string }> {
  if (!section) return []
  const skip = new Set(["status", "message", "timestamp"])
  const rows: Array<{ key: string; value: string }> = []
  for (const [key, value] of Object.entries(section)) {
    if (skip.has(key) || value == null || value === "") continue
    if (typeof value === "object") continue
    rows.push({
      key: `${prefix}.${key}`,
      value:
        key.includes("time") || key.includes("date")
          ? formatDateTime(String(value))
          : key === "file_size"
            ? formatBytes(Number(value))
            : String(value),
    })
  }
  return rows
}

function collectDisplayRows(
  result: EvidenceMetadataAnalysisResult
): Array<{ key: string; value: string }> {
  const rows = [
    ...flattenFields(
      result.filesystem as Record<string, unknown> | null | undefined,
      "filesystem"
    ),
    ...flattenFields(
      result.image as Record<string, unknown> | null | undefined,
      "image"
    ),
    ...flattenFields(
      result.pdf as Record<string, unknown> | null | undefined,
      "pdf"
    ),
    ...flattenFields(
      result.document as Record<string, unknown> | null | undefined,
      "document"
    ),
  ]
  return rows.slice(0, DISPLAY_FIELD_LIMIT)
}

export function MetadataAnalysisSection({
  evidenceId,
}: MetadataAnalysisSectionProps) {
  const [result, setResult] = useState<EvidenceMetadataAnalysisResult | null>(
    null
  )
  const [submitError, setSubmitError] = useState<string | null>(null)

  const analyzeMutation = useAnalyzeEvidenceMetadataMutation(evidenceId)

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

  const isEmpty =
    result &&
    !result.embedded_metadata_found &&
    result.metadata_fields_found === 0
  const noEmbedded =
    result &&
    !result.embedded_metadata_found &&
    result.metadata_fields_found > 0
  const displayRows = result ? collectDisplayRows(result) : []

  return (
    <Card id="metadata-analysis" className="scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileSearch className="h-4 w-4 text-accent" />
          Metadata Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Extract filesystem and embedded metadata (image EXIF, PDF, DOCX) from
          the stored evidence file. This does not modify acquisition metadata or
          hashes.
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
              Analyzing Metadata…
            </>
          ) : (
            <>
              <FileSearch className="h-4 w-4" />
              Analyze Metadata
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
                isEmpty || noEmbedded
                  ? "border-white/10 bg-white/[0.02]"
                  : "border-accent/30 bg-accent/10"
              )}
            >
              <p className="font-display text-lg font-semibold text-white">
                {isEmpty || noEmbedded
                  ? "NO EMBEDDED METADATA FOUND"
                  : "METADATA ANALYSIS COMPLETE"}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {isEmpty
                  ? "No embedded metadata was found."
                  : noEmbedded
                    ? "Filesystem metadata was extracted, but no supported embedded metadata was found."
                    : result.message ||
                      "Metadata analysis completed successfully."}
              </p>
              {result.analyzed_at ? (
                <p className="mt-2 text-xs text-text-muted">
                  Analyzed: {formatDateTime(result.analyzed_at)}
                </p>
              ) : null}
            </div>

            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">File type</p>
                <p className="mt-1 text-white">{result.file_type || "—"}</p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">MIME type</p>
                <p className="mt-1 text-white">
                  {result.filesystem?.mime_type ||
                    result.image?.mime_type ||
                    "—"}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                <p className="text-xs text-text-muted">Metadata fields</p>
                <p className="mt-1 text-white">{result.metadata_fields_found}</p>
              </div>
            </div>

            {result.metadata_categories.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {result.metadata_categories.map((category) => (
                  <Badge key={category} variant="secondary">
                    {humanizeKey(category)}
                  </Badge>
                ))}
              </div>
            ) : null}

            {displayRows.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                  Metadata fields
                </p>
                <div className="max-h-80 space-y-1 overflow-y-auto rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-sm">
                  {displayRows.map((row) => (
                    <div
                      key={row.key}
                      className="flex justify-between gap-4 border-b border-white/[0.04] py-1.5 last:border-0"
                    >
                      <span className="shrink-0 text-text-muted">
                        {humanizeKey(row.key.split(".").pop() || row.key)}
                      </span>
                      <span className="break-all text-right text-white">
                        {row.value}
                      </span>
                    </div>
                  ))}
                </div>
                {result.metadata_fields_found > DISPLAY_FIELD_LIMIT ? (
                  <p className="text-xs text-text-muted">
                    Showing first {DISPLAY_FIELD_LIMIT} of{" "}
                    {result.metadata_fields_found} fields.
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
