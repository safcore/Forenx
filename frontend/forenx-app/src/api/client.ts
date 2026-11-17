import axios, { type InternalAxiosRequestConfig } from "axios"
import type { AuthTokens } from "@/types"

export const API_BASE =
  import.meta.env?.VITE_API_URL ||
  (import.meta.env?.DEV ? "http://localhost:8000/api" : "/api")

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete config.headers["Content-Type"]
  }
  const tokens = localStorage.getItem("forenx_tokens")
  if (tokens) {
    try {
      const { access } = JSON.parse(tokens) as AuthTokens
      if (access && access !== "demo-access-token") {
        config.headers.Authorization = `Bearer ${access}`
      } else if (access === "demo-access-token" && import.meta.env?.VITE_DEMO_MODE === "true") {
        config.headers.Authorization = `Bearer ${access}`
      }
    } catch {
      // ignore parse errors
    }
  }
  return config
})

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error)
    else if (token) prom.resolve(token)
  })
  failedQueue = []
}

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false
  return (
    url.includes("/auth/login/") ||
    url.includes("/token/") ||
    url.includes("/token/refresh/") ||
    url.includes("/auth/register/") ||
    url.includes("/register/") ||
    url.includes("/auth/refresh/") ||
    url.includes("/auth/verify-email/") ||
    url.includes("/verify-email/") ||
    url.includes("/auth/resend-verification/") ||
    url.includes("/resend-verification/")
  )
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (import.meta.env?.VITE_DEMO_MODE === "true") {
        return Promise.reject(error)
      }

      // Failed login/register/refresh must not enter the token-refresh loop.
      if (isAuthEndpoint(originalRequest.url)) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const tokens = localStorage.getItem("forenx_tokens")
      if (!tokens) {
        isRefreshing = false
        localStorage.removeItem("forenx_tokens")
        if (
          typeof window !== "undefined" &&
          window.location.pathname !== "/login" &&
          window.location.pathname !== "/register" &&
          window.location.pathname !== "/verify-email"
        ) {
          window.location.href = "/login"
        }
        return Promise.reject(error)
      }

      try {
        const { refresh } = JSON.parse(tokens) as AuthTokens
        // Use bare axios (not apiClient) so refresh 401 cannot recurse.
        const { data } = await axios.post(`${API_BASE}/token/refresh/`, {
          refresh,
        })
        const newTokens: AuthTokens = {
          access: data.access,
          refresh: data.refresh || refresh,
        }
        localStorage.setItem("forenx_tokens", JSON.stringify(newTokens))
        processQueue(null, newTokens.access)
        originalRequest.headers.Authorization = `Bearer ${newTokens.access}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        localStorage.removeItem("forenx_tokens")
        if (
          typeof window !== "undefined" &&
          window.location.pathname !== "/login" &&
          window.location.pathname !== "/register" &&
          window.location.pathname !== "/verify-email"
        ) {
          window.location.href = "/login"
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

function firstMessage(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value
  if (Array.isArray(value) && value.length > 0) return firstMessage(value[0])
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>
    if (obj.message != null) return firstMessage(obj.message)
    if (obj.detail != null) return firstMessage(obj.detail)
    // Field-level DRF errors: { title: ["..."], investigator: ["..."] }
    for (const [key, val] of Object.entries(obj)) {
      if (key === "code" || key === "details") continue
      const nested = firstMessage(val)
      if (nested) return key === "non_field_errors" ? nested : `${key}: ${nested}`
    }
  }
  return null
}

export function getFieldErrors(error: unknown): Record<string, string[]> {
  if (axios.isAxiosError(error)) {
    const rawData = error.response?.data
    if (
      rawData &&
      typeof rawData === "object" &&
      !(typeof Blob !== "undefined" && rawData instanceof Blob)
    ) {
      const data = rawData as Record<string, unknown>
      const result: Record<string, string[]> = {}
      for (const [key, value] of Object.entries(data)) {
        if (Array.isArray(value)) {
          result[key] = value.map(String)
        } else if (typeof value === "string") {
          result[key] = [value]
        }
      }
      return result
    }
  }
  return {}
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const rawData = error.response?.data
    const data =
      rawData &&
      typeof rawData === "object" &&
      !(typeof Blob !== "undefined" && rawData instanceof Blob)
        ? (rawData as Record<string, unknown>)
        : undefined
    const envelope = data?.error as Record<string, unknown> | undefined
    const code = typeof envelope?.code === "string" ? envelope.code : ""
    const fieldDetail =
      envelope?.details != null ? firstMessage(envelope.details) : null
    const fromEnvelope =
      fieldDetail ||
      firstMessage(data?.error) ||
      firstMessage(data?.detail) ||
      firstMessage(data?.message) ||
      firstMessage(data)

    if (
      code === "EVIDENCE_FILE_MISSING" ||
      (fromEnvelope &&
        /evidence file.*(missing|unavailable)/i.test(fromEnvelope))
    ) {
      return "Evidence file is currently unavailable for this operation."
    }

    if (
      fromEnvelope &&
      /no active account found/i.test(fromEnvelope)
    ) {
      return "Invalid email, username or password. Please try again."
    }

    if (fromEnvelope && fromEnvelope !== "Validation failed") {
      // Never surface stack traces or absolute paths from API text.
      if (/traceback|file:\/\/|[A-Za-z]:\\|\.py:\d+/i.test(fromEnvelope)) {
        return "Something went wrong. Please try again."
      }
      return fromEnvelope
    }
    if (fieldDetail) return fieldDetail

    if (status === 401) {
      return "Invalid email, username or password. Please try again."
    }
    if (status === 403) {
      return "You do not have permission to perform this action."
    }
    if (status === 404) {
      return "The requested resource could not be found."
    }
    if (status === 400) {
      return "Invalid input. Please check the highlighted fields."
    }
    if (status === 413) return "The file exceeds the permitted upload size."
    if (status === 429) return "Too many requests. Please try again later."
    if (status && status >= 500) return "Something went wrong. Please try again."
    if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
      return "Cannot reach the API server. Check the connection and try again."
    }
  }
  if (error instanceof Error) {
    if (/traceback|file:\/\/|[A-Za-z]:\\/i.test(error.message)) {
      return "Something went wrong. Please try again."
    }
    if (/request failed with status code/i.test(error.message)) {
      return "Invalid input. Please check the highlighted fields."
    }
    return error.message
  }
  return "Something went wrong. Please try again."
}

export default apiClient
