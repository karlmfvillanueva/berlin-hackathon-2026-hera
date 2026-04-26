import { Link } from "react-router-dom"

import { BrandMark } from "@/components/BrandMark"
import { Footer } from "@/components/landing/Footer"

/**
 * Impressum nach § 5 TMG (Telemediengesetz) und § 18 MStV.
 *
 * TODO vor öffentlichem Deployment in Deutschland:
 *   1. Echte Operator-Angaben (Name, Anschrift, E-Mail, ggf. Telefon) einsetzen.
 *   2. Falls als Unternehmen / UG / GmbH betrieben: Handelsregister, USt-IdNr.,
 *      Vertretungsberechtigte ergänzen.
 *   3. Falls journalistisch-redaktionelle Inhalte: § 18 Abs. 2 MStV — verant-
 *      wortliche Person nennen.
 *
 * Vorlagen-Generator als Cross-Check: https://www.e-recht24.de/impressum-generator.html
 */
export function Impressum() {
  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <LegalHeader />

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16 lg:py-24">
        <p className="text-label text-primary">Rechtliches</p>
        <h1 className="mt-3 font-display text-display-lg leading-tight sm:text-[44px]">
          Impressum
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
          Angaben gemäß § 5 TMG. Argus ist ein Hackathon-Projekt im Rahmen des
          Berlin Tech Europe Hackathon 2026 (Hera-Track).
        </p>

        <Section title="Diensteanbieter">
          <Field label="Name">[Vollständiger Name des Verantwortlichen]</Field>
          <Field label="Anschrift">
            [Straße und Hausnummer]
            <br />
            [PLZ] [Stadt]
            <br />
            Deutschland
          </Field>
        </Section>

        <Section title="Kontakt">
          <Field label="E-Mail">[kontakt@deine-domain.de]</Field>
          <Field label="Telefon (optional)">[+49 …]</Field>
        </Section>

        <Section title="Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV">
          <p className="text-sm text-foreground">
            [Vollständiger Name], [Anschrift wie oben]
          </p>
        </Section>

        <Section title="Haftung für Inhalte">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Als Diensteanbieter sind wir gemäß § 7 Abs. 1 TMG für eigene Inhalte
            auf diesen Seiten nach den allgemeinen Gesetzen verantwortlich. Nach
            §§ 8 bis 10 TMG sind wir als Diensteanbieter jedoch nicht ver-
            pflichtet, übermittelte oder gespeicherte fremde Informationen zu
            überwachen oder nach Umständen zu forschen, die auf eine rechts-
            widrige Tätigkeit hinweisen. Verpflichtungen zur Entfernung oder
            Sperrung der Nutzung von Informationen nach den allgemeinen Gesetzen
            bleiben hiervon unberührt. Eine diesbezügliche Haftung ist jedoch
            erst ab dem Zeitpunkt der Kenntnis einer konkreten Rechtsverletzung
            möglich. Bei Bekanntwerden von entsprechenden Rechtsverletzungen
            werden wir diese Inhalte umgehend entfernen.
          </p>
        </Section>

        <Section title="Haftung für Links">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Unser Angebot enthält Links zu externen Webseiten Dritter, auf deren
            Inhalte wir keinen Einfluss haben. Deshalb können wir für diese
            fremden Inhalte auch keine Gewähr übernehmen. Für die Inhalte der
            verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber
            der Seiten verantwortlich. Die verlinkten Seiten wurden zum Zeit-
            punkt der Verlinkung auf mögliche Rechtsverstöße überprüft.
            Rechtswidrige Inhalte waren zum Zeitpunkt der Verlinkung nicht
            erkennbar. Bei Bekanntwerden von Rechtsverletzungen werden wir
            derartige Links umgehend entfernen.
          </p>
        </Section>

        <Section title="Urheberrecht">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Die durch die Seitenbetreiber erstellten Inhalte und Werke auf
            diesen Seiten unterliegen dem deutschen Urheberrecht. Die
            Vervielfältigung, Bearbeitung, Verbreitung und jede Art der
            Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der
            schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.
            Bilder von Airbnb-Inseraten, die im Demo-Modus verarbeitet werden,
            verbleiben im Eigentum der jeweiligen Rechteinhaber.
          </p>
        </Section>

        <Section title="EU-Streitschlichtung">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Die Europäische Kommission stellt eine Plattform zur
            Online-Streitbeilegung (OS) bereit:{" "}
            <a
              href="https://ec.europa.eu/consumers/odr"
              target="_blank"
              rel="noreferrer noopener"
              className="text-primary underline-offset-4 hover:underline"
            >
              https://ec.europa.eu/consumers/odr
            </a>
            . Wir sind nicht bereit oder verpflichtet, an Streitbeilegungs-
            verfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.
          </p>
        </Section>

        <p className="mt-12 text-mono-xs text-muted-foreground">
          Stand: 2026-04-26 · Letzte Aktualisierung mit Deployment.
        </p>
      </main>

      <Footer />
    </div>
  )
}

function LegalHeader() {
  return (
    <header className="border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-10">
        <Link to="/" className="text-foreground hover:opacity-80">
          <BrandMark />
        </Link>
        <Link
          to="/"
          className="text-body-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          ← Zur Startseite
        </Link>
      </div>
    </header>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10 border-t border-border pt-6">
      <h2 className="font-display text-display-md leading-tight text-foreground">
        {title}
      </h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-l border-primary/40 pl-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 text-sm text-foreground">{children}</div>
    </div>
  )
}
