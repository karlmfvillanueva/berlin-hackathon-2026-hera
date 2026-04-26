import { UrlField } from "@/components/landing/UrlField"

export function CtaSection() {
  return (
    <section
      id="cta"
      className="relative isolate overflow-hidden text-white"
      style={{ backgroundColor: "#14201B" }}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 animate-hero-mesh"
        style={{
          backgroundImage: [
            "radial-gradient(circle at 80% 20%, rgba(249,75,18,0.32), transparent 50%)",
            "radial-gradient(circle at 20% 80%, rgba(45,74,62,0.55), transparent 55%)",
          ].join(","),
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.10] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='240' height='240' filter='url(%23n)' opacity='0.5'/></svg>\")",
        }}
      />

      <div className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-6 py-24 text-center lg:py-32">
        <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-white/70 backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          Free demo
        </span>

        <h2 className="text-display-xl font-display sm:text-[56px] lg:text-[64px] lg:leading-[1.04]">
          Drop a listing.
          <br />
          <span className="italic text-primary">Watch it decide.</span>
        </h2>

        <p className="max-w-md text-base leading-relaxed text-white/70">
          It takes about ninety seconds. You’ll see the agent’s rationale rail
          unfold in real time — then keep the rendered video.
        </p>

        <UrlField variant="cta" ctaLabel="Make my film" className="mt-2 mx-auto" />

        <p className="text-[11px] uppercase tracking-[0.18em] text-white/45">
          No signup · Hera-rendered · MP4 download
        </p>
      </div>
    </section>
  )
}
