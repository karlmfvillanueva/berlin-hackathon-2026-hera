import { Link } from "react-router-dom"

import { BrandMark } from "@/components/BrandMark"
import { Footer } from "@/components/landing/Footer"

/**
 * Datenschutzerklärung nach DSGVO / TMG.
 *
 * TODO vor öffentlichem Deployment:
 *   1. Verantwortlichen-Daten in Impressum + hier (Block 1) ergänzen.
 *   2. Hosting-Provider-Auftragsverarbeitungsvertrag (AVV) abschließen
 *      (Railway, Vercel, Supabase EU-Region usw.) und hier referenzieren.
 *   3. Cookie-Banner / Consent-Layer einbauen, falls über strikt notwendige
 *      Cookies hinaus weitere Tools (Analytics, Marketing) hinzukommen — derzeit
 *      verarbeiten wir nur Auth-Cookies und keine Tracker.
 *   4. Wenn YouTube-Veröffentlichung produktiv genutzt wird: Hinweis verfeinern,
 *      welche Daten Google erhält (siehe Block "YouTube Data API").
 *
 * Vorlagen-Cross-Check: https://datenschutz-generator.de — nutzungspflichtig
 * für kommerzielle Domains, gut für Plausibilitätsprüfung.
 */
export function Datenschutz() {
  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <LegalHeader />

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-16 lg:py-24">
        <p className="text-label text-primary">Rechtliches</p>
        <h1 className="mt-3 font-display text-display-lg leading-tight sm:text-[44px]">
          Datenschutzerklärung
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
          Diese Erklärung informiert über Art, Umfang und Zweck der Verarbeitung
          personenbezogener Daten innerhalb der Argus-Webanwendung. Argus ist
          ein Hackathon-Projekt im Rahmen des Berlin Tech Europe Hackathon 2026.
          Maßgeblich sind die DSGVO und das BDSG.
        </p>

        <Section title="1. Verantwortlicher">
          <p className="text-sm text-foreground">
            [Vollständiger Name]
            <br />
            [Straße und Hausnummer]
            <br />
            [PLZ] [Stadt], Deutschland
            <br />
            E-Mail:{" "}
            <span className="text-primary">[kontakt@deine-domain.de]</span>
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Vollständige Anbieter-Kennzeichnung siehe{" "}
            <Link to="/impressum" className="text-primary hover:underline">
              Impressum
            </Link>
            .
          </p>
        </Section>

        <Section title="2. Server-Logfiles">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Beim Aufruf der Webseite verarbeitet unser Hosting-Provider
            automatisch Informationen, die Ihr Browser übermittelt: IP-Adresse,
            Datum und Uhrzeit der Anfrage, übertragene Datenmenge, abgerufene
            Seite, Referer-URL und Browser-Kennung. Diese Daten dienen
            ausschließlich der technischen Bereitstellung und Sicherheit
            (Art. 6 Abs. 1 lit. f DSGVO — berechtigtes Interesse) und werden
            nach spätestens 30 Tagen anonymisiert oder gelöscht.
          </p>
        </Section>

        <Section title="3. Cookies und Local Storage">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Wir setzen ausschließlich technisch notwendige Cookies und
            Local-Storage-Einträge ein, um Ihre Anmeldung über Supabase Auth zu
            erhalten. Es findet kein Tracking, kein Profiling und keine Weitergabe
            an Dritte zu Werbezwecken statt. Eine Einwilligung nach § 25 Abs. 1
            TTDSG ist daher nicht erforderlich (§ 25 Abs. 2 Nr. 2 TTDSG).
          </p>
        </Section>

        <Section title="4. Nutzerkonto und Authentifizierung (Supabase)">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Für die Erstellung und Speicherung Ihrer generierten Videos nutzen
            wir Supabase (Auth + Postgres). Anbieter ist die Supabase Inc.,
            970 Toa Payoh North #07-04, Singapur — die EU-Daten werden in der
            Region <span className="font-mono">eu-central-1</span> (Frankfurt)
            gehostet. Verarbeitete Daten: E-Mail, Passwort-Hash, OAuth-Token,
            Listing-URL, Agent-Entscheidungen, Video-Metadaten. Rechtsgrundlage:
            Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung). Mit Supabase besteht
            ein Auftragsverarbeitungsvertrag nach Art. 28 DSGVO.
          </p>
        </Section>

        <Section title="5. Externe Dienste / Auftragsverarbeiter">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Zur Bereitstellung der Funktionalität greifen wir auf folgende
            Dienste zurück. Die Datenübermittlung in die USA erfolgt jeweils auf
            Grundlage des EU-US Data Privacy Frameworks bzw. von
            EU-Standardvertragsklauseln gemäß Art. 46 DSGVO.
          </p>
          <Field label="Hera Video API">
            Die von Ihnen angefragten Listing-Daten und Foto-URLs sowie der
            generierte Prompt werden zur Video-Erzeugung an die Hera Video API
            (Hera Inc., USA) übermittelt. Rechtsgrundlage: Art. 6 Abs. 1 lit. b
            DSGVO. Datenschutz: <a className="text-primary hover:underline" href="https://hera.video/privacy" target="_blank" rel="noreferrer noopener">hera.video/privacy</a>
          </Field>
          <Field label="Google Vertex AI / Gemini 2.5 Pro">
            Listing-Texte, Foto-URLs und Strukturdaten werden an Vertex AI
            (Google LLC, USA / Google Ireland Ltd., EU) für die Klassifikations-
            und Bewertungs-Pipeline übermittelt. Inhalte werden nicht zum
            Training genutzt (Vertex-AI-Standardvertrag).
          </Field>
          <Field label="Google YouTube Data API (optional, nur bei Verbindung)">
            Wenn Sie freiwillig Ihren YouTube-Kanal verbinden, übertragen wir
            das gerenderte MP4 plus Titel/Beschreibung an die YouTube Data API
            v3 (Google LLC, USA). OAuth-Refresh-Tokens werden verschlüsselt in
            Supabase gespeichert. Sie können die Verbindung jederzeit über das
            Dashboard widerrufen — Tokens werden dabei serverseitig gelöscht.
          </Field>
          <Field label="Hosting (Railway)">
            Server-seitige Anwendung läuft auf Railway (USA / EU-Region).
            Auftragsverarbeitung gemäß DPA des Anbieters.
          </Field>
        </Section>

        <Section title="6. KI-generierte Inhalte">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Argus erzeugt redaktionelle Entscheidungen (Hook, Persona, Pacing
            etc.) und Video-Inhalte mithilfe großer Sprach- und Vision-Modelle.
            Diese Ausgaben können fehlerhaft sein, geschützte Marken zeigen oder
            urheberrechtlich relevante Bildelemente enthalten. Sie sind als
            Nutzer:in dafür verantwortlich, die generierten Videos vor einer
            Veröffentlichung zu prüfen.
          </p>
        </Section>

        <Section title="7. Ihre Rechte (Art. 15-22 DSGVO)">
          <ul className="list-inside list-disc space-y-1.5 text-sm text-muted-foreground">
            <li>Recht auf Auskunft (Art. 15 DSGVO)</li>
            <li>Recht auf Berichtigung (Art. 16 DSGVO)</li>
            <li>Recht auf Löschung (Art. 17 DSGVO)</li>
            <li>Recht auf Einschränkung der Verarbeitung (Art. 18 DSGVO)</li>
            <li>Recht auf Datenübertragbarkeit (Art. 20 DSGVO)</li>
            <li>Recht auf Widerspruch (Art. 21 DSGVO)</li>
            <li>
              Recht auf jederzeitigen Widerruf erteilter Einwilligungen (Art. 7
              Abs. 3 DSGVO) — wirkt nur für die Zukunft.
            </li>
            <li>
              Recht auf Beschwerde bei einer Aufsichtsbehörde (Art. 77 DSGVO).
              Zuständig ist die Datenschutzbehörde Ihres Wohnsitzbundeslandes.
            </li>
          </ul>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Anfragen bitte formlos an{" "}
            <span className="text-primary">[kontakt@deine-domain.de]</span>.
          </p>
        </Section>

        <Section title="8. Speicherdauer">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Wir speichern personenbezogene Daten nur so lange, wie es für die
            Zweckerreichung notwendig ist oder gesetzliche Aufbewahrungsfristen
            es vorschreiben. Nutzerkonten und zugehörige Videos werden auf Ihren
            Wunsch gelöscht. Server-Logfiles werden nach 30 Tagen anonymisiert.
          </p>
        </Section>

        <Section title="9. Änderungen dieser Datenschutzerklärung">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Wir behalten uns vor, diese Erklärung anzupassen, wenn sich die
            Rechtslage oder unsere Verarbeitungstätigkeiten ändern. Es gilt
            jeweils die hier veröffentlichte Fassung.
          </p>
        </Section>

        <p className="mt-12 text-mono-xs text-muted-foreground">
          Stand: 2026-04-26 · Hackathon-Projekt — vor produktivem Einsatz durch
          juristische Prüfung validieren.
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
      <div className="mt-0.5 text-sm leading-relaxed text-foreground">{children}</div>
    </div>
  )
}
