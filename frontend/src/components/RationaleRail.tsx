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
