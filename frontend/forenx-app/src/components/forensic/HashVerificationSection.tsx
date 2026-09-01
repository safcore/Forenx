import { useMemo, useState } from "react"
import { Fingerprint, Loader2, ShieldAlert, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { HashDisplay } from "@/components/forensic/HashDisplay"
import { useVerifyEvidenceHashMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import {
  getStoredAcquisitionHash,
  isAcquisitionHashAvailable,
  validateExpectedHashInput,
} from "@/lib/hashVerification"
import { cn } from "@/lib/utils"
import type { Evidence, EvidenceHashCompareResult, HashAlgorithm } from "@/types"

const ALGORITHMS: { value: HashAlgorithm; label: string }[] = [
  { value: "sha256", label: "SHA-256" },
  { value: "sha1", label: "SHA-1" },
  { value: "md5", label: "MD5" },
]

interface HashVerificationSectionProps {
  evidence: Evidence
}

export function HashVerificationSection({ evidence }: HashVerificationSectionProps) {
  const [algorithm, setAlgorithm] = useState<HashAlgorithm>("sha256")
  const [expectedHash, setExpectedHash] = useState("")
  const [validationError, setValidationError] = useState<string | null>(null)
  const [result, setResult] = useState<EvidenceHashCompareResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const verifyMutation = useVerifyEvidenceHashMutation(evidence.id)

  const storedHash = useMemo(
    () => getStoredAcquisitionHash(algorithm, evidence),
    [algorithm, evidence]
  )
  const storedAvailable = useMemo(
    () => isAcquisitionHashAvailable(algorithm, evidence),
    [algorithm, evidence]
  )

  const handleVerify = async () => {
    setSubmitError(null)
    setResult(null)
    const error = validateExpectedHashInput(algorithm, expectedHash)
    if (error) {
      setValidationError(error)
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
    <Card id="hash-verification" className="scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Fingerprint className="h-4 w-4 text-accent" />
          Reference Hash Comparison
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Reference hash comparison: compare a user-supplied digest against the
          hash stored during evidence acquisition. This does not read the
          evidence file or create custody events.
        </p>

        <HashDisplay
          label="Stored acquisition hash"
          algorithm={`Stored ${algorithm.toUpperCase()}`}
          value={storedAvailable ? storedHash : null}
          truncate={false}
        />

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-secondary">
            Algorithm
          </p>
          <div className="flex flex-wrap gap-2">
            {ALGORITHMS.map((item) => (
              <button
                key={item.value}
                type="button"
                aria-pressed={algorithm === item.value}
                onClick={() => {
                  setAlgorithm(item.value)
                  setValidationError(null)
                  setResult(null)
                  setSubmitError(null)
                }}
                className={cn(
                  "rounded-lg border px-3 py-1.5 text-sm font-medium transition-all",
                  algorithm === item.value
                    ? "border-accent/40 bg-accent/15 text-accent"
                    : "border-white/10 bg-white/[0.03] text-text-secondary hover:border-white/20 hover:text-white"
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label
            htmlFor="expected-hash"
            className="mb-2 block text-xs font-medium uppercase tracking-wider text-text-secondary"
          >
            Expected / Reference Hash
          </label>
          <textarea
            id="expected-hash"
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
          className="gap-2"
          disabled={verifyMutation.isPending || !expectedHash.trim()}
          aria-busy={verifyMutation.isPending}
          onClick={() => void handleVerify()}
        >
          {verifyMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Fingerprint className="h-4 w-4" />
          )}
          Compare Reference Hash
        </Button>

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
  )
}
