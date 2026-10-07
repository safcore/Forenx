import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "react-hot-toast"
import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import { ThemeProvider } from "@/contexts/ThemeContext"
import { DashboardLayout } from "@/components/layouts/DashboardLayout"
import { motion } from "framer-motion"

const LoginPage = lazy(() => import("@/pages/auth/LoginPage"))
const RegisterPage = lazy(() => import("@/pages/auth/RegisterPage"))
const VerifyEmailPage = lazy(() => import("@/pages/auth/VerifyEmailPage"))
const DashboardPage = lazy(() => import("@/pages/dashboard/DashboardPage"))
const CasesPage = lazy(() => import("@/pages/cases/CasesPage"))
const CreateCasePage = lazy(() => import("@/pages/cases/CreateCasePage"))
const CaseDetailPage = lazy(() => import("@/pages/cases/CaseDetailPage"))
const EvidencePage = lazy(() => import("@/pages/evidence/EvidencePage"))
const EvidenceDetailPage = lazy(
  () => import("@/pages/evidence/EvidenceDetailPage")
)
const HashVerificationPage = lazy(
  () => import("@/pages/hash-verification/HashVerificationPage")
)
const TimelinePage = lazy(() => import("@/pages/timeline/TimelinePage"))
const CustodyPage = lazy(() => import("@/pages/custody/CustodyPage"))
const ReportsPage = lazy(() => import("@/pages/reports/ReportsPage"))
const AnalyticsPage = lazy(() => import("@/pages/analytics/AnalyticsPage"))
const ProfilePage = lazy(() => import("@/pages/profile/ProfilePage"))
const SettingsPage = lazy(() => import("@/pages/settings/SettingsPage"))
const AdminUsersPage = lazy(() => import("@/pages/admin/AdminUsersPage"))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="h-8 w-8 rounded-full border-2 border-accent border-t-transparent"
        />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const role = user?.role?.toLowerCase()
  if (role !== "admin" && role !== "administrator") {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <motion.div
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        className="text-sm text-text-muted"
      >
        Loading…
      </motion.div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route
                  path="/login"
                  element={
                    <PublicRoute>
                      <LoginPage />
                    </PublicRoute>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <PublicRoute>
                      <RegisterPage />
                    </PublicRoute>
                  }
                />
                <Route
                  path="/verify-email"
                  element={
                    <PublicRoute>
                      <VerifyEmailPage />
                    </PublicRoute>
                  }
                />
                <Route
                  path="/request-access"
                  element={<Navigate to="/register" replace />}
                />
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <DashboardLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<DashboardPage />} />
                  <Route path="cases" element={<CasesPage />} />
                  <Route path="cases/new" element={<CreateCasePage />} />
                  <Route path="cases/:caseId" element={<CaseDetailPage />} />
                  <Route path="cases/:caseId/evidence" element={<EvidencePage />} />
                  <Route
                    path="cases/:caseId/evidence/:evidenceId"
                    element={<EvidenceDetailPage />}
                  />
                  <Route path="cases/:caseId/timeline" element={<TimelinePage />} />
                  <Route path="cases/:caseId/custody" element={<CustodyPage />} />
                  <Route path="cases/:caseId/reports" element={<ReportsPage />} />
                  <Route path="evidence" element={<EvidencePage />} />
                  <Route path="evidence/:evidenceId" element={<EvidenceDetailPage />} />
                  <Route path="hash-verification" element={<HashVerificationPage />} />
                  <Route path="timeline" element={<TimelinePage />} />
                  <Route path="custody" element={<CustodyPage />} />
                  <Route path="reports" element={<ReportsPage />} />
                  <Route path="analytics" element={<AnalyticsPage />} />
                  <Route path="profile" element={<ProfilePage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route
                    path="admin/users"
                    element={
                      <AdminRoute>
                        <AdminUsersPage />
                      </AdminRoute>
                    }
                  />
                </Route>
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: "#141414",
                color: "#fff",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "12px",
                fontSize: "14px",
              },
              success: {
                iconTheme: { primary: "#2ECC71", secondary: "#141414" },
              },
              error: {
                iconTheme: { primary: "#FF4D4F", secondary: "#141414" },
              },
            }}
          />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
