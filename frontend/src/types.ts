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
};

export type JobStatus = "in-progress" | "success" | "failed";

export type AppState =
  | { screen: "idle" }
  | { screen: "reviewing"; listing: ScrapedListing; decision: AgentDecision }
  | { screen: "generating"; listing: ScrapedListing; decision: AgentDecision; videoId: string }
  | { screen: "done"; listing: ScrapedListing; decision: AgentDecision; fileUrl: string }
  | { screen: "error"; message: string };
