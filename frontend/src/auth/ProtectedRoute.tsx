import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "./useAuth"
import type { ReactNode } from "react"

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading, configured } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    )
  }
  // When auth isn't configured at all (no VITE_SUPABASE_URL), let the route through
  // so dev with REQUIRE_AUTH=false on the backend keeps working.
  if (!configured) return <>{children}</>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}
