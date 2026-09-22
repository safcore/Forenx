import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  getEvidence,
  getEvidenceCustody,
  verifyEvidenceCustodyChain,
  listEvidenceForCase,
  listAccessibleEvidence,
  listEvidenceAnalysisRuns,
  uploadEvidenceForCase,
  verifyEvidenceHash,
  verifyEvidenceIntegrity,
  searchEvidenceKeywords,
  analyzeEvidenceBrowser,
  analyzeEvidenceTimeline,
  analyzeEvidenceMetadata,
  generateEvidenceReport,
  assistEvidenceInvestigation,
} from "@/api/evidence.api"
import { dashboardQueryKey } from "@/hooks/useDashboard"
import { reportsQueryKey } from "@/hooks/useReports"
import type { HashAlgorithm } from "@/types"

export function evidenceGlobalQueryKey() {
  return ["evidence-global"] as const
}

export function evidenceQueryKey(caseId: string) {
  return ["evidence", caseId] as const
}

export function evidenceDetailQueryKey(evidenceId: string) {
  return ["evidence-detail", evidenceId] as const
}

export function evidenceCustodyQueryKey(evidenceId: string) {
  return ["evidence-custody", evidenceId] as const
}

export function evidenceAnalysisHistoryQueryKey(evidenceId: string) {
  return ["evidence-analysis-history", evidenceId] as const
}

function invalidateAfterForensicAction(
  queryClient: ReturnType<typeof useQueryClient>,
  evidenceId: string,
  options?: { reports?: boolean }
) {
  void queryClient.invalidateQueries({
    queryKey: evidenceCustodyQueryKey(evidenceId),
  })
  void queryClient.invalidateQueries({
    queryKey: evidenceAnalysisHistoryQueryKey(evidenceId),
  })
  void queryClient.invalidateQueries({ queryKey: dashboardQueryKey() })
  void queryClient.invalidateQueries({ queryKey: ["custody-list"] })
  void queryClient.invalidateQueries({ queryKey: evidenceGlobalQueryKey() })
  if (options?.reports) {
    void queryClient.invalidateQueries({ queryKey: reportsQueryKey() })
  }
}

export function useEvidenceQuery(caseId: string | undefined) {
  return useQuery({
    queryKey: evidenceQueryKey(caseId ?? ""),
    queryFn: () => listEvidenceForCase(caseId!),
    enabled: Boolean(caseId),
  })
}

export function useGlobalEvidenceQuery() {
  return useQuery({
    queryKey: evidenceGlobalQueryKey(),
    queryFn: listAccessibleEvidence,
  })
}

export function useEvidenceDetailQuery(evidenceId: string | undefined) {
  return useQuery({
    queryKey: evidenceDetailQueryKey(evidenceId ?? ""),
    queryFn: () => getEvidence(evidenceId!),
    enabled: Boolean(evidenceId),
  })
}

export function useEvidenceCustodyQuery(evidenceId: string | undefined) {
  return useQuery({
    queryKey: evidenceCustodyQueryKey(evidenceId ?? ""),
    queryFn: () => getEvidenceCustody(evidenceId!),
    enabled: Boolean(evidenceId),
  })
}

export function useEvidenceAnalysisHistoryQuery(evidenceId: string | undefined) {
  return useQuery({
    queryKey: evidenceAnalysisHistoryQueryKey(evidenceId ?? ""),
    queryFn: () => listEvidenceAnalysisRuns(evidenceId!),
    enabled: Boolean(evidenceId),
  })
}

export function useUploadEvidenceMutation(caseId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File
      onProgress?: (percent: number) => void
    }) => uploadEvidenceForCase(caseId, file, onProgress),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: evidenceQueryKey(caseId) })
      void queryClient.invalidateQueries({ queryKey: evidenceGlobalQueryKey() })
      void queryClient.invalidateQueries({ queryKey: dashboardQueryKey() })
      void queryClient.invalidateQueries({ queryKey: ["custody-list"] })
    },
  })
}

export function useVerifyEvidenceHashMutation(evidenceId: string) {
  // Phase 7: no custody / analysis-run side effects expected.
  return useMutation({
    mutationFn: ({
      algorithm,
      expectedHash,
    }: {
      algorithm: HashAlgorithm
      expectedHash: string
    }) => verifyEvidenceHash(evidenceId, algorithm, expectedHash),
  })
}

export function useVerifyEvidenceCustodyChainMutation(evidenceId: string) {
  return useMutation({
    mutationFn: () => verifyEvidenceCustodyChain(evidenceId),
  })
}

export function useVerifyEvidenceIntegrityMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => verifyEvidenceIntegrity(evidenceId),
    onSuccess: () => invalidateAfterForensicAction(queryClient, evidenceId),
  })
}

export function useSearchEvidenceKeywordsMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (keywords: string[]) => searchEvidenceKeywords(evidenceId, keywords),
    onSuccess: () => invalidateAfterForensicAction(queryClient, evidenceId),
  })
}

export function useAnalyzeEvidenceBrowserMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => analyzeEvidenceBrowser(evidenceId),
    onSuccess: () => invalidateAfterForensicAction(queryClient, evidenceId),
  })
}

export function useAnalyzeEvidenceTimelineMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => analyzeEvidenceTimeline(evidenceId),
    onSuccess: () => invalidateAfterForensicAction(queryClient, evidenceId),
  })
}

export function useAnalyzeEvidenceMetadataMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => analyzeEvidenceMetadata(evidenceId),
    onSuccess: () => invalidateAfterForensicAction(queryClient, evidenceId),
  })
}

export function useGenerateEvidenceReportMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (format: "json" | "pdf" | "both" = "both") =>
      generateEvidenceReport(evidenceId, format),
    onSuccess: () =>
      invalidateAfterForensicAction(queryClient, evidenceId, { reports: true }),
  })
}

export function useAssistEvidenceInvestigationMutation(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (question?: string) =>
      assistEvidenceInvestigation(evidenceId, question),
    onSuccess: () => invalidateAfterForensicAction(queryClient, evidenceId),
  })
}
