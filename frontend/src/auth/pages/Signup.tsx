import { useState, type FormEvent } from "react"
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../useAuth"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"

type LocationState = { from?: { pathname?: string; search?: string } }

export function Signup() {
  const { user, signUp, signInWithGoogle, configured, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Same preservation as Login — survive the auth detour with query string intact.
  const fromLoc = (location.state as LocationState | null)?.from
  const from = fromLoc?.pathname
    ? `${fromLoc.pathname}${fromLoc.search ?? ""}`
    : "/"

  if (loading) return null
  if (user) return <Navigate to={from} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (password.length < 6) {
      setError("Password must be at least 6 characters")
      return
    }
    setError(null)
    setSubmitting(true)
    const { error } = await signUp(email, password)
    setSubmitting(false)
    if (error) setError(error)
    else navigate(from, { replace: true })
  }

  async function onGoogle() {
    setError(null)
    const { error } = await signInWithGoogle(from)
    if (error) setError(error)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-display mb-2">Create your account</h1>
        <p className="text-body-sm text-muted-foreground mb-6">
          One agent. Five photos. Done in under a minute.
        </p>

        {!configured && (
          <p className="text-body-sm mb-4 rounded-md border border-yellow-500/40 bg-yellow-500/10 p-3 text-yellow-700">
            Auth is not configured. Set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY.
          </p>
        )}

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <Input
            type="email"
            placeholder="Email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            type="password"
            placeholder="Password (min. 6 characters)"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && (
            <p className="text-body-sm rounded-md border border-destructive/40 bg-destructive/10 p-3 text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" disabled={submitting || !configured}>
            {submitting ? "Creating account…" : "Sign up"}
          </Button>
        </form>

        <Separator className="my-6" />

        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={onGoogle}
          disabled={!configured}
        >
          Continue with Google
        </Button>

        <p className="text-body-sm text-muted-foreground mt-6 text-center">
          Already have an account?{" "}
          <Link
            to="/login"
            state={{ from: fromLoc }}
            className="font-medium text-foreground underline"
          >
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  )
}
