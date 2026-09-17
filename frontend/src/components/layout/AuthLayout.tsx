import type { ReactNode } from "react"
import { Link } from "react-router-dom"

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#cfe0ee] via-[#dceae3] to-[#eef3eb] p-4">
      <div className="w-full max-w-sm rounded-[var(--radius-xl)] bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <Link to="/" className="inline-flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-teal)]" />
            <span className="text-lg font-semibold text-[var(--color-ink)]">SocratiQ</span>
          </Link>
        </div>
        {children}
      </div>
    </div>
  )
}
