-- Seed agent_beliefs with the 12 starter rules verbatim from
-- architecture/03-agent-pipeline.md "Initial seed beliefs (Phase 2 first deploy)".
-- Confidence values are starting points; Phase 3 evolves them from real data.

insert into agent_beliefs (rule_key, rule_text, confidence) values
  ('hook_with_hero_shot',       'Open with the single most visually striking photo (pool, view, exterior)', 0.85),
  ('duration_15s',              '15 seconds is optimal for Reels and TikTok engagement', 0.80),
  ('cta_at_end',                'End every video with a clear CTA showing the listing link or QR code', 0.90),
  ('location_in_first_frame',   'Show city or neighborhood within the first 2 seconds', 0.70),
  ('social_proof_before_cta',   'Place a rating badge or review quote just before the CTA', 0.75),
  ('warm_palette_for_beach',    'Beach and tropical properties should use warm palettes (amber, coral, gold)', 0.80),
  ('minimal_palette_for_urban', 'Urban properties should use clean minimal palettes (white, gray, single accent)', 0.75),
  ('fast_cuts_for_amenities',   'Amenity showcase sequences should use quick cuts (0.8–1.2s per scene)', 0.70),
  ('slow_reveal_for_hero',      'Hero shots get longer screen time (2–3s) with subtle zoom or pan', 0.80),
  ('music_over_voiceover',      'Background music with text overlays outperforms voiceover for property videos', 0.65),
  ('dedicated_workspace_hook',  'For remote_work angle, open on the desk + window combo, not the bedroom', 0.70),
  ('couples_framing_first',     'For romantic_getaway angle, show the intimate detail (tub, fireplace) before the wide shot', 0.65)
on conflict (rule_key) do nothing;
