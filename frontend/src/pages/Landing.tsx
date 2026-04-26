import { Nav } from "@/components/landing/Nav"
import { Hero } from "@/components/landing/Hero"
import { Opinions } from "@/components/landing/Opinions"
import { Watch } from "@/components/landing/Watch"
import { Pipeline } from "@/components/landing/Pipeline"
import { CtaSection } from "@/components/landing/CtaSection"
import { Footer } from "@/components/landing/Footer"

export function Landing() {
  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <Nav />
      <main className="flex flex-1 flex-col">
        <Hero />
        <Opinions />
        <Watch />
        <Pipeline />
        <CtaSection />
      </main>
      <Footer />
    </div>
  )
}
