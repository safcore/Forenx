import { useQuery } from "@tanstack/react-query"
import { listReports } from "@/api/reports.api"

export function reportsQueryKey() {
  return ["reports-list"] as const
}

/** Read-only report list — opening the page does not generate reports. */
export function useReportsQuery() {
  return useQuery({
    queryKey: reportsQueryKey(),
    queryFn: listReports,
  })
}
