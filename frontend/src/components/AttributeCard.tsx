// src/components/AttributeCard.tsx
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface AttributeCardProps {
  label: string
  children: React.ReactNode
  onEdit?: () => void
}

export function AttributeCard({ label, children, onEdit }: AttributeCardProps) {
  const [approved, setApproved] = useState(false)

  return (
    <Card
      className={cn(
        "flex h-[280px] flex-col justify-between gap-4 p-5 transition-colors",
        approved && "border-l-4 border-l-secondary"
      )}
    >
      <div className="flex flex-col gap-2.5">
        <span className="text-label text-muted-foreground">
          {approved ? "✓ Approved" : label}
        </span>
        <div className="text-display-md overflow-hidden">{children}</div>
      </div>

      <div className="flex justify-end gap-2">
        <Button onClick={onEdit} variant="outline" size="sm">
          Edit
        </Button>
        <Button
          onClick={() => setApproved((v) => !v)}
          variant="secondary"
          size="sm"
        >
          {approved ? "✓ Approved" : "✓ Looks good"}
        </Button>
      </div>
    </Card>
  )
}
