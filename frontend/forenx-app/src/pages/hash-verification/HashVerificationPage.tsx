import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  Fingerprint,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  AlertCircle,
} from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { HashDisplay } from "@/components/forensic/HashDisplay"
import { EmptyState } from "@/components/common/EmptyState"
import { useEvidenceDetailQuery, useVerifyEvidenceHashMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import {
  getStoredAcquisitionHash,
  isAcquisitionHashAvailable,
  validateExpectedHashInput,
} from "@/lib/hashVerification"
import { cn } from "@/lib/utils"
import type { EvidenceHashCompareResult, HashAlgorithm } from "@/types"

const ALGORITHMS: { value: HashAlgorithm; label: string }[] = [
  { value: "sha256", label: "SHA-256" },
  { value: "sha1", label: "SHA-1" },
  { value: "md5", label: "MD5" },
]

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export default function HashVerificationPage() {
  const [evidenceId, setEvidenceId] = useState("")
  const [algorithm, setAlgorithm] = useState<HashAlgorithm>("sha256")
  const [expectedHash, setExpectedHash] = useState("")
  const [validationError, setValidationError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<EvidenceHashCompareResult | null>(null)

  const trimmedId = evidenceId.trim()
  const idValid = UUID_PATTERN.test(trimmedId)

  const {
    data: evidence,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useEvidenceDetailQuery(idValid ? trimmedId : undefined)

  const verifyMutation = useVerifyEvidenceHashMutation(trimmedId)

  const storedHash = useMemo(
    () => (evidence ? getStoredAcquisitionHash(algorithm, evidence) : ""),
    [algorithm, evidence]
  )
  const storedAvailable = useMemo(
    () => (evidence ? isAcquisitionHashAvailable(algorithm, evidence) : false),
    [algorithm, evidence]
  )

  const handleCompare = async () => {
    setSubmitError(null)
    setResult(null)
    if (!idValid) {
      setValidationError("Enter a valid evidence UUID.")
      return
    }
    const errorText = validateExpectedHashInput(algorithm, expectedHash)
    if (errorText) {
      setValidationError(errorText)
      return
    }
    if (!storedAvailable) {
      setValidationError(
        `No acquisition ${algorithm.toUpperCase()} hash is stored for this evidence.`
      )
      return
    }
    setValidationError(null)
    try {
      const compareResult = await verifyMutation.mutateAsync({
        algorithm,
        expectedHash,
      })
      setResult(compareResult)
    } catch (err) {
      setSubmitError(getErrorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reference Hash Comparison"
        description="Compare a user-supplied digest against the stored acquisition hash. This does not read the evidence file or create custody events."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Fingerprint className="h-4 w-4 text-accent" />
              Comparison parameters
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Evidence ID"
              placeholder="Evidence UUID"
              value={evidenceId}
              onChange={(event) => {
                setEvidenceId(event.target.value)
                setResult(null)
                setSubmitError(null)
                setValidationError(null)
              }}
            />

            <fieldset>
              <legend className="mb-2 text-xs font-medium uppercase tracking-wider text-text-secondary">
                Algorithm
              </legend>
              <div className="flex flex-wrap gap-2">
                {ALGORITHMS.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    aria-pressed={algorithm === item.value}
                    onClick={() => {
                      setAlgorithm(item.value)
                      setResult(null)
                      setValidationError(null)
                      setSubmitError(null)
                    }}
                    className={cn(
                      "rounded-lg border px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
                      algorithm === item.value
                        ? "border-accent/40 bg-accent/15 text-accent"
                        : "border-white/10 bg-white/[0.03] text-text-secondary hover:border-white/20 hover:text-white"
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </fieldset>

            <div>
              <label
                htmlFor="standalone-expected-hash"
                className="mb-2 block text-xs font-medium uppercase tracking-wider text-text-secondary"
              >
                Expected / Reference Hash
              </label>
              <textarea
                id="standalone-expected-hash"
                value={expectedHash}
                onChange={(event) => {
                  setExpectedHash(event.target.value)
                  setValidationError(null)
                  setResult(null)
                  setSubmitError(null)
                }}
                placeholder={`Paste expected ${algorithm.toUpperCase()} digest`}
                rows={3}
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 font-mono text-xs text-white placeholder:text-text-muted focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15"
              />
            </div>

            {validationError ? (
              <p className="text-sm text-danger" role="alert">
                {validationError}
              </p>
            ) : null}
            {submitError ? (
              <p className="text-sm text-danger" role="alert">
                {submitError}
              </p>
            ) : null}

            <Button
              className="w-full gap-2"
              disabled={
                verifyMutation.isPending ||
                !trimmedId ||
                !expectedHash.trim()
              }
              onClick={() => void handleCompare()}
            >
              {verifyMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Comparing…
                </>
              ) : (
                <>
                  <Fingerprint className="h-4 w-4" />
                  Compare Reference Hash
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Result</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!trimmedId ? (
              <p className="py-8 text-center text-sm text-text-muted">
                Enter an evidence UUID to load the stored acquisition hash.
              </p>
            ) : !idValid ? (
              <p className="text-sm text-danger" role="alert">
                Enter a valid evidence UUID.
              </p>
            ) : isLoading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-text-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading evidence…
              </div>
            ) : isError || !evidence ? (
              <EmptyState
                icon={<AlertCircle className="h-6 w-6 text-danger" />}
                title="Could not load evidence"
                description={getErrorMessage(error)}
                action={
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => void refetch()}
                    disabled={isFetching}
                  >
                    Try again
                  </Button>
                }
              />
            ) : (
              <>
                <HashDisplay
                  label="Stored acquisition hash"
                  algorithm={`Stored ${algorithm.toUpperCase()}`}
                  value={storedAvailable ? storedHash : null}
                  truncate={false}
                />
                <p className="break-words text-xs text-text-muted">
                  {evidence.original_filename}
                  {" · "}
                  <Link
                    to={`/evidence/${evidence.id}`}
                    className="text-accent hover:underline"
                  >
                    Open evidence detail
                  </Link>
                </p>
              </>
            )}

            {result ? (
              <div
                className={cn(
                  "rounded-xl border p-4",
                  result.match
                    ? "border-success/30 bg-success/10"
                    : "border-danger/30 bg-danger/10"
                )}
              >
                <div className="flex items-start gap-3">
                  {result.match ? (
                    <ShieldCheck className="h-6 w-6 shrink-0 text-success" />
                  ) : (
                    <ShieldAlert className="h-6 w-6 shrink-0 text-danger" />
                  )}
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p
                        className={cn(
                          "font-display text-lg font-semibold",
                          result.match ? "text-success" : "text-danger"
                        )}
                      >
                        {result.match ? "MATCH" : "MISMATCH"}
                      </p>
                      <Badge variant="secondary">
                        {result.algorithm.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-text-secondary">
                      {result.match
                        ? "Reference hash matches the stored acquisition digest."
                        : "Reference hash does not match the stored acquisition digest."}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
