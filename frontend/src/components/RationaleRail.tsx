import type { AgentDecision } from "../types";

interface RationaleRailProps {
  decision: AgentDecision;
}

const SECTIONS: { label: string; key: keyof AgentDecision }[] = [
  { label: "HOOK", key: "hook" },
  { label: "PACING", key: "pacing" },
  { label: "ANGLE", key: "angle" },
  { label: "BACKGROUND", key: "background" },
];

export function RationaleRail({ decision }: RationaleRailProps) {
  return (
    <div className="w-[360px] shrink-0 bg-[#FAFAFA] border border-black p-6 flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <span className="text-[16px] font-bold text-black">
          What the agent decided
        </span>
        <span className="text-[12px] font-normal text-[#666666]">
          Editorial calls for this 15s cut.
        </span>
      </div>

      <div className="h-px bg-black" />

      <div className="flex flex-col gap-[18px]">
        {SECTIONS.map(({ label, key }) => (
          <div key={key} className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
              {label}
            </span>
            <span className="text-[13px] font-normal text-black leading-[1.4]">
              {String(decision[key])}
            </span>
          </div>
        ))}
      </div>

      {decision.beliefs_applied && decision.beliefs_applied.length > 0 && (
        <>
          <div className="h-px bg-black" />
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
              BELIEFS APPLIED
            </span>
            <div className="flex flex-wrap gap-1">
              {decision.beliefs_applied.map((belief) => (
                <span
                  key={belief}
                  className="text-[12px] font-normal text-black border border-[#E5E5E5] px-2 py-0.5"
                >
                  {belief.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        </>
      )}

      {(decision.icp ||
        decision.visual_system ||
        decision.reviews_evaluation ||
        decision.photo_analysis) && (
        <>
          <div className="h-px bg-black" />
          <details>
            <summary className="text-[13px] font-bold text-black cursor-pointer list-none">
              Agent insights →
            </summary>
            <div className="mt-3 flex flex-col gap-3">
              {decision.icp?.best_icp?.persona && (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
                    ICP
                  </span>
                  <span className="text-[12px] font-bold text-black">
                    {decision.icp.best_icp.persona}
                    {typeof decision.icp.best_icp.fit_score === "number" && (
                      <span className="text-[#666] font-normal">
                        {" · fit "}
                        {decision.icp.best_icp.fit_score.toFixed(2)}
                      </span>
                    )}
                  </span>
                  {decision.icp.best_icp.booking_trigger && (
                    <span className="text-[12px] text-[#444] leading-[1.4]">
                      Trigger: {decision.icp.best_icp.booking_trigger}
                    </span>
                  )}
                </div>
              )}
              {decision.visual_system?.inferred_setting && (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
                    VISUAL SYSTEM
                  </span>
                  <span className="text-[12px] text-black">
                    Setting:{" "}
                    <span className="font-bold">
                      {decision.visual_system.inferred_setting}
                    </span>
                  </span>
                  {decision.visual_system.music && (
                    <span className="text-[11px] text-[#444] leading-[1.4]">
                      Music: {decision.visual_system.music}
                    </span>
                  )}
                  {decision.visual_system.transitions && (
                    <span className="text-[11px] text-[#444] leading-[1.4]">
                      Transitions: {decision.visual_system.transitions}
                    </span>
                  )}
                </div>
              )}
              {decision.reviews_evaluation?.best_video_quotes?.[0]?.quote && (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
                    REVIEW PROOF
                  </span>
                  <span className="text-[12px] italic text-black leading-[1.4]">
                    "{decision.reviews_evaluation.best_video_quotes[0].quote}"
                  </span>
                </div>
              )}
              {decision.photo_analysis?.analysis_summary?.one_line_strategy && (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
                    PHOTO STRATEGY
                  </span>
                  <span className="text-[12px] text-black leading-[1.4]">
                    {decision.photo_analysis.analysis_summary.one_line_strategy}
                  </span>
                </div>
              )}
            </div>
          </details>
        </>
      )}

      <details className="mt-auto">
        <summary className="text-[13px] font-bold text-black cursor-pointer list-none">
          View full rationale →
        </summary>
        <pre className="mt-3 text-[11px] text-[#555555] whitespace-pre-wrap break-words leading-[1.5]">
          {decision.hera_prompt}
        </pre>
      </details>
    </div>
  );
}
