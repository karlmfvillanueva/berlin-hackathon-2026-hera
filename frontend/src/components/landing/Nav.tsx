import { Link } from "react-router-dom"
import { useEffect, useState } from "react"

import { useAuth } from "@/auth/useAuth"
import { BrandMark } from "@/components/BrandMark"
import { cn } from "@/lib/utils"

const LINKS = [
  { href: "#opinions", label: "How it thinks" },
  { href: "#watch", label: "Watch" },
  { href: "#pipeline", label: "Pipeline" },
] as const

export function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header
      className={cn(
        "sticky top-0 z-40 transition-colors duration-200",
        scrolled
          ? "border-b border-border bg-background/85 backdrop-blur-md"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-10">
        <Link to="/" className="text-foreground hover:opacity-80">
          <BrandMark />
        </Link>

        <nav className="hidden gap-8 text-body-sm text-muted-foreground md:flex">
          {LINKS.map(({ href, label }) => (
            <a
              key={href}
              href={href}
              className="transition-colors hover:text-foreground"
            >
              {label}
            </a>
          ))}
        </nav>

        <AuthButtons scrolled={scrolled} />
      </div>
    </header>
  )
}

/**
 * Auth-aware nav cluster. Two visual modes so it reads on both the dark hero
 * (transparent header, white text) and the scrolled-light header (background
 * blur). When unauthenticated: Sign in (ghost) + Sign up (primary). When
 * authenticated: Dashboard (primary) + Sign out (ghost).
 */
function AuthButtons({ scrolled }: { scrolled: boolean }) {
  const { user, loading, configured, signOut } = useAuth()

  // Auth not wired up at all → fall back to the original "Try a listing" CTA
  // so the page is still clickable in dev / no-Supabase mode.
  if (!configured) {
    return (
      <a
        href="#cta"
        className="inline-flex items-center rounded-sm bg-primary px-4 py-2 text-body-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
      >
        Try a listing →
      </a>
    )
  }

  if (loading) return <div className="h-9 w-32" aria-hidden />

  const ghostClass = cn(
    "inline-flex items-center rounded-sm border px-3 py-2 text-body-sm font-medium transition-colors",
    scrolled
      ? "border-border text-foreground hover:bg-muted"
      : "border-white/25 text-white hover:bg-white/10",
  )
  const primaryClass =
    "inline-flex items-center rounded-sm bg-primary px-4 py-2 text-body-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Link to="/login" className={ghostClass}>
          Sign in
        </Link>
        <Link to="/signup" className={primaryClass}>
          Sign up
        </Link>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Link to="/dashboard" className={primaryClass}>
        Dashboard
      </Link>
      <button type="button" onClick={() => void signOut()} className={ghostClass}>
        Sign out
      </button>
    </div>
  )
}
