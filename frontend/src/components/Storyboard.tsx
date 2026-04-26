import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type {
  EmphasisOption,
  HookOption,
  Language,
  Overrides,
  Phase1Decision,
  ScrapedListing,
  Tone,
} from "@/types"

const LANGUAGES: { code: Language; label: string }[] = [
  { code: "de", label: "DE" },
  { code: "en", label: "EN" },
  { code: "es", label: "ES" },
]

const TONES: { key: Tone; label: string; rationale: string }[] = [
  { key: "luxury", label: "Luxury", rationale: "Restrained, slow, cinematic." },
  { key: "family", label: "Family", rationale: "Warm, safe, nostalgic." },
  { key: "urban", label: "Urban", rationale: "High contrast, fast, editorial." },
  { key: "cozy", label: "Cozy", rationale: "Intimate, soft, lo-fi acoustic." },
]

const SOURCE_LABELS: Record<EmphasisOption["source"], string> = {
  amenity: "Amenity",
  review: "Reviews",
  location: "Location",
}

const HOOK_KIND_LABEL: Record<HookOption["kind"], string> = {
  amenity: "Amenity",
  location: "Location",
  review: "Review",
  view: "View",
}

type EmphasisState = "neutral" | "up" | "down"

interface StoryboardProps {
  listing: ScrapedListing
  phase1: Phase1Decision
  overrides: Overrides
  onChange: (next: Overrides) => void
  onRender: () => void
  onBack: () => void
  submitting: boolean
}

export function Storyboard({
  listing,
  phase1,
  overrides,
  onChange,
  onRender,
  onBack,
  submitting,
}: StoryboardProps) {
  const [showAllEmphasis, setShowAllEmphasis] = useState(false)

  const emphasisState = useMemo(() => {
    const map: Record<string, EmphasisState> = {}
    for (const slug of overrides.emphasis) map[slug] = "up"
    for (const slug of overrides.deemphasis) map[slug] = "down"
    return map
  }, [overrides.emphasis, overrides.deemphasis])

  // Track which sections the user has overridden, so labels can switch from
  // "Suggested" to "Picked" and a single Reset button surfaces only when relevant.
  const overrideFlags = useMemo(() => {
    return {
      language: overrides.language !== phase1.suggested_language,
      tone: overrides.tone !== phase1.suggested_tone,
      emphasis:
        overrides.emphasis.length > 0 || overrides.deemphasis.length > 0,
      hook: overrides.hook_id !== "auto",
    }
  }, [overrides, phase1.suggested_language, phase1.suggested_tone])

  const overrideCount =
    Number(overrideFlags.language) +
    Number(overrideFlags.tone) +
    Number(overrideFlags.emphasis) +
    Number(overrideFlags.hook)

  function cycleEmphasis(slug: string) {
    const current = emphasisState[slug] ?? "neutral"
    const next: EmphasisState = current === "neutral" ? "up" : current === "up" ? "down" : "neutral"
    const emphasis = overrides.emphasis.filter((s) => s !== slug)
    const deemphasis = overrides.deemphasis.filter((s) => s !== slug)
    if (next === "up") emphasis.push(slug)
    if (next === "down") deemphasis.push(slug)
    onChange({ ...overrides, emphasis, deemphasis })
  }

  function setLanguage(language: Language) {
    onChange({ ...overrides, language })
  }

  function setTone(tone: Tone) {
    onChange({ ...overrides, tone })
  }

  function setHookId(hook_id: string) {
    onChange({ ...overrides, hook_id })
  }

  function reset() {
    onChange({
      language: phase1.suggested_language,
      tone: phase1.suggested_tone,
      emphasis: [],
      deemphasis: [],
      hook_id: "auto",
    })
  }

  const visibleEmphasis = showAllEmphasis
    ? phase1.emphasis_options
    : phase1.emphasis_options.slice(0, 8)

  const upCount = overrides.emphasis.length
  const downCount = overrides.deemphasis.length

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-12">
      <header className="flex flex-col gap-3">
        <p className="text-label text-muted-foreground">Storyboard plan · ready</p>
        <h2 className="text-display-lg">Approve, or steer it.</h2>
        <p className="text-body max-w-prose text-muted-foreground">
          {listing.title} · {listing.location}. The agent committed to a
          direction below. Change anything you want, then render — takes ~3 minutes.
        </p>
        {overrideCount > 0 && (
          <div className="flex items-center gap-3 pt-1">
            <Badge variant="outline" className="border-foreground/30">
              {overrideCount} change{overrideCount === 1 ? "" : "s"} from defaults
            </Badge>
            <button
              type="button"
              onClick={reset}
              className="text-label text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              Reset to agent defaults
            </button>
          </div>
        )}
      </header>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-display-md">Output language</h3>
          <SectionMeta
            suggested={phase1.suggested_language.toUpperCase()}
            overridden={overrideFlags.language}
          />
        </div>
        <div className="inline-flex w-fit gap-1 rounded-md border border-border bg-muted p-1">
          {LANGUAGES.map((lang) => {
            const active = overrides.language === lang.code
            const isSuggested = lang.code === phase1.suggested_language
            return (
              <button
                key={lang.code}
                type="button"
                onClick={() => setLanguage(lang.code)}
                aria-pressed={active}
                className={cn(
                  "relative rounded-sm px-4 py-1.5 text-label transition-colors",
                  active
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {lang.label}
                {isSuggested && !active && (
                  <span className="ml-1.5 text-[10px] uppercase tracking-wider opacity-70">
                    suggested
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-display-md">Tone preset</h3>
          <SectionMeta
            suggested={phase1.suggested_tone}
            overridden={overrideFlags.tone}
          />
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {TONES.map((tone) => {
            const active = overrides.tone === tone.key
            const isSuggested = tone.key === phase1.suggested_tone
            return (
              <button
                key={tone.key}
                type="button"
                onClick={() => setTone(tone.key)}
                aria-pressed={active}
                className={cn(
                  "relative flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors",
                  active
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background hover:border-foreground/50",
                )}
              >
                {isSuggested && !active && (
                  <span className="absolute right-2 top-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                    suggested
                  </span>
                )}
                <span className="text-label">{tone.label}</span>
                <span
                  className={cn(
                    "text-body-sm leading-snug",
                    active ? "text-background/80" : "text-muted-foreground",
                  )}
                >
                  {tone.rationale}
                </span>
              </button>
            )
          })}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-display-md">Emphasis</h3>
          <span className="text-label text-muted-foreground">
            {upCount + downCount === 0
              ? "Click to cycle: ↑ feature · ↓ downplay · neutral"
              : `${upCount} featured${downCount > 0 ? ` · ${downCount} downplayed` : ""}`}
          </span>
        </div>
        {phase1.emphasis_options.length === 0 ? (
          <p className="text-body italic text-muted-foreground">
            No emphasis chips available — the agent will choose freely.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {visibleEmphasis.map((opt) => {
              const state = emphasisState[opt.slug] ?? "neutral"
              const arrow = state === "up" ? "↑" : state === "down" ? "↓" : ""
              return (
                <button
                  key={opt.slug}
                  type="button"
                  onClick={() => cycleEmphasis(opt.slug)}
                  aria-pressed={state !== "neutral"}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-label transition-colors",
                    state === "up" &&
                      "border-foreground bg-foreground text-background",
                    state === "down" &&
                      "border-destructive bg-destructive/10 text-destructive line-through",
                    state === "neutral" &&
                      "border-border bg-background text-foreground hover:border-foreground/50",
                  )}
                >
                  {arrow && <span>{arrow}</span>}
                  <span>{opt.label}</span>
                  <Badge variant="secondary" className="text-[10px]">
                    {SOURCE_LABELS[opt.source]}
                  </Badge>
                </button>
              )
            })}
            {phase1.emphasis_options.length > 8 && (
              <button
                type="button"
                onClick={() => setShowAllEmphasis((v) => !v)}
                className="text-label text-muted-foreground underline-offset-2 hover:underline"
              >
                {showAllEmphasis
                  ? "Show fewer"
                  : `Show ${phase1.emphasis_options.length - 8} more`}
              </button>
            )}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-display-md">Opening hook</h3>
          <SectionMeta
            suggested="Auto"
            overridden={overrideFlags.hook}
          />
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <HookCard
            id="auto"
            label="Auto"
            kind="Default"
            rationale="Let the Strategic Opinion Agent pick the strongest hook from the listing data."
            active={overrides.hook_id === "auto"}
            onSelect={() => setHookId("auto")}
          />
          {phase1.hook_options.map((hook) => (
            <HookCard
              key={hook.id}
              id={hook.id}
              label={hook.label}
              kind={HOOK_KIND_LABEL[hook.kind]}
              rationale={hook.rationale}
              active={overrides.hook_id === hook.id}
              onSelect={() => setHookId(hook.id)}
            />
          ))}
        </div>
      </section>

      <footer className="sticky bottom-4 z-10 mt-4 flex flex-col-reverse items-center gap-3 rounded-xl border border-border bg-background/95 p-4 shadow-sm backdrop-blur sm:flex-row sm:justify-between">
        <Button onClick={onBack} variant="ghost">
          ← Back
        </Button>
        <Button onClick={onRender} disabled={submitting} size="lg" className="min-w-[260px]">
          {submitting ? "Starting render…" : "Render with these choices · ~3 min"}
        </Button>
      </footer>
    </main>
  )
}

function SectionMeta({
  suggested,
  overridden,
}: {
  suggested: string
  overridden: boolean
}) {
  return (
    <span className="flex items-center gap-2">
      <span className="text-label text-muted-foreground">
        Suggested: <span className="font-medium uppercase">{suggested}</span>
      </span>
      {overridden && (
        <Badge variant="outline" className="border-foreground/40 text-[10px]">
          Adjusted
        </Badge>
      )}
    </span>
  )
}

interface HookCardProps {
  id: string
  label: string
  kind: string
  rationale: string
  active: boolean
  onSelect: () => void
}

function HookCard({ label, kind, rationale, active, onSelect }: HookCardProps) {
  return (
    <Card
      onClick={onSelect}
      className={cn(
        "cursor-pointer p-4 transition-colors",
        active
          ? "border-foreground bg-foreground/5"
          : "border-border hover:border-foreground/40",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-label">{label}</span>
          <span className="text-body-sm leading-snug text-muted-foreground">
            {rationale}
          </span>
        </div>
        <Badge variant="outline" className="shrink-0 text-[10px]">
          {kind}
        </Badge>
      </div>
    </Card>
  )
}
