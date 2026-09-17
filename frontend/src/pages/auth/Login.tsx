import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AuthLayout } from "@/components/layout/AuthLayout"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"

export default function Login() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!email || !password) {
      setError("Enter your email and password.")
      return
    }
    setSubmitting(true)
    setTimeout(() => {
      setSubmitting(false)
      navigate(email.includes("teacher") ? "/teacher" : "/student")
    }, 500)
  }

  return (
    <AuthLayout>
      <h1 className="text-center text-lg font-semibold text-[var(--color-ink)]">Log in</h1>
      <form className="mt-6 space-y-3" onSubmit={handleSubmit} noValidate>
        <Input type="email" placeholder="Enter email..." value={email} onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
        <Input type="password" placeholder="Enter password..." value={password} onChange={(e) => setPassword(e.target.value)} aria-label="Password" />

        {error && (
          <p role="alert" className="text-sm text-[var(--color-danger)]">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between pt-1">
          <Link to="/" className="text-sm font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]">
            Go to previous
          </Link>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Logging in…" : "Log in"}
          </Button>
        </div>
      </form>
      <p className="mt-4 text-center text-xs text-[var(--color-ink-faint)]">
        Tip: use an email containing "teacher" to preview the instructor view.
      </p>
    </AuthLayout>
  )
}
