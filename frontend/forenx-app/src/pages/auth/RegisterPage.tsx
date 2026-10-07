import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { motion } from "framer-motion"
import { Shield, Eye, EyeOff, Loader2, ArrowRight, AlertCircle } from "lucide-react"
import { toast } from "react-hot-toast"
import * as authService from "@/services/auth"
import { getErrorMessage } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const registerSchema = z.object({
  first_name: z.string().trim().min(1, "First name is required"),
  last_name: z.string().trim().min(1, "Last name is required"),
  username: z
    .string()
    .trim()
    .min(3, "Username must be at least 3 characters")
    .max(150, "Username must be at most 150 characters")
    .regex(/^[\w.@+-]+$/, "Letters, digits, and @/./+/-/_ only"),
  email: z.string().trim().email("Enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  phone: z.string().trim().max(20, "Phone number too long").optional().or(z.literal("")),
  department: z.string().trim().max(100, "Department name too long").optional().or(z.literal("")),
})

type RegisterFormData = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      username: "",
      email: "",
      password: "",
      phone: "",
      department: "",
    },
  })

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true)
    setApiError(null)
    try {
      await authService.register({
        first_name: data.first_name.trim(),
        last_name: data.last_name.trim(),
        username: data.username.trim(),
        email: data.email.trim(),
        password: data.password,
        phone: data.phone?.trim() || undefined,
        department: data.department?.trim() || undefined,
      })

      toast.success(
        "Account created! Please check your email for the verification link."
      )
      navigate("/verify-email")
    } catch (err) {
      const msg = getErrorMessage(err)
      setApiError(msg)
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-background">
      {/* Left panel - Hero & Brand */}
      <div className="relative hidden w-1/2 flex-col justify-between p-12 lg:flex">
        {/* Gradient orbs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -left-20 -top-20 h-[500px] w-[500px] rounded-full bg-accent/10 blur-[120px]" />
          <div className="absolute bottom-0 right-0 h-[400px] w-[400px] rounded-full bg-accent/5 blur-[100px]" />
          <div className="absolute left-1/2 top-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/[0.02] blur-[80px]" />
        </div>

        {/* Grid pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
          }}
        />

        <div className="relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex items-center gap-3"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent/15 border border-accent/25">
              <Shield className="h-6 w-6 text-accent" />
            </div>
            <span className="font-display text-2xl font-semibold tracking-tight">
              ForenX
            </span>
          </motion.div>
        </div>

        <div className="relative z-10 max-w-lg">
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="font-display text-5xl font-semibold leading-[1.15] tracking-tight text-white"
          >
            Join ForenX.
            <br />
            Secure Evidence.
            <br />
            <span className="text-gradient-accent">Begin Investigations.</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-6 text-lg leading-relaxed text-text-secondary"
          >
            Create your account to access enterprise-grade digital forensic tools,
            cryptographic chain-of-custody verification, and offline-capable analysis.
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="relative z-10 flex items-center gap-8 text-sm text-text-muted"
        >
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-success" />
            SOC 2 Compliant
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-success" />
            Cryptographic Integrity
          </div>
        </motion.div>
      </div>

      {/* Right panel - Registration form */}
      <div className="flex w-full items-center justify-center p-6 lg:w-1/2 lg:p-12 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-lg my-auto py-6"
        >
          <div className="glass-strong rounded-3xl p-8 soft-shadow lg:p-10">
            <div className="mb-6">
              <h2 className="font-display text-2xl font-semibold text-white">
                Create New Account
              </h2>
              <p className="mt-2 text-sm text-text-secondary">
                Create your ForenX investigation workspace account
              </p>
            </div>

            {apiError && (
              <div
                className="mb-5 flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger/10 p-3.5 text-xs text-danger"
                role="alert"
              >
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{apiError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="First Name"
                  type="text"
                  placeholder="Sarah"
                  error={errors.first_name?.message}
                  {...register("first_name")}
                />
                <Input
                  label="Last Name"
                  type="text"
                  placeholder="Chen"
                  error={errors.last_name?.message}
                  {...register("last_name")}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="Username"
                  type="text"
                  placeholder="sarah.chen"
                  error={errors.username?.message}
                  {...register("username")}
                />
                <Input
                  label="Email"
                  type="email"
                  placeholder="investigator@agency.gov"
                  error={errors.email?.message}
                  {...register("email")}
                />
              </div>

              <div className="relative">
                <Input
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  placeholder="At least 8 characters"
                  error={errors.password?.message}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-[38px] text-text-muted hover:text-white transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="Department (Optional)"
                  type="text"
                  placeholder="Digital Forensics Unit"
                  error={errors.department?.message}
                  {...register("department")}
                />
                <Input
                  label="Phone (Optional)"
                  type="tel"
                  placeholder="+1 (555) 019-2834"
                  error={errors.phone?.message}
                  {...register("phone")}
                />
              </div>

              <Button
                type="submit"
                className="w-full h-12 text-base font-medium mt-2"
                disabled={isLoading}
                magnetic
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-8 text-center text-sm text-text-muted">
              Already have an account?{" "}
              <Link
                to="/login"
                onClick={(e) => {
                  e.preventDefault()
                  navigate("/login")
                }}
                className="text-accent hover:text-accent/80 font-medium transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
