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

  const tonePreset = TONES.find((t) => t.key === overrides.tone)

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-12">
      <header className="flex flex-col gap-2">
        <p className="text-label text-muted-foreground">Storyboard plan ready</p>
        <h2 className="text-display-lg">Approve, or steer it.</h2>
        <p className="text-body max-w-prose text-muted-foreground">
          {listing.title} · {listing.location}. The agent committed to a
          direction below — change anything you want, then render. Render takes
          ~3 minutes.
        </p>
      </header>

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <h3 className="text-display-md">Output language</h3>
          <span className="text-label text-muted-foreground">
            Detected: {phase1.suggested_language.toUpperCase()}
          </span>
        </div>
        <div className="inline-flex w-fit gap-1 rounded-md border border-border bg-muted p-1">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              onClick={() => setLanguage(lang.code)}
              className={cn(
                "rounded-sm px-4 py-1.5 text-label transition-colors",
                overrides.language === lang.code
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <h3 className="text-display-md">Tone preset</h3>
          <span className="text-label text-muted-foreground">
            Suggested: {phase1.suggested_tone}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {TONES.map((tone) => {
            const active = overrides.tone === tone.key
            return (
              <button
                key={tone.key}
                type="button"
                onClick={() => setTone(tone.key)}
                className={cn(
                  "flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors",
                  active
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background hover:border-foreground/50",
                )}
              >
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
        {tonePreset && (
          <p className="text-body-sm italic text-muted-foreground">
            Picked tone overrides the visual_system suggestion if they conflict.
          </p>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <h3 className="text-display-md">Emphasis</h3>
          <span className="text-label text-muted-foreground">
            Click to cycle: ↑ feature · ↓ downplay · neutral
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
        <div className="flex items-baseline justify-between">
          <h3 className="text-display-md">Opening hook</h3>
          <span className="text-label text-muted-foreground">
            Default: Auto (let the agent decide)
          </span>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <HookCard
            id="auto"
            label="Auto"
            kind="—"
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

      <footer className="flex flex-col-reverse items-center gap-3 pt-4 sm:flex-row sm:justify-between">
        <div className="flex items-center gap-3">
          <Button onClick={onBack} variant="outline">
            Back
          </Button>
          <Button onClick={reset} variant="link" className="text-muted-foreground">
            Reset to agent defaults
          </Button>
        </div>
        <Button onClick={onRender} disabled={submitting} size="lg">
          {submitting ? "Starting render…" : "Render with these choices (~3 min)"}
        </Button>
      </footer>
    </main>
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
