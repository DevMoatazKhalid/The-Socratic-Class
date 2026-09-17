import { Card } from "@/components/ui/Card"

export function MetricCard({ value, label }: { value: string; label: string }) {
  return (
    <Card className="p-5">
      <p className="text-2xl font-semibold text-[var(--color-ink)]">{value}</p>
      <p className="mt-1 text-sm text-[var(--color-ink-soft)]">{label}</p>
    </Card>
  )
}
