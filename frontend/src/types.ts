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
};

export type JobStatus = "in-progress" | "success" | "failed";

export type AppState =
  | { screen: "idle" }
  | { screen: "reviewing"; listing: ScrapedListing; decision: AgentDecision }
  | { screen: "generating"; listing: ScrapedListing; decision: AgentDecision; videoId: string; outpaint_enabled?: boolean }
  | { screen: "done"; listing: ScrapedListing; decision: AgentDecision; fileUrl: string; videoId: string }
  | { screen: "error"; message: string };
