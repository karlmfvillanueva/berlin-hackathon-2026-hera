import { useEffect, useState } from "react"

import { getMe, type Me } from "@/api/me"
import { useAuth } from "./useAuth"

/** Wraps /api/me. Re-fetches whenever the Supabase session flips so the
 *  is_team_member flag reflects the currently logged-in account, not a stale
 *  one. Returns null while loading or if the call failed. */
export function useMe(): Me | null {
  const { session } = useAuth()
  const [me, setMe] = useState<Me | null>(null)

  useEffect(() => {
    if (!session) {
      setMe(null)
      return
    }
    let cancelled = false
    getMe()
      .then((m) => {
        if (!cancelled) setMe(m)
      })
      .catch(() => {
        if (!cancelled) setMe(null)
      })
    return () => {
      cancelled = true
    }
  }, [session])

  return me
}
