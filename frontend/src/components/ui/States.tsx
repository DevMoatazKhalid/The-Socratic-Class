import type { ReactNode } from "react"
import { Button } from "./Button"

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description: string
  action?: { label: string; onClick?: () => void }
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-6 py-14 text-center">
      {icon && <div className="mb-3 text-[var(--color-ink-faint)]">{icon}</div>}
      <h3 className="text-base font-semibold text-[var(--color-ink)]">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-[var(--color-ink-soft)]">{description}</p>
      {action && (
        <Button className="mt-4" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}

export function ErrorState({ title, description, onRetry }: { title: string; description: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-[var(--color-danger-light)] bg-[var(--color-danger-light)]/40 px-6 py-14 text-center">
      <h3 className="text-base font-semibold text-[var(--color-danger)]">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-[var(--color-ink-soft)]">{description}</p>
      {onRetry && (
        <Button className="mt-4" size="sm" variant="outline" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-[var(--radius-md)] bg-[var(--color-border)] ${className}`} />
}

export function CardSkeleton() {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-white p-5">
      <Skeleton className="h-24 w-full rounded-[var(--radius-md)] mb-4" />
      <Skeleton className="h-4 w-2/3 mb-2" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  )
}
