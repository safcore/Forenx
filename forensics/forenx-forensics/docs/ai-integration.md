# AI Integration Guide (Phase 9)

AI assistance in ForenX is **advisory only** and does **not** constitute independent
forensic evidence.

## Architecture

```
Deterministic forensic engine
    ↓
Evidence / Metadata / Keywords / Browser / Timeline / Custody / Reports
    ↓
Normalized forensic context (bounded + sanitized)
    ↓
AIService
    ↓
Provider (local deterministic by default)
    ↓
AIAnalysis (structured, provenance-preserving)
    ↓
Optional ForensicReport section
```

The AI layer depends on **schemas / services**, not extractor internals.

Package layout:

```
app/ai/
  models.py
  context_builder.py
  prompt_builder.py
  provider.py
  local_provider.py
  dispatcher.py
app/services/ai_service.py
app/schemas/ai.py
```

## Provider abstraction

`AIProvider.analyze(context, instructions, prompt=...) -> AIAnalysis`

Implementations shipping today:

| Provider | Behavior |
|----------|----------|
| `LocalDeterministicProvider` | Offline heuristics labeled `DETERMINISTIC FALLBACK` |
| `UnavailableAIProvider` | Structured unavailable/disabled result |

Remote vendor clients are intentionally **not** shipped. Selecting `openai` /
`gemini` / `anthropic` / `ollama` never performs network I/O in this build.

## Local-first behavior

Defaults (see `app/utils/config.py`):

```
FORENX_AI_ENABLED=false
FORENX_AI_PROVIDER=local
FORENX_AI_MODEL=deterministic-local
FORENX_AI_ALLOW_NETWORK=false
```

Core functionality and the test suite require:

- no OpenAI / Gemini / Anthropic / Ollama dependency
- no external network access
- no API key

When AI is disabled, `AIService.analyze()` returns `status=disabled`.

## Context construction

`build_ai_context()` consumes already-computed forensic results (or a
`ForensicReport`) and produces an `AIContextSummary` containing bounded
summaries of metadata, hashes, keywords, browser artifacts (no cookie values),
timeline events, custody verification, findings, notes, and limitations.

Large collections are truncated deterministically via:

- `FORENX_AI_MAX_KEYWORD_MATCHES`
- `FORENX_AI_MAX_TIMELINE_EVENTS`
- `FORENX_AI_MAX_BROWSER_ITEMS`
- `FORENX_AI_MAX_STRING_CHARS`
- `FORENX_AI_MAX_CUSTODY_EVENTS`

## Sanitization

Before AI processing:

- secret-like keys are redacted (`password`, `api_key`, `token`, `cookie_value`, …)
- inline `password=` / `api_key:` patterns are redacted
- long strings are truncated
- forensic identifiers (hashes, timestamps, event IDs) are preserved

Never log API keys, passwords, tokens, or cookie values.

## Fact vs inference

Every AI finding uses `AIStatementKind`:

- `observed_fact`
- `inference`
- `recommendation`

Inferences/recommendations must not be presented as confirmed forensic facts.
Unsupported claims should be marked speculative.

## Provenance

Findings reference deterministic sources via `AIEvidenceRef`
(`source`, `event_id`, `keyword`, `source_file`, …).

## Report integration

`ReportService.build_report(..., ai_analysis=analysis)` optionally attaches
AI output. Existing reports continue to work when AI is omitted.

PDF/JSON label AI material as:

`AI-ASSISTED ANALYSIS - NOT A SUBSTITUTE FOR FORENSIC FINDINGS`

## Django integration contract

```
Django API
  → Forensic Engine Service wrappers
    → AIService
      → AIAnalysis
        → Django serializer / model persistence
          → Frontend
```

Host application owns auth, users, cases, persistence, API endpoints, IP logging,
and DB transactions.

This engine owns deterministic forensic processing + advisory AI interpretation.

Do **not** add Django models, PostgreSQL, or REST endpoints to this repository.

## Future LLM providers

Implement `AIProvider`, register selection in `resolve_ai_provider()`, keep
network gated by `FORENX_AI_ALLOW_NETWORK`, and never send unsanitized evidence.
Until a provider is implemented, remote names resolve to unavailable/fallback
without network calls.

## Limitations

- AI does not modify evidence, hashes, custody ledgers, or deterministic findings
- AI must not invent artifacts
- Deterministic fallback is useful but not model-generated intelligence
- AI conclusions without supporting evidence must be treated as speculative
