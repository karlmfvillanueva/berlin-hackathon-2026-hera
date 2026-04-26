import { useRef, useState } from "react"
import { Play } from "lucide-react"

import { Ripple } from "@/components/ui/magic/ripple"
import { cn } from "@/lib/utils"

export function Watch() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [playing, setPlaying] = useState(false)

  const start = () => {
    const video = videoRef.current
    if (!video) return
    setPlaying(true)
    void video.play().catch(() => setPlaying(false))
  }

  return (
    <section
      id="watch"
      className="relative py-24 lg:py-32"
      style={{ backgroundColor: "#F4F2EC" }}
    >
      <div className="mx-auto max-w-6xl px-6 lg:px-10">
        <div className="mb-10 max-w-2xl">
          <p className="text-label text-primary">See it in action</p>
          <h2 className="mt-3 text-display-lg text-foreground sm:text-[44px]">
            From URL to short film, in <span className="font-mono">60</span> seconds.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            A click-to-play walkthrough: paste a real listing, watch the agent
            decide, end on the rendered output. No edits, no cheats.
          </p>
        </div>

        <div className="relative overflow-hidden rounded-xl border border-border bg-[#14201B] shadow-[0_30px_120px_-30px_rgba(0,0,0,0.45)]">
          <div className="relative aspect-video">
            <video
              ref={videoRef}
              src="/videos/argus-demo.mp4"
              poster="/videos/argus-demo-poster.jpg"
              controls={playing}
              preload="metadata"
              playsInline
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
              className="h-full w-full object-cover"
            />
            {!playing && (
              <button
                type="button"
                onClick={start}
                className={cn(
                  "absolute inset-0 grid place-items-center",
                  "transition-opacity duration-300",
                  "bg-[radial-gradient(ellipse_at_center,_rgba(20,32,27,0.05),_rgba(20,32,27,0.55))]",
                  "hover:bg-[radial-gradient(ellipse_at_center,_rgba(20,32,27,0),_rgba(20,32,27,0.65))]",
                )}
                aria-label="Play demo video"
              >
                <Ripple
                  mainCircleSize={140}
                  mainCircleOpacity={0.22}
                  numCircles={5}
                  color="#F94B12"
                />
                <span className="relative z-10 inline-flex h-20 w-20 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-[0_10px_40px_rgba(249,75,18,0.5)] ring-1 ring-white/20 transition-transform group-hover:scale-105">
                  <Play className="lucide ml-1 h-7 w-7 fill-current" />
                </span>
              </button>
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-x-8 gap-y-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          <span><span className="text-foreground">00:00</span> · Paste URL</span>
          <span><span className="text-foreground">00:12</span> · Agent thinks</span>
          <span><span className="text-foreground">00:38</span> · Render begins</span>
          <span><span className="text-foreground">00:52</span> · Final film</span>
        </div>
      </div>
    </section>
  )
}
