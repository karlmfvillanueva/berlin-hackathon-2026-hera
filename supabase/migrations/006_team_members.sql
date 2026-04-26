-- Demo-mode gating: only emails in team_members may bypass the fixture-only
-- restriction on /api/listing. Anyone else gets demo mode by default — the
-- frontend hides the free-text URL input and surfaces curated demo cards.
create table if not exists team_members (
  email text primary key,
  added_at timestamptz default now()
);

-- Service role reads/writes only — keep the table opaque to authenticated users.
alter table team_members enable row level security;

-- Seed the founding team.
insert into team_members (email)
values ('haertel.joscha@gmail.com')
on conflict (email) do nothing;
