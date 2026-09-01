import { useState } from "react"
import { Outlet } from "react-router-dom"
import { motion } from "framer-motion"
import { Sidebar } from "./Sidebar"
import { Navbar } from "./Navbar"
import { cn } from "@/lib/utils"

export function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <Navbar
        sidebarCollapsed={collapsed}
        onMenuClick={() => setCollapsed(!collapsed)}
      />
      <main
        className={cn(
          "min-h-screen pt-16 transition-all duration-300",
          collapsed ? "pl-20" : "pl-[260px]"
        )}
      >
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="p-6 lg:p-8"
        >
          <Outlet />
        </motion.div>
      </main>
    </div>
  )
}
