import { PageHeader } from "@/components/common/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/contexts/AuthContext"
import { useTheme } from "@/contexts/ThemeContext"
import { isDemoMode } from "@/services/auth"
import { API_BASE } from "@/api/client"
import { Moon, Sun } from "lucide-react"

export default function SettingsPage() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()
  const demo = isDemoMode()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Account, security, and application preferences. Only options that affect real behavior are shown."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Signed in as</span>
              <span className="text-white">{user?.email ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Username</span>
              <span className="text-white">{user?.username ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Role</span>
              <span className="capitalize text-white">
                {user?.role?.replace(/_/g, " ") ?? "—"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Security</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Session</span>
              <Badge variant="success">Authenticated</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Inactivity Timeout</span>
              <Badge variant="default">30 Minutes</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Auth mode</span>
              <Badge variant={demo ? "warning" : "default"}>
                {demo ? "Demo mode" : "JWT (backend)"}
              </Badge>
            </div>
            <p className="text-xs text-text-muted">
              JWT tokens are secured in client storage. Sessions automatically expire after 30 minutes of inactivity.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Appearance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-text-secondary">
              Workstation visual theme. Switch between dark mode and light mode across all views.
            </p>
            <div className="flex gap-3">
              <Button
                variant={theme === "dark" ? "default" : "secondary"}
                size="sm"
                className="gap-2"
                onClick={() => setTheme("dark")}
              >
                <Moon className="h-4 w-4" />
                Dark Theme
              </Button>
              <Button
                variant={theme === "light" ? "default" : "secondary"}
                size="sm"
                className="gap-2"
                onClick={() => setTheme("light")}
              >
                <Sun className="h-4 w-4" />
                Light Theme
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Application</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">API base</span>
              <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-xs text-text-secondary">
                {API_BASE}
              </code>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Demo mode</span>
              <span className="text-white">{demo ? "Enabled" : "Disabled"}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
