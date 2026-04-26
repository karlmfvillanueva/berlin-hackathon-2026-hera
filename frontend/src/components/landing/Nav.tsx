import { Link } from "react-router-dom"
import { useEffect, useState } from "react"

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

        <a
          href="#cta"
          className="inline-flex items-center rounded-sm bg-primary px-4 py-2 text-body-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Try a listing →
        </a>
      </div>
    </header>
  )
}
