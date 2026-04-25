-- Phase 2 outpainter (B-03 native refactor): public Supabase Storage bucket
-- where Gemini-outpainted photos land. Hera fetches them via the public URL
-- pattern: {SUPABASE_URL}/storage/v1/object/public/outpainted-photos/{path}
--
-- Public read (no signed URLs) keeps Hera's reference_image_urls flow simple.
-- Service role uploads go through the service-role key, which bypasses RLS.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'outpainted-photos',
  'outpainted-photos',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
