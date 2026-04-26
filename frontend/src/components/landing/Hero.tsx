import { BorderBeam } from "@/components/ui/magic/border-beam"
import { WordRotate } from "@/components/ui/magic/word-rotate"
import { UrlField } from "@/components/landing/UrlField"

const ROTATING_WORDS = ["opinions included.", "taste included.", "an angle, included."]

export function Hero() {
  return (
    <section
      id="hero"
      className="relative isolate overflow-hidden text-white"
      style={{ backgroundColor: "#14201B" }}
    >
      {/* gradient mesh — animated drift */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 animate-hero-mesh"
        style={{
          backgroundImage: [
            "radial-gradient(circle at 18% 25%, rgba(249,75,18,0.32), transparent 50%)",
            "radial-gradient(circle at 82% 78%, rgba(45,74,62,0.55), transparent 55%)",
            "radial-gradient(circle at 50% 100%, rgba(249,75,18,0.10), transparent 60%)",
          ].join(","),
        }}
      />
      {/* hairline grain veil */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.12] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='240' height='240' filter='url(%23n)' opacity='0.5'/></svg>\")",
        }}
      />

      <div className="mx-auto grid max-w-7xl gap-10 px-6 pb-20 pt-24 lg:grid-cols-[1.15fr_1fr] lg:gap-14 lg:px-10 lg:pt-32">
        {/* Left column */}
        <div className="flex flex-col items-start justify-center gap-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-white/80 backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            A motion graphics agent for boutique hosts
          </span>

          <h1 className="text-display-xl font-display text-white sm:text-[56px] lg:text-[64px] lg:leading-[1.04]">
            Listings that move,
            <br />
            <span className="italic text-primary">
              <WordRotate words={ROTATING_WORDS} />
            </span>
          </h1>

          <p className="max-w-md text-base leading-relaxed text-white/70">
            Drop an Airbnb URL. Our agent watches the photos, reads the reviews,
            finds your guest, and directs a 30-second short film about your
            place — with a stance on what to show first.
          </p>

          <UrlField variant="hero" ctaLabel="Make my film" className="mt-2" />

          <div className="mt-3 flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-white/45">
            <span>~90s end-to-end</span>
            <span aria-hidden>·</span>
            <span>Hera-rendered</span>
            <span aria-hidden>·</span>
            <span>Free demo</span>
          </div>
        </div>

        {/* Right column — hero video in smartphone frame */}
        <div className="flex items-center justify-center py-4">
          <SmartphoneFrame>
            <video
              src="/videos/argus-hero.mp4"
              poster="/videos/argus-hero-poster.jpg"
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              className="absolute inset-0 h-full w-full object-cover"
            />
          </SmartphoneFrame>
        </div>
      </div>
    </section>
  )
}

/**
 * Minimal Quiet-Luxury smartphone mockup. Outer is a near-black rounded slab
 * with a soft inner highlight; the inner screen carries the 9:16 video. A
 * Dynamic-Island-style pill sits over the top of the screen. Coral BorderBeam
 * runs along the outer chassis to keep the hero brand tied to the phone.
 */
function SmartphoneFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative mx-auto w-full max-w-[320px] [filter:drop-shadow(0_30px_80px_rgba(0,0,0,0.55))]">
      {/* Subtle outer coral glow — strengthens the social-warm association */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-6 -z-10 rounded-[3.5rem] opacity-60 blur-2xl"
        style={{
          background:
            "radial-gradient(60% 60% at 50% 50%, rgba(249,75,18,0.28), transparent 70%)",
        }}
      />

      {/* Outer chassis */}
      <div
        className="relative overflow-hidden rounded-[2.75rem] p-3"
        style={{
          background:
            "linear-gradient(160deg, #1a2421 0%, #0a1310 55%, #1a2421 100%)",
          boxShadow:
            "inset 0 0 0 1px rgba(255,255,255,0.05), inset 0 1px 0 rgba(255,255,255,0.08)",
        }}
      >
        {/* Inner screen — modern iPhone aspect (~9:19.5). The 9:16 video uses
            object-cover and crops ~11% off the top + bottom; hero content is
            center-framed so this is invisible in practice. */}
        <div className="relative aspect-[9/19.5] overflow-hidden rounded-[2rem] bg-black ring-1 ring-inset ring-white/10">
          {children}

          {/* Dynamic Island */}
          <div
            aria-hidden
            className="absolute left-1/2 top-2.5 z-10 flex h-[22px] w-[88px] -translate-x-1/2 items-center justify-end gap-1 rounded-full bg-black px-3"
          >
            <span className="h-1 w-1 rounded-full bg-neutral-700" />
          </div>

          {/* Glass sheen — diagonal highlight on the screen */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              backgroundImage:
                "linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0) 35%, rgba(255,255,255,0) 100%)",
            }}
          />
        </div>

        {/* Side button hairlines — subtle, just enough to read as a phone */}
        <span
          aria-hidden
          className="absolute -left-[3px] top-[26%] h-10 w-[3px] rounded-l-sm bg-[#0a1310]"
        />
        <span
          aria-hidden
          className="absolute -left-[3px] top-[39%] h-14 w-[3px] rounded-l-sm bg-[#0a1310]"
        />
        <span
          aria-hidden
          className="absolute -right-[3px] top-[33%] h-16 w-[3px] rounded-r-sm bg-[#0a1310]"
        />

        <BorderBeam size={140} duration={9} colorFrom="#F94B12" colorTo="#FFD3BF" />
      </div>
    </div>
  )
}
