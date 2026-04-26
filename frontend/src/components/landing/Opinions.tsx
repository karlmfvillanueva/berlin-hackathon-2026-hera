import { Card } from "@/components/ui/card"
import { AnimatedList } from "@/components/ui/magic/animated-list"
import { TextReveal } from "@/components/ui/magic/text-reveal"
import { cn } from "@/lib/utils"

import heroDecision from "@/data/hero-decision.json"

interface OpinionCard {
  index: string
  label: string
  pick: string
  why: string
}

// Pull real fields from the actual AgentDecision the orchestrator produced.
// If we re-render with a different listing, replace src/data/hero-decision.json
// and these strings update automatically.
const decision = heroDecision as {
  hook: string
  pacing: string
  angle: string
  vibes: string
  icp?: {
    best_icp?: { persona?: string; why_it_wins?: string; emotional_driver?: string }
  }
  visual_system?: { music?: string; pacing?: string; primary_background?: string }
}

const persona = decision.icp?.best_icp?.persona ?? "—"
const whyItWins = decision.icp?.best_icp?.why_it_wins ?? ""

function trim(text: string, max: number): string {
  if (!text) return ""
  if (text.length <= max) return text
  return text.slice(0, max - 1).replace(/[,;:.\s]+\S*$/, "") + "…"
}

const CARDS: OpinionCard[] = [
  {
    index: "01",
    label: "The hook",
    pick: trim(decision.hook, 90),
    why: trim(decision.angle, 180),
  },
  {
    index: "02",
    label: "The guest",
    pick: persona,
    why: trim(whyItWins, 180),
  },
  {
    index: "03",
    label: "The pacing",
    pick: trim(decision.pacing.split(":")[0] || decision.pacing, 60),
    why: trim(decision.pacing, 200),
  },
]

export function Opinions() {
  return (
    <section
      id="opinions"
      className="relative bg-background py-24 lg:py-32"
    >
      <div className="mx-auto max-w-7xl px-6 lg:px-10">
        <div className="mb-12 max-w-2xl">
          <p className="text-label text-primary">The agent has opinions</p>
          <h2 className="mt-3 text-display-lg text-foreground sm:text-[44px]">
            What it actually <span className="italic">decided.</span>
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            A snapshot from a real run on a Paris listing. Three picks the agent
            made — and why. This is the rationale rail you’ll see live during your
            own render.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <AnimatedList>
            {CARDS.map((card) => (
              <OpinionCardView key={card.index} card={card} />
            ))}
          </AnimatedList>
        </div>
      </div>
    </section>
  )
}

function OpinionCardView({ card }: { card: OpinionCard }) {
  return (
    <Card
      className={cn(
        "flex h-full flex-col gap-4 p-6 transition-colors hover:bg-accent/40",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {card.label} · {card.index} of 03
        </span>
        <span aria-hidden className="h-1 w-1 rounded-full bg-primary" />
      </div>
      <p className="text-display-md font-display leading-tight text-foreground">
        “{card.pick}”
      </p>
      <div className="mt-auto border-l border-primary pl-3 pt-1">
        <span className="text-sm leading-relaxed text-muted-foreground">
          <TextReveal>{card.why}</TextReveal>
        </span>
      </div>
    </Card>
  )
}
