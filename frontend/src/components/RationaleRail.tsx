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
  const hasAgentInsights =
    decision.icp ||
    decision.visual_system ||
    decision.reviews_evaluation ||
    decision.photo_analysis
  const hasJudge = typeof decision.judge_score === "number"

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

      {hasJudge && (
        <Card className="p-5">
          <details>
            <summary className="text-label text-secondary cursor-pointer list-none">
              Editorial Judge ·{" "}
              <span className="font-semibold text-foreground">
                {decision.judge_score?.toFixed(1)}/10
              </span>
            </summary>
            <Separator className="my-3" />
            {decision.judge_rationale && (
              <p className="text-body-sm text-muted-foreground leading-relaxed">
                {decision.judge_rationale}
              </p>
            )}
            {decision.judge_scores_per_brief &&
              decision.judge_scores_per_brief.length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  {decision.judge_scores_per_brief.map((s) => (
                    <div
                      key={s.index}
                      className="text-body-sm text-muted-foreground"
                    >
                      <span className="font-medium text-foreground">
                        Brief {s.index}
                      </span>
                      {typeof s.aggregate === "number" && (
                        <> · agg {s.aggregate.toFixed(1)}</>
                      )}
                      {s.weakness && (
                        <span className="block italic">{s.weakness}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
          </details>
        </Card>
      )}

      {hasAgentInsights && (
        <Card className="p-5">
          <details>
            <summary className="text-label text-secondary cursor-pointer list-none">
              Agent Insights
            </summary>
            <Separator className="my-3" />
            <div className="flex flex-col gap-4">
              {decision.icp?.best_icp?.persona && (
                <div className="flex flex-col gap-1">
                  <p className="text-label text-secondary">ICP</p>
                  <p className="text-rationale">
                    <span className="font-semibold">
                      {decision.icp.best_icp.persona}
                    </span>
                    {typeof decision.icp.best_icp.fit_score === "number" && (
                      <span className="text-muted-foreground">
                        {" · fit "}
                        {decision.icp.best_icp.fit_score.toFixed(2)}
                      </span>
                    )}
                  </p>
                  {decision.icp.best_icp.booking_trigger && (
                    <p className="text-body-sm text-muted-foreground">
                      Trigger: {decision.icp.best_icp.booking_trigger}
                    </p>
                  )}
                </div>
              )}
              {decision.visual_system?.inferred_setting && (
                <div className="flex flex-col gap-1">
                  <p className="text-label text-secondary">Visual System</p>
                  <p className="text-rationale">
                    Setting:{" "}
                    <span className="font-semibold">
                      {decision.visual_system.inferred_setting}
                    </span>
                  </p>
                  {decision.visual_system.music && (
                    <p className="text-body-sm text-muted-foreground">
                      Music: {decision.visual_system.music}
                    </p>
                  )}
                  {decision.visual_system.transitions && (
                    <p className="text-body-sm text-muted-foreground">
                      Transitions: {decision.visual_system.transitions}
                    </p>
                  )}
                </div>
              )}
              {decision.reviews_evaluation?.best_video_quotes?.[0]?.quote && (
                <div className="flex flex-col gap-1">
                  <p className="text-label text-secondary">Review Proof</p>
                  <p className="text-rationale italic">
                    “{decision.reviews_evaluation.best_video_quotes[0].quote}”
                  </p>
                </div>
              )}
              {decision.photo_analysis?.analysis_summary?.one_line_strategy && (
                <div className="flex flex-col gap-1">
                  <p className="text-label text-secondary">Photo Strategy</p>
                  <p className="text-rationale">
                    {decision.photo_analysis.analysis_summary.one_line_strategy}
                  </p>
                </div>
              )}
            </div>
          </details>
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
