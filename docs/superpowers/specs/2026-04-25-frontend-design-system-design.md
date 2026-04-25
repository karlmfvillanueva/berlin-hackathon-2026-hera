# Frontend Design System — Quiet Luxury with Hera-Wink

**Status:** Draft — pending user review
**Date:** 2026-04-25
**Branch:** `feat/design-system`
**Author:** Joscha + Claude
**Replaces:** the de-facto styling on `main` (~17 lines of CSS, no design system)

---

## 1. Purpose

Define a coherent, opinionated visual language for the frontend so that:
- Every existing component (`Header`, `UrlInput`, `StatusRow`, `VideoPlayer`, `RationaleRail`, `AttributeCard`, `ErrorState`) reads as part of one product.
- Future components can be built quickly without re-deciding palette / type / spacing each time.
- The product looks credible to two distinct audiences in the same demo: **Hera judges** (subconscious affinity to their brand) and **boutique Airbnb hosts** (premium hospitality codes).

This spec defines the system. The implementation plan is a separate document (next step via writing-plans skill).

## 2. Positioning

**Vibe:** Quiet Luxury. References: Aman Resorts, Soho House, Ace Hotel, Cereal Magazine, Aesop.

The system is **restrained, magazine-editorial, light-only**. Generous whitespace, hairline borders instead of shadows, serif display headlines paired with sans body, single saturated accent used sparingly.

**The Hera-Wink:** the primary CTA color is borrowed from `hera.video` (vibrant coral `#F94B12`). It appears only on the single most important action per screen ("Generate Video", "Download"). Everywhere else — labels, links, badges, focus rings, secondary buttons, vibe-chips — uses our forest green (`#2D4A3E`).

The wink rationale: judges from the Hera team unconsciously register "this product is in our world" the moment they see the coral button, while the rest of the system signals independent taste and a clear customer-fit (boutique hosts).

**Out:** dark mode (deferred; the shadcn CSS-variable structure used here is dual-ready — adding dark later means defining a `.dark { ... }` block with new values, no structural changes), marketing/landing page (separate spec when needed), motion graphics (not our surface — that's Hera's job), custom illustration system.

## 3. Library Stack

| Layer | Choice | Why |
|---|---|---|
| CSS framework | Tailwind v4 (already installed) | Existing stack, atomic, ships with `@theme` for token definition. |
| Component library | **shadcn/ui** | Copy-owned components (no runtime dep), CSS-variable tokens, plays natively with Tailwind v4. Industry-standard for React+TS+Tailwind. |
| Icons | **Lucide React** | shadcn default, restrained line-icon style fits Quiet Luxury. |
| Custom components | **magic mcp** (`mcp__magic__21st_magic_component_builder`) | When shadcn doesn't have what we need (e.g. `StatusRow` step-indicator, vibe-chip group). Generates components inspired by 21st.dev that match our tokens. |
| Fonts | Google Fonts: **Playfair Display** (display) + **Inter** (body) + **JetBrains Mono** (numerals/codes) | Free, served via `<link>` in `index.html` for fastest first paint. |

## 4. Color Tokens

Light theme only (Phase 1). All values defined as CSS variables in `index.css`, surfaced via `@theme` for Tailwind.

### 4.1 Semantic palette (shadcn naming)

| Token | Hex | HSL | Role |
|---|---|---|---|
| `--background` | `#FAFAF7` | `48 33% 98%` | Page background — warm bone |
| `--foreground` | `#0A0A0A` | `0 0% 4%` | Primary text — near-black |
| `--card` | `#FFFFFF` | `0 0% 100%` | Card surface — pure white on bone bg |
| `--card-foreground` | `#0A0A0A` | `0 0% 4%` | Text on cards |
| `--popover` | `#FFFFFF` | `0 0% 100%` | Popover/menu surface |
| `--popover-foreground` | `#0A0A0A` | `0 0% 4%` | Text on popovers |
| `--primary` | `#F94B12` | `15 95% 53%` | **Hera-wink coral.** Primary CTA only |
| `--primary-foreground` | `#FFFFFF` | `0 0% 100%` | Text on coral CTA |
| `--secondary` | `#2D4A3E` | `155 24% 23%` | Forest. Labels, links, badge accents, focus ring |
| `--secondary-foreground` | `#FAFAF7` | `48 33% 98%` | Text on forest |
| `--muted` | `#F0EDE4` | `42 25% 92%` | Subtle bg (badges, hover, secondary surfaces) |
| `--muted-foreground` | `#6B6963` | `40 4% 40%` | Secondary text — warm gray |
| `--accent` | `#F0EDE4` | `42 25% 92%` | Same as muted; used for hover bg |
| `--accent-foreground` | `#0A0A0A` | `0 0% 4%` | Text on accent |
| `--destructive` | `#B91C1C` | `0 73% 42%` | Errors. Deep, not bright |
| `--destructive-foreground` | `#FFFFFF` | `0 0% 100%` | Text on destructive |
| `--border` | `#E8E5DD` | `42 19% 88%` | Hairline borders, dividers |
| `--input` | `#E8E5DD` | `42 19% 88%` | Input border (same as border) |
| `--ring` | `#2D4A3E` | `155 24% 23%` | Focus ring — forest |

### 4.2 Token usage rules

- **Coral (`primary`) is precious.** One per screen, on the most important action. Not on multiple buttons. Not on labels. Not on badges. Not on hover. Period.
- **Forest (`secondary`) is the workhorse accent.** Use it for: section labels (uppercase tracking-wide), section divider headlines, vibe-chip background when "active", badge text, link color, focus rings, the brand-mark dot in the logo.
- **Muted (`#F0EDE4`)** is for secondary surfaces: badge backgrounds, button-hover backgrounds, subtle stage areas. Never for primary surfaces.
- **Borders are hairline.** 1px solid `--border`. No 2px borders. No box-shadows on hover (use a slight bg tint instead, or a border-color shift).
- **Type contrast on `--background`:** primary text uses `--foreground`. Secondary text uses `--muted-foreground`. Don't introduce new grays.

## 5. Typography

### 5.1 Font families

```css
--font-display: 'Playfair Display', Georgia, serif;       /* h1, hero text, card titles */
--font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;  /* body, UI, buttons */
--font-mono: 'JetBrains Mono', ui-monospace, monospace;   /* numerals, timestamps, codes */
```

Playfair carries weights 400/500/600. Inter carries 400/500/600/700. JetBrains Mono carries 400.

### 5.2 Type scale

| Class | Size / line-height | Family | Weight | Tracking | Use |
|---|---|---|---|---|---|
| `text-display-xl` | 48px / 1.05 | Playfair | 500 | -0.015em | Hero listing title |
| `text-display-lg` | 36px / 1.1 | Playfair | 500 | -0.015em | Section heads |
| `text-display-md` | 26px / 1.15 | Playfair | 500 | -0.01em | Card titles |
| `text-h2` | 20px / 1.3 | Inter | 600 | -0.005em | UI section heads |
| `text-h3` | 16px / 1.4 | Inter | 600 | normal | Subsection heads |
| `text-body` | 14px / 1.55 | Inter | 400 | normal | Body |
| `text-body-sm` | 12px / 1.5 | Inter | 400 | normal | Captions, helper text |
| `text-label` | 10px / 1.2 | Inter | 600 | 0.18em uppercase | Section labels ("LISTING", "VIBES") |
| `text-mono-xs` | 11px / 1.4 | JetBrains Mono | 400 | normal | Timestamps, durations ("15 SEC") |
| `text-rationale` | 16px / 1.45 | Playfair | 400 | -0.005em | Rationale-rail body (the agent's voice) |

### 5.3 Type usage rules

- **The agent speaks in Playfair.** Hook, pacing, angle, background — these are the editorial voice. Render them in `text-rationale` (Playfair 400). It signals "this is a written take", not "this is system text".
- **The UI speaks in Inter.** Buttons, inputs, nav, status, errors.
- **Labels are loud-quiet.** `text-label` (10px, 600 weight, 0.18em letter-spacing, uppercase, `--muted-foreground`). Above every grouping. They establish the magazine grid.
- **Numerals get mono.** Durations, timestamps, percentages. JetBrains Mono adds a "considered" feel and tabularizes alignments.
- **Italic = whisper.** Use italic in body for the agent's emphasis (e.g. *"that's the one shot that earns the stop-scroll"*). Sparingly.

## 6. Spacing & Layout

### 6.1 Spacing scale

Tailwind defaults (4px base). The system uses these primarily:
- `gap-2` (8px), `gap-3` (12px), `gap-4` (16px) — within components
- `gap-6` (24px), `gap-7` (28px) — between component groups
- `gap-12` (48px) — between sections

**Density: comfortable.** Card padding `p-6` (24px). Page container padding `py-12 px-6` (48px V, 24px H). Don't compact card padding below `p-4`.

### 6.2 Layout primitives

- **Page container:** `max-w-6xl mx-auto px-6 py-12` (1152px max, 48px V padding).
- **Two-column on result page:** `grid-cols-[1.4fr_1fr] gap-7` collapses to `grid-cols-1 gap-6` below `md` (768px).
- **Breakpoints:** Tailwind defaults — `sm 640`, `md 768`, `lg 1024`, `xl 1280`.

## 7. Border Radius

```css
--radius-sm: 6px;     /* badges, chips, mono pills */
--radius-md: 8px;     /* inputs, small buttons */
--radius-lg: 12px;    /* cards */
--radius-xl: 14px;    /* outermost containers */
--radius-full: 999px; /* primary buttons, avatars, status pills */
```

Mapping to Tailwind: extend the theme so `rounded` (default) → 8px, `rounded-lg` → 12px, `rounded-full` stays at 9999px.

## 8. Elevation

**No shadows by default.** The system is a flat magazine. Use border + bg-tint to create depth.

Two narrow exceptions:
- The whole result-page card-container may use `shadow-[0_24px_48px_-24px_rgba(0,0,0,0.08)]` to lift it from the page (anchors the eye).
- Popovers / menus / dropdowns get the shadcn default popover shadow.

Hover states do **not** add shadows. Hover = `bg-accent` (the muted bone) + transition 150ms.

## 9. Iconography

- **Lucide React** — `lucide-react@latest`. Stroke weight 1.5 (override default).
- Sizes: 16px (inline with body), 20px (inline with h3), 24px (inline with display).
- Color: inherits text color (`currentColor`).
- No filled icons. Line only — matches the Aman/Cereal aesthetic.

## 10. Motion

- **Default transition:** `150ms cubic-bezier(0.4, 0, 0.2, 1)`.
- **Hover, focus, state changes:** 150ms.
- **Page transitions / skeletons:** 250ms.
- **No bounces, no scale-pops.** Quiet Luxury moves slowly.

Tailwind utility: `transition-colors duration-150` is the default for most interactive elements.

## 10a. Accessibility Minimums

- **Contrast:** body text on `--background` (`#0A0A0A` on `#FAFAF7`) meets WCAG AAA. Coral primary button (`#FFFFFF` on `#F94B12`) meets AA for ≥14px text. Forest on bone (`#2D4A3E` on `#FAFAF7`) meets AAA. Don't introduce new mid-grays without checking contrast.
- **Focus rings** use `--ring` (forest), 2px, offset 2px. Always visible — never `outline: none` without a replacement.
- **Hit targets** ≥ 40px tall for any interactive element.
- **Don't rely on color alone.** Status states (current / completed / future in `StatusRow`) get color + size + label, not color alone.

## 11. Component Catalog

### 11.1 shadcn primitives to install

```bash
npx shadcn@latest init
npx shadcn@latest add button input card badge separator skeleton tooltip sonner
```

Each primitive gets re-themed via the CSS variables defined in §4 — no per-component overrides needed.

### 11.2 Custom components (build via magic mcp)

| Component | Replaces | Notes |
|---|---|---|
| `BrandMark` | inline logo in `Header` | Wordmark in Playfair 500 + a 10×10px forest square placed after the wordmark, echoing Hera's logo pattern in our brand color. **Wordmark text:** product name not yet decided per `CLAUDE.md` (POV/positioning is TBD). Use the placeholder `Editorial` for now; swap once a name is chosen. |
| `ChipGroup` | (new — for vibes) | Pill-row with one "active" chip in forest, rest with hairline border. |
| `StatusRow` (rebuild) | existing `StatusRow.tsx` | Step-indicator: a row of small dots (4px) connected by a 1px line, current step in forest, completed in `--muted-foreground`, future in `--border`. Caption underneath in `text-label`. |
| `VideoPlayerCard` | existing `VideoPlayer.tsx` | Card with a 9:16 frame, label + name underneath, two pill buttons (Download = primary coral, Regenerate = secondary outline). |
| `RationaleCard` | existing `AttributeCard.tsx` (used in `RationaleRail`) | Card with a forest `text-label` on top, then `text-rationale` body. Optional bottom-row `Separator` + meta line. |

### 11.3 Existing-component migration map

| Existing | Becomes |
|---|---|
| `Header.tsx` | `BrandMark` left, nav center (text-body-sm, `text-muted-foreground`, active = `text-foreground`), avatar/profile right (32px circle, forest bg, initials in `--secondary-foreground`). |
| `UrlInput.tsx` | `Card p-7` containing a `text-label` ("Drop a listing URL"), an `Input` (border `--border`, focus ring `--ring`), and a primary `Button` (coral, rounded-full, "Generate Video"). |
| `StatusRow.tsx` | New `StatusRow` custom component (see 11.2). |
| `VideoPlayer.tsx` | New `VideoPlayerCard` custom component (see 11.2). |
| `RationaleRail.tsx` | A `flex flex-col gap-4` of `RationaleCard`s, top one being the `ChipGroup` (vibes) variant. |
| `AttributeCard.tsx` | `RationaleCard` (see 11.2). |
| `ErrorState.tsx` | `Card` with a small Lucide `AlertTriangle` icon (16px, `--destructive`), `text-h3` headline ("That listing didn't load."), `text-body` body in `--muted-foreground`, and a single secondary outline `Button` ("Try another URL"). |

## 12. Reference Mockup

Visual reference for the result-page composition — Header + Listing block + two-column (VideoPlayerCard | RationaleRail) — was developed during brainstorming. Recreate it in code from the tokens and components above; no separate Figma file is maintained.

Key visual cues to preserve from the mockup:
- Listing title in `text-display-xl` (Playfair) with a trailing period for editorial cadence ("Kreuzberg Loft.").
- "LISTING · airbnb.de/rooms/…" as `text-label` above the title.
- Vibes-chip group as the first card in the rationale rail (one active chip in forest, others hairline-bordered).
- Forest-only `text-label` on each `RationaleCard` ("HOOK", "PACING", "ANGLE").
- Single coral "Download" button on the video card; "Regenerate" as outline secondary.

## 13. Out of Scope (for this spec)

- Dark mode (tokens are dual-ready but not defined here)
- Marketing / landing page (separate spec)
- Mobile-specific patterns beyond the basic two-column collapse
- Animation library (Framer Motion etc.) — defer until a real motion need exists
- Custom illustration / iconography system
- Logo design / brand mark beyond the wordmark + dot
- Localisation typography rules (German-only ligatures, etc.)
- Belief management / settings UI surfaces (out of demo scope)

## 14. Success Criteria

The system is done when:
1. shadcn is initialized in `frontend/` with the tokens from §4 wired into `index.css` and `tailwind.config` (or `@theme` block).
2. Playfair + Inter + JetBrains Mono load via `<link>` in `index.html`.
3. All 7 existing components render against the new tokens with no visual leakage of the old (default Tailwind) styles.
4. The `BrandMark`, `ChipGroup`, `StatusRow`, `VideoPlayerCard`, `RationaleCard` custom components exist and are used.
5. The result page (after a successful generate) visually matches the brainstormed mockup composition — same layout, same type hierarchy, same restraint.
6. `make lint` passes (TypeScript clean).
7. The dev server boots without warnings related to design tokens or font loading.

Out of scope for "done": a Storybook/visual regression suite (deferred), full responsive-mobile polish below 640px (basic stack only), accessibility audit beyond keyboard focus rings (deferred to a follow-up).
