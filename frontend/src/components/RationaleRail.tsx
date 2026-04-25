import type { AgentDecision } from "../types";

interface RationaleRailProps {
  decision: AgentDecision;
}

function strVal(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "";
}

export function RationaleRail({ decision }: RationaleRailProps) {
  const icp = decision.icp as {
    best_icp?: Record<string, unknown>;
    conversion_summary?: Record<string, unknown>;
  };
  const best = icp?.best_icp ?? {};
  const conv = icp?.conversion_summary ?? {};
  const loc = decision.location_enrichment as {
    location_summary?: Record<string, unknown>;
  };
  const locSum = loc?.location_summary ?? {};

  const photo = decision.photo_analysis as {
    analysis_summary?: Record<string, unknown>;
    selected_indices_hero_first?: unknown[];
    creative_director_notes_for_assembly?: unknown;
  };
  const photoSum = photo?.analysis_summary ?? {};

  const sections: { label: string; value: string }[] = [
    { label: "DURATION", value: `${decision.duration_seconds}s` },
    { label: "BEST ICP — PERSONA", value: strVal(best.persona) },
    { label: "BEST ICP — FIT SCORE", value: strVal(best.fit_score) },
    { label: "WHY IT WINS", value: strVal(best.why_it_wins) },
    { label: "BOOKING TRIGGER", value: strVal(best.booking_trigger) },
    { label: "EMOTIONAL DRIVER", value: strVal(best.emotional_driver) },
    {
      label: "WHAT THEY ARE REALLY BOOKING",
      value: strVal(conv.what_guest_is_really_booking),
    },
    {
      label: "WHAT THEY DO NOT CARE ABOUT",
      value: strVal(conv.what_they_do_not_care_about),
    },
    {
      label: "WHY THIS LISTING CONVERTS",
      value: strVal(conv.why_this_listing_converts_for_this_icp),
    },
    { label: "LOCATION — HEADLINE", value: strVal(locSum.headline) },
    { label: "LOCATION — TRIP PAYOFF", value: strVal(locSum.guest_trip_payoff) },
    {
      label: "LOCATION — VS GENERIC STAYS",
      value: strVal(locSum.differentiator_vs_generic_stays),
    },
    {
      label: "PHOTO ANALYSER — STRATEGY",
      value: strVal(photoSum.one_line_strategy),
    },
    {
      label: "PHOTO ANALYSER — ICP READ",
      value: strVal(photoSum.icp_visual_hypothesis),
    },
    {
      label: "PHOTO ANALYSER — RISK",
      value: strVal(photoSum.biggest_visual_risk),
    },
    {
      label: "PHOTO ANALYSER — SHORTLIST (1-BASED INDICES)",
      value: Array.isArray(photo?.selected_indices_hero_first)
        ? photo.selected_indices_hero_first.join(", ")
        : "",
    },
    {
      label: "PHOTO ANALYSER — NOTES FOR ASSEMBLY",
      value: strVal(photo?.creative_director_notes_for_assembly),
    },
  ];

  return (
    <div className="w-[360px] shrink-0 bg-[#FAFAFA] border border-black p-6 flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <span className="text-[16px] font-bold text-black">What the agents decided</span>
        <span className="text-[12px] font-normal text-[#666666]">
          ICP, location, reviews, visual system, and photo analysis for this cut.
        </span>
      </div>

      <div className="h-px bg-black" />

      <div className="flex flex-col gap-[18px]">
        {sections.map(({ label, value }) => (
          <div key={label} className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-[1.5px]">
              {label}
            </span>
            <span className="text-[13px] font-normal text-black leading-[1.4]">{value}</span>
          </div>
        ))}
      </div>

      <details className="mt-auto">
        <summary className="text-[13px] font-bold text-black cursor-pointer list-none">
          View Hera brief (assembled) →
        </summary>
        <pre className="mt-3 text-[11px] text-[#555555] whitespace-pre-wrap break-words leading-[1.5]">
          {decision.hera_prompt}
        </pre>
      </details>
    </div>
  );
}
