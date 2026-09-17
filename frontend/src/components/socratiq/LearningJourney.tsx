import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

export interface JourneyStep {
  label: string
  state: "done" | "current" | "upcoming"
}

export function LearningJourney({ steps }: { steps: JourneyStep[] }) {
  return (
    <ol className="flex items-center gap-0" aria-label="Learning journey">
      {steps.map((step, i) => (
        <li key={step.label} className="flex flex-1 items-center last:flex-none">
          <div className="flex flex-col items-center gap-1.5">
            <span
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold",
                step.state === "done" && "bg-[var(--color-teal)] text-white",
                step.state === "current" && "bg-[var(--color-plum)] text-white",
                step.state === "upcoming" && "bg-[var(--color-surface-muted)] text-[var(--color-ink-faint)] border border-[var(--color-border-strong)]"
              )}
            >
              {step.state === "done" ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </span>
            <span
              className={cn(
                "max-w-[6.5rem] text-center text-xs",
                step.state === "upcoming" ? "text-[var(--color-ink-faint)]" : "text-[var(--color-ink-soft)] font-medium"
              )}
            >
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              className={cn(
                "mx-1 mb-4 h-px flex-1",
                step.state === "done" ? "bg-[var(--color-teal)]" : "bg-[var(--color-border-strong)]"
              )}
            />
          )}
        </li>
      ))}
    </ol>
  )
}
