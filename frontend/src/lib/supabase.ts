import { createClient } from "@supabase/supabase-js"

const url = import.meta.env.VITE_SUPABASE_URL ?? ""
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ""

if (!url || !anonKey) {
  // Don't throw — the app must still boot in environments where Supabase
  // hasn't been configured yet (e.g. backend running with REQUIRE_AUTH=false
  // and a mock-friendly frontend dev session). Auth flows will surface this
  // later via clear errors.
  // eslint-disable-next-line no-console
  console.warn(
    "[supabase] VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY not set — auth UI will be disabled",
  )
}

export const supabase = createClient(url || "https://placeholder.supabase.co", anonKey || "placeholder", {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})

export const isSupabaseConfigured = Boolean(url) && Boolean(anonKey)
