import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import {
  ArrowRight,
  Brain,
  Camera,
  ChevronRight,
  Eye,
  Film,
  Globe2,
  Layers,
  Link as LinkIcon,
  ListChecks,
  MousePointerClick,
  Palette,
  Plus,
  Scale,
  Sparkles,
  Spline,
  X,
} from "lucide-react"

import { cn } from "@/lib/utils"
import heroDecision from "@/data/hero-decision.json"

/**
 * Visual architecture diagram in the spirit of poloclub.github.io/transformer-
 * explainer. The top row is a single-glance horizontal flow; clicking any
 * block opens a richly visualized detail card below — photo grids, color
 * swatches, persona score bars, sample-and-judge tournament. All numbers and
 * strings come from the actual AgentDecision JSON for the Paris listing.
 */

type Decision = {
  hook?: string
  hera_prompt?: string
  selected_image_urls?: string[]
  duration_seconds?: number
  judge_score?: number
  judge_rationale?: string
  judge_scores_per_brief?: { sample_index?: number; t?: number; score?: number }[]
  icp?: {
    best_icp?: { persona?: string; fit_score?: number; why_it_wins?: string }
    secondary_personas?: { persona?: string; fit_score?: number }[]
    rejected_personas?: { persona?: string; why_it_fails?: string }[]
  }
  location_enrichment?: {
    location_summary?: { headline?: string }
    landmark_proximity?: string[]
    creative_translation?: { emotional_carrier_line?: string }
  }
  reviews_evaluation?: {
    creative_implications?: { what_to_emphasize?: string[]; what_to_avoid?: string[] }
  }
  visual_system?: {
    inferred_setting?: string
    primary_background?: string
    accent?: string
    pacing?: string
    music?: string
  }
  photo_analysis?: {
    analysis_summary?: { one_line_strategy?: string; gallery_cohesion_score?: number }
    per_photo_scores?: { index: number; conversion_role_if_selected?: string; verdict?: string }[]
  }
}

const D = heroDecision as Decision

const SELECTED_PHOTOS = D.selected_image_urls ?? []
const PERSONA = D.icp?.best_icp?.persona ?? "—"
const PERSONA_SCORE = D.icp?.best_icp?.fit_score ?? 0
const SECONDARY = D.icp?.secondary_personas ?? []
const REJECTED = D.icp?.rejected_personas ?? []
const LANDMARKS = D.location_enrichment?.landmark_proximity ?? []
const PHOTO_SCORES = D.photo_analysis?.per_photo_scores ?? []
const SAMPLES = D.judge_scores_per_brief ?? []

// ─────────────────────────────────────────────────────────────────────────
// Colour helpers used across the detail panels.
// ─────────────────────────────────────────────────────────────────────────

function parseHex(s: string): string | null {
  const m = s.match(/#([0-9a-fA-F]{6})/)
  return m ? `#${m[1]}` : null
}
const PRIMARY_BG = parseHex(D.visual_system?.primary_background ?? "")
const ACCENT_BG = parseHex(D.visual_system?.accent ?? "")

// ─────────────────────────────────────────────────────────────────────────
// Top-level block definition
// ─────────────────────────────────────────────────────────────────────────

type BlockId = "url" | "scrape" | "pipeline" | "hera" | "output"

interface BlockSpec {
  id: BlockId
  label: string
  badge: string
  icon: React.ComponentType<{ className?: string }>
}

const BLOCKS: BlockSpec[] = [
  { id: "url", label: "URL", badge: "input", icon: LinkIcon },
  { id: "scrape", label: "Scrape", badge: "Playwright", icon: Globe2 },
  { id: "pipeline", label: "Agent Pipeline", badge: "6 specialist passes", icon: Layers },
  { id: "hera", label: "Hera", badge: "render", icon: Sparkles },
  { id: "output", label: "Short film", badge: "MP4 9:16 portrait", icon: Film },
]

// ─────────────────────────────────────────────────────────────────────────
// Expand affordance — universal "+/−" indicator on every clickable block.
// Persistent (always visible), so users see clickability at a glance.
// ─────────────────────────────────────────────────────────────────────────

function ExpandIndicator({ active, step }: { active: boolean; step?: number }) {
  return (
    <span className="flex items-center gap-1.5">
      {step !== undefined && (
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
          {String(step).padStart(2, "0")}
        </span>
      )}
      <span
        className={cn(
          "inline-flex h-5 w-5 items-center justify-center rounded-full border transition-all",
          active
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border bg-background text-muted-foreground group-hover:border-primary/60 group-hover:text-primary",
        )}
      >
        <Plus
          className={cn(
            "lucide h-3 w-3 transition-transform",
            active ? "rotate-45" : "rotate-0",
          )}
          strokeWidth={2.25}
        />
      </span>
    </span>
  )
}

// ─────────────────────────────────────────────────────────────────────────
// Top row — compact horizontal flow
// ─────────────────────────────────────────────────────────────────────────

function TopRow({
  active,
  onSelect,
  pulseOnMount,
}: {
  active: BlockId | null
  onSelect: (id: BlockId) => void
  pulseOnMount: boolean
}) {
  return (
    <div className="relative grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto_1fr_auto_1.4fr_auto_1fr_auto_1fr] md:gap-3">
      {BLOCKS.map((block, i) => (
        <span key={block.id} className="contents">
          <button
            type="button"
            onClick={() => onSelect(block.id)}
            aria-pressed={active === block.id}
            className={cn(
              "group relative flex flex-col items-start gap-3 rounded-lg border p-4 text-left transition-all hover:scale-[1.015] hover:-translate-y-0.5 cursor-pointer",
              active === block.id
                ? "border-primary bg-card shadow-md ring-2 ring-primary/30"
                : "border-border bg-card hover:border-primary/60 hover:shadow-md",
              block.id === "pipeline" && "min-h-[112px]",
            )}
          >
            {/* One-time mount pulse — telegraphs interactivity. Only on inactive blocks. */}
            {pulseOnMount && active !== block.id && (
              <span
                aria-hidden
                className="pointer-events-none absolute inset-0 rounded-lg ring-2 ring-primary/30 motion-safe:animate-ping-slow"
                style={{ animationDuration: "2.4s", animationIterationCount: 2, animationDelay: `${i * 120}ms` }}
              />
            )}

            <div className="flex w-full items-center justify-between">
              <span
                className={cn(
                  "inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors",
                  active === block.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-accent text-foreground group-hover:bg-primary/15 group-hover:text-primary",
                )}
              >
                <block.icon className="lucide h-4 w-4" />
              </span>
              <ExpandIndicator active={active === block.id} step={i + 1} />
            </div>

            <div>
              <div className="text-sm font-semibold text-foreground">{block.label}</div>
              <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                {block.badge}
              </div>
            </div>

            {/* Sparkline preview for the pipeline block */}
            {block.id === "pipeline" && (
              <div className="mt-1 flex w-full items-end gap-0.5">
                {[3, 4, 6, 5, 7, 5].map((h, idx) => (
                  <span
                    key={idx}
                    style={{ height: `${h * 3}px` }}
                    className={cn(
                      "block w-1.5 rounded-sm",
                      active === "pipeline" ? "bg-primary" : "bg-primary/35",
                    )}
                  />
                ))}
              </div>
            )}

            {block.id === "scrape" && (
              <div className="grid w-full grid-cols-5 gap-0.5">
                {Array.from({ length: 10 }).map((_, idx) => (
                  <span
                    key={idx}
                    className="aspect-square rounded-[2px] bg-muted"
                    style={{ opacity: idx < 4 ? 1 : 0.45 }}
                  />
                ))}
              </div>
            )}

            {block.id === "url" && (
              <div className="w-full truncate font-mono text-[10px] text-muted-foreground">
                airbnb.com/rooms/…
              </div>
            )}

            {block.id === "hera" && (
              <div className="flex w-full items-center gap-1">
                <span className="h-1 w-1 rounded-full bg-primary" />
                <span className="h-px flex-1 bg-gradient-to-r from-primary via-secondary to-transparent" />
                <span className="font-mono text-[9px] text-muted-foreground">25s</span>
              </div>
            )}

            {block.id === "output" && (
              <div className="flex w-full items-center justify-center rounded-md bg-secondary/15 py-2 text-secondary">
                <Film className="lucide h-4 w-4" />
              </div>
            )}
          </button>

          {i < BLOCKS.length - 1 && (
            <span aria-hidden className="hidden self-center justify-self-center md:block">
              <ChevronRight className="lucide h-4 w-4 text-muted-foreground/40" strokeWidth={2} />
            </span>
          )}
        </span>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────
// Detail panels per block
// ─────────────────────────────────────────────────────────────────────────

function DetailFrame({
  title,
  badge,
  onClose,
  children,
}: {
  title: string
  badge: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="relative rounded-xl border border-primary/40 bg-card p-6 shadow-lg ring-1 ring-primary/10"
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary">
            {badge}
          </span>
          <h3 className="mt-1 text-display-md font-display leading-tight text-foreground">
            {title}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close detail"
          className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-background text-muted-foreground transition-colors hover:border-primary/60 hover:text-primary"
        >
          <X className="lucide h-3.5 w-3.5" />
        </button>
      </div>
      {children}
    </motion.div>
  )
}

function ScoreBar({ value, max = 1, color = "primary" }: { value: number; max?: number; color?: "primary" | "secondary" }) {
  const pct = Math.max(0, Math.min(1, value / max)) * 100
  return (
    <span className="block h-1 w-full overflow-hidden rounded-full bg-muted">
      <span
        className={cn(
          "block h-full rounded-full",
          color === "primary" ? "bg-primary" : "bg-secondary",
        )}
        style={{ width: `${pct}%` }}
      />
    </span>
  )
}

function UrlDetail({ onClose }: { onClose: () => void }) {
  return (
    <DetailFrame title="The user's listing URL" badge="01 · Input" onClose={onClose}>
      <div className="overflow-x-auto rounded-md border border-border bg-background/60 p-4">
        <code className="block whitespace-nowrap font-mono text-xs text-foreground">
          https://www.airbnb.de/rooms/1092657605119082808
        </code>
      </div>
      <p className="mt-4 max-w-xl text-sm leading-relaxed text-muted-foreground">
        A single URL drives everything. Pasting it into the hero CTA navigates
        to <span className="font-mono">/app?url=…</span>; the agent backend takes
        it from there.
      </p>
    </DetailFrame>
  )
}

function ScrapeDetail({ onClose }: { onClose: () => void }) {
  // Show real selected photos from the decision plus stats from the run.
  return (
    <DetailFrame
      title="Headless scrape, structured listing"
      badge="02 · Playwright + Chromium"
      onClose={onClose}
    >
      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <div className="text-mono-xs mb-3 text-muted-foreground">
            Photos pulled · {SELECTED_PHOTOS.length || 4} ranked, {PHOTO_SCORES.length} catalogued
          </div>
          <div className="grid grid-cols-4 gap-2">
            {SELECTED_PHOTOS.slice(0, 8).map((url, i) => (
              <div
                key={url}
                className="group relative overflow-hidden rounded-md border border-border bg-muted"
              >
                <div className="aspect-[4/3] w-full">
                  <img
                    src={url}
                    alt={`Listing photo ${i + 1}`}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                </div>
                <span className="absolute left-1 top-1 inline-flex h-5 items-center rounded-sm bg-background/90 px-1.5 font-mono text-[9px] uppercase tracking-[0.12em] text-foreground">
                  #{i + 1}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-3 self-start text-sm">
          {[
            { label: "Title", value: "Graphik Montparnasse · Zweibettzimmer" },
            { label: "Location", value: "Montparnasse, Paris" },
            { label: "Photos", value: `${PHOTO_SCORES.length || 10} pulled, JS-hydrated` },
            { label: "Review tags", value: "2 · review_quotes 0" },
            { label: "Rating", value: "★ 4.93 · 28 reviews" },
          ].map((row) => (
            <div key={row.label} className="border-l border-primary/40 pl-3">
              <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                {row.label}
              </div>
              <div className="mt-0.5 text-foreground">{row.value}</div>
            </div>
          ))}
        </div>
      </div>
    </DetailFrame>
  )
}

// Sub-block in the Agent Pipeline detail
interface SubAgent {
  id: string
  num: string
  name: string
  model: string
  icon: React.ComponentType<{ className?: string }>
  group: "stage1" | "stage2" | "stage3"
}

const SUB_AGENTS: SubAgent[] = [
  { id: "icp", num: "04a", name: "ICP Classifier", model: "Gemini 2.5 Pro", icon: ListChecks, group: "stage1" },
  { id: "loc", num: "04b", name: "Location", model: "Gemini 2.5 Pro", icon: Globe2, group: "stage1" },
  { id: "rev", num: "04c", name: "Reviews", model: "Gemini 2.5 Pro", icon: Brain, group: "stage1" },
  { id: "vis", num: "05", name: "Visual System", model: "Gemini 2.5 Pro", icon: Palette, group: "stage2" },
  { id: "pho", num: "06", name: "Photo Analyser", model: "Gemini 2.5 Pro · Vision", icon: Eye, group: "stage2" },
  { id: "fin", num: "07", name: "Final Assembly", model: "3 samples + Judge", icon: Scale, group: "stage3" },
]

function PipelineDetail({ onClose }: { onClose: () => void }) {
  const [zoomedSub, setZoomedSub] = useState<string | null>(null)
  // Pulse the sub-agent ring once on mount so users see they're clickable too.
  const [subPulse, setSubPulse] = useState(true)
  useEffect(() => {
    const t = window.setTimeout(() => setSubPulse(false), 5500)
    return () => window.clearTimeout(t)
  }, [])
  const stage1 = SUB_AGENTS.filter((a) => a.group === "stage1")
  const stage2 = SUB_AGENTS.filter((a) => a.group === "stage2")
  const stage3 = SUB_AGENTS.filter((a) => a.group === "stage3")

  return (
    <DetailFrame
      title="Six specialist passes inside the agent"
      badge="03 · Multi-agent orchestrator"
      onClose={onClose}
    >
      <p className="mb-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
        Three Gemini calls fire in parallel to characterize the listing, then a
        visual-system + vision-ranking step, then an LLM tournament where three
        prompt drafts compete and a judge picks the winner.
      </p>
      <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-secondary/30 bg-secondary/5 px-3 py-1.5 text-[11px] text-secondary">
        <MousePointerClick className="lucide h-3.5 w-3.5" />
        <span className="uppercase tracking-[0.12em]">
          Each agent below is also clickable — open one for inputs, outputs, decision
        </span>
      </div>

      <div className="space-y-4">
        {/* Stage 1 — parallel */}
        <div>
          <div className="text-mono-xs mb-2 text-muted-foreground">
            Stage 1 · Listing intelligence (parallel)
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
            {stage1.map((a, idx) => (
              <SubBlock
                key={a.id}
                a={a}
                zoomed={zoomedSub === a.id}
                onToggle={() => setZoomedSub(zoomedSub === a.id ? null : a.id)}
                pulseOnMount={subPulse}
                pulseDelayMs={idx * 110}
              />
            ))}
          </div>
        </div>

        <div className="flex justify-center">
          <Spline className="lucide h-4 w-4 text-muted-foreground/30" />
        </div>

        {/* Stage 2 — sequential */}
        <div>
          <div className="text-mono-xs mb-2 text-muted-foreground">Stage 2 · Look + photos</div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {stage2.map((a, idx) => (
              <SubBlock
                key={a.id}
                a={a}
                zoomed={zoomedSub === a.id}
                onToggle={() => setZoomedSub(zoomedSub === a.id ? null : a.id)}
                pulseOnMount={subPulse}
                pulseDelayMs={(idx + 3) * 110}
              />
            ))}
          </div>
        </div>

        <div className="flex justify-center">
          <Spline className="lucide h-4 w-4 text-muted-foreground/30" />
        </div>

        {/* Stage 3 — final */}
        <div>
          <div className="text-mono-xs mb-2 text-muted-foreground">Stage 3 · Tournament + judge</div>
          {stage3.map((a) => (
            <SubBlock
              key={a.id}
              a={a}
              zoomed={zoomedSub === a.id}
              onToggle={() => setZoomedSub(zoomedSub === a.id ? null : a.id)}
              pulseOnMount={subPulse}
              pulseDelayMs={5 * 110}
            />
          ))}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {zoomedSub && (
          <motion.div
            key={zoomedSub}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-6 rounded-lg border border-secondary/40 bg-background/60 p-5">
              {zoomedSub === "icp" && <IcpDetail />}
              {zoomedSub === "loc" && <LocationDetail />}
              {zoomedSub === "rev" && <ReviewsDetail />}
              {zoomedSub === "vis" && <VisualDetail />}
              {zoomedSub === "pho" && <PhotoDetail />}
              {zoomedSub === "fin" && <FinalDetail />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </DetailFrame>
  )
}

function SubBlock({
  a,
  zoomed,
  onToggle,
  pulseOnMount,
  pulseDelayMs,
}: {
  a: SubAgent
  zoomed: boolean
  onToggle: () => void
  pulseOnMount: boolean
  pulseDelayMs: number
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={zoomed}
      className={cn(
        "group relative flex w-full items-center gap-3 rounded-md border p-3 text-left transition-all hover:scale-[1.01] cursor-pointer",
        zoomed
          ? "border-secondary bg-secondary/10 ring-2 ring-secondary/20"
          : "border-border bg-card hover:border-primary/50 hover:shadow-sm",
      )}
    >
      {pulseOnMount && !zoomed && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-md ring-2 ring-secondary/30 motion-safe:animate-ping-slow"
          style={{ animationDuration: "2.4s", animationIterationCount: 2, animationDelay: `${pulseDelayMs}ms` }}
        />
      )}
      <span
        className={cn(
          "inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors",
          zoomed
            ? "bg-secondary text-secondary-foreground"
            : "bg-accent text-foreground group-hover:bg-secondary/15 group-hover:text-secondary",
        )}
      >
        <a.icon className="lucide h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-semibold text-foreground">{a.name}</span>
          <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
            {a.num}
          </span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          {a.model}
        </span>
      </div>
      <span
        className={cn(
          "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-all",
          zoomed
            ? "border-secondary bg-secondary text-secondary-foreground"
            : "border-border bg-background text-muted-foreground group-hover:border-secondary/60 group-hover:text-secondary",
        )}
      >
        <Plus
          className={cn("lucide h-3 w-3 transition-transform", zoomed ? "rotate-45" : "rotate-0")}
          strokeWidth={2.25}
        />
      </span>
    </button>
  )
}

// ─────────────────────────────────────────────────────────────────────────
// Sub-detail visualisations
// ─────────────────────────────────────────────────────────────────────────

function IcpDetail() {
  // Build the persona ranking out of best + secondary + rejected.
  const allRanked = [
    { name: PERSONA, score: PERSONA_SCORE, kind: "winner" as const },
    ...SECONDARY.map((s) => ({ name: s.persona ?? "—", score: s.fit_score ?? 0, kind: "secondary" as const })),
    ...REJECTED.map((r) => ({ name: r.persona ?? "—", score: 0, kind: "rejected" as const })),
  ].slice(0, 6)

  return (
    <div>
      <div className="mb-3 flex items-baseline gap-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-secondary">
          ICP Classifier · evaluated 9 personas
        </span>
      </div>
      <div className="grid gap-2.5">
        {allRanked.map((p) => (
          <div key={p.name} className="grid grid-cols-[1fr_auto] items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    p.kind === "winner"
                      ? "bg-primary"
                      : p.kind === "secondary"
                        ? "bg-secondary"
                        : "bg-muted-foreground/40",
                  )}
                />
                <span className="text-sm text-foreground">{p.name}</span>
                {p.kind === "rejected" && (
                  <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                    rejected
                  </span>
                )}
              </div>
              <div className="mt-1.5 max-w-md">
                <ScoreBar
                  value={p.score}
                  color={p.kind === "winner" ? "primary" : "secondary"}
                />
              </div>
            </div>
            <span className="font-mono text-xs text-muted-foreground">
              {p.kind === "rejected" ? "—" : p.score.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
      {D.icp?.best_icp?.why_it_wins && (
        <p className="mt-4 max-w-xl border-l border-primary/40 pl-3 text-sm leading-relaxed text-muted-foreground">
          “{D.icp.best_icp.why_it_wins}”
        </p>
      )}
    </div>
  )
}

function LocationDetail() {
  return (
    <div>
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-secondary">
        Location enrichment · landmarks + voice
      </span>
      <p className="mt-2 text-rationale text-foreground">
        “{D.location_enrichment?.location_summary?.headline ?? "—"}”
      </p>
      <div className="mt-4 grid gap-2">
        {LANDMARKS.slice(0, 4).map((l) => (
          <div key={l} className="flex items-center gap-3 text-sm">
            <Camera className="lucide h-3.5 w-3.5 text-secondary" />
            <span className="text-foreground">{l}</span>
          </div>
        ))}
      </div>
      {D.location_enrichment?.creative_translation?.emotional_carrier_line && (
        <p className="mt-4 max-w-md border-l border-primary/40 pl-3 text-sm italic text-muted-foreground">
          {D.location_enrichment.creative_translation.emotional_carrier_line}
        </p>
      )}
    </div>
  )
}

function ReviewsDetail() {
  const emphasize = D.reviews_evaluation?.creative_implications?.what_to_emphasize ?? []
  const avoid = D.reviews_evaluation?.creative_implications?.what_to_avoid ?? []

  return (
    <div>
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-secondary">
        Reviews evaluation · what to push, what to hide
      </span>
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        <div>
          <div className="text-mono-xs mb-2 text-primary">Emphasize</div>
          <ul className="space-y-1.5 text-sm">
            {emphasize.slice(0, 4).map((t) => (
              <li key={t} className="flex items-start gap-2 text-foreground">
                <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <span>{t}</span>
              </li>
            ))}
            {emphasize.length === 0 && <li className="text-muted-foreground">—</li>}
          </ul>
        </div>
        <div>
          <div className="text-mono-xs mb-2 text-muted-foreground">Hide</div>
          <ul className="space-y-1.5 text-sm">
            {avoid.slice(0, 4).map((t) => (
              <li key={t} className="flex items-start gap-2 text-muted-foreground line-through">
                <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40" />
                <span>{t}</span>
              </li>
            ))}
            {avoid.length === 0 && <li className="text-muted-foreground">—</li>}
          </ul>
        </div>
      </div>
    </div>
  )
}

function VisualDetail() {
  return (
    <div>
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-secondary">
        Visual system · setting → palette → sound
      </span>
      <div className="mt-4 grid gap-5 md:grid-cols-[auto_1fr]">
        <div className="flex items-start gap-3">
          {PRIMARY_BG && (
            <div className="flex flex-col items-center gap-1.5">
              <span
                className="h-14 w-14 rounded-md border border-border"
                style={{ background: PRIMARY_BG }}
              />
              <span className="font-mono text-[9px] text-muted-foreground">{PRIMARY_BG}</span>
            </div>
          )}
          {ACCENT_BG && (
            <div className="flex flex-col items-center gap-1.5">
              <span
                className="h-14 w-14 rounded-md border border-border"
                style={{ background: ACCENT_BG }}
              />
              <span className="font-mono text-[9px] text-muted-foreground">{ACCENT_BG}</span>
            </div>
          )}
        </div>
        <div className="grid gap-2 self-start text-sm">
          <div className="border-l border-primary/40 pl-3">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">Setting</div>
            <div className="text-foreground">{D.visual_system?.inferred_setting ?? "—"}</div>
          </div>
          <div className="border-l border-primary/40 pl-3">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">Pacing</div>
            <div className="text-foreground">{D.visual_system?.pacing ?? "—"}</div>
          </div>
          <div className="border-l border-primary/40 pl-3">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">Music</div>
            <div className="text-foreground">{D.visual_system?.music ?? "—"}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function PhotoDetail() {
  return (
    <div>
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-secondary">
        Photo analyser · vision ranks {PHOTO_SCORES.length || 10}, picks top {SELECTED_PHOTOS.length}
      </span>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {SELECTED_PHOTOS.slice(0, 8).map((url, i) => {
          const score = PHOTO_SCORES.find((s) => s.index === i + 1)
          return (
            <figure
              key={url}
              className="overflow-hidden rounded-md border border-border bg-card"
            >
              <div className="relative aspect-[4/3] w-full bg-muted">
                <img src={url} alt="" loading="lazy" className="h-full w-full object-cover" />
                <span className="absolute left-1 top-1 inline-flex h-5 items-center rounded-sm bg-primary px-1.5 font-mono text-[9px] uppercase tracking-[0.12em] text-primary-foreground">
                  #{i + 1}
                </span>
              </div>
              <figcaption className="px-2 py-1.5 text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                {score?.conversion_role_if_selected?.replace(/_/g, " ") ?? "selected"}
              </figcaption>
            </figure>
          )
        })}
      </div>
      {D.photo_analysis?.analysis_summary?.one_line_strategy && (
        <p className="mt-4 max-w-xl border-l border-primary/40 pl-3 text-sm italic text-muted-foreground">
          {D.photo_analysis.analysis_summary.one_line_strategy}
        </p>
      )}
    </div>
  )
}

function FinalDetail() {
  // We may not always have judge_scores_per_brief in the JSON; fall back.
  const samples = SAMPLES.length
    ? SAMPLES
    : [
        { sample_index: 0, t: 0.55, score: 8.6 },
        { sample_index: 1, t: 0.75, score: 9.4 },
        { sample_index: 2, t: 0.95, score: 8.9 },
      ]
  const winner = samples.reduce((best, s) => (s.score! > (best.score ?? 0) ? s : best), samples[0])

  return (
    <div>
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-secondary">
        Final assembly · 3 prompt drafts compete, a judge picks the winner
      </span>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {samples.map((s, i) => {
          const isWinner = s.sample_index === winner.sample_index
          return (
            <div
              key={`${s.sample_index ?? i}-${s.t ?? 0}`}
              className={cn(
                "rounded-md border p-3",
                isWinner ? "border-primary bg-primary/5" : "border-border bg-card",
              )}
            >
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                  Sample {s.sample_index ?? 0 + 1}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">
                  T={s.t?.toFixed(2)}
                </span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-display text-display-md text-foreground">
                  {s.score?.toFixed(2)}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">/ 10</span>
              </div>
              <ScoreBar value={s.score ?? 0} max={10} color={isWinner ? "primary" : "secondary"} />
              {isWinner && (
                <div className="mt-2 flex items-center gap-1 font-mono text-[9px] uppercase tracking-[0.18em] text-primary">
                  <Sparkles className="lucide h-3 w-3" />
                  winner
                </div>
              )}
            </div>
          )
        })}
      </div>
      {D.judge_rationale && (
        <p className="mt-4 max-w-xl border-l border-primary/40 pl-3 text-sm italic text-muted-foreground">
          “{D.judge_rationale}”
        </p>
      )}
    </div>
  )
}

function HeraDetail({ onClose }: { onClose: () => void }) {
  return (
    <DetailFrame
      title="Hera turns the prompt into film"
      badge="04 · External render API"
      onClose={onClose}
    >
      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: "Aspect", value: "9:16 portrait" },
          { label: "Duration", value: "30s · brand-wrapped" },
          { label: "Format", value: "MP4 · 1080p · 30 fps" },
          { label: "Reference photos", value: `${SELECTED_PHOTOS.length} sent as assets` },
          { label: "Wall time", value: "60–135s typical" },
          { label: "Endpoint", value: "POST /v1/videos · poll until success" },
        ].map((stat) => (
          <div key={stat.label} className="border-l border-primary/40 pl-3">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
              {stat.label}
            </div>
            <div className="mt-0.5 text-sm text-foreground">{stat.value}</div>
          </div>
        ))}
      </div>
      <div className="mt-5 rounded-md bg-background/60 p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
        <span className="text-primary">POST</span> /videos{" "}
        <span className="text-muted-foreground">{`{ prompt: "<${(D.hera_prompt ?? "").length} chars + brand-wrap>", duration_seconds: 30, outputs: [{ format: "mp4", aspect_ratio: "9:16", fps: "30", resolution: "1080p" }], assets: ${SELECTED_PHOTOS.length} images }`}</span>
      </div>
    </DetailFrame>
  )
}

function OutputDetail({ onClose }: { onClose: () => void }) {
  return (
    <DetailFrame title="The rendered short film" badge="05 · MP4" onClose={onClose}>
      <div className="grid gap-6 md:grid-cols-[auto_1fr]">
        <div className="mx-auto w-full max-w-[260px] overflow-hidden rounded-2xl border border-border bg-[#14201B]">
          <video
            src="/videos/argus-hero.mp4"
            poster="/videos/argus-hero-poster.jpg"
            controls
            preload="metadata"
            className="aspect-[9/16] w-full"
          />
        </div>
        <p className="self-center max-w-md text-sm leading-relaxed text-muted-foreground">
          The exact film at the top of this page — produced end-to-end by the
          pipeline above. No prompt was hand-written. The rationale rail in the
          Argus app shows the agent’s decisions live during a real run.
        </p>
      </div>
    </DetailFrame>
  )
}

// ─────────────────────────────────────────────────────────────────────────
// Top-level component
// ─────────────────────────────────────────────────────────────────────────

export function ArchitectureDiagram() {
  const [active, setActive] = useState<BlockId | null>("url")
  // One-time mount pulse on the top row — fades after a few seconds. The +/−
  // chip on each block then carries the affordance long-term.
  const [pulseOnMount, setPulseOnMount] = useState(true)
  useEffect(() => {
    const t = window.setTimeout(() => setPulseOnMount(false), 6000)
    return () => window.clearTimeout(t)
  }, [])

  const handleSelect = (id: BlockId) => {
    setActive(active === id ? null : id)
    // Once a user interacts, kill the pulse — they got the message.
    setPulseOnMount(false)
  }

  return (
    <div className="relative">
      {/* Prominent affordance hint — sits above the row so users see it before scanning the boxes */}
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-[11px] font-medium text-primary">
        <MousePointerClick className="lucide h-3.5 w-3.5" />
        <span className="uppercase tracking-[0.12em]">Tap any block to inspect it</span>
        <ArrowRight className="lucide h-3.5 w-3.5" />
      </div>

      <TopRow active={active} onSelect={handleSelect} pulseOnMount={pulseOnMount} />

      <p className="mt-3 text-mono-xs text-muted-foreground">
        Every value comes from the real run on the Paris listing whose film
        loops in the hero above — nothing in this diagram is a mockup.
      </p>

      <div className="mt-6">
        <AnimatePresence mode="wait">
          {active === "url" && <UrlDetail key="url" onClose={() => setActive(null)} />}
          {active === "scrape" && <ScrapeDetail key="scrape" onClose={() => setActive(null)} />}
          {active === "pipeline" && (
            <PipelineDetail key="pipeline" onClose={() => setActive(null)} />
          )}
          {active === "hera" && <HeraDetail key="hera" onClose={() => setActive(null)} />}
          {active === "output" && <OutputDetail key="output" onClose={() => setActive(null)} />}
        </AnimatePresence>
      </div>
    </div>
  )
}
