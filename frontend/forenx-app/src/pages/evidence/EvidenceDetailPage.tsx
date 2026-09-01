import { Link, useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft,
  AlertCircle,
  Loader2,
  HardDrive,
  Shield,
  Link2,
} from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { HashDisplay } from "@/components/forensic/HashDisplay"
import { AIAssistSection } from "@/components/forensic/AIAssistSection"
import { BrowserAnalysisSection } from "@/components/forensic/BrowserAnalysisSection"
import { EvidenceIntegritySection } from "@/components/forensic/EvidenceIntegritySection"
import { KeywordSearchSection } from "@/components/forensic/KeywordSearchSection"
import { MetadataAnalysisSection } from "@/components/forensic/MetadataAnalysisSection"
import { ReportGenerationSection } from "@/components/forensic/ReportGenerationSection"
import { TimelineAnalysisSection } from "@/components/forensic/TimelineAnalysisSection"
import { HashVerificationSection } from "@/components/forensic/HashVerificationSection"
import { MetadataDisplay } from "@/components/forensic/MetadataDisplay"
import { CustodySection } from "@/components/forensic/CustodyTimeline"
import { AnalysisHistorySection } from "@/components/forensic/AnalysisHistorySection"
import { useEvidenceCustodyQuery, useEvidenceDetailQuery } from "@/hooks/useEvidence"
import { useCaseQuery } from "@/hooks/useCases"
import { formatCaseRef } from "@/api/cases.api"
import { getErrorMessage } from "@/api/client"
import { formatBytes, formatDateTime } from "@/lib/utils"
import type { ReactNode } from "react"

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/[0.04] py-2.5 last:border-0">
      <span className="shrink-0 text-text-muted">{label}</span>
      <span className="break-all text-right text-white">{value ?? "—"}</span>
    </div>
  )
}

function evidenceStatus(storageAvailable: boolean): {
  label: string
  variant: "success" | "warning"
} {
  return storageAvailable
    ? { label: "Acquired", variant: "success" }
    : { label: "Storage unavailable", variant: "warning" }
}

export default function EvidenceDetailPage() {
  const { caseId, evidenceId } = useParams<{
    caseId?: string
    evidenceId: string
  }>()
  const navigate = useNavigate()

  const {
    data: evidence,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useEvidenceDetailQuery(evidenceId)

  const {
    data: custodyChain,
    isLoading: custodyLoading,
    isError: custodyError,
    error: custodyQueryError,
    refetch: refetchCustody,
    isFetching: custodyFetching,
  } = useEvidenceCustodyQuery(evidenceId)

  const resolvedCaseId = caseId ?? evidence?.case_id
  const { data: caseData } = useCaseQuery(resolvedCaseId)

  const backToEvidencePath = resolvedCaseId
    ? `/cases/${resolvedCaseId}/evidence`
    : "/cases"

  if (!evidenceId) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-6 w-6 text-danger" />}
        title="Evidence not specified"
        description="Open evidence from a case to view acquisition details."
        action={
          <Button variant="secondary" onClick={() => navigate("/cases")}>
            Go to Cases
          </Button>
        }
      />
    )
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading evidence…
      </div>
    )
  }

  if (isError || !evidence) {
    const message = getErrorMessage(error)
    const isNotFound =
      message.toLowerCase().includes("not found") ||
      (error &&
        typeof error === "object" &&
        "response" in error &&
        (error as { response?: { status?: number } }).response?.status === 404)

    return (
      <div className="space-y-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(backToEvidencePath)}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to evidence
        </Button>
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title={isNotFound ? "Evidence not found" : "Could not load evidence"}
          description={message}
          action={
            <div className="flex gap-2">
              {isError ? (
                <Button
                  variant="secondary"
                  onClick={() => void refetch()}
                  disabled={isFetching}
                >
                  Try again
                </Button>
              ) : null}
              <Button
                variant="secondary"
                onClick={() => navigate(backToEvidencePath)}
              >
                Back to evidence list
              </Button>
            </div>
          }
        />
      </div>
    )
  }

  const status = evidenceStatus(evidence.storage_available)
  const caseLabel = caseData?.title ?? formatCaseRef(evidence.case_id)
  const uploadedAt = evidence.created_at || evidence.acquisition_timestamp

  return (
    <div className="space-y-6">
      <Link
        to={backToEvidencePath}
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to evidence
      </Link>

      <PageHeader
        title={evidence.original_filename}
        description={`${caseLabel} · Evidence acquisition record`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="secondary"
              className="gap-2"
              onClick={() =>
                document
                  .getElementById("chain-of-custody")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" })
              }
            >
              <Link2 className="h-4 w-4" />
              Chain of Custody
            </Button>
            <Badge variant={status.variant}>{status.label}</Badge>
            <Badge variant={evidence.storage_available ? "success" : "warning"}>
              {evidence.storage_available
                ? "File stored securely"
                : "File not on storage"}
            </Badge>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <HardDrive className="h-4 w-4 text-accent" />
              Acquisition Metadata
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <DetailRow label="Original filename" value={evidence.original_filename} />
            <DetailRow
              label="File type"
              value={evidence.file_type ? `.${evidence.file_type}` : "—"}
            />
            <DetailRow label="MIME type" value={evidence.mime_type || "—"} />
            <DetailRow label="File size" value={formatBytes(evidence.file_size)} />
            <DetailRow label="Status" value={status.label} />
            <DetailRow
              label="Evidence ID"
              value={
                <span className="font-mono text-xs">{evidence.id}</span>
              }
            />
            <DetailRow
              label="Case ID"
              value={
                resolvedCaseId ? (
                  <Link
                    to={`/cases/${resolvedCaseId}`}
                    className="font-mono text-xs text-accent hover:underline"
                  >
                    {evidence.case_id}
                  </Link>
                ) : (
                  <span className="font-mono text-xs">{evidence.case_id}</span>
                )
              }
            />
            <DetailRow
              label="Acquisition timestamp"
              value={
                evidence.acquisition_timestamp
                  ? formatDateTime(evidence.acquisition_timestamp)
                  : "—"
              }
            />
            <DetailRow
              label="Uploaded timestamp"
              value={uploadedAt ? formatDateTime(uploadedAt) : "—"}
            />
            <DetailRow
              label="Uploaded by"
              value={
                evidence.uploaded_by ? (
                  <span className="font-mono text-xs">{evidence.uploaded_by}</span>
                ) : (
                  "—"
                )
              }
            />
            <div className="pt-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-muted">
                Captured acquisition metadata
              </p>
              <MetadataDisplay metadata={evidence.metadata} />
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Shield className="h-4 w-4 text-accent" />
              Acquisition Hashes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <HashDisplay
              label="MD5"
              algorithm="MD5"
              value={evidence.md5 || null}
              truncate={false}
            />
            <HashDisplay
              label="SHA-1"
              algorithm="SHA-1"
              value={evidence.sha1 || null}
              truncate={false}
            />
            <HashDisplay
              label="SHA-256"
              algorithm="SHA-256"
              value={evidence.sha256 || null}
              truncate={false}
            />
            <p className="pt-1 text-xs text-text-muted">
              Hashes were calculated server-side during acquisition. This page
              is read-only.
            </p>
          </CardContent>
        </Card>

        <HashVerificationSection evidence={evidence} />

        <EvidenceIntegritySection evidence={evidence} />

        <KeywordSearchSection evidenceId={evidence.id} />

        <BrowserAnalysisSection evidenceId={evidence.id} />

        <TimelineAnalysisSection evidenceId={evidence.id} />

        <MetadataAnalysisSection evidenceId={evidence.id} />

        <ReportGenerationSection evidenceId={evidence.id} />

        <AIAssistSection evidenceId={evidence.id} />

        <AnalysisHistorySection evidenceId={evidence.id} />

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Storage</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-text-secondary">
            {evidence.storage_available ? (
              <p>
                The evidence file is present in secure storage and available for
                authorized forensic processing.
              </p>
            ) : (
              <p>
                The evidence record exists, but the underlying file could not be
                located in storage. Contact an administrator if this persists.
              </p>
            )}
          </CardContent>
        </Card>

        <Card id="chain-of-custody" className="lg:col-span-2 scroll-mt-24">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Link2 className="h-4 w-4 text-accent" />
              Chain of Custody
              {custodyChain ? (
                <Badge variant="secondary">{custodyChain.count} event(s)</Badge>
              ) : null}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CustodySection
              evidenceId={evidence.id}
              isLoading={custodyLoading}
              isError={custodyError}
              error={custodyQueryError}
              events={custodyChain?.events}
              onRetry={() => void refetchCustody()}
              isFetching={custodyFetching}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
