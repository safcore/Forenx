import { useState, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
  Search,
  Bell,
  Command,
  Moon,
  Sun,
  Menu,
  CheckCheck,
  Shield,
  Briefcase,
  HardDrive,
  FileText,
  Fingerprint,
} from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { useTheme } from "@/contexts/ThemeContext"
import { useDashboardQuery } from "@/hooks/useDashboard"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { formatDateTime, cn } from "@/lib/utils"

interface NavbarProps {
  onMenuClick?: () => void
  sidebarCollapsed: boolean
}

export function Navbar({ onMenuClick, sidebarCollapsed }: NavbarProps) {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const [searchFocused, setSearchFocused] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [readEventIds, setReadEventIds] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem("forenx_read_notifications")
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })

  const notificationPanelRef = useRef<HTMLDivElement>(null)
  const bellButtonRef = useRef<HTMLButtonElement>(null)

  const { data: dashboardData } = useDashboardQuery()

  // Generate notifications from live platform activity
  const notifications = (() => {
    if (!dashboardData) return []
    const items: Array<{
      id: string
      title: string
      description: string
      timestamp: string
      type: "case" | "evidence" | "custody" | "report"
      link?: string
    }> = []

    // Recent cases
    dashboardData.recent_cases?.slice(0, 3).forEach((c) => {
      items.push({
        id: `case-${c.id}`,
        title: `Case: ${c.title}`,
        description: `Status: ${c.status.toUpperCase()} • Priority: ${c.priority.toUpperCase()}`,
        timestamp: c.created_at,
        type: "case",
        link: `/cases/${c.id}`,
      })
    })

    // Recent evidence
    dashboardData.recent_evidence?.slice(0, 3).forEach((ev) => {
      items.push({
        id: `ev-${ev.id}`,
        title: `Evidence: ${ev.original_filename}`,
        description: `Uploaded and registered in persistent storage`,
        timestamp: ev.created_at,
        type: "evidence",
        link: `/evidence/${ev.id}`,
      })
    })

    // Recent reports
    dashboardData.recent_reports?.slice(0, 3).forEach((rep) => {
      items.push({
        id: `rep-${rep.id}`,
        title: `Report: ${rep.title}`,
        description: rep.case_title ? `Case: ${rep.case_title}` : "Forensic report generated",
        timestamp: rep.created_at,
        type: "report",
        link: "/reports",
      })
    })

    // Recent custody / verification events
    dashboardData.recent_custody?.slice(0, 3).forEach((cust) => {
      items.push({
        id: `cust-${cust.id}`,
        title: `Custody: ${cust.action.replace(/_/g, " ")}`,
        description: cust.description || `Recorded by ${cust.actor_role || cust.actor_id}`,
        timestamp: cust.timestamp || "",
        type: "custody",
        link: "/custody",
      })
    })

    // Sort descending by timestamp
    return items
      .filter((item) => item.timestamp)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 8)
  })()

  const unreadCount = notifications.filter((n) => !readEventIds.includes(n.id)).length

  const markAllAsRead = () => {
    const allIds = notifications.map((n) => n.id)
    setReadEventIds(allIds)
    try {
      localStorage.setItem("forenx_read_notifications", JSON.stringify(allIds))
    } catch {
      // Ignore storage errors
    }
  }

  // Close notifications popover on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        notificationPanelRef.current &&
        !notificationPanelRef.current.contains(event.target as Node) &&
        bellButtonRef.current &&
        !bellButtonRef.current.contains(event.target as Node)
      ) {
        setNotificationsOpen(false)
      }
    }

    if (notificationsOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [notificationsOpen])

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "case":
        return <Briefcase className="h-4 w-4 text-accent" />
      case "evidence":
        return <HardDrive className="h-4 w-4 text-accent" />
      case "report":
        return <FileText className="h-4 w-4 text-warning" />
      case "custody":
        return <Fingerprint className="h-4 w-4 text-success" />
      default:
        return <Shield className="h-4 w-4 text-text-muted" />
    }
  }

  return (
    <header
      className={cn(
        "fixed top-0 right-0 z-30 flex h-16 items-center justify-between border-b border-white/[0.06] bg-[#0B0B0D]/80 px-6 backdrop-blur-xl transition-all duration-300",
        sidebarCollapsed ? "left-20" : "left-[260px]"
      )}
    >
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-white/5 hover:text-white lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div
          className={cn(
            "relative flex items-center transition-all duration-300",
            searchFocused ? "w-80" : "w-64"
          )}
        >
          <Search className="absolute left-3 h-4 w-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search cases, evidence, reports..."
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className="h-10 w-full rounded-xl border border-white/10 bg-white/[0.03] pl-10 pr-12 text-sm text-white placeholder:text-text-muted transition-all focus:border-accent/40 focus:bg-white/[0.05] focus:outline-none focus:ring-2 focus:ring-accent/15"
          />
          <kbd className="absolute right-3 flex items-center gap-0.5 rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] text-text-muted">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Notification Bell with live popover */}
        <div className="relative">
          <Button
            ref={bellButtonRef}
            variant="ghost"
            size="icon"
            className="relative"
            onClick={() => setNotificationsOpen((prev) => !prev)}
            aria-label="View notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-accent ring-2 ring-[#0B0B0D]" />
            )}
          </Button>

          {notificationsOpen && (
            <div
              ref={notificationPanelRef}
              className="absolute right-0 top-12 z-50 w-80 sm:w-96 rounded-2xl border border-white/10 bg-[#141414] shadow-2xl backdrop-blur-2xl transition-all"
            >
              <div className="flex items-center justify-between border-b border-white/[0.08] px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="rounded-full bg-accent/20 px-2 py-0.5 text-[10px] font-medium text-accent">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="flex items-center gap-1 text-xs text-text-muted hover:text-white transition-colors"
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-white/[0.04]">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-sm text-text-muted">
                    No recent events recorded yet.
                  </div>
                ) : (
                  notifications.map((n) => {
                    const isUnread = !readEventIds.includes(n.id)
                    return (
                      <div
                        key={n.id}
                        onClick={() => {
                          if (!readEventIds.includes(n.id)) {
                            const updated = [...readEventIds, n.id]
                            setReadEventIds(updated)
                            try {
                              localStorage.setItem(
                                "forenx_read_notifications",
                                JSON.stringify(updated)
                              )
                            } catch {
                              // Ignore
                            }
                          }
                          if (n.link) {
                            setNotificationsOpen(false)
                            navigate(n.link)
                          }
                        }}
                        className={cn(
                          "flex items-start gap-3 p-3.5 transition-colors cursor-pointer hover:bg-white/[0.04]",
                          isUnread && "bg-white/[0.02]"
                        )}
                      >
                        <div className="mt-0.5 rounded-lg border border-white/10 bg-white/[0.04] p-1.5">
                          {getNotificationIcon(n.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-white truncate">{n.title}</p>
                          <p className="mt-0.5 text-[11px] text-text-muted line-clamp-2">
                            {n.description}
                          </p>
                          <span className="mt-1 block text-[10px] text-text-muted/80">
                            {formatDateTime(n.timestamp)}
                          </span>
                        </div>
                        {isUnread && (
                          <div className="mt-1 h-1.5 w-1.5 rounded-full bg-accent shrink-0" />
                        )}
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* Theme Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label={`Toggle theme (currently ${theme})`}
        >
          {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4 text-warning" />}
        </Button>

        {/* Top-Right Profile Badge: Clickable to /profile */}
        <div
          onClick={() => navigate("/profile")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              navigate("/profile")
            }
          }}
          className="ml-2 flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.03] py-1.5 pl-1.5 pr-3 cursor-pointer hover:bg-white/[0.06] hover:border-white/15 transition-all select-none"
          title="Open your profile"
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={user?.avatar ?? undefined} />
            <AvatarFallback>
              {user?.first_name?.[0]}
              {user?.last_name?.[0]}
            </AvatarFallback>
          </Avatar>
          <div className="hidden sm:block">
            <p className="text-sm font-medium leading-none text-white">
              {user?.first_name} {user?.last_name}
            </p>
            <p className="text-[11px] text-text-muted capitalize">
              {user?.role?.replace(/_/g, " ")}
            </p>
          </div>
        </div>
      </div>
    </header>
  )
}
