import { useState } from "react"
import { Brain, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAssistEvidenceInvestigationMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import type { EvidenceAIAssistResult } from "@/types"

interface AIAssistSectionProps {
  evidenceId: string
}

const MAX_QUESTION_LENGTH = 1000

function ResultList({
  title,
  items,
}: {
  title: string
  items: string[]
}) {
  if (items.length === 0) return null
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
        {title}
      </p>
      <ul className="list-inside list-disc space-y-1 text-sm text-white/90">
        {items.map((item) => (
          <li key={`${title}-${item.slice(0, 48)}`}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

export function AIAssistSection({ evidenceId }: AIAssistSectionProps) {
  const [question, setQuestion] = useState("")
  const [validationError, setValidationError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<EvidenceAIAssistResult | null>(null)

  const assistMutation = useAssistEvidenceInvestigationMutation(evidenceId)

  const handleAnalyze = async () => {
    const trimmed = question.trim()
    if (question.length > 0 && !trimmed) {
      setValidationError("Investigation question must not be empty.")
      return
    }
    if (trimmed.length > MAX_QUESTION_LENGTH) {
      setValidationError(
        `Investigation question must be ${MAX_QUESTION_LENGTH} characters or fewer.`
      )
      return
    }
    setValidationError(null)
    setSubmitError(null)
    setResult(null)
    try {
      const analysis = await assistMutation.mutateAsync(
        trimmed ? trimmed : undefined
      )
      setResult(analysis)
    } catch (err) {
      setSubmitError(getErrorMessage(err))
    }
  }

  return (
    <Card id="ai-assisted-investigation" className="scroll-mt-24 lg:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-4 w-4 text-accent" />
          AI-Assisted Investigation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          AI-assisted analysis is advisory only. Verify findings using
          deterministic forensic evidence. The AI does not read evidence files,
          recalculate hashes, or modify acquisition records.
        </p>

        <div className="space-y-2">
          <label
            htmlFor="ai-investigation-question"
            className="text-xs font-medium uppercase tracking-wider text-text-muted"
          >
            Investigation Question
          </label>
          <textarea
            id="ai-investigation-question"
            className="min-h-24 w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-white outline-none ring-accent/40 placeholder:text-text-muted focus:ring-2"
            placeholder="What notable correlations exist between timeline and keyword findings?"
            value={question}
            maxLength={MAX_QUESTION_LENGTH}
            onChange={(event) => {
              setQuestion(event.target.value)
              setValidationError(null)
            }}
          />
          <p className="text-xs text-text-muted">
            {question.length}/{MAX_QUESTION_LENGTH}
          </p>
        </div>

        <Button
          className="gap-2"
          disabled={assistMutation.isPending}
          aria-busy={assistMutation.isPending}
          onClick={() => void handleAnalyze()}
        >
          {assistMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Running AI Assist…
            </>
          ) : (
            <>
              <Brain className="h-4 w-4" />
              Run AI Assist
            </>
          )}
        </Button>

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

        {result ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-accent/30 bg-accent/10 p-4">
              <p className="font-display text-lg font-semibold text-white">
                {result.insufficient_context
                  ? "INSUFFICIENT FORENSIC CONTEXT"
                  : "AI ANALYSIS COMPLETE"}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {result.insufficient_context
                  ? "Insufficient forensic context is available for meaningful AI analysis."
                  : "AI-ASSISTED INVESTIGATION"}
              </p>
              {result.generated_at ? (
                <p className="mt-2 text-xs text-text-muted">
                  Generated: {formatDateTime(result.generated_at)}
                </p>
              ) : null}
            </div>

            <div className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
              {result.disclaimer ||
                "AI-assisted analysis is advisory only. Verify findings using deterministic forensic evidence."}
            </div>

            {!result.insufficient_context ? (
              <>
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                    Summary
                  </p>
                  <p className="text-sm text-white/90">{result.summary || "—"}</p>
                </div>
                <ResultList title="Observations" items={result.observations} />
                <ResultList title="Correlations" items={result.correlations} />
                <ResultList title="Potential Leads" items={result.potential_leads} />
                <ResultList
                  title="Recommended Next Steps"
                  items={result.recommended_next_steps}
                />
              </>
            ) : null}

            <ResultList title="Limitations" items={result.limitations} />
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                Disclaimer
              </p>
              <p className="text-sm text-text-secondary">
                AI output is advisory and requires investigator review.
              </p>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
