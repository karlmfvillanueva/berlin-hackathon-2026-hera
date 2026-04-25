// src/components/RationaleRail.tsx
import { ChipGroup } from "@/components/ChipGroup"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { AgentDecision } from "../types"

interface RationaleRailProps {
  decision: AgentDecision
}

const SECTIONS: { label: string; key: "hook" | "pacing" | "angle" | "background" }[] = [
  { label: "Hook", key: "hook" },
  { label: "Pacing", key: "pacing" },
  { label: "Angle", key: "angle" },
  { label: "Background", key: "background" },
]

function parseVibes(vibes: string): string[] {
  return vibes
    .split("·")
    .map((v) => v.trim())
    .filter(Boolean)
}

export function RationaleRail({ decision }: RationaleRailProps) {
  const tags = parseVibes(decision.vibes)

  return (
    <aside className="flex w-full max-w-sm shrink-0 flex-col gap-4">
      {tags.length > 0 && (
        <Card className="p-5">
          <p className="text-label text-secondary mb-3">Vibes</p>
          <ChipGroup tags={tags} />
        </Card>
      )}

      {SECTIONS.map(({ label, key }) => (
        <Card key={key} className="p-5">
          <p className="text-label text-secondary mb-3">{label}</p>
          <p className="text-rationale">{String(decision[key])}</p>
        </Card>
      ))}

      {decision.beliefs_applied && decision.beliefs_applied.length > 0 && (
        <Card className="p-5">
          <p className="text-label text-secondary mb-3">Beliefs Applied</p>
          <div className="flex flex-wrap gap-1.5">
            {decision.beliefs_applied.map((belief) => (
              <Badge key={belief} variant="secondary">
                {belief.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-5">
        <details>
          <summary className="text-label text-secondary cursor-pointer list-none">
            Full Rationale
          </summary>
          <Separator className="my-3" />
          <pre className="text-body-sm whitespace-pre-wrap break-words text-muted-foreground">
            {decision.hera_prompt}
          </pre>
        </details>
      </Card>
    </aside>
  )
}
