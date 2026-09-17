import { Link, useNavigate } from "react-router-dom"
import { AuthLayout } from "@/components/layout/AuthLayout"
import { Button } from "@/components/ui/Button"

export default function ChooseSignup() {
  const navigate = useNavigate()
  return (
    <AuthLayout>
      <h1 className="text-center text-lg font-semibold text-[var(--color-ink)]">Choose what to sign up as</h1>
      <div className="mt-6 space-y-3">
        <Button variant="outline" size="lg" className="w-full" onClick={() => navigate("/signup/student")}>
          Sign up as student
        </Button>
        <Button variant="outline" size="lg" className="w-full" onClick={() => navigate("/signup/teacher")}>
          Sign up as teacher
        </Button>
      </div>
      <p className="mt-5 text-center text-sm">
        <Link to="/" className="font-medium text-[var(--color-plum)]">
          Go to previous
        </Link>
      </p>
    </AuthLayout>
  )
}
