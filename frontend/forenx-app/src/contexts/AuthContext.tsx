import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react"
import type { User, AuthTokens } from "@/types"
import * as authService from "@/services/auth"

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes
const ACTIVITY_STORAGE_KEY = "forenx_last_activity"

function getStoredLastActivity(): number {
  const raw = localStorage.getItem(ACTIVITY_STORAGE_KEY)
  const parsed = raw ? parseInt(raw, 10) : 0
  return Number.isNaN(parsed) ? 0 : parsed
}

function updateStoredLastActivity() {
  localStorage.setItem(ACTIVITY_STORAGE_KEY, String(Date.now()))
}

function clearStoredLastActivity() {
  localStorage.removeItem(ACTIVITY_STORAGE_KEY)
}

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const lastRecordedActivityRef = useRef<number>(Date.now())

  const logout = useCallback(() => {
    authService.clearTokens()
    clearStoredLastActivity()
    setUser(null)
  }, [])

  const refreshProfile = useCallback(async () => {
    try {
      const profile = await authService.getProfile()
      setUser(profile)
      updateStoredLastActivity()
    } catch {
      logout()
    }
  }, [logout])

  // Initial load check: validates stored token and verifies inactivity expiry
  useEffect(() => {
    const tokens = authService.getStoredTokens()
    const lastActive = getStoredLastActivity()
    const isExpired =
      Boolean(tokens?.access) &&
      lastActive > 0 &&
      Date.now() - lastActive > INACTIVITY_TIMEOUT_MS

    if (isExpired) {
      logout()
      setIsLoading(false)
    } else if (tokens?.access) {
      updateStoredLastActivity()
      refreshProfile().finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [logout, refreshProfile])

  // Inactivity tracking listener while authenticated
  useEffect(() => {
    if (!user) return

    const handleUserActivity = () => {
      const now = Date.now()
      // Throttle localStorage updates to at most once every 5 seconds
      if (now - lastRecordedActivityRef.current > 5000) {
        lastRecordedActivityRef.current = now
        updateStoredLastActivity()
      }
    }

    const activityEvents = [
      "mousemove",
      "mousedown",
      "keydown",
      "scroll",
      "touchstart",
      "click",
    ]

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleUserActivity, { passive: true })
    })

    // Periodic watchdog timer to enforce 30-minute auto-logout
    const intervalId = window.setInterval(() => {
      const lastActive = getStoredLastActivity()
      if (lastActive > 0 && Date.now() - lastActive > INACTIVITY_TIMEOUT_MS) {
        logout()
      }
    }, 15000)

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleUserActivity)
      })
      window.clearInterval(intervalId)
    }
  }, [user, logout])

  const login = async (email: string, password: string) => {
    const tokens: AuthTokens = await authService.login(email, password)
    authService.saveTokens(tokens)
    updateStoredLastActivity()
    lastRecordedActivityRef.current = Date.now()
    await refreshProfile()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
