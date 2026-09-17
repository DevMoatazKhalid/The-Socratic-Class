import { initials, cn } from "@/lib/utils"

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <div
      className={cn(
        "flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-slate-light)] text-sm font-semibold text-[#4b5b78]",
        className
      )}
      aria-hidden
    >
      {initials(name)}
    </div>
  )
}
