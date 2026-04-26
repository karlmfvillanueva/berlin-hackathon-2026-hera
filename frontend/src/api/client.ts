import type {
  ScrapedListing,
  AgentDecision,
  JobStatus,
  Phase1Decision,
  Overrides,
} from "../types";
import { supabase } from "../lib/supabase";

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { authorization: `Bearer ${token}` } : {};
}

export async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = {
    ...(init.headers as Record<string, string> | undefined),
    ...(await authHeaders()),
  };
  return fetch(input, { ...init, headers });
}

export type ListingResponse = {
  listing: ScrapedListing;
  phase1: Phase1Decision;
};

// POST /api/generate is now async-kickoff. The body returns immediately
// with the internal job id; the heavy phase 2 + Hera POST run server-side.
export type GenerateResponse = {
  internal_video_id: string;
  state: JobState;
};

export type JobState = "planning" | "rendering" | "success" | "failed";

// Live status of one job. Decision becomes available after phase 2 finishes;
// file_url only at the very end. Server-side proxy through to Hera handles
// the render-status read so the frontend hits one endpoint.
export type JobStatusResponse = {
  internal_video_id: string;
  state: JobState;
  stage: string;
  hera_video_id: string | null;
  decision: AgentDecision | null;
  file_url: string | null;
  error: string | null;
};

export type PollResponse = {
  video_id: string;
  status: JobStatus;
  outputs: { file_url: string | null; error: string | null }[];
};

export async function postListing(
  listing_url: string,
  outpaint_enabled: boolean,
): Promise<ListingResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/listing`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ listing_url, outpaint_enabled }),
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
  phase1: Phase1Decision,
  overrides: Overrides,
): Promise<GenerateResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/generate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ listing_url, listing, phase1, overrides }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Backend returned ${res.status}`);
  }
  return res.json() as Promise<GenerateResponse>;
}

export async function pollStatus(video_id: string): Promise<PollResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/videos/${video_id}`);
  if (!res.ok) {
    throw new Error(`Poll returned ${res.status}`);
  }
  return res.json() as Promise<PollResponse>;
}

// Poll the unified async-job endpoint. Server returns the live state of phase 2
// and the Hera render through one URL — frontend doesn't have to switch
// endpoints when the job moves from 'planning' → 'rendering' → 'success'.
export async function pollJob(internalVideoId: string): Promise<JobStatusResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/jobs/${internalVideoId}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Job poll returned ${res.status}`);
  }
  return res.json() as Promise<JobStatusResponse>;
}

// Same async-kickoff shape as postGenerate — backend returns the new job id
// immediately, frontend polls /api/jobs/{internal_video_id} for the new
// render. No phase 2; just a fresh Hera POST under the hood.
export async function postRegenerate(
  listing_url: string,
  listing: ScrapedListing,
  decision: AgentDecision,
): Promise<GenerateResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/regenerate`, {
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
