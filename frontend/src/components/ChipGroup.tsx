// src/components/ChipGroup.tsx
import { cn } from "@/lib/utils"

interface ChipGroupProps {
  /** Tags to render. The first item (or the one matching `activeLabel`) is rendered as active. */
  tags: string[]
  /** Optional explicit active tag. Falls back to the first tag. */
  activeLabel?: string
  className?: string
}

export function ChipGroup({ tags, activeLabel, className }: ChipGroupProps) {
  const active = activeLabel ?? tags[0]
  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {tags.map((tag) => {
        const isActive = tag === active
        return (
          <span
            key={tag}
            className={cn(
              "rounded-full px-2.5 py-1 text-[11px] italic",
              isActive
                ? "bg-secondary not-italic font-medium text-secondary-foreground"
                : "border border-border text-foreground"
            )}
          >
            {tag}
          </span>
        )
      })}
    </div>
  )
}
