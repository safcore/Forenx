import { Link } from "react-router-dom"
import { motion } from "framer-motion"
import {
  Briefcase,
  FolderOpen,
  CheckCircle2,
  HardDrive,
  FileText,
  Database,
  ArrowUpRight,
  Clock,
  AlertCircle,
  Loader2,
  Activity,
  Link2,
} from "lucide-react"
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/common/EmptyState"
import { useDashboardQuery } from "@/hooks/useDashboard"
import { formatCaseRef } from "@/api/cases.api"
import { getErrorMessage } from "@/api/client"
import { formatBytes, formatDateTime, cn } from "@/lib/utils"
import { formatCustodyAction } from "@/components/forensic/CustodyTimeline"
import type { CaseStatus, CasePriority } from "@/types"

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
}

const item = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
  },
}

const statusVariant: Record<
  CaseStatus,
  "default" | "success" | "warning" | "secondary"
> = {
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

const PRIORITY_COLORS: Record<CasePriority, string> = {
  critical: "#FF4D4F",
  high: "#F39C12",
  medium: "#5EA7FF",
  low: "#2ECC71",
}

function analysisTypeLabel(type: string): string {
  const map: Record<string, string> = {
    hash: "HASH",
    keyword: "KEYWORD",
    browser: "BROWSER",
    timeline: "TIMELINE",
    metadata: "METADATA",
    report: "REPORT",
    ai: "AI",
    custody: "CUSTODY",
  }
  return map[type.toLowerCase()] ?? type.toUpperCase()
}

export default function DashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useDashboardQuery()

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading dashboard…
      </div>
    )
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-6 w-6 text-danger" />}
        title="Could not load dashboard"
        description={getErrorMessage(error)}
        action={
          <Button
            variant="secondary"
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            Try again
          </Button>
        }
      />
    )
  }

  const stats = [
    {
      label: "Total Cases",
      value: String(data.total_cases),
      icon: Briefcase,
      color: "text-accent",
      bg: "bg-accent/10",
    },
    {
      label: "Open Cases",
      value: String(data.open_cases),
      icon: FolderOpen,
      color: "text-warning",
      bg: "bg-warning/10",
    },
    {
      label: "Closed Cases",
      value: String(data.closed_cases),
      icon: CheckCircle2,
      color: "text-success",
      bg: "bg-success/10",
    },
    {
      label: "Evidence Items",
      value: String(data.total_evidence),
      icon: HardDrive,
      color: "text-accent",
      bg: "bg-accent/10",
    },
    {
      label: "Reports Generated",
      value: String(data.reports_generated),
      icon: FileText,
      color: "text-success",
      bg: "bg-success/10",
    },
    {
      label: "Evidence Storage",
      value: formatBytes(data.storage_bytes),
      icon: Database,
      color: "text-text-secondary",
      bg: "bg-white/5",
    },
  ]

  const priorityData = (
    ["critical", "high", "medium", "low"] as CasePriority[]
  ).map((name) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: data.priority_counts[name] ?? 0,
    color: PRIORITY_COLORS[name],
  }))
  const priorityTotal = priorityData.reduce((sum, row) => sum + row.value, 0)

  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-white">
            Dashboard
          </h1>
          <p className="mt-1 text-text-secondary">
            Live investigation overview from stored case, evidence, custody, and
            report records. Opening this page does not run forensic analysis.
          </p>
        </div>
        <Button asChild className="gap-2">
          <Link to="/cases/new">
            <Briefcase className="h-4 w-4" />
            New Case
          </Link>
        </Button>
      </motion.div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
      >
        {stats.map((stat) => (
          <motion.div key={stat.label} variants={item}>
            <Card hover className="p-5">
              <div className="flex items-start justify-between">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-xl",
                    stat.bg
                  )}
                >
                  <stat.icon className={cn("h-5 w-5", stat.color)} />
                </div>
              </div>
              <p className="mt-4 font-display text-2xl font-semibold text-white">
                {stat.value}
              </p>
              <p className="mt-1 text-xs text-text-muted">{stat.label}</p>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.45 }}
          className="lg:col-span-2"
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent Cases</CardTitle>
              <Button variant="ghost" size="sm" asChild className="gap-1 text-accent">
                <Link to="/cases">
                  View all
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {data.recent_cases.length === 0 ? (
                <div className="px-6 py-10">
                  <EmptyState
                    icon={<Briefcase className="h-6 w-6" />}
                    title="No cases yet"
                    description="Create a case to begin registering evidence and recording investigation activity."
                    action={
                      <Button asChild variant="secondary">
                        <Link to="/cases/new">Create case</Link>
                      </Button>
                    }
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px]">
                    <thead>
                      <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-text-muted">
                        <th className="px-6 py-3 font-medium">Case</th>
                        <th className="px-6 py-3 font-medium">Status</th>
                        <th className="px-6 py-3 font-medium">Priority</th>
                        <th className="px-6 py-3 font-medium">Investigator</th>
                        <th className="px-6 py-3 font-medium">Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_cases.map((c) => (
                        <tr
                          key={c.id}
                          className="border-b border-white/[0.04] transition-colors hover:bg-white/[0.02]"
                        >
                          <td className="px-6 py-4">
                            <Link
                              to={`/cases/${c.id}`}
                              className="font-medium text-white hover:text-accent"
                            >
                              <span className="break-words">{c.title}</span>
                            </Link>
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
                          <td className="px-6 py-4 text-sm text-text-muted">
                            {c.updated_at ? formatDateTime(c.updated_at) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.45 }}
        >
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Priority Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {priorityTotal === 0 ? (
                <p className="py-8 text-center text-sm text-text-muted">
                  No cases available for priority distribution.
                </p>
              ) : (
                <>
                  <div className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={priorityData}
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={80}
                          paddingAngle={4}
                          dataKey="value"
                        >
                          {priorityData.map((entry) => (
                            <Cell
                              key={entry.name}
                              fill={entry.color}
                              stroke="transparent"
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: "#141414",
                            border: "1px solid rgba(255,255,255,0.08)",
                            borderRadius: 12,
                            color: "#fff",
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {priorityData.map((p) => (
                      <div key={p.name} className="flex items-center gap-2 text-xs">
                        <div
                          className="h-2 w-2 rounded-full"
                          style={{ background: p.color }}
                        />
                        <span className="text-text-secondary">{p.name}</span>
                        <span className="ml-auto font-medium text-white">
                          {p.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-accent" />
              Recent Evidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_evidence.length === 0 ? (
              <p className="text-sm text-text-muted">No evidence registered yet.</p>
            ) : (
              <ul className="space-y-3">
                {data.recent_evidence.map((ev) => (
                  <li key={ev.id} className="border-b border-white/[0.04] pb-3 last:border-0">
                    <Link
                      to={`/evidence/${ev.id}`}
                      className="break-all text-sm font-medium text-white hover:text-accent"
                    >
                      {ev.original_filename}
                    </Link>
                    <p className="mt-1 text-xs text-text-muted">
                      {formatBytes(ev.file_size)}
                      {ev.created_at ? ` · ${formatDateTime(ev.created_at)}` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-accent" />
              Recent Analysis Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_analysis.length === 0 ? (
              <p className="text-sm text-text-muted">
                No analysis activity recorded yet. Run forensic actions from an
                evidence detail page.
              </p>
            ) : (
              <ul className="space-y-3">
                {data.recent_analysis.map((run) => (
                  <li key={run.id} className="flex gap-3">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
                      <Clock className="h-3.5 w-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">
                          {analysisTypeLabel(run.analysis_type)}
                        </Badge>
                        <Badge
                          variant={
                            run.status === "success"
                              ? "success"
                              : run.status === "failed"
                                ? "danger"
                                : "secondary"
                          }
                        >
                          {run.status}
                        </Badge>
                      </div>
                      <p className="mt-1 break-words text-sm text-white/90">
                        {run.result_summary || "Analysis completed."}
                      </p>
                      <p className="mt-0.5 text-xs text-text-muted">
                        {[
                          run.evidence_filename,
                          run.created_by_username,
                          run.created_at ? formatDateTime(run.created_at) : null,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link2 className="h-4 w-4 text-accent" />
              Recent Custody Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_custody.length === 0 ? (
              <p className="text-sm text-text-muted">
                No custody events recorded yet.
              </p>
            ) : (
              <ul className="space-y-3">
                {data.recent_custody.map((event) => (
                  <li key={event.id} className="min-w-0">
                    <p className="text-sm font-medium text-white">
                      {formatCustodyAction(event.action)}
                    </p>
                    <p className="mt-0.5 break-words text-xs text-text-secondary">
                      {event.description || "—"}
                    </p>
                    <p className="mt-0.5 text-xs text-text-muted">
                      {[
                        event.actor_role || event.actor_id,
                        event.evidence_filename,
                        event.timestamp ? formatDateTime(event.timestamp) : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-accent" />
            Reports Generated
          </CardTitle>
          <Button variant="ghost" size="sm" asChild className="gap-1 text-accent">
            <Link to="/reports">
              View all
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {data.recent_reports.length === 0 ? (
            <p className="text-sm text-text-muted">
              No reports generated yet. Generate a report from an evidence detail
              page.
            </p>
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {data.recent_reports.map((report) => (
                <li
                  key={report.id}
                  className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
                >
                  <p className="break-all font-mono text-xs text-accent">
                    {report.report_id}
                  </p>
                  <p className="mt-1 break-words text-sm text-white">
                    {report.title || report.evidence_filename || "Report"}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    {report.created_at ? formatDateTime(report.created_at) : "—"}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
