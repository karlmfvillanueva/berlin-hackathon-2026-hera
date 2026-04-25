// src/components/StepIndicator.tsx
import { cn } from "@/lib/utils"

interface StepIndicatorProps {
  /** Ordered step labels from first to last. */
  steps: string[]
  /** 1-based index of the currently-active step. Steps before it are "done". */
  currentStep: number
  className?: string
}

export function StepIndicator({ steps, currentStep, className }: StepIndicatorProps) {
  return (
    <div className={cn("flex items-start", className)} role="list" aria-label="Progress">
      {steps.map((label, i) => {
        const idx = i + 1
        const stateClass =
          idx < currentStep
            ? "bg-muted-foreground" // done
            : idx === currentStep
              ? "bg-secondary"      // active
              : "bg-border"         // future

        const lineClass =
          idx < currentStep ? "bg-muted-foreground" : "bg-border"

        const labelClass =
          idx < currentStep
            ? "text-muted-foreground"
            : idx === currentStep
              ? "text-foreground"
              : "text-muted-foreground/60"

        return (
          <div key={label} className="flex flex-1 items-start" role="listitem">
            <div className="flex flex-col items-center gap-2 px-1">
              <span
                aria-hidden
                className={cn("h-2 w-2 rounded-full", stateClass)}
              />
              <span className={cn("text-label whitespace-nowrap", labelClass)}>
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                aria-hidden
                className={cn("mt-[3px] h-px flex-1", lineClass)}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
