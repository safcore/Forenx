import { useQuery } from "@tanstack/react-query"
import { getDashboardSummary } from "@/api/dashboard.api"

export function dashboardQueryKey() {
  return ["dashboard-summary"] as const
}

/** Read-only dashboard aggregates — never triggers forensic analysis. */
export function useDashboardQuery() {
  return useQuery({
    queryKey: dashboardQueryKey(),
    queryFn: getDashboardSummary,
  })
}
