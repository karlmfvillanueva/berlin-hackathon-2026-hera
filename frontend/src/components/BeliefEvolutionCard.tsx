import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import type { BeliefEvolutionItem } from "@/api/dashboard"

function ConfidenceBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div className="flex flex-col gap-1">
      <p className="text-body-sm text-muted-foreground">{label}</p>
      <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
        <div className="bg-foreground h-full" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-body-sm font-medium">{value.toFixed(2)}</p>
    </div>
  )
}

export function BeliefEvolutionCard({ item }: { item: BeliefEvolutionItem }) {
  const delta = item.new_confidence - item.current_confidence
  const direction = delta > 0 ? "↑" : delta < 0 ? "↓" : "·"
  return (
    <Card className="flex flex-col gap-4 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-label text-secondary">{item.rule_key.replace(/_/g, " ")}</p>
          <p className="text-rationale">{item.rule_text}</p>
        </div>
        {item.is_demo && (
          <Badge variant="secondary" className="shrink-0">
            Demo data
          </Badge>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <ConfidenceBar label="Before" value={item.current_confidence} />
        <ConfidenceBar label={`After ${direction}`} value={item.new_confidence} />
      </div>
      <p className="text-body-sm text-muted-foreground">{item.rationale}</p>
      <p className="text-body-sm text-muted-foreground">
        Sample: {item.sample_size} videos
      </p>
    </Card>
  )
}
