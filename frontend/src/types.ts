export type ScrapedListing = {
  url: string;
  title: string;
  description: string;
  amenities: string[];
  photos: { url: string; label: string | null }[];
  location: string;
  price_display: string;
  bedrooms_sleeps: string;
};

// Phase 3 multi-agent pipeline structured outputs. Optional — present only
// when the multi-agent orchestrator runs. Full dicts kept loose to avoid
// brittle coupling; RationaleRail reads a small typed surface defined inline.
export type IcpClassification = {
  best_icp?: {
    persona?: string;
    fit_score?: number;
    why_it_wins?: string;
    booking_trigger?: string;
    emotional_driver?: string;
  };
  conversion_summary?: {
    what_guest_is_really_booking?: string;
  };
};

export type VisualSystem = {
  inferred_setting?: string;
  primary_background?: string;
  cta_card_only?: string;
  primary_type?: string;
  accent?: string;
  pacing?: string;
  transitions?: string;
  music?: string;
};

export type ReviewsEvaluation = {
  review_summary?: {
    overall_sentiment?: string;
    most_repeated_positive_theme?: string;
  };
  best_video_quotes?: { quote?: string; theme?: string }[];
};

export type PhotoAnalysis = {
  analysis_summary?: {
    one_line_strategy?: string;
    icp_visual_hypothesis?: string;
  };
};

export type AgentDecision = {
  vibes: string;
  hook: string;
  pacing: string;
  angle: string;
  background: string;
  selected_image_urls: string[];
  hera_prompt: string;
  // Optional: true if backend ran the outpainter on selected_image_urls.
  outpaint_enabled?: boolean;
  // Optional: rule_keys of agent beliefs that influenced this decision.
  beliefs_applied?: string[];
  // Phase 3 optional structured outputs (multi-agent pipeline).
  icp?: IcpClassification;
  location_enrichment?: Record<string, unknown>;
  reviews_evaluation?: ReviewsEvaluation;
  visual_system?: VisualSystem;
  photo_analysis?: PhotoAnalysis;
  duration_seconds?: number;
  // Editorial Judge metadata — set when Final Assembly's multi-sample path
  // ran 3 candidates and a Judge agent picked the strongest brief.
  judge_score?: number | null;
  judge_rationale?: string | null;
  judge_scores_per_brief?: JudgeBriefScore[] | null;
};

export type JudgeBriefScore = {
  index: number;
  aggregate?: number;
  weakness?: string;
};

export type JobStatus = "in-progress" | "success" | "failed";

export type AppState =
  | { screen: "idle" }
  | { screen: "reviewing"; listing: ScrapedListing; decision: AgentDecision }
  | {
      screen: "generating";
      listing: ScrapedListing;
      decision: AgentDecision;
      videoId: string;
      outpaint_enabled?: boolean;
    }
  | {
      screen: "done";
      listing: ScrapedListing;
      decision: AgentDecision;
      fileUrl: string;
      videoId: string;
    }
  | { screen: "error"; message: string };
