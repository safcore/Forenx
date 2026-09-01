import { useNavigate, Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "react-hot-toast"
import { ArrowLeft, Loader2 } from "lucide-react"
import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { getErrorMessage } from "@/api/client"
import { useCreateCaseMutation } from "@/hooks/useCases"
import { useAuth } from "@/contexts/AuthContext"
import type { CasePriority } from "@/types"
import { cn } from "@/lib/utils"

const schema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters"),
  description: z.string().optional(),
  priority: z.enum(["low", "medium", "high", "critical"]),
  tags: z.string().optional(),
})

type FormData = z.infer<typeof schema>

const PRIORITIES: { value: CasePriority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
]

export default function CreateCasePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const createCaseMutation = useCreateCaseMutation()

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { priority: "medium", description: "" },
  })

  const priority = watch("priority")

  const onSubmit = async (data: FormData) => {
    try {
      // Tags are UI-only for now — CaseSerializer has no tags field.
      const created = await createCaseMutation.mutateAsync({
        title: data.title,
        description: data.description || "",
        priority: data.priority,
        investigator: user?.id != null ? String(user.id) : undefined,
      })
      toast.success("Case created")
      navigate(`/cases/${created.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const submitting = createCaseMutation.isPending

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        to="/cases"
        className="inline-flex items-center gap-1.5 text-sm text-text-secondary transition-colors hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to cases
      </Link>

      <PageHeader
        title="New Case"
        description="Open a new investigation. Evidence and custody events attach after creation."
      />

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <Input
              label="Case title"
              placeholder="e.g. Ransomware Investigation — Acme Corp"
              error={errors.title?.message}
              {...register("title")}
            />

            <div>
              <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-text-secondary">
                Description
              </label>
              <textarea
                {...register("description")}
                rows={4}
                placeholder="Scope, initial allegations, systems involved…"
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white placeholder:text-text-muted focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15"
              />
            </div>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-secondary">
                Priority
              </p>
              <div className="flex flex-wrap gap-2">
                {PRIORITIES.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setValue("priority", p.value)}
                    className={cn(
                      "rounded-lg border px-3 py-1.5 text-sm font-medium transition-all",
                      priority === p.value
                        ? "border-accent/40 bg-accent/15 text-accent"
                        : "border-white/10 bg-white/[0.03] text-text-secondary hover:border-white/20"
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Input
                label="Tags (comma-separated)"
                placeholder="ransomware, endpoint, finance"
                {...register("tags")}
              />
              <p className="mt-1.5 text-xs text-text-muted">
                Not stored by the API yet — kept for local form UX only.
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={submitting} className="gap-2">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Create case
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate("/cases")}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
