import { forwardRef, type InputHTMLAttributes } from "react"
import { cn } from "@/lib/utils"

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-full border border-[var(--color-border-strong)] bg-white px-4 text-sm text-[var(--color-ink)] placeholder:text-[var(--color-ink-faint)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-teal-dark)] focus-visible:ring-offset-1",
        className
      )}
      {...props}
    />
  )
)
Input.displayName = "Input"
