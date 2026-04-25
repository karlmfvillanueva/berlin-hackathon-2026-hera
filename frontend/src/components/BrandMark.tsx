// src/components/BrandMark.tsx
import { cn } from "@/lib/utils"

interface BrandMarkProps {
  className?: string
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-display-md leading-none">Editorial</span>
      <span
        aria-hidden
        className="inline-block h-2.5 w-2.5 bg-secondary"
      />
    </div>
  )
}
