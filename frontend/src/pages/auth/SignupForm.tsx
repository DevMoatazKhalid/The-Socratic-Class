import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AuthLayout } from "@/components/layout/AuthLayout"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"
import type { Role } from "@/types"

export function SignupForm({ role }: { role: Role }) {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [values, setValues] = useState({ name: "", email: "", password: "", confirm: "" })

  function update(key: keyof typeof values) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setValues((v) => ({ ...v, [key]: e.target.value }))
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!values.name || !values.email || !values.password) {
      setError("Fill in every field to continue.")
      return
    }
    if (values.password !== values.confirm) {
      setError("Passwords don't match.")
      return
    }
    setSubmitting(true)
    setTimeout(() => {
      setSubmitting(false)
      navigate(role === "student" ? "/student" : "/teacher")
    }, 600)
  }

  return (
    <AuthLayout>
      <h1 className="text-center text-lg font-semibold text-[var(--color-ink)]">
        Sign up as {role}
      </h1>
      <form className="mt-6 space-y-3" onSubmit={handleSubmit} noValidate>
        <Input placeholder={`Enter ${role} name...`} value={values.name} onChange={update("name")} aria-label="Full name" />
        <Input type="email" placeholder={`Enter ${role} email...`} value={values.email} onChange={update("email")} aria-label="Email" />
        <Input type="password" placeholder={`Enter ${role} password...`} value={values.password} onChange={update("password")} aria-label="Password" />
        <Input type="password" placeholder="Confirm password..." value={values.confirm} onChange={update("confirm")} aria-label="Confirm password" />

        {error && (
          <p role="alert" className="text-sm text-[var(--color-danger)]">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between pt-1">
          <Link to="/signup" className="text-sm font-medium text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]">
            Go to previous
          </Link>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating account…" : "Next"}
          </Button>
        </div>
      </form>
    </AuthLayout>
  )
}
