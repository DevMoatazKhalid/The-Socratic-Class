import { Link } from "react-router-dom"
import { Button } from "@/components/ui/Button"

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--color-canvas)] px-4 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-[var(--color-teal-dark)]">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-[var(--color-ink)]">Page not found</h1>
      <p className="mt-2 max-w-sm text-[var(--color-ink-soft)]">
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link to="/">
        <Button className="mt-5">Back to landing</Button>
      </Link>
    </div>
  )
}
