import { createContext, useEffect, useState, type ReactNode } from "react"
import type { Session, User } from "@supabase/supabase-js"
import { supabase, isSupabaseConfigured } from "@/lib/supabase"

export type AuthContextValue = {
  user: User | null
  session: Session | null
  loading: boolean
  configured: boolean
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signUp: (email: string, password: string) => Promise<{ error: string | null }>
  /** `redirectPath` is appended to window.location.origin to build the OAuth
   *  redirectTo. Defaults to "/dashboard". Pass the deep link target when the
   *  user came from a protected route so the path survives the round-trip. */
  signInWithGoogle: (redirectPath?: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false)
      return
    }
    let mounted = true
    // We rely solely on onAuthStateChange — supabase-js v2 fires INITIAL_SESSION
    // AFTER the PKCE code in the URL has been exchanged, which the previous
    // getSession() race lost: getSession resolved with null before the exchange
    // finished, ProtectedRoute redirected to /login, and the now-stale ?code=
    // in the URL got re-tried (and failed) on the way back. One subscription
    // handles initial recover-from-storage, URL-detect, and live updates.
    const { data: sub } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!mounted) return
      setSession(nextSession)
      setLoading(false)
    })
    return () => {
      mounted = false
      sub.subscription.unsubscribe()
    }
  }, [])

  const signIn: AuthContextValue["signIn"] = async (email, password) => {
    if (!isSupabaseConfigured) return { error: "Auth not configured" }
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error: error?.message ?? null }
  }

  const signUp: AuthContextValue["signUp"] = async (email, password) => {
    if (!isSupabaseConfigured) return { error: "Auth not configured" }
    const { error } = await supabase.auth.signUp({ email, password })
    return { error: error?.message ?? null }
  }

  const signInWithGoogle: AuthContextValue["signInWithGoogle"] = async (
    redirectPath = "/dashboard",
  ) => {
    if (!isSupabaseConfigured) return { error: "Auth not configured" }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}${redirectPath}` },
    })
    return { error: error?.message ?? null }
  }

  const signOut: AuthContextValue["signOut"] = async () => {
    if (!isSupabaseConfigured) return
    await supabase.auth.signOut()
  }

  const value: AuthContextValue = {
    user: session?.user ?? null,
    session,
    loading,
    configured: isSupabaseConfigured,
    signIn,
    signUp,
    signInWithGoogle,
    signOut,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
