import { useMemo, useRef, useState, type ChangeEvent } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { motion } from "framer-motion"
import {
  HardDrive,
  Upload,
  Search,
  FileText,
  Image,
  Film,
  Archive,
  AlertCircle,
  Loader2,
  ArrowLeft,
  ChevronRight,
} from "lucide-react"
import { toast } from "react-hot-toast"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { TableSkeleton } from "@/components/common/LoadingSkeleton"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { HashDisplay } from "@/components/forensic/HashDisplay"
import { useCaseQuery } from "@/hooks/useCases"
import { useEvidenceQuery, useGlobalEvidenceQuery, useUploadEvidenceMutation } from "@/hooks/useEvidence"
import { formatCaseRef } from "@/api/cases.api"
import { getErrorMessage } from "@/api/client"
import { formatBytes, formatDateTime } from "@/lib/utils"

function fileIcon(type: string, mime: string) {
  const t = `${type} ${mime}`.toLowerCase()
  if (t.includes("image")) return Image
  if (t.includes("video")) return Film
  if (t.includes("zip") || t.includes("archive")) return Archive
  return FileText
}

function GlobalEvidenceInventory() {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const { data, isLoading, isError, error, refetch, isFetching } =
    useGlobalEvidenceQuery()

  const items = useMemo(() => {
    const rows = data ?? []
    const q = search.trim().toLowerCase()
    if (!q) return rows
    return rows.filter(
      (item) =>
        item.original_filename.toLowerCase().includes(q) ||
        item.file_type.toLowerCase().includes(q) ||
        item.mime_type.toLowerCase().includes(q) ||
        (item.case_title ?? "").toLowerCase().includes(q) ||
        item.sha256.toLowerCase().includes(q)
    )
  }, [data, search])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence"
        description="Inventory of evidence from cases you can access. Opening this page does not hash or analyze files."
      />

      <Card className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <label htmlFor="global-evidence-search" className="sr-only">
            Filter evidence inventory
          </label>
          <input
            id="global-evidence-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Filter by filename, type, case, or hash…"
            className="h-10 w-full rounded-xl border border-white/10 bg-white/[0.03] pl-10 pr-4 text-sm text-white placeholder:text-text-muted focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15"
          />
        </div>
      </Card>

      {isLoading ? (
        <div className="flex min-h-[30vh] items-center justify-center gap-2 text-sm text-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading evidence inventory…
        </div>
      ) : null}

      {isError ? (
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Could not load evidence"
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

      {!isLoading && !isError && items.length === 0 ? (
        <EmptyState
          icon={<HardDrive className="h-6 w-6" />}
          title={search ? "No matching evidence" : "No evidence collected"}
          description={
            search
              ? "Try a different filter."
              : "Open a case to upload digital evidence. This inventory does not run forensic analysis."
          }
          action={
            !search ? (
              <Button variant="secondary" onClick={() => navigate("/cases")}>
                Go to Cases
              </Button>
            ) : undefined
          }
        />
      ) : null}

      {!isLoading && !isError && items.length > 0 ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-text-muted">
                  <th className="px-4 py-3 font-medium">Evidence</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Size</th>
                  <th className="px-4 py-3 font-medium">Case</th>
                  <th className="px-4 py-3 font-medium">Acquired</th>
                  <th className="px-4 py-3 font-medium">Hashes</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-white/[0.04] align-top hover:bg-white/[0.02]"
                  >
                    <td className="px-4 py-4">
                      <p className="break-all text-sm font-medium text-white">
                        {item.original_filename}
                      </p>
                    </td>
                    <td className="px-4 py-4 text-sm text-text-secondary">
                      {item.file_type || item.mime_type || "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-text-secondary">
                      {formatBytes(item.file_size)}
                    </td>
                    <td className="px-4 py-4 text-sm">
                      <p className="break-words text-white">
                        {item.case_title || "Case"}
                      </p>
                      {item.case_id ? (
                        <Link
                          to={`/cases/${item.case_id}`}
                          className="mt-1 inline-block text-xs text-accent hover:underline"
                        >
                          Open case
                        </Link>
                      ) : null}
                    </td>
                    <td className="px-4 py-4 text-sm text-text-muted">
                      {item.acquisition_timestamp
                        ? formatDateTime(item.acquisition_timestamp)
                        : "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-text-secondary">
                      {item.sha256 || item.sha1 || item.md5
                        ? "Acquisition hashes stored"
                        : "No acquisition hashes"}
                    </td>
                    <td className="px-4 py-4">
                      {item.storage_available ? (
                        <Badge variant="success">Stored</Badge>
                      ) : (
                        <Badge variant="warning">Storage unavailable</Badge>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="gap-1.5"
                        onClick={() => navigate(`/evidence/${item.id}`)}
                      >
                        Open Evidence Detail
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  )
}

export default function EvidencePage() {
  const { caseId } = useParams<{ caseId: string; evidenceId?: string }>()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)

  const { data: caseData } = useCaseQuery(caseId)
  const {
    data: evidence,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useEvidenceQuery(caseId)
  const uploadMutation = useUploadEvidenceMutation(caseId ?? "")

  const filtered = useMemo(() => {
    const items = evidence ?? []
    const q = search.trim().toLowerCase()
    if (!q) return items
    return items.filter(
      (item) =>
        item.original_filename.toLowerCase().includes(q) ||
        item.file_type.toLowerCase().includes(q) ||
        item.mime_type.toLowerCase().includes(q) ||
        item.sha256.toLowerCase().includes(q)
    )
  }, [evidence, search])

  const openFilePicker = () => fileInputRef.current?.click()

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    event.target.value = ""
  }

  const handleUpload = async () => {
    if (!caseId || !selectedFile) return
    setUploadProgress(null)
    try {
      const result = await uploadMutation.mutateAsync({
        file: selectedFile,
        onProgress: (percent) => setUploadProgress(percent),
      })
      toast.success(`Evidence uploaded: ${result.filename}`)
      setSelectedFile(null)
      setUploadProgress(null)
    } catch (err) {
      setUploadProgress(null)
      toast.error(getErrorMessage(err))
    }
  }

  if (!caseId) {
    return <GlobalEvidenceInventory />
  }

  const caseLabel = caseData?.title ?? "Case"
  const caseRef = caseData ? formatCaseRef(caseData.id) : formatCaseRef(caseId)
  const uploading = uploadMutation.isPending

  return (
    <div className="space-y-6">
      <Link
        to={`/cases/${caseId}`}
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to case overview
      </Link>

      <PageHeader
        title="Evidence"
        description={`${caseLabel} · ${caseRef} · ${evidence?.length ?? 0} item(s)`}
        actions={
          <Button
            className="gap-2"
            onClick={openFilePicker}
            disabled={uploading}
          >
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Upload Evidence
          </Button>
        }
      />

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
      />

      <Card className="p-4 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <label htmlFor="evidence-search" className="sr-only">
            Search evidence
          </label>
          <input
            id="evidence-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by filename, type, or hash…"
            className="h-10 w-full rounded-xl border border-white/10 bg-white/[0.03] pl-10 pr-4 text-sm text-white placeholder:text-text-muted focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15"
          />
        </div>

        {selectedFile && (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-white">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-text-muted">
                  {formatBytes(selectedFile.size)}
                  {selectedFile.type ? ` · ${selectedFile.type}` : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleUpload}
                  disabled={uploading}
                  className="gap-2"
                >
                  {uploading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  Upload
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={uploading}
                  onClick={() => {
                    setSelectedFile(null)
                    setUploadProgress(null)
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
            {uploading && (
              <div className="mt-3">
                {uploadProgress != null ? (
                  <>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-accent transition-all"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-text-muted">
                      Uploading… {uploadProgress}%
                    </p>
                  </>
                ) : (
                  <p className="text-xs text-text-muted">Uploading…</p>
                )}
              </div>
            )}
          </div>
        )}
      </Card>

      {isLoading ? (
        <Card className="overflow-hidden">
          <TableSkeleton rows={4} />
        </Card>
      ) : isError ? (
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Could not load evidence"
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
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<HardDrive className="h-6 w-6" />}
          title={search ? "No matching evidence" : "No evidence collected"}
          description={
            search
              ? "Try a different search term."
              : "Upload documents or other digital artifacts. The backend will store, hash, and extract initial metadata."
          }
          action={
            !search ? (
              <Button className="gap-2" onClick={openFilePicker}>
                <Upload className="h-4 w-4" />
                Upload first evidence
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((item, index) => {
            const Icon = fileIcon(item.file_type, item.mime_type)
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.04, 0.3) }}
              >
                <Card className="p-4 sm:p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent/10 text-accent">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-3">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="break-all font-medium text-white">
                              {item.original_filename}
                            </p>
                            {item.storage_available ? (
                              <Badge variant="success">Stored</Badge>
                            ) : (
                              <Badge variant="warning">Storage unavailable</Badge>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-text-muted">
                            {formatBytes(item.file_size)}
                            {item.mime_type ? ` · ${item.mime_type}` : item.file_type ? ` · .${item.file_type}` : ""}
                            {item.acquisition_timestamp
                              ? ` · ${formatDateTime(item.acquisition_timestamp)}`
                              : ""}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="shrink-0 gap-1.5"
                          onClick={() =>
                            navigate(`/cases/${caseId}/evidence/${item.id}`)
                          }
                        >
                          View Details
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="grid gap-2 md:grid-cols-3">
                        <HashDisplay
                          label="MD5"
                          algorithm="MD5"
                          value={item.md5 || null}
                        />
                        <HashDisplay
                          label="SHA-1"
                          algorithm="SHA-1"
                          value={item.sha1 || null}
                        />
                        <HashDisplay
                          label="SHA-256"
                          algorithm="SHA-256"
                          value={item.sha256 || null}
                        />
                      </div>

                      {item.metadata &&
                        Object.keys(item.metadata).length > 0 &&
                        item.metadata.status !== "unavailable" && (
                          <p className="text-xs text-text-secondary">
                            Initial metadata captured at acquisition.
                          </p>
                        )}
                    </div>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
