import { useState } from "react"
import { Loader2, Shield, ShieldAlert, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { HashDisplay } from "@/components/forensic/HashDisplay"
import { useVerifyEvidenceIntegrityMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { Evidence, EvidenceIntegrityVerifyResult } from "@/types"

interface EvidenceIntegritySectionProps {
  evidence: Evidence
}

export function EvidenceIntegritySection({ evidence }: EvidenceIntegritySectionProps) {
  const [result, setResult] = useState<EvidenceIntegrityVerifyResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const verifyMutation = useVerifyEvidenceIntegrityMutation(evidence.id)
  const sha256Result = result?.algorithms.sha256

  const handleVerify = async () => {
    setSubmitError(null)
    setResult(null)
    try {
      const verificationResult = await verifyMutation.mutateAsync()
      setResult(verificationResult)
    } catch (err) {
      const message = getErrorMessage(err)
      setSubmitError(message)
    }
  }

  return (
    <Card id="integrity-verification" className="scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Shield className="h-4 w-4 text-accent" />
          Integrity Verification
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Read the stored evidence file on the server, recalculate its current
          digests, and compare them against the original acquisition hashes.
          This is separate from reference hash comparison.
        </p>

        <HashDisplay
          label="Stored acquisition SHA-256"
          algorithm="Acquisition SHA-256"
          value={evidence.sha256 || null}
          truncate={false}
        />

        <Button
          className="gap-2"
          disabled={verifyMutation.isPending || !evidence.sha256}
          aria-busy={verifyMutation.isPending}
          onClick={() => void handleVerify()}
        >
          {verifyMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Verifying…
            </>
          ) : (
            <>
              <Shield className="h-4 w-4" />
              Verify Evidence Integrity
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
                result.overall_match
                  ? "border-success/30 bg-success/10"
                  : "border-danger/30 bg-danger/10"
              )}
            >
              <div className="flex items-start gap-3">
                {result.overall_match ? (
                  <ShieldCheck className="h-6 w-6 shrink-0 text-success" />
                ) : (
                  <ShieldAlert className="h-6 w-6 shrink-0 text-danger" />
                )}
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p
                      className={cn(
                        "font-display text-lg font-semibold",
                        result.overall_match ? "text-success" : "text-danger"
                      )}
                    >
                      {result.overall_match ? "MATCH" : "MISMATCH"}
                    </p>
                    <Badge variant="secondary">File integrity</Badge>
                  </div>
                  <p className="mt-1 text-sm text-text-secondary">
                    {result.overall_match
                      ? "Current file hash matches the acquisition hash."
                      : "Current file hash does not match the acquisition hash."}
                  </p>
                  {result.verified_at ? (
                    <p className="mt-2 text-xs text-text-muted">
                      Verified: {formatDateTime(result.verified_at)}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>

            {sha256Result ? (
              <div className="grid gap-2 lg:grid-cols-2">
                <HashDisplay
                  label="Acquisition SHA-256"
                  algorithm="Acquisition SHA-256"
                  value={sha256Result.acquisition_hash || null}
                  truncate={false}
                />
                <HashDisplay
                  label="Current file SHA-256"
                  algorithm="Current file SHA-256"
                  value={sha256Result.current_hash || null}
                  truncate={false}
                />
              </div>
            ) : null}

            {result.algorithms.md5 || result.algorithms.sha1 ? (
              <div className="space-y-2">
                {result.algorithms.md5 ? (
                  <p className="text-xs text-text-secondary">
                    MD5: {result.algorithms.md5.match ? "MATCH" : "MISMATCH"}
                  </p>
                ) : null}
                {result.algorithms.sha1 ? (
                  <p className="text-xs text-text-secondary">
                    SHA-1: {result.algorithms.sha1.match ? "MATCH" : "MISMATCH"}
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
