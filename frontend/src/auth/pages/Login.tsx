import { useState, type FormEvent } from "react"
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../useAuth"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"

type LocationState = { from?: { pathname?: string } }

export function Login() {
  const { user, signIn, signInWithGoogle, configured, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as LocationState | null)?.from?.pathname ?? "/"

  if (loading) return null
  if (user) return <Navigate to={from} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const { error } = await signIn(email, password)
    setSubmitting(false)
    if (error) setError(error)
    else navigate(from, { replace: true })
  }

  async function onGoogle() {
    setError(null)
    const { error } = await signInWithGoogle()
    if (error) setError(error)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-display mb-2">Sign in</h1>
        <p className="text-body-sm text-muted-foreground mb-6">
          Welcome back. Continue where you left off.
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
            placeholder="Password"
            autoComplete="current-password"
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
            {submitting ? "Signing in…" : "Sign in"}
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
          New here?{" "}
          <Link to="/signup" className="font-medium text-foreground underline">
            Create an account
          </Link>
        </p>
      </Card>
    </div>
  )
}
