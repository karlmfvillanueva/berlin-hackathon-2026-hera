-- Phase 2 schema: videos + agent_beliefs.
-- Source: architecture/02-architecture.md Layer 7.
-- RLS is enabled on every table from day 0. No policies in Phase 2 — the backend
-- writes/reads with the service role key, which bypasses RLS. Policies are added
-- in Phase 3 once end-user auth lands.

create table if not exists videos (
  id uuid primary key default gen_random_uuid(),
  listing_url text not null,
  hera_video_id text not null,
  hera_project_url text,
  video_url text,                       -- final MP4, refreshed on demand (S3 pre-signed, 24h)
  outpaint_enabled boolean not null default false,
  listing_data jsonb not null,          -- full ScrapedListing
  agent_decision jsonb not null,        -- full AgentDecision
  hera_payload jsonb not null,          -- exact body sent to POST /videos
  created_at timestamptz default now()
);

create table if not exists agent_beliefs (
  id uuid primary key default gen_random_uuid(),
  rule_key text unique not null,        -- e.g. "pool_hook_priority"
  rule_text text not null,              -- human-readable rule the agent applies
  confidence float default 0.5,
  evidence_count int default 0,
  last_updated timestamptz default now()
);

alter table videos enable row level security;
alter table agent_beliefs enable row level security;
