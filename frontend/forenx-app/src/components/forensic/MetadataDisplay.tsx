import { cn } from "@/lib/utils"

interface MetadataDisplayProps {
  metadata: Record<string, unknown> | null | undefined
  className?: string
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatPrimitive(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "number") return String(value)
  if (typeof value === "string") return value.trim() || "—"
  return String(value)
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

function MetadataValue({
  value,
  depth,
}: {
  value: unknown
  depth: number
}) {
  if (depth > 6) {
    return (
      <p className="text-xs text-text-muted break-all">
        {formatPrimitive(value)}
      </p>
    )
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <p className="text-xs text-text-muted">Empty list</p>
    }
    return (
      <ul className="space-y-2">
        {value.map((item, index) => (
          <li
            key={index}
            className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2"
          >
            {isPlainObject(item) || Array.isArray(item) ? (
              <MetadataValue value={item} depth={depth + 1} />
            ) : (
              <p className="text-xs text-white/90 break-all">
                {formatPrimitive(item)}
              </p>
            )}
          </li>
        ))}
      </ul>
    )
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value)
    if (entries.length === 0) {
      return <p className="text-xs text-text-muted">Empty object</p>
    }
    return (
      <dl className="space-y-2">
        {entries.map(([key, item]) => (
          <div key={key} className="grid gap-1 sm:grid-cols-[minmax(0,180px)_1fr]">
            <dt className="text-xs font-medium text-text-muted">
              {humanizeKey(key)}
            </dt>
            <dd className="min-w-0">
              {isPlainObject(item) || Array.isArray(item) ? (
                <MetadataValue value={item} depth={depth + 1} />
              ) : (
                <p className="text-xs text-white/90 break-all">
                  {formatPrimitive(item)}
                </p>
              )}
            </dd>
          </div>
        ))}
      </dl>
    )
  }

  return (
    <p className="text-xs text-white/90 break-all">{formatPrimitive(value)}</p>
  )
}

export function MetadataDisplay({ metadata, className }: MetadataDisplayProps) {
  if (!metadata || Object.keys(metadata).length === 0) {
    return (
      <p className={cn("text-sm text-text-muted", className)}>
        No metadata available.
      </p>
    )
  }

  if (metadata.status === "unavailable") {
    const message =
      typeof metadata.message === "string" && metadata.message.trim()
        ? metadata.message
        : "Metadata extraction was not available for this file at acquisition."
    return (
      <p className={cn("text-sm text-text-secondary", className)}>{message}</p>
    )
  }

  return (
    <div className={cn("space-y-3", className)}>
      <MetadataValue value={metadata} depth={0} />
    </div>
  )
}
