import apiClient from "@/api/client"
import type { AuthTokens, User, UserRole } from "@/types"

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true"

const DEMO_USER: User = {
  id: 1,
  email: "investigator@forenx.io",
  first_name: "Sarah",
  last_name: "Chen",
  role: "investigator",
  department: "Digital Forensics Unit",
  created_at: "2025-01-15T00:00:00Z",
}

/** Map Django `/auth/me/` payload into the frontend User shape. */
function normalizeUser(raw: Record<string, unknown>): User {
  const role = String(raw.role ?? "investigator") as UserRole
  return {
    id: (raw.id as string | number) ?? "",
    email: String(raw.email ?? ""),
    username: raw.username != null ? String(raw.username) : undefined,
    first_name: String(raw.first_name ?? ""),
    last_name: String(raw.last_name ?? ""),
    role,
    avatar: (raw.avatar as string | null | undefined) ?? null,
    department: (raw.department as string | null | undefined) ?? null,
    phone: (raw.phone as string | null | undefined) ?? null,
    created_at: String(raw.created_at ?? raw.date_joined ?? ""),
    last_login: (raw.last_login as string | null | undefined) ?? null,
    is_active: typeof raw.is_active === "boolean" ? raw.is_active : undefined,
  }
}

/**
 * Backend contract (Django):
 * POST /api/auth/login/
 * POST /api/auth/register/
 * POST /api/auth/refresh/
 * GET  /api/auth/me/
 */
export async function login(
  email: string,
  password: string
): Promise<AuthTokens> {
  if (DEMO_MODE) {
    if (email && password.length >= 6) {
      return { access: "demo-access-token", refresh: "demo-refresh-token" }
    }
    throw new Error("Invalid credentials")
  }

  const { data } = await apiClient.post("/auth/login/", { email, password })
  // Integrated backend returns SimpleJWT { access, refresh }
  if (data?.access && data?.refresh) {
    return { access: data.access, refresh: data.refresh }
  }
  if (data?.tokens?.access && data?.tokens?.refresh) {
    return data.tokens as AuthTokens
  }
  throw new Error("Login response did not include access and refresh tokens")
}

export async function register(payload: {
  email: string
  password: string
  first_name: string
  last_name: string
}): Promise<User> {
  if (DEMO_MODE) {
    return { ...DEMO_USER, ...payload, id: Date.now() }
  }
  // NOTE (Phase 2): backend RegisterSerializer requires `username`.
  // Do not wire UI registration until a username strategy is agreed.
  const { data } = await apiClient.post("/auth/register/", payload)
  return normalizeUser(data as Record<string, unknown>)
}

export async function getProfile(): Promise<User> {
  if (DEMO_MODE) {
    const tokens = getStoredTokens()
    if (tokens?.access === "demo-access-token") return DEMO_USER
    throw new Error("Unauthorized")
  }
  const { data } = await apiClient.get("/auth/me/")
  return normalizeUser(data as Record<string, unknown>)
}

export async function refreshAccessToken(refresh: string): Promise<AuthTokens> {
  if (DEMO_MODE) {
    return { access: "demo-access-token", refresh }
  }
  const { data } = await apiClient.post("/auth/refresh/", { refresh })
  return {
    access: data.access,
    refresh: data.refresh || refresh,
  }
}

export function saveTokens(tokens: AuthTokens) {
  localStorage.setItem("forenx_tokens", JSON.stringify(tokens))
}

export function clearTokens() {
  localStorage.removeItem("forenx_tokens")
}

export function getStoredTokens(): AuthTokens | null {
  const raw = localStorage.getItem("forenx_tokens")
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthTokens
  } catch {
    return null
  }
}

export function isDemoMode(): boolean {
  return DEMO_MODE
}
