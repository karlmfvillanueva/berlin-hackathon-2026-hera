// src/components/Header.tsx
import { useEffect, useRef, useState } from "react"
import { Link, useLocation } from "react-router-dom"

import { useAuth } from "@/auth/useAuth"
import { BrandMark } from "@/components/BrandMark"
import { cn } from "@/lib/utils"

interface HeaderProps {
  className?: string
}

const NAV = [
  { label: "Generate", to: "/app" },
  { label: "Dashboard", to: "/dashboard" },
] as const

export function Header({ className }: HeaderProps) {
  const location = useLocation()

  return (
    <header
      className={cn(
        "flex h-16 shrink-0 items-center justify-between border-b border-border bg-background px-8",
        className,
      )}
    >
      <Link to="/" aria-label="Home">
        <BrandMark />
      </Link>

      <nav className="flex gap-6 text-body-sm">
        {NAV.map((item) => {
          const active =
            item.to === "/app"
              ? location.pathname === "/app"
              : location.pathname.startsWith("/dashboard")
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "transition-colors",
                active
                  ? "font-medium text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>

      <ProfileMenu />
    </header>
  )
}

/** Tiny avatar + click-to-open menu with sign-out. Initials are derived from
 *  the email so two users in the same room won't see the same JH. */
function ProfileMenu() {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onDocClick)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onDocClick)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  const initials = (user?.email ?? "?").trim().slice(0, 2).toUpperCase()

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label="Profile menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold text-secondary-foreground transition-opacity hover:opacity-90"
      >
        {initials}
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-50 flex min-w-[200px] flex-col overflow-hidden rounded-md border border-border bg-popover shadow-md">
          {user?.email && (
            <div className="truncate border-b border-border px-3 py-2 text-body-sm text-muted-foreground">
              {user.email}
            </div>
          )}
          <Link
            to="/dashboard"
            onClick={() => setOpen(false)}
            className="px-3 py-2 text-body-sm hover:bg-muted"
          >
            Dashboard
          </Link>
          <button
            type="button"
            onClick={() => {
              setOpen(false)
              void signOut()
            }}
            className="px-3 py-2 text-left text-body-sm hover:bg-muted"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
