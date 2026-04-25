import type { ScrapedListing, AgentDecision, JobStatus } from "../types";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

export type ListingResponse = {
  listing: ScrapedListing;
  decision: AgentDecision;
};

export type GenerateResponse = {
  video_id: string;
  decision: AgentDecision;
};

export type PollResponse = {
  video_id: string;
  status: JobStatus;
  outputs: { file_url: string | null; error: string | null }[];
};

export async function postListing(listing_url: string): Promise<ListingResponse> {
  const res = await fetch(`${BACKEND_URL}/api/listing`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ listing_url }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Backend returned ${res.status}`);
  }
  return res.json() as Promise<ListingResponse>;
}

export async function postGenerate(
  listing_url: string,
  listing: ScrapedListing,
  decision: AgentDecision,
): Promise<GenerateResponse> {
  const res = await fetch(`${BACKEND_URL}/api/generate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ listing_url, listing, decision }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Backend returned ${res.status}`);
  }
  return res.json() as Promise<GenerateResponse>;
}

export async function pollStatus(video_id: string): Promise<PollResponse> {
  const res = await fetch(`${BACKEND_URL}/api/videos/${video_id}`);
  if (!res.ok) {
    throw new Error(`Poll returned ${res.status}`);
  }
  return res.json() as Promise<PollResponse>;
}
