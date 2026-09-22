import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { Plus, Search, Filter, AlertCircle, Briefcase } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { TableSkeleton } from "@/components/common/LoadingSkeleton"
import { useCasesQuery } from "@/hooks/useCases"
import { formatCaseRef } from "@/api/cases.api"
import { getErrorMessage } from "@/api/client"
import { formatDateTime } from "@/lib/utils"
import type { CaseStatus, CasePriority } from "@/types"

const statusVariant: Record<CaseStatus, "default" | "warning" | "secondary" | "success"> = {
  open: "default",
  active: "warning",
  in_progress: "warning",
  closed: "success",
  archived: "secondary",
}

const priorityVariant: Record<
  CasePriority,
  "danger" | "warning" | "default" | "success"
> = {
  critical: "danger",
  high: "warning",
  medium: "default",
  low: "success",
}

export default function CasesPage() {
  const [search, setSearch] = useState("")
  const navigate = useNavigate()
  const { data, isLoading, isError, error, refetch, isFetching } = useCasesQuery()

  const filtered = useMemo(() => {
    const cases = data ?? []
    const q = search.trim().toLowerCase()
    if (!q) return cases
    return cases.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        c.investigator_username.toLowerCase().includes(q) ||
        formatCaseRef(c.id).toLowerCase().includes(q)
    )
  }, [data, search])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cases"
        description="Manage and track digital forensics investigations"
        actions={
          <Button className="gap-2" onClick={() => navigate("/cases/new")}>
            <Plus className="h-4 w-4" />
            Create Case
          </Button>
        }
      />

      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <label htmlFor="cases-search" className="sr-only">
              Search cases
            </label>
            <input
              id="cases-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, investigator, or case ID…"
              className="h-10 w-full rounded-xl border border-white/10 bg-white/[0.03] pl-10 pr-4 text-sm text-white placeholder:text-text-muted focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15"
            />
          </div>
          <Button variant="secondary" size="sm" className="gap-2" disabled>
            <Filter className="h-4 w-4" />
            Filters
          </Button>
        </div>
      </Card>

      {isLoading ? (
        <Card className="overflow-hidden">
          <TableSkeleton rows={6} />
        </Card>
      ) : isError ? (
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Could not load cases"
          description={getErrorMessage(error)}
          action={
            <Button variant="secondary" onClick={() => void refetch()} disabled={isFetching}>
              Try again
            </Button>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="h-6 w-6" />}
          title={search ? "No matching cases" : "No cases yet"}
          description={
            search
              ? "Try a different search term."
              : "Create your first investigation to get started."
          }
          action={
            !search ? (
              <Button className="gap-2" onClick={() => navigate("/cases/new")}>
                <Plus className="h-4 w-4" />
                Create Case
              </Button>
            ) : undefined
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-text-muted">
                  <th className="px-6 py-4 font-medium">Case</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Priority</th>
                  <th className="px-6 py-4 font-medium">Investigator</th>
                  <th className="px-6 py-4 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c, i) => (
                  <motion.tr
                    key={c.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.3) }}
                    onClick={() => navigate(`/cases/${c.id}`)}
                    className="cursor-pointer border-b border-white/[0.04] transition-colors hover:bg-white/[0.025] group"
                  >
                    <td className="px-6 py-4">
                      <p className="break-words font-medium text-white transition-colors group-hover:text-accent">
                        {c.title}
                      </p>
                      <p className="font-mono text-xs text-text-muted">
                        {formatCaseRef(c.id)}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={statusVariant[c.status]}>
                        {c.status.replace("_", " ")}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={priorityVariant[c.priority]}>
                        {c.priority}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-text-secondary">
                      {c.investigator_username || "—"}
                    </td>
                    <td className="px-6 py-4 text-sm text-text-secondary">
                      {c.updated_at ? formatDateTime(c.updated_at) : "—"}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
