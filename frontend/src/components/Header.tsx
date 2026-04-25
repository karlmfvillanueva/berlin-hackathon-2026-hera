// src/components/Header.tsx
import { BrandMark } from "@/components/BrandMark"
import { cn } from "@/lib/utils"

interface HeaderProps {
  className?: string
}

const NAV = ["Generate", "Library", "Beliefs"] as const
const ACTIVE = "Generate"

export function Header({ className }: HeaderProps) {
  return (
    <header
      className={cn(
        "flex h-16 shrink-0 items-center justify-between border-b border-border bg-background px-8",
        className
      )}
    >
      <BrandMark />

      <nav className="flex gap-6 text-body-sm">
        {NAV.map((item) => (
          <span
            key={item}
            className={cn(
              item === ACTIVE
                ? "font-medium text-foreground"
                : "text-muted-foreground"
            )}
          >
            {item}
          </span>
        ))}
      </nav>

      <div
        aria-label="Profile"
        className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold text-secondary-foreground"
      >
        JH
      </div>
    </header>
  )
}
