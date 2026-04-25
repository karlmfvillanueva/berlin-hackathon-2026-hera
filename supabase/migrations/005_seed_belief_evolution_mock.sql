-- Demo seed for the belief-evolution dashboard.
-- 12 mock videos (user_id = NULL) spread across personas + settings, each with
-- 8–14 metrics snapshots over a simulated 30-day window. Numbers are realistic
-- but not real — the dashboard renders these alongside real user videos to
-- show the "agent learns" story for the hackathon demo. is_demo_seed=true on
-- every snapshot row so RLS lets all users see them.
--
-- Replace `null` user_id seeds with real user inserts as soon as production
-- traffic exists; the same simulator (belief_evolution.py) will then produce
-- non-mock confidence updates from genuine retention data.

-- Idempotent insert keyed on listing_url so re-running the migration is safe.

-- Persona: Couples weekend break ----------------------------------------------
insert into videos (
  id, user_id, listing_url, hera_video_id, listing_data, agent_decision,
  hera_payload, youtube_video_id, published_at, visibility
)
select gen_random_uuid(), null, v.url, 'demo-' || encode(gen_random_bytes(6), 'hex'),
       jsonb_build_object('url', v.url, 'title', v.title, 'description', '', 'amenities',
                          '[]'::jsonb, 'photos', '[]'::jsonb, 'location', v.location,
                          'price_display', v.price, 'bedrooms_sleeps', '1 BR · sleeps 2'),
       jsonb_build_object('vibes', v.vibes, 'hook', v.hook, 'pacing', v.pacing,
                          'angle', v.angle, 'background', v.background,
                          'selected_image_urls', '[]'::jsonb, 'hera_prompt', v.hera_prompt,
                          'duration_seconds', v.duration_seconds,
                          'beliefs_applied', v.beliefs_applied,
                          'icp', jsonb_build_object('best_icp',
                              jsonb_build_object('persona', v.persona, 'fit_score', 0.88)),
                          'visual_system', jsonb_build_object('inferred_setting', v.setting,
                              'pacing', v.pacing)),
       jsonb_build_object('demo', true),
       'YT_' || substr(md5(v.url), 1, 11), now() - (v.days_old || ' days')::interval, 'unlisted'
from (values
  ('demo://couples/coastal/01', 'Cliffside cottage with sea view', 'Lisbon, PT',
   '€220/night', 'romantic · sunset · slow', 'Open on tub steam at golden hour',
   'slow', 'Couples weekend break', 'Sunset solitude', 'Tub-fireplace vignette',
   'sample prompt — couples coastal', 25, 'coastal', 'Couples weekend break',
   '["couples_framing_first","slow_reveal_for_hero","cta_at_end","warm_palette_for_beach"]'::jsonb, 22),
  ('demo://couples/coastal/02', 'Tide-pool studio with private deck', 'Sintra, PT',
   '€180/night', 'romantic · breeze · soft', 'Champagne flutes catch the sea spray',
   'medium', 'Couples weekend break', 'Two-only horizon', 'Hammock-bath duo',
   'sample prompt — couples coastal 2', 20, 'coastal', 'Couples weekend break',
   '["couples_framing_first","slow_reveal_for_hero","cta_at_end"]'::jsonb, 18),
  ('demo://couples/city/03', 'Loft with claw-foot tub overlooking park', 'Paris, FR',
   '€310/night', 'intimate · industrial · warm', 'Candlelight on copper tub',
   'slow', 'Couples weekend break', 'Two pink wines', 'Tub against city window',
   'sample prompt — couples city', 25, 'city', 'Couples weekend break',
   '["couples_framing_first","minimal_palette_for_urban","slow_reveal_for_hero"]'::jsonb, 14)
) as v(url, title, location, price, vibes, hook, pacing, persona, angle, background,
       hera_prompt, duration_seconds, setting, persona_again, beliefs_applied, days_old)
where not exists (select 1 from videos where listing_url = v.url);

-- Persona: Digital nomad ------------------------------------------------------
insert into videos (
  id, user_id, listing_url, hera_video_id, listing_data, agent_decision,
  hera_payload, youtube_video_id, published_at, visibility
)
select gen_random_uuid(), null, v.url, 'demo-' || encode(gen_random_bytes(6), 'hex'),
       jsonb_build_object('url', v.url, 'title', v.title, 'description', '', 'amenities',
                          '[]'::jsonb, 'photos', '[]'::jsonb, 'location', v.location,
                          'price_display', v.price, 'bedrooms_sleeps', 'Studio · sleeps 2'),
       jsonb_build_object('vibes', v.vibes, 'hook', v.hook, 'pacing', v.pacing,
                          'angle', v.angle, 'background', v.background,
                          'selected_image_urls', '[]'::jsonb, 'hera_prompt', v.hera_prompt,
                          'duration_seconds', v.duration_seconds,
                          'beliefs_applied', v.beliefs_applied,
                          'icp', jsonb_build_object('best_icp',
                              jsonb_build_object('persona', 'Digital nomad', 'fit_score', 0.91)),
                          'visual_system', jsonb_build_object('inferred_setting', v.setting,
                              'pacing', v.pacing)),
       jsonb_build_object('demo', true),
       'YT_' || substr(md5(v.url), 1, 11), now() - (v.days_old || ' days')::interval, 'unlisted'
from (values
  ('demo://nomad/city/01', 'Ergonomic loft with fiber + AC', 'Lisbon, PT',
   '€95/night', 'minimal · focus · airy', 'Desk + window combo opens the reel',
   'medium', 'Digital nomad', 'Where you actually ship', 'Desk-first hero',
   'sample prompt — nomad city', 22, 'city',
   '["dedicated_workspace_hook","minimal_palette_for_urban","fast_cuts_for_amenities","cta_at_end"]'::jsonb,
   28),
  ('demo://nomad/city/02', 'Coworking-floor flat near metro', 'Berlin, DE',
   '€110/night', 'industrial · clean · efficient', 'Stair flythrough lands on standing desk',
   'fast', 'Digital nomad', 'Predictable workday', 'Workspace + kitchen tour',
   'sample prompt — nomad city 2', 20, 'city',
   '["dedicated_workspace_hook","fast_cuts_for_amenities"]'::jsonb, 24),
  ('demo://nomad/coastal/03', 'Ocean-side studio with wired desk', 'Tarifa, ES',
   '€85/night', 'coastal · breezy · focused', 'Window-lit desk with sea audio',
   'medium', 'Digital nomad', 'Work between the waves', 'Desk-window-deck triptych',
   'sample prompt — nomad coastal', 25, 'coastal',
   '["dedicated_workspace_hook","slow_reveal_for_hero","warm_palette_for_beach"]'::jsonb, 16)
) as v(url, title, location, price, vibes, hook, pacing, persona, angle, background,
       hera_prompt, duration_seconds, setting, beliefs_applied, days_old)
where not exists (select 1 from videos where listing_url = v.url);

-- Persona: Friend group / family / first-time tourist (mixed) -----------------
insert into videos (
  id, user_id, listing_url, hera_video_id, listing_data, agent_decision,
  hera_payload, youtube_video_id, published_at, visibility
)
select gen_random_uuid(), null, v.url, 'demo-' || encode(gen_random_bytes(6), 'hex'),
       jsonb_build_object('url', v.url, 'title', v.title, 'description', '',
                          'amenities', '[]'::jsonb, 'photos', '[]'::jsonb,
                          'location', v.location, 'price_display', v.price,
                          'bedrooms_sleeps', '3 BR · sleeps ' || v.sleeps),
       jsonb_build_object('vibes', v.vibes, 'hook', v.hook, 'pacing', v.pacing,
                          'angle', v.angle, 'background', v.background,
                          'selected_image_urls', '[]'::jsonb, 'hera_prompt', v.hera_prompt,
                          'duration_seconds', v.duration_seconds,
                          'beliefs_applied', v.beliefs_applied,
                          'icp', jsonb_build_object('best_icp',
                              jsonb_build_object('persona', v.persona, 'fit_score', 0.82)),
                          'visual_system', jsonb_build_object('inferred_setting', v.setting,
                              'pacing', v.pacing)),
       jsonb_build_object('demo', true),
       'YT_' || substr(md5(v.url), 1, 11), now() - (v.days_old || ' days')::interval, 'unlisted'
from (values
  ('demo://friends/mountain/01', 'Chalet with hot tub for six', 'Chamonix, FR',
   '€520/night', 'alpine · cozy · group', 'Door swings open, six glasses chime',
   'fast', 'Friend group', 'Snow days, shared dinners', 'Hot-tub plus kitchen montage',
   'sample prompt — friends mountain', 25, 'mountain', 6,
   '["fast_cuts_for_amenities","hook_with_hero_shot"]'::jsonb, 12),
  ('demo://friends/countryside/02', 'Vineyard farmhouse for groups', 'Tuscany, IT',
   '€480/night', 'rustic · warm · communal', 'Long table, candle, eight plates',
   'medium', 'Friend group', 'Long-table dinners', 'Vineyard + table cinematic',
   'sample prompt — friends countryside', 20, 'countryside', 8,
   '["hook_with_hero_shot","cta_at_end"]'::jsonb, 26),
  ('demo://family/coastal/03', 'Beachfront family villa', 'Algarve, PT',
   '€340/night', 'coastal · spacious · safe', 'Kids running into the dunes',
   'medium', 'Family', 'Multi-gen beach week', 'Pool + outdoor dining sequence',
   'sample prompt — family coastal', 22, 'coastal', 6,
   '["warm_palette_for_beach","social_proof_before_cta","cta_at_end"]'::jsonb, 11),
  ('demo://family/countryside/04', 'Farmhouse with chickens + trampoline', 'Provence, FR',
   '€290/night', 'rural · warm · kid-safe', 'Chickens in soft focus, kid laughter',
   'medium', 'Family', 'Kids outside all day', 'Garden + breakfast spread',
   'sample prompt — family countryside', 25, 'countryside', 5,
   '["hook_with_hero_shot","slow_reveal_for_hero"]'::jsonb, 30),
  ('demo://tourist/city/05', 'Walk-everywhere old-town flat', 'Porto, PT',
   '€140/night', 'historic · walkable · light', 'Open shutters reveal blue tiles',
   'medium', 'First-time tourist', 'Walking-distance everything', 'Tiles + bridge view',
   'sample prompt — tourist city', 20, 'city', 4,
   '["minimal_palette_for_urban","location_in_first_frame","cta_at_end"]'::jsonb, 9),
  ('demo://tourist/city/06', 'Skyline studio near landmarks', 'Berlin, DE',
   '€120/night', 'urban · clean · accessible', 'Train arrives 90 seconds in',
   'fast', 'First-time tourist', 'See it all in three days', 'Transit + skyline cuts',
   'sample prompt — tourist city 2', 18, 'city', 3,
   '["minimal_palette_for_urban","fast_cuts_for_amenities","location_in_first_frame"]'::jsonb, 6)
) as v(url, title, location, price, vibes, hook, pacing, persona, angle, background,
       hera_prompt, duration_seconds, setting, sleeps, beliefs_applied, days_old)
where not exists (select 1 from videos where listing_url = v.url);

-- Generate 8–14 metrics snapshots per demo video, growing organically over time.
-- Pure-SQL deterministic generator using generate_series + pseudo-random noise
-- seeded by md5(listing_url). is_demo_seed=true so RLS lets all clients read.
do $$
declare
  v record;
  i int;
  n_snap int;
  base_views int;
  base_dur numeric;
  base_ret numeric;
  views int;
  dur numeric;
  ret numeric;
  obs timestamptz;
  beliefs jsonb;
  setting text;
begin
  for v in select id, listing_url, agent_decision from videos where user_id is null loop
    -- Skip if we already seeded snapshots for this video (idempotent).
    if exists (select 1 from video_metrics_snapshot where video_id = v.id and is_demo_seed) then
      continue;
    end if;

    setting := coalesce(v.agent_decision->'visual_system'->>'inferred_setting', 'city');
    beliefs := v.agent_decision->'beliefs_applied';

    -- Base performance varies by setting/beliefs to make the simulator's
    -- belief-confidence updates show meaningful spread later.
    base_views := 800 + (abs(hashtext(v.listing_url)) % 8000);
    base_dur := 7.0 + ((abs(hashtext(v.listing_url)) % 80) / 10.0);
    base_ret := 0.30 + ((abs(hashtext(v.listing_url)) % 40) / 100.0);

    -- Coastal + warm palette belief gets a retention boost.
    if setting = 'coastal' and beliefs ? 'warm_palette_for_beach' then
      base_ret := base_ret + 0.08;
      base_dur := base_dur + 1.5;
    end if;
    -- Slow-reveal belief on hero shots boosts retention.
    if beliefs ? 'slow_reveal_for_hero' then
      base_ret := base_ret + 0.05;
    end if;
    -- Workspace hook on Digital Nomad listings → above-baseline views.
    if beliefs ? 'dedicated_workspace_hook' then
      base_views := base_views + 2500;
    end if;

    n_snap := 8 + (abs(hashtext(v.listing_url || 'n')) % 7);
    for i in 1..n_snap loop
      obs := now() - ((30 - i * (30.0 / n_snap)) || ' days')::interval;
      views := round(base_views * (i::numeric / n_snap)
                     + (abs(hashtext(v.listing_url || i::text)) % 200));
      dur := base_dur + ((abs(hashtext(v.listing_url || i::text || 'd')) % 30) / 100.0);
      ret := least(0.95, base_ret + ((abs(hashtext(v.listing_url || i::text || 'r')) % 15) / 100.0));
      insert into video_metrics_snapshot (
        video_id, observed_at, view_count, like_count, comment_count,
        avg_view_duration_s, retention_50pct, is_demo_seed
      ) values (
        v.id, obs, views, round(views * 0.04), round(views * 0.005),
        round(dur::numeric, 2), round(ret::numeric, 3), true
      );
    end loop;
  end loop;
end $$;
