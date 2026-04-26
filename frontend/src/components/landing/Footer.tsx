import { Link } from "react-router-dom"

export function Footer() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-8 text-label text-muted-foreground sm:flex-row sm:items-center sm:justify-between lg:px-10">
        <span>Made for Hera Berlin · 2026</span>
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <Link
            to="/impressum"
            className="transition-colors hover:text-foreground"
          >
            Impressum
          </Link>
          <Link
            to="/datenschutz"
            className="transition-colors hover:text-foreground"
          >
            Datenschutz
          </Link>
          <span className="hidden sm:inline" aria-hidden>
            ·
          </span>
          <span>Anthropic · Hera API · Supabase</span>
        </nav>
      </div>
    </footer>
  )
}
