import { useState, useEffect } from "react"
import { useNavigate, useSearchParams, Link } from "react-router-dom"
import { motion } from "framer-motion"
import { Shield, CheckCircle2, AlertCircle, Loader2, ArrowRight, Mail } from "lucide-react"
import { toast } from "react-hot-toast"
import { verifyEmail, resendVerification } from "@/services/auth"
import { getErrorMessage } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const initialToken = searchParams.get("token") || ""
  const navigate = useNavigate()

  const [token, setToken] = useState(initialToken)
  const [resendEmail, setResendEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    initialToken ? "loading" : "idle"
  )
  const [errorMessage, setErrorMessage] = useState("")
  const [resending, setResending] = useState(false)

  useEffect(() => {
    if (initialToken) {
      handleVerify(initialToken)
    }
  }, [initialToken])

  const handleVerify = async (tokenToVerify: string) => {
    if (!tokenToVerify.trim()) return
    setStatus("loading")
    setErrorMessage("")
    try {
      await verifyEmail(tokenToVerify.trim())
      setStatus("success")
      toast.success("Email verified successfully!")
    } catch (err) {
      setStatus("error")
      const msg = getErrorMessage(err)
      setErrorMessage(msg || "Invalid or expired verification token.")
      toast.error(msg || "Verification failed.")
    }
  }

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resendEmail.trim()) return
    setResending(true)
    try {
      const res = await resendVerification(resendEmail.trim())
      toast.success(res.message || "Verification email sent.")
      setResendEmail("")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md rounded-2xl border border-white/10 bg-[#141414] p-8 shadow-2xl backdrop-blur-xl"
      >
        <div className="flex justify-center mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-accent/20 bg-accent/15">
            <Shield className="h-6 w-6 text-accent" />
          </div>
        </div>

        <h1 className="text-center font-display text-2xl font-bold tracking-tight text-white mb-2">
          Email Verification
        </h1>
        <p className="text-center text-sm text-text-secondary mb-8">
          Verify your credentials to activate forensic workstation access.
        </p>

        {status === "loading" && (
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-accent" />
            <p className="text-sm text-text-muted">Validating verification token…</p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-success/20 bg-success/10 p-4 text-center">
              <CheckCircle2 className="mx-auto h-8 w-8 text-success mb-2" />
              <p className="font-medium text-white">Email Address Verified</p>
              <p className="text-xs text-text-secondary mt-1">
                Your account is active. You may now sign in to your ForenX dashboard.
              </p>
            </div>
            <Button
              className="w-full gap-2"
              onClick={() => navigate("/login")}
            >
              Sign In <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {(status === "idle" || status === "error") && (
          <div className="space-y-6">
            {status === "error" && (
              <div className="rounded-xl border border-danger/20 bg-danger/10 p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
                <div className="text-sm text-danger leading-relaxed">
                  {errorMessage}
                </div>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleVerify(token)
              }}
              className="space-y-4"
            >
              <div className="space-y-2">
                <label className="text-xs font-medium text-text-secondary">
                  Verification Token
                </label>
                <Input
                  type="text"
                  placeholder="Paste your 32-character token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>
              <Button type="submit" className="w-full" disabled={!token.trim()}>
                Verify Account
              </Button>
            </form>

            <div className="border-t border-white/[0.08] pt-6 space-y-4">
              <p className="text-xs text-text-muted text-center">
                Need a new verification link?
              </p>
              <form onSubmit={handleResend} className="flex gap-2">
                <Input
                  type="email"
                  placeholder="investigator@agency.gov"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  className="text-xs"
                />
                <Button
                  type="submit"
                  variant="secondary"
                  size="sm"
                  disabled={resending || !resendEmail.trim()}
                  className="shrink-0 gap-1.5"
                >
                  <Mail className="h-3.5 w-3.5" />
                  {resending ? "Sending…" : "Resend"}
                </Button>
              </form>
            </div>

            <div className="text-center">
              <Link
                to="/login"
                className="text-xs text-text-secondary hover:text-white transition-colors"
              >
                Back to Sign In
              </Link>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}
