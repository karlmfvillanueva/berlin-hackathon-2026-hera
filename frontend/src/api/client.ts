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

export type GenerateResponse = {
  video_id: string;
  decision: AgentDecision;
  internal_video_id: string | null;
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

export type RegenerateResponse = {
  video_id: string;
  decision: AgentDecision;
};

export async function postRegenerate(
  listing_url: string,
  listing: ScrapedListing,
  decision: AgentDecision,
): Promise<RegenerateResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/regenerate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ listing_url, listing, decision }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Backend returned ${res.status}`);
  }
  return res.json() as Promise<RegenerateResponse>;
}
