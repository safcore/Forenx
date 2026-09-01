import { useState } from "react"
import {
  Search,
  Bell,
  Command,
  Moon,
  Menu,
} from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface NavbarProps {
  onMenuClick?: () => void
  sidebarCollapsed: boolean
}

export function Navbar({ onMenuClick, sidebarCollapsed }: NavbarProps) {
  const { user } = useAuth()
  const [searchFocused, setSearchFocused] = useState(false)

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
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-accent" />
        </Button>

        <Button variant="ghost" size="icon">
          <Moon className="h-4 w-4" />
        </Button>

        <div className="ml-2 flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.03] py-1.5 pl-1.5 pr-3">
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
            <p className="text-[11px] text-text-muted capitalize">{user?.role}</p>
          </div>
        </div>
      </div>
    </header>
  )
}
