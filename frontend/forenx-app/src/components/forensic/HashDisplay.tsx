import { useState } from "react"
import { Check, Copy } from "lucide-react"
import { toast } from "react-hot-toast"
import { cn } from "@/lib/utils"

interface HashDisplayProps {
  label: string
  value?: string | null
  algorithm?: string
  className?: string
  truncate?: boolean
}

export function HashDisplay({
  label,
  value,
  algorithm,
  className,
  truncate = true,
}: HashDisplayProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      toast.success("Hash copied")
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error("Failed to copy")
    }
  }

  const display =
    value && truncate && value.length > 24
      ? `${value.slice(0, 12)}…${value.slice(-8)}`
      : value

  return (
    <div
      className={cn(
        "group flex items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-2.5",
        className
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
          {algorithm || label}
        </p>
        {value ? (
          <p
            className="mt-0.5 font-mono text-xs text-white/90 break-all"
            title={value}
          >
            {display}
          </p>
        ) : (
          <p className="mt-0.5 text-xs text-text-muted">Not available</p>
        )}
      </div>
      {value && (
        <button
          type="button"
          onClick={handleCopy}
          aria-label={`Copy ${label}`}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-success" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      )}
    </div>
  )
}
