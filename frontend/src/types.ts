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

/** Full pipeline output: five prerequisite agents + Final Assembly (Strategic Opinion) prompt. */
export type AgentDecision = {
  icp: Record<string, unknown>;
  location_enrichment: Record<string, unknown>;
  reviews_evaluation: Record<string, unknown>;
  visual_system: Record<string, unknown>;
  photo_analysis: Record<string, unknown>;
  duration_seconds: number;
  selected_image_urls: string[];
  hera_prompt: string;
};

export type JobStatus = "in-progress" | "success" | "failed";

export type AppState =
  | { screen: "idle" }
  | { screen: "reviewing"; listing: ScrapedListing; decision: AgentDecision }
  | { screen: "generating"; listing: ScrapedListing; decision: AgentDecision; videoId: string }
  | { screen: "done"; listing: ScrapedListing; decision: AgentDecision; fileUrl: string }
  | { screen: "error"; message: string };
