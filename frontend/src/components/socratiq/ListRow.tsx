import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/Badge"
import type { AssignmentStatus } from "@/types"

const statusLabel: Record<AssignmentStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  submitted: "Submitted",
  verified: "Verified",
}

const statusTone: Record<AssignmentStatus, "neutral" | "warning" | "teal" | "success"> = {
  not_started: "neutral",
  in_progress: "warning",
  submitted: "teal",
  verified: "success",
}

export function AssignmentRow({
  to,
  title,
  topic,
  status,
}: {
  to: string
  title: string
  topic: string
  status: AssignmentStatus
}) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-4 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-white px-4 py-3.5 transition-colors hover:bg-[var(--color-surface-muted)]"
    >
      <div className="min-w-0">
        <p className="truncate font-medium text-[var(--color-ink)]">{title}</p>
        <p className="truncate text-sm text-[var(--color-ink-soft)]">{topic}</p>
      </div>
      <Badge tone={statusTone[status]}>{statusLabel[status]}</Badge>
    </Link>
  )
}

export function MaterialRow({ to, title, summary }: { to: string; title: string; summary: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-4 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-white px-4 py-3.5 transition-colors hover:bg-[var(--color-surface-muted)]"
    >
      <div className="min-w-0">
        <p className="truncate font-medium text-[var(--color-ink)]">{title}</p>
        <p className="truncate text-sm text-[var(--color-ink-soft)]">{summary}</p>
      </div>
      <Badge tone="slate">Material</Badge>
    </Link>
  )
}
