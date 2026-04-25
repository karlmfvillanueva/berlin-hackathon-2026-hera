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
  signInWithGoogle: () => Promise<{ error: string | null }>
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
    supabase.auth.getSession().then(({ data }) => {
      if (mounted) {
        setSession(data.session)
        setLoading(false)
      }
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
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

  const signInWithGoogle: AuthContextValue["signInWithGoogle"] = async () => {
    if (!isSupabaseConfigured) return { error: "Auth not configured" }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/dashboard` },
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
