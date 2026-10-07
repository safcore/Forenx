import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import {
  Users,
  Shield,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  Search,
  UserCheck,
  UserX,
} from "lucide-react"
import { toast } from "react-hot-toast"
import { PageHeader } from "@/components/common/PageHeader"
import { EmptyState } from "@/components/common/EmptyState"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAuth } from "@/contexts/AuthContext"
import { listAdminUsers, updateAdminUser } from "@/services/auth"
import { getErrorMessage } from "@/api/client"
import { formatDate } from "@/lib/utils"
import type { AdminUser } from "@/types"

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [confirmModal, setConfirmModal] = useState<{
    user: AdminUser
    action: "promote" | "demote" | "activate" | "deactivate"
  } | null>(null)

  const {
    data: users = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["admin-users"],
    queryFn: listAdminUsers,
  })

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number | string
      payload: { role?: string; is_active?: boolean; is_email_verified?: boolean }
    }) => updateAdminUser(id, payload),
    onSuccess: (updated) => {
      toast.success(`User ${updated.username} updated successfully.`)
      queryClient.invalidateQueries({ queryKey: ["admin-users"] })
      setConfirmModal(null)
    },
    onError: (err) => {
      toast.error(getErrorMessage(err))
    },
  })

  const filteredUsers = users.filter((u) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    const fullName = `${u.first_name} ${u.last_name}`.toLowerCase()
    return (
      fullName.includes(q) ||
      u.username.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      u.role.toLowerCase().includes(q)
    )
  })

  const activeAdminsCount = users.filter(
    (u) => u.role.toUpperCase() === "ADMIN" && u.is_active
  ).length

  const handleExecuteAction = () => {
    if (!confirmModal) return
    const { user: target, action } = confirmModal

    if (action === "promote") {
      updateMutation.mutate({ id: target.id, payload: { role: "ADMIN" } })
    } else if (action === "demote") {
      updateMutation.mutate({ id: target.id, payload: { role: "INVESTIGATOR" } })
    } else if (action === "activate") {
      updateMutation.mutate({ id: target.id, payload: { is_active: true } })
    } else if (action === "deactivate") {
      updateMutation.mutate({ id: target.id, payload: { is_active: false } })
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        description="Admin console: manage platform users, investigator roles, and account access authorization."
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="default" className="gap-1.5 py-1 px-3">
              <ShieldCheck className="h-3.5 w-3.5 text-accent" />
              {activeAdminsCount} Active Admin{activeAdminsCount === 1 ? "" : "s"}
            </Badge>
          </div>
        }
      />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search by name, username, or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-full rounded-xl border border-white/10 bg-white/[0.03] pl-10 pr-4 text-sm text-white placeholder:text-text-muted transition-all focus:border-accent/40 focus:bg-white/[0.05] focus:outline-none focus:ring-2 focus:ring-accent/15"
          />
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="self-start sm:self-auto"
        >
          {isFetching ? "Refreshing…" : "Refresh list"}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex min-h-[30vh] items-center justify-center gap-2 text-sm text-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading user directory…
        </div>
      ) : null}

      {isError ? (
        <EmptyState
          icon={<AlertCircle className="h-6 w-6 text-danger" />}
          title="Could not load users"
          description={getErrorMessage(error)}
          action={
            <Button variant="secondary" onClick={() => void refetch()}>
              Try again
            </Button>
          }
        />
      ) : null}

      {!isLoading && !isError && filteredUsers.length === 0 ? (
        <EmptyState
          icon={<Users className="h-6 w-6" />}
          title="No users found"
          description={
            search
              ? "No accounts match your search filter."
              : "No user accounts registered in system."
          }
        />
      ) : null}

      {!isLoading && !isError && filteredUsers.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[840px] text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-text-muted">
                    <th className="px-6 py-4 font-medium">User</th>
                    <th className="px-6 py-4 font-medium">Email</th>
                    <th className="px-6 py-4 font-medium">Role</th>
                    <th className="px-6 py-4 font-medium">Account Status</th>
                    <th className="px-6 py-4 font-medium">Email Verified</th>
                    <th className="px-6 py-4 font-medium">Joined</th>
                    <th className="px-6 py-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {filteredUsers.map((u) => {
                    const isAdmin = u.role.toUpperCase() === "ADMIN"
                    const isSelf = String(u.id) === String(currentUser?.id)
                    const isLastAdmin = isAdmin && activeAdminsCount <= 1

                    return (
                      <tr
                        key={u.id}
                        className="transition-colors hover:bg-white/[0.02]"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback>
                                {u.first_name?.[0] || u.username[0]}
                                {u.last_name?.[0] || ""}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium text-white">
                                {u.first_name || u.last_name
                                  ? `${u.first_name} ${u.last_name}`.trim()
                                  : u.username}
                              </p>
                              <p className="font-mono text-xs text-text-muted">
                                @{u.username}
                                {isSelf && " (You)"}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-text-secondary">
                          {u.email}
                        </td>
                        <td className="px-6 py-4">
                          <Badge
                            variant={isAdmin ? "default" : "secondary"}
                            className="capitalize"
                          >
                            {u.role.toLowerCase()}
                          </Badge>
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={u.is_active ? "success" : "danger"}>
                            {u.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </td>
                        <td className="px-6 py-4">
                          {u.is_email_verified ? (
                            <span className="inline-flex items-center gap-1.5 text-xs text-success font-medium">
                              <CheckCircle2 className="h-3.5 w-3.5" /> Verified
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-xs text-warning font-medium">
                              <XCircle className="h-3.5 w-3.5" /> Unverified
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs text-text-muted">
                          {u.date_joined || u.created_at
                            ? formatDate(u.date_joined || u.created_at)
                            : "—"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {/* Role Toggle Button */}
                            {isAdmin ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={isSelf || isLastAdmin}
                                onClick={() =>
                                  setConfirmModal({ user: u, action: "demote" })
                                }
                                title={
                                  isSelf
                                    ? "You cannot modify your own role"
                                    : isLastAdmin
                                      ? "Cannot demote the last administrator"
                                      : "Demote to Investigator"
                                }
                                className="text-xs text-text-muted hover:text-white"
                              >
                                Set Investigator
                              </Button>
                            ) : (
                              <Button
                                variant="secondary"
                                size="sm"
                                disabled={isSelf}
                                onClick={() =>
                                  setConfirmModal({ user: u, action: "promote" })
                                }
                                title="Promote to Administrator"
                                className="text-xs text-accent border-accent/20 hover:border-accent/40"
                              >
                                Promote to Admin
                              </Button>
                            )}

                            {/* Active Toggle Button */}
                            {u.is_active ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={isSelf || isLastAdmin}
                                onClick={() =>
                                  setConfirmModal({
                                    user: u,
                                    action: "deactivate",
                                  })
                                }
                                title={
                                  isSelf
                                    ? "You cannot deactivate your own account"
                                    : isLastAdmin
                                      ? "Cannot deactivate the last administrator"
                                      : "Deactivate user account"
                                }
                                className="text-xs text-text-muted hover:text-danger"
                              >
                                <UserX className="h-3.5 w-3.5 mr-1" />
                                Deactivate
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  setConfirmModal({
                                    user: u,
                                    action: "activate",
                                  })
                                }
                                className="text-xs text-success hover:text-success/80"
                              >
                                <UserCheck className="h-3.5 w-3.5 mr-1" />
                                Activate
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-md rounded-2xl border border-white/10 bg-[#141414] p-6 shadow-2xl"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-xl border border-accent/20 bg-accent/10 p-2.5">
                <Shield className="h-5 w-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-white">
                Confirm Admin Action
              </h3>
            </div>

            <p className="text-sm text-text-secondary leading-relaxed mb-6">
              {confirmModal.action === "promote" && (
                <>
                  Are you sure you want to promote{" "}
                  <strong className="text-white">
                    @{confirmModal.user.username}
                  </strong>{" "}
                  to <strong className="text-white">ADMIN</strong>? This will
                  grant full administrative access to user management and system
                  settings.
                </>
              )}
              {confirmModal.action === "demote" && (
                <>
                  Are you sure you want to demote{" "}
                  <strong className="text-white">
                    @{confirmModal.user.username}
                  </strong>{" "}
                  to <strong className="text-white">INVESTIGATOR</strong>? Admin
                  management privileges will be removed.
                </>
              )}
              {confirmModal.action === "deactivate" && (
                <>
                  Are you sure you want to deactivate the account for{" "}
                  <strong className="text-white">
                    @{confirmModal.user.username}
                  </strong>
                  ? The user will immediately be barred from signing in.
                </>
              )}
              {confirmModal.action === "activate" && (
                <>
                  Activate account access for{" "}
                  <strong className="text-white">
                    @{confirmModal.user.username}
                  </strong>
                  ?
                </>
              )}
            </p>

            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setConfirmModal(null)}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="default"
                onClick={handleExecuteAction}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Updating…
                  </>
                ) : (
                  "Confirm"
                )}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
