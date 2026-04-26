// src/components/BrandMark.tsx
import { cn } from "@/lib/utils"

interface BrandMarkProps {
  className?: string
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <div className={cn("flex items-baseline gap-1.5", className)}>
      <span className="font-serif text-display-md leading-none tracking-tight">
        Argus
      </span>
      <span
        aria-hidden
        className="inline-block h-1.5 w-1.5 rounded-full bg-primary"
      />
    </div>
  )
}
