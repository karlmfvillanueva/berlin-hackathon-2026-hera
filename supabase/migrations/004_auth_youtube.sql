-- Phase 3 schema: end-user auth, YouTube tokens, time-series metrics.
-- Adds: profiles (mirror of auth.users), videos.user_id + RLS, user_youtube_tokens,
-- video_metrics_snapshot. Seed beliefs + agent_beliefs from 001/002 stay untouched.

-- ---------- profiles ----------
-- One row per auth.users row, populated by trigger. Used for display data
-- (display_name, avatar_url) without exposing auth.users to the API.
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  created_at timestamptz default now()
);

create or replace function handle_new_user() returns trigger as $$
begin
  insert into profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'name', new.email));
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();

alter table profiles enable row level security;

drop policy if exists profiles_self_read on profiles;
create policy profiles_self_read on profiles
  for select using (id = auth.uid());

drop policy if exists profiles_self_update on profiles;
create policy profiles_self_update on profiles
  for update using (id = auth.uid());

-- ---------- videos: ownership + youtube fields ----------
alter table videos
  add column if not exists user_id uuid references auth.users(id) on delete set null,
  add column if not exists youtube_video_id text,
  add column if not exists youtube_channel_id text,
  add column if not exists published_at timestamptz,
  add column if not exists visibility text default 'unlisted';

create index if not exists videos_user_id_idx on videos(user_id);

-- Service-role inserts (backend) bypass RLS. End-user reads use this policy.
drop policy if exists user_owns_video on videos;
create policy user_owns_video on videos
  for all using (user_id = auth.uid());

-- ---------- user_youtube_tokens ----------
-- One row per user. access_token rotates; refresh_token is long-lived.
-- Backend never returns these to the frontend.
create table if not exists user_youtube_tokens (
  user_id uuid primary key references auth.users(id) on delete cascade,
  access_token text not null,
  refresh_token text not null,
  expires_at timestamptz not null,
  scopes text[],
  channel_id text,
  channel_title text,
  connected_at timestamptz default now()
);

alter table user_youtube_tokens enable row level security;

-- No client-side policy needed — only the service role reads/writes this.
-- Explicit deny: nothing here for authenticated users to do directly.

-- ---------- video_metrics_snapshot ----------
-- Time-series — never overwrite. Plot the curve.
create table if not exists video_metrics_snapshot (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  observed_at timestamptz not null default now(),
  view_count int,
  like_count int,
  comment_count int,
  avg_view_duration_s numeric,
  retention_50pct numeric,
  is_demo_seed boolean default false
);

create index if not exists video_metrics_video_observed_idx
  on video_metrics_snapshot (video_id, observed_at desc);

alter table video_metrics_snapshot enable row level security;

drop policy if exists user_owns_metrics on video_metrics_snapshot;
create policy user_owns_metrics on video_metrics_snapshot
  for select using (
    exists (select 1 from videos v where v.id = video_id and v.user_id = auth.uid())
    or is_demo_seed = true
  );
