import type { ReactNode } from "react"
import { Menu, Search } from "lucide-react"
import { Link } from "react-router-dom"

export function PageHeader({
  crumbs,
  search,
  onMenuClick,
  right,
}: {
  crumbs: { label: string; to?: string }[]
  search?: string
  onMenuClick: () => void
  right?: ReactNode
}) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-[var(--color-border)] bg-white px-4 py-3 lg:px-6">
      <button
        className="rounded-[var(--radius-sm)] p-2 text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-muted)] lg:hidden"
        onClick={onMenuClick}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <nav aria-label="Breadcrumb" className="min-w-0 flex-1 truncate text-sm text-[var(--color-ink-soft)]">
        {crumbs.map((c, i) => (
          <span key={i}>
            {c.to ? (
              <Link to={c.to} className="hover:text-[var(--color-ink)]">
                {c.label}
              </Link>
            ) : (
              <span className="font-semibold text-[var(--color-ink)]">{c.label}</span>
            )}
            {i < crumbs.length - 1 && <span className="mx-2 text-[var(--color-ink-faint)]">/</span>}
          </span>
        ))}
      </nav>

      {right}

      {search !== undefined && (
        <div className="relative hidden w-64 sm:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-ink-faint)]" />
          <input
            defaultValue={search}
            placeholder="Search…"
            className="h-9 w-full rounded-full border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] pl-9 pr-3 text-sm placeholder:text-[var(--color-ink-faint)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-teal-dark)]"
          />
        </div>
      )}
    </header>
  )
}
