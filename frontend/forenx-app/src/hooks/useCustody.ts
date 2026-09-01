import { useQuery } from "@tanstack/react-query"
import { listCustodyEvents } from "@/api/custody.api"

export function custodyListQueryKey(caseId?: string) {
  return ["custody-list", caseId ?? "all"] as const
}

/** Read-only custody list — opening the page does not create events. */
export function useCustodyListQuery(caseId?: string) {
  return useQuery({
    queryKey: custodyListQueryKey(caseId),
    queryFn: () => listCustodyEvents(caseId),
  })
}
