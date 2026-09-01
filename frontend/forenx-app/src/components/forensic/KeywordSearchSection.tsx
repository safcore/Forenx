import { useMemo, useState } from "react"
import { Loader2, Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useSearchEvidenceKeywordsMutation } from "@/hooks/useEvidence"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { EvidenceKeywordSearchResult } from "@/types"

interface KeywordSearchSectionProps {
  evidenceId: string
}

function countByKeyword(result: EvidenceKeywordSearchResult): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const keyword of result.keywords) {
    counts[keyword] = 0
  }
  for (const match of result.matches) {
    counts[match.keyword] = (counts[match.keyword] ?? 0) + 1
  }
  return counts
}

export function KeywordSearchSection({ evidenceId }: KeywordSearchSectionProps) {
  const [draftKeyword, setDraftKeyword] = useState("")
  const [keywords, setKeywords] = useState<string[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<EvidenceKeywordSearchResult | null>(null)

  const searchMutation = useSearchEvidenceKeywordsMutation(evidenceId)
  const keywordCounts = useMemo(
    () => (result ? countByKeyword(result) : {}),
    [result]
  )

  const addKeyword = () => {
    const value = draftKeyword.trim()
    if (!value) return
    if (value.length > 128) {
      setValidationError("Each keyword must be 128 characters or fewer.")
      return
    }
    if (keywords.length >= 50) {
      setValidationError("A maximum of 50 keywords is allowed.")
      return
    }
    if (keywords.some((item) => item.toLowerCase() === value.toLowerCase())) {
      setValidationError("That keyword is already in the list.")
      return
    }
    setKeywords((current) => [...current, value])
    setDraftKeyword("")
    setValidationError(null)
    setResult(null)
    setSubmitError(null)
  }

  const removeKeyword = (value: string) => {
    setKeywords((current) => current.filter((item) => item !== value))
    setResult(null)
  }

  const handleSearch = async () => {
    if (keywords.length === 0) {
      setValidationError("Enter at least one keyword.")
      return
    }
    setValidationError(null)
    setSubmitError(null)
    setResult(null)
    try {
      const searchResult = await searchMutation.mutateAsync(keywords)
      setResult(searchResult)
    } catch (err) {
      setSubmitError(getErrorMessage(err))
    }
  }

  return (
    <Card id="keyword-search" className="scroll-mt-24">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Search className="h-4 w-4 text-accent" />
          Keyword Search
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Search the stored evidence file for investigator-supplied keywords.
          Matching is case-insensitive by default. This is separate from hash
          comparison and integrity verification.
        </p>

        <div className="flex flex-col gap-2 sm:flex-row">
          <label htmlFor="keyword-search-input" className="sr-only">
            Keyword
          </label>
          <input
            id="keyword-search-input"
            value={draftKeyword}
            onChange={(event) => {
              setDraftKeyword(event.target.value)
              setValidationError(null)
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                addKeyword()
              }
            }}
            placeholder="Enter a keyword"
            className="h-10 flex-1 rounded-xl border border-white/10 bg-white/[0.03] px-4 text-sm text-white placeholder:text-text-muted focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15"
          />
          <Button
            type="button"
            variant="secondary"
            onClick={addKeyword}
            disabled={searchMutation.isPending}
          >
            Add
          </Button>
        </div>

        {keywords.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {keywords.map((keyword) => (
              <Badge key={keyword} variant="secondary" className="gap-1.5 pr-1">
                {keyword}
                <button
                  type="button"
                  aria-label={`Remove ${keyword}`}
                  className="rounded p-0.5 hover:bg-white/10"
                  onClick={() => removeKeyword(keyword)}
                  disabled={searchMutation.isPending}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        ) : null}

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
          disabled={searchMutation.isPending || keywords.length === 0}
          aria-busy={searchMutation.isPending}
          onClick={() => void handleSearch()}
        >
          {searchMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching…
            </>
          ) : (
            <>
              <Search className="h-4 w-4" />
              Search Evidence
            </>
          )}
        </Button>

        {result ? (
          <div className="space-y-4">
            <div
              className={cn(
                "rounded-xl border p-4",
                result.match_count > 0
                  ? "border-accent/30 bg-accent/10"
                  : "border-white/10 bg-white/[0.02]"
              )}
            >
              <p className="font-display text-lg font-semibold text-white">
                {result.match_count > 0 ? "MATCHES FOUND" : "NO MATCHES"}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {result.match_count > 0
                  ? "Keyword search returned matching content."
                  : "No keyword matches were found."}
              </p>
              {result.searched_at ? (
                <p className="mt-2 text-xs text-text-muted">
                  Searched: {formatDateTime(result.searched_at)}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              {Object.entries(keywordCounts).map(([keyword, count]) => (
                <div
                  key={keyword}
                  className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm"
                >
                  <span className="text-white">{keyword}</span>
                  <span className="text-text-secondary">
                    {count} match{count === 1 ? "" : "es"} found
                  </span>
                </div>
              ))}
            </div>

            {result.matches.length > 0 ? (
              <div className="space-y-2">
                {result.matches.slice(0, 20).map((match, index) => (
                  <div
                    key={`${match.keyword}-${match.match_position ?? index}-${index}`}
                    className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{match.keyword}</Badge>
                      {match.line_number ? (
                        <span className="text-xs text-text-muted">
                          Line {match.line_number}
                        </span>
                      ) : null}
                      {match.page_number ? (
                        <span className="text-xs text-text-muted">
                          Page {match.page_number}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 break-words font-mono text-xs text-white/90">
                      {match.context || match.matched_text}
                    </p>
                  </div>
                ))}
                {result.matches.length > 20 ? (
                  <p className="text-xs text-text-muted">
                    Showing first 20 of {result.matches.length} matches.
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
