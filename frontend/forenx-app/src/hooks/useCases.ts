import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createCase,
  getCase,
  listCases,
  type CreateCasePayload,
} from "@/api/cases.api"

import { dashboardQueryKey } from "@/hooks/useDashboard"

export const casesQueryKey = ["cases"] as const

export function caseDetailQueryKey(id: string) {
  return ["cases", id] as const
}

export function useCasesQuery(enabled = true) {
  return useQuery({
    queryKey: casesQueryKey,
    queryFn: () => listCases(),
    enabled,
  })
}

export function useCaseQuery(id: string | undefined) {
  return useQuery({
    queryKey: caseDetailQueryKey(id ?? ""),
    queryFn: () => getCase(id!),
    enabled: Boolean(id),
  })
}

export function useCreateCaseMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateCasePayload) => createCase(payload),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: casesQueryKey })
      void queryClient.invalidateQueries({ queryKey: dashboardQueryKey() })
      queryClient.setQueryData(caseDetailQueryKey(created.id), created)
    },
  })
}
