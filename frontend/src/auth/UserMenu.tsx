import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useAuth } from "./useAuth"

export function UserMenu() {
  const { user, signOut, loading, configured } = useAuth()
  if (loading) return null
  if (!configured) return null
  if (!user) {
    return (
      <Link to="/login">
        <Button size="sm" variant="outline">
          Sign in
        </Button>
      </Link>
    )
  }
  return (
    <div className="flex items-center gap-3">
      <span className="text-body-sm text-muted-foreground hidden sm:inline">
        {user.email}
      </span>
      <Button size="sm" variant="ghost" onClick={() => void signOut()}>
        Sign out
      </Button>
    </div>
  )
}
