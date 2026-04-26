import { useEffect, useState } from "react"
import { ChevronRight } from "lucide-react"

import { ArchitectureDiagram } from "@/components/landing/ArchitectureDiagram"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface Stage {
  num: string
  name: string
  desc: string
}

const STAGES: Stage[] = [
  { num: "01", name: "Scrape", desc: "Photos, reviews, location, price." },
  { num: "02", name: "Read", desc: "ICP · location feel · review themes." },
  { num: "03", name: "See", desc: "Vision-rank the top 3 photos." },
  { num: "04", name: "Decide", desc: "Hook · vibes · pacing · angle." },
  { num: "05", name: "Render", desc: "Hera prompt + reference assets." },
]

function PipelineRow() {
  // Drive a single pulsing chevron index that walks 0 → STAGES.length-1.
  const [active, setActive] = useState(0)
  useEffect(() => {
    const id = setInterval(() => {
      setActive((i) => (i + 1) % (STAGES.length - 1))
    }, 1200)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="grid grid-cols-1 items-stretch gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr] md:gap-3">
      {STAGES.map((stage, i) => (
        <span key={stage.num} className="contents">
          <Card className="flex flex-col items-start gap-2 p-5 transition-shadow hover:shadow-md">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary">
              {stage.num}
            </span>
            <span className="text-display-md font-display leading-tight text-foreground">
              {stage.name}
            </span>
            <span className="text-xs leading-relaxed text-muted-foreground">
              {stage.desc}
            </span>
          </Card>
          {i < STAGES.length - 1 ? (
            <span
              aria-hidden
              className={cn(
                "hidden self-center justify-self-center transition-all duration-300 md:block",
                i === active ? "scale-125 text-primary" : "scale-100 text-muted-foreground/40",
              )}
            >
              <ChevronRight className="lucide h-5 w-5" strokeWidth={2} />
            </span>
          ) : null}
        </span>
      ))}
    </div>
  )
}

export function Pipeline() {
  return (
    <section id="pipeline" className="relative bg-background py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-10">
        <div className="mb-12 max-w-2xl">
          <p className="text-label text-primary">How it thinks</p>
          <h2 className="mt-3 text-display-lg text-foreground sm:text-[44px]">
            Five passes <span className="italic">before</span> a single frame is rendered.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Most “AI video” tools jump straight from prompt to pixel. We don’t.
            The agent runs five specialist passes — each forming an opinion the
            next one inherits.
          </p>
        </div>

        <PipelineRow />

        <div className="mt-20">
          <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
            <div>
              <p className="text-label text-primary">Under the hood</p>
              <h3 className="mt-3 text-display-md font-display text-foreground sm:text-[28px]">
                Open the system. <span className="italic">Layer by layer.</span>
              </h3>
            </div>
            <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
              Every node below ran on the real Paris listing whose film is at the
              top of this page. Open any pass to see what came in, what came out,
              and which model decided it.
            </p>
          </div>

          <ArchitectureDiagram />
        </div>
      </div>
    </section>
  )
}
