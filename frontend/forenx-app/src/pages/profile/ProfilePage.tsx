import { PageHeader } from "@/components/common/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "@/contexts/AuthContext"
import { formatDate } from "@/lib/utils"

export default function ProfilePage() {
  const { user } = useAuth()

  if (!user) {
    return (
      <div className="space-y-6">
        <PageHeader title="Profile" description="Account information" />
        <p className="text-sm text-text-secondary">No profile loaded.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Profile"
        description="Your investigator identity and role within ForenX."
      />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/20 text-xl font-semibold text-accent">
              {user.first_name?.[0]}
              {user.last_name?.[0]}
            </div>
            <div>
              <CardTitle className="text-xl">
                {user.first_name} {user.last_name}
              </CardTitle>
              <p className="mt-1 text-sm text-text-secondary">{user.email}</p>
              <Badge variant="default" className="mt-2 capitalize">
                {user.role?.replace("_", " ")}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wider text-text-muted">
                Department
              </dt>
              <dd className="mt-1 text-sm text-white">
                {user.department || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-text-muted">
                Phone
              </dt>
              <dd className="mt-1 text-sm text-white">{user.phone || "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-text-muted">
                Account created
              </dt>
              <dd className="mt-1 text-sm text-white">
                {user.created_at ? formatDate(user.created_at) : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-text-muted">
                Last login
              </dt>
              <dd className="mt-1 text-sm text-white">
                {user.last_login ? formatDate(user.last_login) : "—"}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
