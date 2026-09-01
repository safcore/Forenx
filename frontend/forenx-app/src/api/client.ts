import axios, { type InternalAxiosRequestConfig } from "axios"
import type { AuthTokens } from "@/types"

export const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? "http://localhost:8000/api" : "/api")

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const tokens = localStorage.getItem("forenx_tokens")
  if (tokens) {
    try {
      const { access } = JSON.parse(tokens) as AuthTokens
      if (access && access !== "demo-access-token") {
        config.headers.Authorization = `Bearer ${access}`
      } else if (access === "demo-access-token" && import.meta.env.VITE_DEMO_MODE === "true") {
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
    url.includes("/auth/register/") ||
    url.includes("/auth/refresh/")
  )
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (import.meta.env.VITE_DEMO_MODE === "true") {
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
        window.location.href = "/login"
        return Promise.reject(error)
      }

      try {
        const { refresh } = JSON.parse(tokens) as AuthTokens
        // Use bare axios (not apiClient) so refresh 401 cannot recurse.
        const { data } = await axios.post(`${API_BASE}/auth/refresh/`, {
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
        window.location.href = "/login"
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
      firstMessage(data?.message)

    if (
      code === "EVIDENCE_FILE_MISSING" ||
      (fromEnvelope &&
        /evidence file.*(missing|unavailable)/i.test(fromEnvelope))
    ) {
      return "Evidence file is currently unavailable for this operation."
    }

    if (status === 401) {
      return "Your session has expired. Please sign in again."
    }
    if (status === 403) {
      return "You do not have permission to perform this action."
    }
    if (status === 404) {
      return "The requested resource could not be found."
    }

    if (fromEnvelope && fromEnvelope !== "Validation failed") {
      // Never surface stack traces or absolute paths from API text.
      if (/traceback|file:\/\/|[A-Za-z]:\\|\.py:\d+/i.test(fromEnvelope)) {
        return "Something went wrong. Please try again."
      }
      return fromEnvelope
    }
    if (fieldDetail) return fieldDetail
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
    return error.message
  }
  return "Something went wrong. Please try again."
}

export default apiClient
