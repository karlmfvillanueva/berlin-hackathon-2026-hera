import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowRight } from "lucide-react"

import { ShimmerButton } from "@/components/ui/magic/shimmer-button"
import { cn } from "@/lib/utils"

interface UrlFieldProps {
  variant: "hero" | "cta"
  ctaLabel?: string
  className?: string
}

const AIRBNB_HOST_RE = /(?:^|\.)airbnb\.[a-z.]+$/i

function isValidAirbnbUrl(value: string): boolean {
  try {
    const url = new URL(value.trim())
    if (!AIRBNB_HOST_RE.test(url.hostname)) return false
    return url.pathname.startsWith("/rooms/")
  } catch {
    return false
  }
}

export function UrlField({ variant, ctaLabel = "Try", className }: UrlFieldProps) {
  const [url, setUrl] = useState("")
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const value = url.trim()
    // Empty submit is allowed — user clicks "Make my film" without pasting and
    // lands on /app where they can paste later (or sign up first via the auth
    // wall). With a value, we still validate so we don't deep-link garbage.
    if (value && !isValidAirbnbUrl(value)) {
      setError("That doesn’t look like an Airbnb listing.")
      return
    }
    setError(null)
    navigate(value ? `/app?url=${encodeURIComponent(value)}` : "/app")
  }

  const isHero = variant === "hero"

  return (
    <form
      onSubmit={onSubmit}
      className={cn("w-full max-w-md", className)}
      noValidate
    >
      <div
        className={cn(
          "flex items-stretch gap-1 rounded-md p-1.5",
          isHero
            ? "border border-white/15 bg-white/5 backdrop-blur-sm"
            : "border border-border bg-card",
        )}
      >
        <input
          type="url"
          inputMode="url"
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="off"
          placeholder="https://airbnb.com/rooms/…"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value)
            if (error) setError(null)
          }}
          aria-invalid={Boolean(error)}
          className={cn(
            "min-w-0 flex-1 bg-transparent px-3 py-2 font-mono text-sm outline-none placeholder:text-muted-foreground",
            isHero
              ? "text-white placeholder:text-white/40"
              : "text-foreground",
          )}
        />
        <ShimmerButton
          type="submit"
          className="shrink-0 px-4 py-2 text-sm font-medium"
        >
          <span className="inline-flex items-center gap-1.5">
            {ctaLabel}
            <ArrowRight className="lucide h-4 w-4" />
          </span>
        </ShimmerButton>
      </div>
      {error ? (
        <p
          role="alert"
          className={cn(
            "mt-2 text-xs",
            isHero ? "text-rose-300" : "text-destructive",
          )}
        >
          {error}
        </p>
      ) : null}
    </form>
  )
}
