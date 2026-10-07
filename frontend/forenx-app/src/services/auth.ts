import apiClient from "@/api/client"
import type {
  AdminUser,
  AuthTokens,
  RegisterPayload,
  User,
  UserRole,
} from "@/types"

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

function normalizeRole(rawRole: unknown): UserRole {
  const r = String(rawRole ?? "").toUpperCase()
  switch (r) {
    case "ADMIN":
    case "ADMINISTRATOR":
      return "administrator"
    case "LEAD":
    case "LEAD_INVESTIGATOR":
      return "lead_investigator"
    case "INVESTIGATOR":
      return "investigator"
    case "ANALYST":
      return "analyst"
    case "AUDITOR":
      return "auditor"
    case "VIEWER":
      return "viewer"
    default:
      return "investigator"
  }
}

/** Map Django `/profile/` payload directly into the frontend User shape. */
function normalizeUser(raw: Record<string, unknown>): User {
  return {
    id: (raw.id as string | number) ?? "",
    email: String(raw.email ?? ""),
    username: raw.username != null ? String(raw.username) : undefined,
    first_name: String(raw.first_name ?? ""),
    last_name: String(raw.last_name ?? ""),
    role: normalizeRole(raw.role),
    avatar: (raw.avatar as string | null | undefined) ?? null,
    department: (raw.department as string | null | undefined) ?? null,
    phone: (raw.phone as string | null | undefined) ?? null,
    created_at: String(raw.created_at ?? raw.date_joined ?? ""),
    last_login: (raw.last_login as string | null | undefined) ?? null,
    is_active: typeof raw.is_active === "boolean" ? raw.is_active : undefined,
    is_email_verified:
      typeof raw.is_email_verified === "boolean"
        ? raw.is_email_verified
        : undefined,
  }
}

/**
 * Backend contract (Django):
 * POST /api/auth/login/ (or /api/token/)
 * POST /api/auth/register/ (or /api/register/)
 * POST /api/token/refresh/
 * GET  /api/profile/
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

export async function register(payload: RegisterPayload): Promise<User> {
  if (DEMO_MODE) {
    return {
      ...DEMO_USER,
      ...payload,
      id: Date.now(),
      role: "investigator",
      created_at: new Date().toISOString(),
    }
  }

  // Ensure username is included as required by Django RegisterSerializer.
  // If the caller provides a username, use it.
  // Otherwise, derive a clean fallback username from email local-part:
  // e.g., 'sarah.chen@example.com' -> 'sarah.chen' (sanitized for Django AbstractUser: letters, digits, and @/./+/-/_).
  const derivedUsername =
    payload.username?.trim() ||
    payload.email
      .split("@")[0]
      .replace(/[^\w.@+-]/g, "_")
      .slice(0, 150)

  const requestBody = {
    username: derivedUsername,
    email: payload.email.trim().toLowerCase(),
    password: payload.password,
    first_name: payload.first_name.trim(),
    last_name: payload.last_name.trim(),
    ...(payload.phone ? { phone: payload.phone.trim() } : {}),
  }

  const { data } = await apiClient.post("/auth/register/", requestBody)
  return normalizeUser(data as Record<string, unknown>)
}

export async function getProfile(): Promise<User> {
  if (DEMO_MODE) {
    const tokens = getStoredTokens()
    if (tokens?.access === "demo-access-token") return DEMO_USER
    throw new Error("Unauthorized")
  }
  const { data } = await apiClient.get("/profile/")
  return normalizeUser(data as Record<string, unknown>)
}

export async function refreshAccessToken(refresh: string): Promise<AuthTokens> {
  if (DEMO_MODE) {
    return { access: "demo-access-token", refresh }
  }
  const { data } = await apiClient.post("/token/refresh/", { refresh })
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

export async function verifyEmail(
  token: string
): Promise<{ message: string; email?: string }> {
  const { data } = await apiClient.post("/auth/verify-email/", { token })
  return data
}

export async function resendVerification(
  email: string
): Promise<{ message: string }> {
  const { data } = await apiClient.post("/auth/resend-verification/", { email })
  return data
}

export async function listAdminUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get("/admin/users/")
  return Array.isArray(data) ? data : (data?.results ?? [])
}

export async function updateAdminUser(
  id: number | string,
  payload: { role?: string; is_active?: boolean; is_email_verified?: boolean }
): Promise<AdminUser> {
  const { data } = await apiClient.patch(`/admin/users/${id}/`, payload)
  return data
}
