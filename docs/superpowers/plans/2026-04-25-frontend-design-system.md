# Frontend Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the Quiet Luxury + Hera-wink design system from the spec to the existing 7-component frontend, replacing all ad-hoc inline styling with shadcn/ui primitives and named tokens.

**Architecture:** Single Tailwind v4 `@theme` block in `index.css` defines all tokens (color, type, radius). shadcn/ui primitives in `src/components/ui/` consume those tokens via CSS variables. Custom components (`BrandMark`, `ChipGroup`, `StepIndicator`) sit alongside in `src/components/`; the spec's `VideoPlayerCard` and `RationaleCard` are realized in place by extending the existing `VideoPlayer.tsx` and inlining `Card` instances inside `RationaleRail.tsx` (no separate files — same visual outcome, fewer surfaces). The 7 existing components are migrated in place to use these primitives, and the old `StatusRow.tsx` is replaced by `StepIndicator.tsx`.

**Tech Stack:** React 19 + TypeScript 6 + Tailwind v4 + Vite 7 + Bun + shadcn/ui + Lucide React + Radix UI (Slot, Separator only) + class-variance-authority + tw-animate-css.

**Spec:** `docs/superpowers/specs/2026-04-25-frontend-design-system-design.md` (read it before executing — every section is referenced below).

**Working directory:** `/Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system` on branch `feat/design-system`.

**Verification model:** This is a frontend-visual project with no existing test framework, and the spec explicitly defers visual-regression tooling. "Test" steps therefore mean (a) `bun run build` (tsc + vite) for type/build correctness, (b) `bun run lint` for eslint, (c) manual browser smoke at `http://localhost:5173` for visual correctness. Don't add test infrastructure — that's out of scope per the spec.

**Conventional commits:** `type(scope): description` (matches repo convention). Use `chore(frontend):` for setup, `feat(frontend):` for new components, `refactor(frontend):` for migrations.

---

## File Structure

**New files (created by this plan):**
```
frontend/
├── components.json                         # shadcn config
└── src/
    ├── lib/
    │   └── utils.ts                        # cn() helper
    └── components/
        ├── BrandMark.tsx                   # custom: wordmark + dot
        ├── ChipGroup.tsx                   # custom: vibe-chip pill row
        ├── StepIndicator.tsx               # custom: horizontal step indicator (replaces StatusRow)
        └── ui/
            ├── button.tsx                  # shadcn primitive
            ├── input.tsx                   # shadcn primitive
            ├── card.tsx                    # shadcn primitive
            ├── badge.tsx                   # shadcn primitive
            └── separator.tsx               # shadcn primitive
```

**Modified files:**
```
frontend/
├── package.json                            # +deps
├── index.html                              # font links
├── tsconfig.app.json                       # @/* path alias
├── vite.config.ts                          # @/* alias resolution
└── src/
    ├── index.css                           # FULL REWRITE: @theme + tokens + tw-animate-css
    ├── App.tsx                             # layout migration + swap StatusRow → StepIndicator
    └── components/
        ├── Header.tsx                      # BrandMark + nav + profile
        ├── UrlInput.tsx                    # Card + shadcn Input + Button + Playfair h1
        ├── VideoPlayer.tsx                 # rebuild as VideoPlayerCard
        ├── RationaleRail.tsx               # use new RationaleCard pattern + ChipGroup
        ├── AttributeCard.tsx               # use Card primitive + new tokens
        └── ErrorState.tsx                  # Card + Button + Lucide AlertTriangle
```

**Deleted files:**
```
frontend/src/components/StatusRow.tsx       # superseded by StepIndicator.tsx (deleted in Task 13)
```

**Why a new file `StepIndicator.tsx` instead of mutating `StatusRow.tsx`?** The new component takes a fundamentally different prop shape (`steps: string[]`, `currentStep: number`) — not just visuals. Keeping `StatusRow.tsx` intact through Tasks 7–12 means the build stays clean throughout each migration, and the deletion lands atomically with the App.tsx swap in Task 13.

---

## Task 1: shadcn Foundation (deps, aliases, components.json, cn helper)

**Goal:** Install all dependencies needed for shadcn primitives, wire up the `@/*` path alias, and create the `cn()` utility.

**Files:**
- Modify: `frontend/package.json` (via `bun add`)
- Modify: `frontend/tsconfig.app.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/components.json`
- Create: `frontend/src/lib/utils.ts`

- [ ] **Step 1: Install shadcn-required runtime deps**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun add class-variance-authority clsx tailwind-merge lucide-react @radix-ui/react-slot @radix-ui/react-separator tw-animate-css
```

Expected: bun adds 7 deps. No errors. `package.json` `dependencies` now includes all 7.

- [ ] **Step 2: Add `@/*` path alias to `tsconfig.app.json`**

Open `frontend/tsconfig.app.json`. Inside `compilerOptions`, add `baseUrl` and `paths`:

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "es2023",
    "lib": ["ES2023", "DOM"],
    "module": "esnext",
    "types": ["vite/client"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Add alias resolution in `vite.config.ts`**

Replace `frontend/vite.config.ts` with:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

export default defineConfig({
  plugins: [tailwindcss(), react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 4: Create `frontend/components.json`**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/index.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

(`config: ""` is correct for Tailwind v4 — no separate config file. `style: "new-york"` is the more restrained shadcn variant — fits Quiet Luxury.)

- [ ] **Step 5: Create `frontend/src/lib/utils.ts`**

```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 6: Verify build still passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: `tsc -b` clean, `vite build` produces `dist/` with no errors. (No type errors from new path alias; no missing-import errors.)

- [ ] **Step 7: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/package.json frontend/bun.lock frontend/tsconfig.app.json frontend/vite.config.ts frontend/components.json frontend/src/lib/utils.ts && git commit -m "chore(frontend): set up shadcn foundation (deps, @/ alias, cn helper)

Adds class-variance-authority, clsx, tailwind-merge, lucide-react,
@radix-ui/react-slot, @radix-ui/react-separator, tw-animate-css.
Wires up @/* path alias and creates the cn() utility.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Design Tokens (CSS @theme + Google Fonts)

**Goal:** Replace `index.css` with a full token definition (color, type, radius) consumable by Tailwind v4 utilities and shadcn primitives. Load all three font families.

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Update font links in `frontend/index.html`**

Replace the existing `<link href="...Inter..." />` line with the combined three-family link. Final `<head>` should look like:

```html
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hera · Airbnb Video Agent</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap"
    rel="stylesheet"
  />
</head>
```

- [ ] **Step 2: Rewrite `frontend/src/index.css` with full token definition**

```css
@import "tailwindcss";
@import "tw-animate-css";

/* ============================================================
   Design Tokens — Quiet Luxury + Hera-wink (light mode only)
   See docs/superpowers/specs/2026-04-25-frontend-design-system-design.md
   ============================================================ */

@theme {
  /* Fonts */
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Playfair Display", Georgia, serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* Radius — exposed as Tailwind utilities (rounded, rounded-lg, etc.) */
  --radius-sm: 6px;
  --radius: 8px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 14px;
  --radius-full: 9999px;
}

:root {
  /* shadcn semantic tokens — light mode (Phase 1) */
  --background: oklch(0.98 0.005 80);          /* #FAFAF7 — warm bone */
  --foreground: oklch(0.10 0 0);               /* #0A0A0A — near-black */
  --card: oklch(1 0 0);                         /* #FFFFFF — pure white */
  --card-foreground: oklch(0.10 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.10 0 0);
  --primary: oklch(0.65 0.20 35);              /* #F94B12 — Hera coral */
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(0.34 0.04 160);           /* #2D4A3E — forest */
  --secondary-foreground: oklch(0.98 0.005 80);
  --muted: oklch(0.93 0.02 80);                /* #F0EDE4 */
  --muted-foreground: oklch(0.45 0.01 80);     /* #6B6963 — warm gray */
  --accent: oklch(0.93 0.02 80);               /* same as muted */
  --accent-foreground: oklch(0.10 0 0);
  --destructive: oklch(0.50 0.20 25);          /* #B91C1C — deep red */
  --destructive-foreground: oklch(1 0 0);
  --border: oklch(0.90 0.02 80);               /* #E8E5DD */
  --input: oklch(0.90 0.02 80);
  --ring: oklch(0.34 0.04 160);                /* forest */
}

/* shadcn @theme inline mapping — surfaces semantic vars as Tailwind colors */
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
}

/* Reset */
*,
*::before,
*::after {
  box-sizing: border-box;
}

* {
  border-color: var(--border);
}

body {
  margin: 0;
  background-color: var(--background);
  color: var(--foreground);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Native checkbox tinting → forest */
input[type="checkbox"] {
  accent-color: var(--secondary);
}
```

(Note: oklch values are an exact-as-possible conversion of the spec's hex. If a per-pixel hex match matters, the inline comment shows the source hex and tools like culori or oklch.com can verify.)

- [ ] **Step 3: Smoke test — boot dev server, verify body bg + fonts load**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run dev
```

Expected: Vite serves `http://localhost:5173`. Open in browser. Body background should be a warm off-white (not pure white, not gray). DevTools → Network tab → fonts.googleapis.com requests for Inter, Playfair Display, JetBrains Mono should return 200. Stop server with Ctrl+C.

- [ ] **Step 4: Verify build still passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/index.html frontend/src/index.css && git commit -m "chore(frontend): define design tokens (colors, fonts, radius)

Implements §4–7 of the design spec: 16 semantic color tokens via CSS
variables, three font families (Inter / Playfair Display / JetBrains
Mono) loaded from Google Fonts, six radius scale steps. Tokens surface
as Tailwind v4 utilities through @theme inline mapping.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: shadcn Primitives (Button, Input, Card, Badge, Separator)

**Goal:** Add the five shadcn primitives we'll actually use. Each one consumes the tokens from Task 2 — no further theming needed.

**Files:**
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/separator.tsx`

- [ ] **Step 1: Add Button via shadcn CLI**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bunx --bun shadcn@latest add button --yes --overwrite
```

Expected: creates `src/components/ui/button.tsx`. No prompts (components.json already exists from Task 1).

If the CLI fails or prompts (some shadcn versions don't read components.json cleanly), fall back to writing it manually:

```tsx
// src/components/ui/button.tsx
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 rounded-full",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-full",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/85 rounded-full",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-secondary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-9 px-4",
        lg: "h-11 px-7",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { buttonVariants }
```

(Per spec §4.2 "coral primary, rounded-full pills" — variants `default`, `outline`, `secondary` are pill-shaped. `link` uses forest. `link` color uses forest per spec.)

- [ ] **Step 2: Add Input**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bunx --bun shadcn@latest add input --yes --overwrite
```

Or manually:

```tsx
// src/components/ui/input.tsx
import * as React from "react"

import { cn } from "@/lib/utils"

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-md border border-input bg-background px-4 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"
```

- [ ] **Step 3: Add Card**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bunx --bun shadcn@latest add card --yes --overwrite
```

Or manually (full standard shadcn card.tsx):

```tsx
// src/components/ui/card.tsx
import * as React from "react"

import { cn } from "@/lib/utils"

export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

export const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

export const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("text-h3 font-semibold leading-none tracking-tight", className)}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

export const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"
```

- [ ] **Step 4: Add Badge**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bunx --bun shadcn@latest add badge --yes --overwrite
```

Or manually:

```tsx
// src/components/ui/badge.tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-secondary text-secondary-foreground",
        secondary: "border-transparent bg-muted text-secondary",
        outline: "text-foreground border-border",
        destructive: "border-transparent bg-destructive text-destructive-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { badgeVariants }
```

- [ ] **Step 5: Add Separator**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bunx --bun shadcn@latest add separator --yes --overwrite
```

Or manually:

```tsx
// src/components/ui/separator.tsx
import * as React from "react"
import * as SeparatorPrimitive from "@radix-ui/react-separator"

import { cn } from "@/lib/utils"

export const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(
  (
    { className, orientation = "horizontal", decorative = true, ...props },
    ref
  ) => (
    <SeparatorPrimitive.Root
      ref={ref}
      decorative={decorative}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-border",
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        className
      )}
      {...props}
    />
  )
)
Separator.displayName = SeparatorPrimitive.Root.displayName
```

- [ ] **Step 6: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean. (No "Cannot find module" errors. No `text-h3` errors yet — that utility comes in Task 3a below.)

Note: the `text-h3` class on `CardTitle` requires custom utility classes for the type scale from spec §5.2. We add those in Task 3a so the build won't actually fail on that — Tailwind treats unknown utilities as no-ops, just doesn't style them. We'll fix this concretely below.

- [ ] **Step 6a: Add custom type-scale utilities to `index.css`**

Append to `frontend/src/index.css` (below the `body {}` block):

```css
/* ============================================================
   Type Scale — see spec §5.2
   ============================================================ */

@utility text-display-xl {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 48px;
  line-height: 1.05;
  letter-spacing: -0.015em;
}

@utility text-display-lg {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 36px;
  line-height: 1.1;
  letter-spacing: -0.015em;
}

@utility text-display-md {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 26px;
  line-height: 1.15;
  letter-spacing: -0.01em;
}

@utility text-h2 {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 20px;
  line-height: 1.3;
  letter-spacing: -0.005em;
}

@utility text-h3 {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 16px;
  line-height: 1.4;
}

@utility text-body {
  font-family: var(--font-sans);
  font-weight: 400;
  font-size: 14px;
  line-height: 1.55;
}

@utility text-body-sm {
  font-family: var(--font-sans);
  font-weight: 400;
  font-size: 12px;
  line-height: 1.5;
}

@utility text-label {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 10px;
  line-height: 1.2;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

@utility text-mono-xs {
  font-family: var(--font-mono);
  font-weight: 400;
  font-size: 11px;
  line-height: 1.4;
}

@utility text-rationale {
  font-family: var(--font-display);
  font-weight: 400;
  font-size: 16px;
  line-height: 1.45;
  letter-spacing: -0.005em;
}
```

- [ ] **Step 7: Verify build still clean**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 8: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/ui/ frontend/src/index.css && git commit -m "feat(frontend): add shadcn primitives + type-scale utilities

Adds Button, Input, Card, Badge, Separator from shadcn/ui (new-york
style, customized to use forest secondary + coral primary). Adds type
scale utilities (text-display-xl through text-rationale) per spec §5.2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: BrandMark Component

**Goal:** Build the brand wordmark component for the header. Wordmark text is `Editorial` (placeholder per spec §11.2 — product name TBD).

**Files:**
- Create: `frontend/src/components/BrandMark.tsx`

- [ ] **Step 1: Write the component**

```tsx
// src/components/BrandMark.tsx
import { cn } from "@/lib/utils"

interface BrandMarkProps {
  className?: string
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-display-md leading-none">Editorial</span>
      <span
        aria-hidden
        className="inline-block h-2.5 w-2.5 bg-secondary"
      />
    </div>
  )
}
```

(10×10px square = `h-2.5 w-2.5` in Tailwind. Forest = `bg-secondary`. The wordmark uses `text-display-md` from Task 3a.)

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/BrandMark.tsx && git commit -m "feat(frontend): add BrandMark component

Wordmark in Playfair (text-display-md) + 10×10 forest square dot,
echoing Hera's logo pattern in our brand color. Wordmark text is the
'Editorial' placeholder per spec §11.2 until product name is decided.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: ChipGroup Component

**Goal:** Pill-row component for vibe tags. One chip can be marked active (forest filled), the rest are outline (hairline border).

**Files:**
- Create: `frontend/src/components/ChipGroup.tsx`

- [ ] **Step 1: Write the component**

```tsx
// src/components/ChipGroup.tsx
import { cn } from "@/lib/utils"

interface ChipGroupProps {
  /** Tags to render. The first item (or the one matching `activeLabel`) is rendered as active. */
  tags: string[]
  /** Optional explicit active tag. Falls back to the first tag. */
  activeLabel?: string
  className?: string
}

export function ChipGroup({ tags, activeLabel, className }: ChipGroupProps) {
  const active = activeLabel ?? tags[0]
  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {tags.map((tag) => {
        const isActive = tag === active
        return (
          <span
            key={tag}
            className={cn(
              "rounded-full px-2.5 py-1 text-[11px] italic",
              isActive
                ? "bg-secondary not-italic font-medium text-secondary-foreground"
                : "border border-border text-foreground"
            )}
          >
            {tag}
          </span>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/ChipGroup.tsx && git commit -m "feat(frontend): add ChipGroup component for vibe tags

Pill row with one active chip (filled forest, non-italic) and the rest
as italic hairline-bordered chips. Used in the rationale rail to render
the agent's vibes as a magazine-style tag list.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Build StepIndicator (horizontal step indicator)

**Goal:** Build the new horizontal step indicator as `StepIndicator.tsx`, a new file alongside (not replacing) the existing `StatusRow.tsx`. Per spec §11.2: a row of small dots connected by a 1px line, current in forest, completed in muted, future in border, with a label under each dot. The old `StatusRow.tsx` keeps working until Task 13 wires `App.tsx` to use the new component and deletes the old file.

**Files:**
- Create: `frontend/src/components/StepIndicator.tsx`

- [ ] **Step 1: Write the component**

```tsx
// src/components/StepIndicator.tsx
import { cn } from "@/lib/utils"

interface StepIndicatorProps {
  /** Ordered step labels from first to last. */
  steps: string[]
  /** 1-based index of the currently-active step. Steps before it are "done". */
  currentStep: number
  className?: string
}

export function StepIndicator({ steps, currentStep, className }: StepIndicatorProps) {
  return (
    <div className={cn("flex items-start", className)} role="list" aria-label="Progress">
      {steps.map((label, i) => {
        const idx = i + 1
        const stateClass =
          idx < currentStep
            ? "bg-muted-foreground" // done
            : idx === currentStep
              ? "bg-secondary"      // active
              : "bg-border"         // future

        const lineClass =
          idx < currentStep ? "bg-muted-foreground" : "bg-border"

        const labelClass =
          idx < currentStep
            ? "text-muted-foreground"
            : idx === currentStep
              ? "text-foreground"
              : "text-muted-foreground/60"

        return (
          <div key={label} className="flex flex-1 items-start" role="listitem">
            <div className="flex flex-col items-center gap-2 px-1">
              <span
                aria-hidden
                className={cn("h-2 w-2 rounded-full", stateClass)}
              />
              <span className={cn("text-label whitespace-nowrap", labelClass)}>
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                aria-hidden
                className={cn("mt-[3px] h-px flex-1", lineClass)}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean. (Old `StatusRow.tsx` and its `App.tsx` callers remain unchanged — both StatusRow and StepIndicator coexist. They diverge in Task 13.)

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/StepIndicator.tsx && git commit -m "feat(frontend): add StepIndicator (horizontal step component)

New custom component per spec §11.2. Replaces the per-row StatusRow
visual idiom with a horizontal dot+line indicator. Old StatusRow.tsx
stays in place until App.tsx is migrated in Task 13.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Migrate Header

**Goal:** Replace the inline `Berlin Hackathon 2026...` text and `Step X of Y` with `BrandMark` + nav + profile circle, per spec §11.3.

**Files:**
- Modify: `frontend/src/components/Header.tsx`

- [ ] **Step 1: Replace Header.tsx**

```tsx
// src/components/Header.tsx
import { BrandMark } from "@/components/BrandMark"
import { cn } from "@/lib/utils"

interface HeaderProps {
  className?: string
}

const NAV = ["Generate", "Library", "Beliefs"] as const
const ACTIVE = "Generate"

export function Header({ className }: HeaderProps) {
  return (
    <header
      className={cn(
        "flex h-16 shrink-0 items-center justify-between border-b border-border bg-background px-8",
        className
      )}
    >
      <BrandMark />

      <nav className="flex gap-6 text-body-sm">
        {NAV.map((item) => (
          <span
            key={item}
            className={cn(
              item === ACTIVE
                ? "font-medium text-foreground"
                : "text-muted-foreground"
            )}
          >
            {item}
          </span>
        ))}
      </nav>

      <div
        aria-label="Profile"
        className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold text-secondary-foreground"
      >
        JH
      </div>
    </header>
  )
}
```

(Nav is non-interactive for now — the app doesn't have a router. Profile is hard-coded "JH" — this is a hackathon demo.)

- [ ] **Step 2: Update App.tsx Header usage (drops `step` prop)**

The current App.tsx has `<Header step={step} />` at line 213. Open `frontend/src/App.tsx` and replace that single line with:

```tsx
<Header />
```

Also delete the now-unused helper at lines 16-21 (`stepFromScreen`) and the line `const step = stepFromScreen(state.screen);` near line 208.

- [ ] **Step 3: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean. (App.tsx no longer references `step` in Header. Other usages of `step` in App.tsx that we didn't touch — there shouldn't be any besides the Header line; verify by grep.)

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && grep -n "stepFromScreen\|const step\b" src/App.tsx
```

Expected: empty output.

- [ ] **Step 4: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/Header.tsx frontend/src/App.tsx && git commit -m "refactor(frontend): migrate Header to BrandMark + nav + profile

Replaces the 'Berlin Hackathon 2026 / Step X of Y' header with the
spec's BrandMark + 3-item nav + profile circle. Drops the no-longer-
needed stepFromScreen helper from App.tsx.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Migrate UrlInput

**Goal:** Restyle the URL input page to use `Card`, shadcn `Input`, shadcn `Button`, Playfair display heading, and the new tokens. Per spec §11.3.

**Files:**
- Modify: `frontend/src/components/UrlInput.tsx`

- [ ] **Step 1: Replace UrlInput.tsx**

```tsx
// src/components/UrlInput.tsx
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

const FIXTURE_URL = "https://www.airbnb.com/rooms/kreuzberg-loft-demo"

interface UrlInputProps {
  onSubmit: (url: string) => void
  loading: boolean
  outpaintEnabled: boolean
  onOutpaintChange: (v: boolean) => void
}

export function UrlInput({
  onSubmit,
  loading,
  outpaintEnabled,
  onOutpaintChange,
}: UrlInputProps) {
  const [value, setValue] = useState(FIXTURE_URL)
  const [validationError, setValidationError] = useState<string | null>(null)

  function handleSubmit() {
    setValidationError(null)
    try {
      new URL(value)
    } catch {
      setValidationError("Enter a valid URL.")
      return
    }
    onSubmit(value)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit()
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-8 px-6 py-16">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-display-xl">Turn an Airbnb listing into a 15-second video.</h1>
        <p className="text-body max-w-prose text-muted-foreground">
          Paste a link. Our agent picks the hook, the angle, and the pacing.
        </p>
      </div>

      <Card className="flex w-full flex-col gap-4 p-6">
        <span className="text-label text-muted-foreground">Listing URL</span>
        <div className="flex gap-3">
          <Input
            type="url"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={FIXTURE_URL}
            aria-label="Airbnb listing URL"
          />
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Loading…" : "Generate Video"}
          </Button>
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-body-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={outpaintEnabled}
            onChange={(e) => onOutpaintChange(e.target.checked)}
            className="h-4 w-4 cursor-pointer"
          />
          Outpaint photos to 9:16
        </label>

        {validationError ? (
          <p className="text-body-sm text-destructive">{validationError}</p>
        ) : (
          <p className="text-body-sm text-muted-foreground/80">
            Example: airbnb.com/rooms/12345
          </p>
        )}
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/UrlInput.tsx && git commit -m "refactor(frontend): migrate UrlInput to Card + shadcn primitives

Display heading uses text-display-xl (Playfair). Form lives in a Card
with text-label, shadcn Input + coral primary Button. Native checkbox
keeps native rendering, tinted to forest via accent-color.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Migrate AttributeCard

**Goal:** Restyle the reviewing-screen card. Use `Card` primitive + new tokens. Drop the hand-rolled border-bump on approval; use a forest left-border instead (subtler).

**Files:**
- Modify: `frontend/src/components/AttributeCard.tsx`

- [ ] **Step 1: Replace AttributeCard.tsx**

```tsx
// src/components/AttributeCard.tsx
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface AttributeCardProps {
  label: string
  children: React.ReactNode
  onEdit?: () => void
}

export function AttributeCard({ label, children, onEdit }: AttributeCardProps) {
  const [approved, setApproved] = useState(false)

  return (
    <Card
      className={cn(
        "flex h-[280px] flex-col justify-between gap-4 p-5 transition-colors",
        approved && "border-l-4 border-l-secondary"
      )}
    >
      <div className="flex flex-col gap-2.5">
        <span className="text-label text-muted-foreground">
          {approved ? "✓ Approved" : label}
        </span>
        <div className="text-display-md overflow-hidden">{children}</div>
      </div>

      <div className="flex justify-end gap-2">
        <Button onClick={onEdit} variant="outline" size="sm">
          Edit
        </Button>
        <Button
          onClick={() => setApproved((v) => !v)}
          variant="secondary"
          size="sm"
        >
          {approved ? "✓ Approved" : "✓ Looks good"}
        </Button>
      </div>
    </Card>
  )
}
```

(Note: the inner content was previously `text-[18px] font-bold` — now `text-display-md` per spec §5.2. The buttons swap from black-fill to forest secondary + outline pill, matching the rest of the system.)

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/AttributeCard.tsx && git commit -m "refactor(frontend): migrate AttributeCard to Card + design tokens

Uses the Card primitive, text-label for labels, text-display-md for
content. Approval indicator is a forest left-border (4px) instead of
border-width bump. Buttons become Button outline + secondary variants.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Rebuild VideoPlayer as VideoPlayerCard

**Goal:** Wrap the bare 9:16 `<video>` in a Card with label/title meta and primary/secondary action buttons. Keep the file name `VideoPlayer.tsx` so the import in App.tsx doesn't break, but the exported component is the new richer version.

**Files:**
- Modify: `frontend/src/components/VideoPlayer.tsx`

- [ ] **Step 1: Replace VideoPlayer.tsx**

```tsx
// src/components/VideoPlayer.tsx
import { Download, RotateCw, Share2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

interface VideoPlayerProps {
  fileUrl: string
  /** Optional caption shown below the player (e.g. the agent's hook). */
  caption?: string
  onDownload?: () => void
  onRegenerate?: () => void
  onShare?: () => void
  downloading?: boolean
  regenerating?: boolean
  downloadError?: boolean
}

export function VideoPlayer({
  fileUrl,
  caption,
  onDownload,
  onRegenerate,
  onShare,
  downloading,
  regenerating,
  downloadError,
}: VideoPlayerProps) {
  return (
    <Card className="flex w-full max-w-md flex-col overflow-hidden p-0">
      <div className="aspect-[9/16] max-h-[560px] w-full bg-foreground/5">
        <video
          src={fileUrl}
          autoPlay
          muted
          loop
          controls
          className="h-full w-full object-contain"
        />
      </div>

      <div className="flex flex-col gap-3 p-5">
        <div>
          <p className="text-label text-muted-foreground">Output · 15 sec · 9:16</p>
          {caption && <p className="text-rationale mt-1">{caption}</p>}
        </div>

        {downloadError ? (
          <p className="text-body-sm text-destructive">
            Download failed. Try regenerating.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button onClick={onDownload} disabled={downloading}>
              <Download />
              {downloading ? "Downloading…" : "Download MP4"}
            </Button>
            <Button onClick={onRegenerate} variant="outline" disabled={regenerating}>
              <RotateCw />
              {regenerating ? "Regenerating…" : "Regenerate"}
            </Button>
            <Button onClick={onShare} variant="outline">
              <Share2 />
              Share link
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}
```

(Lucide icon size is locked to 16px via the `[&_svg]:size-4` rule on Button, so no per-icon sizing needed. Per spec §9, stroke weight is 1.5 — Lucide React inherits the page default of 2; we override globally in Step 2 below.)

- [ ] **Step 2: Lower Lucide stroke weight globally**

Append to `frontend/src/index.css`:

```css
/* Lucide line-weight per spec §9 — Quiet Luxury wants 1.5px strokes */
svg.lucide {
  stroke-width: 1.5;
}
```

- [ ] **Step 3: Verify build fails on App.tsx (VideoPlayer prop mismatch)**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build 2>&1 | head -30
```

Expected: passes (the new VideoPlayer makes all new props optional, and the existing call site `<VideoPlayer fileUrl={state.fileUrl} />` is still valid). The action buttons just won't fire — App.tsx is updated in Task 13 to pass them.

- [ ] **Step 4: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/VideoPlayer.tsx frontend/src/index.css && git commit -m "refactor(frontend): rebuild VideoPlayer as a Card with meta + actions

Wraps the 9:16 video frame in a Card with a text-label meta line and
optional Lucide-iconified action buttons (Download primary coral,
Regenerate / Share outline). Sets svg.lucide stroke-width to 1.5
globally per spec §9.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Migrate RationaleRail

**Goal:** Restyle the right-rail editorial-decisions panel. Use `Card` per section + `Separator` + `Badge` (for beliefs) + `ChipGroup` for vibes. Add a vibes section at the top of the rail (the spec calls this out as "the first card in the rationale rail").

**Files:**
- Modify: `frontend/src/components/RationaleRail.tsx`

- [ ] **Step 1: Replace RationaleRail.tsx**

```tsx
// src/components/RationaleRail.tsx
import { ChipGroup } from "@/components/ChipGroup"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { AgentDecision } from "../types"

interface RationaleRailProps {
  decision: AgentDecision
}

const SECTIONS: { label: string; key: "hook" | "pacing" | "angle" | "background" }[] = [
  { label: "Hook", key: "hook" },
  { label: "Pacing", key: "pacing" },
  { label: "Angle", key: "angle" },
  { label: "Background", key: "background" },
]

function parseVibes(vibes: string): string[] {
  return vibes
    .split("·")
    .map((v) => v.trim())
    .filter(Boolean)
}

export function RationaleRail({ decision }: RationaleRailProps) {
  const tags = parseVibes(decision.vibes)

  return (
    <aside className="flex w-full max-w-sm shrink-0 flex-col gap-4">
      {tags.length > 0 && (
        <Card className="p-5">
          <p className="text-label text-secondary mb-3">Vibes</p>
          <ChipGroup tags={tags} />
        </Card>
      )}

      {SECTIONS.map(({ label, key }) => (
        <Card key={key} className="p-5">
          <p className="text-label text-secondary mb-3">{label}</p>
          <p className="text-rationale">{String(decision[key])}</p>
        </Card>
      ))}

      {decision.beliefs_applied && decision.beliefs_applied.length > 0 && (
        <Card className="p-5">
          <p className="text-label text-secondary mb-3">Beliefs Applied</p>
          <div className="flex flex-wrap gap-1.5">
            {decision.beliefs_applied.map((belief) => (
              <Badge key={belief} variant="secondary">
                {belief.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-5">
        <details>
          <summary className="text-label text-secondary cursor-pointer list-none">
            Full Rationale
          </summary>
          <Separator className="my-3" />
          <pre className="text-body-sm whitespace-pre-wrap break-words text-muted-foreground">
            {decision.hera_prompt}
          </pre>
        </details>
      </Card>
    </aside>
  )
}
```

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/RationaleRail.tsx && git commit -m "refactor(frontend): migrate RationaleRail to Card stack + ChipGroup

Splits each editorial decision into its own Card with a forest text-label
header. Adds a Vibes card at the top using ChipGroup (parsed from the
existing decision.vibes dot-separated string). Beliefs become Badge
secondary chips. Full prompt collapses behind a details summary.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Migrate ErrorState

**Goal:** Restyle the error fallback. Card + Lucide AlertTriangle + outline retry button.

**Files:**
- Modify: `frontend/src/components/ErrorState.tsx`

- [ ] **Step 1: Replace ErrorState.tsx**

```tsx
// src/components/ErrorState.tsx
import { AlertTriangle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

const ERROR_MESSAGES: Record<string, string> = {
  scrape_blocked:
    "Airbnb blocked us on that listing. Try a different one, or paste a listing we've seen before.",
  scrape_failed: "We couldn't read that listing. The page may have changed. Try again.",
  fixture_not_found: "We don't have a fixture for that listing yet.",
  classifier_failed: "The agent couldn't read this listing. Try another.",
  hera_submission_failed: "Video generation failed. Try again.",
  hera_unreachable: "Video generation failed. Try again.",
  timeout: "This is taking longer than expected.",
}

function parseMessage(raw: string): string {
  try {
    const parsed: unknown = JSON.parse(raw)
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "detail" in parsed &&
      parsed.detail !== null &&
      typeof parsed.detail === "object" &&
      "error" in parsed.detail &&
      typeof (parsed.detail as Record<string, unknown>).error === "string"
    ) {
      const code = (parsed.detail as Record<string, string>).error
      if (code in ERROR_MESSAGES) {
        return ERROR_MESSAGES[code]
      }
    }
  } catch {
    // not JSON — fall through
  }
  return raw
}

interface ErrorStateProps {
  message: string
  onRetry: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="flex w-full max-w-md flex-col gap-4 p-6">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="size-4" />
          <span className="text-label">Something went wrong</span>
        </div>
        <p className="text-rationale">
          {parseMessage(message) || "We couldn't generate the video. Try again."}
        </p>
        <Button onClick={onRetry} variant="outline" className="self-start">
          Try again
        </Button>
      </Card>
    </div>
  )
}
```

(Existing copy preserved — "Something went wrong" stays. Spec §11.3 example was illustrative.)

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/components/ErrorState.tsx && git commit -m "refactor(frontend): migrate ErrorState to Card + Lucide icon + Button

Card with destructive-colored AlertTriangle + 'Something went wrong'
text-label header, error message in text-rationale, outline retry
Button. Existing parseMessage logic preserved unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Migrate App.tsx (Layout, Generating Screen, VideoPlayer Wiring, StepIndicator Swap)

**Goal:** Update App.tsx to use the new tokens, wire VideoPlayer's new action props, swap the per-row `StatusRow` stack for the new horizontal `StepIndicator`, delete the now-unused `StatusRow.tsx`, and clean up the inline reviewing/done-screen styling.

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/components/StatusRow.tsx`

- [ ] **Step 1: Replace App.tsx**

The whole render block is rewritten. Logic (handlers, state, polling) stays identical — only JSX changes. Replace `frontend/src/App.tsx` with:

```tsx
import { useEffect, useRef, useState } from "react"

import { AttributeCard } from "@/components/AttributeCard"
import { ErrorState } from "@/components/ErrorState"
import { Header } from "@/components/Header"
import { RationaleRail } from "@/components/RationaleRail"
import { StepIndicator } from "@/components/StepIndicator"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { UrlInput } from "@/components/UrlInput"
import { VideoPlayer } from "@/components/VideoPlayer"
import "./index.css"

import { postGenerate, postListing, postRegenerate, pollStatus } from "./api/client"
import type { AgentDecision, AppState, ScrapedListing } from "./types"

const POLL_INTERVAL_MS = 5000
const POLL_TIMEOUT_MS = 3 * 60 * 1000

const GENERATING_STEPS = [
  "Analyze",
  "Draft",
  "Render",
  "Finalize",
] as const

export default function App() {
  const [state, setState] = useState<AppState>({ screen: "idle" })
  const [listingUrl, setListingUrl] = useState(
    "https://www.airbnb.com/rooms/kreuzberg-loft-demo",
  )
  const [submitting, setSubmitting] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [scriptStep, setScriptStep] = useState(0)
  const [outpaintEnabled, setOutpaintEnabled] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState(false)

  const pollIntervalRef = useRef<number | null>(null)
  const pollStartRef = useRef<number>(0)

  function clearPolling() {
    if (pollIntervalRef.current !== null) {
      window.clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  function goIdle() {
    clearPolling()
    setElapsedSeconds(0)
    setScriptStep(0)
    setOutpaintEnabled(false)
    setDownloadError(false)
    setState({ screen: "idle" })
  }

  async function handleGenerate(url: string) {
    setListingUrl(url)
    setSubmitting(true)
    try {
      const { listing, decision } = await postListing(url, outpaintEnabled)
      setState({ screen: "reviewing", listing, decision })
    } catch (err) {
      setState({
        screen: "error",
        message: err instanceof Error ? err.message : "Failed to fetch listing.",
      })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleContinue(listing: ScrapedListing, decision: AgentDecision) {
    setSubmitting(true)
    setScriptStep(0)
    setElapsedSeconds(0)
    try {
      const { video_id } = await postGenerate(listingUrl, listing, decision)
      setState({
        screen: "generating",
        listing,
        decision,
        videoId: video_id,
        outpaint_enabled: outpaintEnabled,
      })
    } catch (err) {
      setState({
        screen: "error",
        message: err instanceof Error ? err.message : "Failed to start generation.",
      })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRegenerate() {
    if (state.screen !== "done") return
    const { listing, decision } = state
    setRegenerating(true)
    try {
      const { video_id, decision: newDecision } = await postRegenerate(
        listingUrl,
        listing,
        decision,
      )
      setState({
        screen: "generating",
        listing,
        decision: newDecision,
        videoId: video_id,
        outpaint_enabled: outpaintEnabled,
      })
    } catch (err) {
      setState({
        screen: "error",
        message: err instanceof Error ? err.message : "Failed to regenerate.",
      })
    } finally {
      setRegenerating(false)
    }
  }

  async function handleDownload() {
    if (state.screen !== "done") return
    setDownloadError(false)
    setDownloading(true)

    async function fetchAndTrigger(fileUrl: string): Promise<boolean> {
      const res = await fetch(fileUrl)
      if (!res.ok) return false
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = objectUrl
      a.download = "hera-video.mp4"
      a.click()
      URL.revokeObjectURL(objectUrl)
      return true
    }

    try {
      const ok = await fetchAndTrigger(state.fileUrl)
      if (!ok) {
        const data = await pollStatus(state.videoId)
        const freshUrl = data.outputs[0]?.file_url ?? ""
        if (freshUrl) {
          const retryOk = await fetchAndTrigger(freshUrl)
          if (!retryOk) setDownloadError(true)
        } else {
          setDownloadError(true)
        }
      }
    } catch {
      setDownloadError(true)
    } finally {
      setDownloading(false)
    }
  }

  function handleShare() {
    if (state.screen !== "done") return
    void navigator.clipboard.writeText(state.fileUrl)
  }

  useEffect(() => {
    if (state.screen !== "generating") return
    const { videoId, listing, decision } = state

    let cancelled = false
    pollStartRef.current = Date.now()

    setScriptStep(1)
    const step2Timer = window.setTimeout(() => {
      if (!cancelled) setScriptStep(2)
    }, 1000)

    async function doPoll() {
      if (cancelled) return

      const elapsed = Date.now() - pollStartRef.current
      setElapsedSeconds(Math.floor(elapsed / 1000))

      if (elapsed >= POLL_TIMEOUT_MS) {
        clearPolling()
        if (!cancelled) {
          setState({ screen: "error", message: "Generation timed out after 3 minutes." })
        }
        return
      }

      try {
        const data = await pollStatus(videoId)
        if (cancelled) return

        if (data.status === "success") {
          clearPolling()
          const fileUrl = data.outputs[0]?.file_url ?? ""
          setState({ screen: "done", listing, decision, fileUrl, videoId })
        } else if (data.status === "failed") {
          clearPolling()
          setState({
            screen: "error",
            message: data.outputs[0]?.error ?? "Hera reported a failure.",
          })
        }
      } catch (err) {
        if (!cancelled) {
          clearPolling()
          setState({
            screen: "error",
            message: err instanceof Error ? err.message : "Polling failed.",
          })
        }
      }
    }

    void doPoll()
    pollIntervalRef.current = window.setInterval(doPoll, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      clearPolling()
      window.clearTimeout(step2Timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.screen === "generating" ? state.videoId : null])

  // Map elapsed time → which step the horizontal indicator highlights.
  // Step 1 = Analyze (instant), Step 2 = Draft (~1s in), Step 3 = Render (most time),
  // Step 4 = Finalize (last few seconds).
  const generatingCurrent =
    scriptStep < 2 ? Math.max(scriptStep, 1) : elapsedSeconds < 75 ? 3 : 4

  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <Header />

      {/* idle */}
      {state.screen === "idle" && (
        <main className="flex flex-1 items-center justify-center">
          <UrlInput
            onSubmit={handleGenerate}
            loading={submitting}
            outpaintEnabled={outpaintEnabled}
            onOutpaintChange={setOutpaintEnabled}
          />
        </main>
      )}

      {/* reviewing */}
      {state.screen === "reviewing" && (
        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-12">
          <div className="flex flex-col gap-2">
            <p className="text-label text-muted-foreground">Listing scraped</p>
            <h2 className="text-display-lg">Here's what we found.</h2>
            <p className="text-body max-w-prose text-muted-foreground">
              Our agent picked these attributes. Approve each card or edit before we generate.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            <AttributeCard label="Title">
              <span className="line-clamp-3">{state.listing.title}</span>
            </AttributeCard>

            <AttributeCard label="Location">
              <span className="line-clamp-3">{state.listing.location}</span>
            </AttributeCard>

            <AttributeCard label="Vibes / Tags">
              <span className="line-clamp-3">{state.decision.vibes}</span>
            </AttributeCard>

            <AttributeCard label={`Hero Images (${state.decision.selected_image_urls.length})`}>
              <div className="flex flex-col gap-2">
                <div className="flex gap-2 overflow-hidden">
                  {state.decision.selected_image_urls.slice(0, 4).map((url, i) => (
                    <div
                      key={i}
                      className="h-[88px] w-[88px] shrink-0 overflow-hidden rounded-md bg-muted"
                    >
                      <img
                        src={url}
                        alt=""
                        className="h-full w-full object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = "none"
                        }}
                      />
                    </div>
                  ))}
                  {state.decision.selected_image_urls.length === 0 && (
                    <div className="h-[88px] w-[88px] rounded-md bg-muted" />
                  )}
                </div>
                {state.decision.selected_image_urls.length > 4 && (
                  <span className="text-body-sm text-muted-foreground">
                    +{state.decision.selected_image_urls.length - 4} more · agent picked these as strongest
                  </span>
                )}
              </div>
            </AttributeCard>

            <AttributeCard label="Bedrooms / Sleeps">
              <span className="line-clamp-3">{state.listing.bedrooms_sleeps}</span>
            </AttributeCard>

            <AttributeCard label="Price / Night">
              <span className="line-clamp-3">{state.listing.price_display}</span>
            </AttributeCard>
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button onClick={goIdle} variant="outline">
              Back
            </Button>
            <Button
              onClick={() => handleContinue(state.listing, state.decision)}
              disabled={submitting}
            >
              {submitting ? "Starting…" : "Continue → Generate Video"}
            </Button>
          </div>
        </main>
      )}

      {/* generating */}
      {state.screen === "generating" && (
        <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-8 px-6 py-16">
          <div className="flex flex-col items-center gap-2 text-center">
            <p className="text-label text-muted-foreground">In progress</p>
            <h2 className="text-display-lg">Generating your video.</h2>
            <p className="text-body text-muted-foreground">
              Our agent is making editorial calls. Hang tight — usually 60–90 seconds.
            </p>
          </div>

          <Card className="w-full max-w-lg p-6">
            <StepIndicator steps={[...GENERATING_STEPS]} currentStep={generatingCurrent} />
          </Card>

          <Button onClick={goIdle} variant="link">
            Cancel
          </Button>
        </main>
      )}

      {/* done */}
      {state.screen === "done" && (
        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-12">
          <div className="flex flex-col gap-2">
            <p className="text-label text-muted-foreground">
              Listing · {new URL(listingUrl).pathname}
            </p>
            <h2 className="text-display-xl">{state.listing.title}.</h2>
            <p className="text-body italic text-muted-foreground">
              {state.listing.location} · {state.listing.bedrooms_sleeps}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-7 lg:grid-cols-[1.4fr_1fr]">
            <div className="flex justify-center">
              <VideoPlayer
                fileUrl={state.fileUrl}
                caption={state.decision.hook}
                onDownload={() => void handleDownload()}
                onRegenerate={() => void handleRegenerate()}
                onShare={handleShare}
                downloading={downloading}
                regenerating={regenerating}
                downloadError={downloadError}
              />
            </div>

            <RationaleRail decision={state.decision} />
          </div>
        </main>
      )}

      {/* error */}
      {state.screen === "error" && (
        <ErrorState message={state.message} onRetry={goIdle} />
      )}
    </div>
  )
}
```

(Notable changes from old App.tsx: imports use `@/` aliases; `stepFromScreen` and `step` removed; new `generatingCurrent` derives the StatusRow active index; the done-screen layout uses the spec's two-column grid with the listing title in `text-display-xl` Playfair; the four hand-rolled buttons on done are now props on `VideoPlayer`; the `outpaint_enabled` row in the generating screen is dropped since the new horizontal indicator doesn't have a slot for it — the outpaint flag is honored by the API call regardless.)

- [ ] **Step 2: Verify build passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 3: Verify lint passes**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run lint
```

Expected: clean. (One known false-positive — `state.listing.title` interpolation in `text-display-xl` won't trigger lint warnings.)

- [ ] **Step 4: Smoke test in browser**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run dev
```

Open `http://localhost:5173`. Without backend running, the URL submit will fail — that's expected. Visually verify:
1. Header shows "Editorial · " wordmark + forest dot, "Generate / Library / Beliefs" nav, "JH" forest avatar.
2. Idle screen: large Playfair heading, Card with the URL input + coral "Generate Video" pill button.
3. Click Generate (will error) → ErrorState card with AlertTriangle.
4. Click "Try again" → back to idle.

Stop the dev server.

- [ ] **Step 5: Delete the now-unused `StatusRow.tsx`**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git rm frontend/src/components/StatusRow.tsx
```

- [ ] **Step 6: Verify build and lint after deletion**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build && bun run lint
```

Expected: both clean. (`grep -r "StatusRow" src/` should return no hits — the component is gone and App.tsx now uses StepIndicator.)

- [ ] **Step 7: Commit**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git add frontend/src/App.tsx && git commit -m "refactor(frontend): migrate App.tsx + swap StatusRow for StepIndicator

Rewrites all four screens to use the new tokens, drops hand-rolled inline
button styles in favor of Button + variant props. Done screen gets the
spec's two-column grid (VideoPlayerCard + RationaleRail) with the listing
title in text-display-xl. Generating screen gets the horizontal
StepIndicator replacing the per-row StatusRow stack (StatusRow.tsx is
deleted in this commit). Reviewing screen grid becomes responsive
(1/2/3 columns at sm/md/lg).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Final Visual QA + Lint + Final Commit

**Goal:** End-to-end visual check across all four screens, ensure lint is clean, capture any remaining inconsistencies, and tag the work.

**Files:** none modified by default; only fix issues found.

- [ ] **Step 1: Boot backend + frontend together**

In a first terminal:

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && make dev-backend
```

In a second terminal:

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && make dev-frontend
```

Open `http://localhost:5173`.

- [ ] **Step 2: Walk every screen and check against the spec**

For each screen, verify:

| Screen | Check |
|---|---|
| **Idle** | Bone background; Playfair display heading; coral pill button; Card around input. No old black borders or "Step X of Y". |
| **Reviewing** | Six AttributeCards in 3-column grid; forest left-border on approval; outline + secondary buttons (no black fills). Two pill buttons at bottom. |
| **Generating** | Horizontal 4-dot StatusRow with mini labels; current dot in forest; Playfair display heading; link-style "Cancel" in forest. |
| **Done** | Listing title in `text-display-xl` Playfair with trailing period; two-column layout (video left, rail right); video card with coral Download + outline Regenerate/Share; rail has Vibes ChipGroup + 4 rationale cards + (optional) Beliefs card + collapsible full-prompt card. |
| **Error** | AlertTriangle in destructive color; "Something went wrong" in `text-label`; outline retry button. |

If any screen deviates, fix in the relevant component file, commit as `fix(frontend): <screen>:<issue>`.

- [ ] **Step 3: Lint pass**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run lint
```

Expected: clean.

If warnings appear (unused imports from removed components, etc.), fix them and commit `chore(frontend): lint cleanup` before proceeding.

- [ ] **Step 4: Final build pass**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system/frontend && bun run build
```

Expected: clean.

- [ ] **Step 5: Tag the design-system completion**

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git log --oneline origin/main..HEAD
```

Expected: ~10–13 commits from this plan, all `chore(frontend)` / `feat(frontend)` / `refactor(frontend)`.

```bash
cd /Users/joschahaertel/Projects/Hackathons/berlin-hackathon-2026-hera-design-system && git tag -a design-system-v1 -m "Design system v1 — Quiet Luxury + Hera-wink"
```

(No push to origin yet — user decides when to open the PR against main.)

- [ ] **Step 6: Status report**

Report back to the user:
- Number of commits on `feat/design-system`
- Tag created
- Any deviations from the spec discovered during QA (if any)
- Recommendation: open PR against main, or sit on the branch until backend pipeline work merges

---

## Verification Summary

| Spec section | Implemented in task |
|---|---|
| §1 Purpose | Plan as a whole |
| §2 Positioning (Quiet Luxury + Hera-wink) | Task 2 (tokens) + Task 3 (Button primary coral) |
| §3 Library Stack (shadcn + Lucide + magic mcp + 3 fonts) | Task 1 + Task 2 + Task 3 |
| §4 Color Tokens (16 semantic) | Task 2 |
| §5 Typography (10-step scale) | Task 3 step 6a |
| §6 Spacing & Layout (max-w-6xl, py-12 px-6, two-col on done) | Task 13 |
| §7 Border Radius (sm/md/lg/xl/full) | Task 2 |
| §8 Elevation (no shadows by default) | Task 3 (Button uses bg-tint hover, not shadow) |
| §9 Iconography (Lucide, stroke 1.5) | Task 10 step 2 |
| §10 Motion (150ms cubic-bezier) | Task 3 (Button has `transition-colors`) |
| §10a A11y (focus rings, contrast) | Task 3 (Button + Input use `focus-visible:ring-2 ring-ring`) |
| §11.1 shadcn primitives | Task 3 |
| §11.2 BrandMark | Task 4 |
| §11.2 ChipGroup | Task 5 |
| §11.2 StatusRow → StepIndicator | Task 6 (build) + Task 13 (App.tsx swap + StatusRow.tsx deletion) |
| §11.2 VideoPlayerCard | Task 10 (realized in place — `VideoPlayer.tsx` becomes a Card-wrapped player with meta + actions) |
| §11.2 RationaleCard | Task 11 (inlined as `Card` instances inside RationaleRail — simpler, fewer files. If a separate `RationaleCard.tsx` is desired, factor out post-Task 11.) |
| §11.3 Header migration | Task 7 |
| §11.3 UrlInput migration | Task 8 |
| §11.3 StatusRow migration | Task 13 (App.tsx swap to StepIndicator + StatusRow.tsx deletion) |
| §11.3 VideoPlayer migration | Task 10 |
| §11.3 RationaleRail migration | Task 11 |
| §11.3 AttributeCard migration | Task 9 |
| §11.3 ErrorState migration | Task 12 |
| §12 Reference mockup adherence | Task 13 done-screen + Task 14 QA |
| §14 Success Criteria 1 (shadcn init + tokens wired) | Task 1 + 2 |
| §14 Success Criteria 2 (3 fonts loaded) | Task 2 |
| §14 Success Criteria 3 (no leakage of old styles) | Tasks 7–13 |
| §14 Success Criteria 4 (5 custom components used) | BrandMark (4) + ChipGroup (5) + StepIndicator (6) + extended VideoPlayer (10) + Card-based rationale sections (11) |
| §14 Success Criteria 5 (done screen matches mockup) | Task 13 |
| §14 Success Criteria 6 (`make lint` passes) | Task 14 |
| §14 Success Criteria 7 (dev server boots clean) | Task 14 |

## Notes & Deviations

- **§11.2 StatusRow renamed to `StepIndicator`**: the spec says "rebuild StatusRow as horizontal step indicator". The plan creates `StepIndicator.tsx` as a new file (Task 6) and deletes `StatusRow.tsx` (Task 13) instead of mutating it in place. Reason: the prop shape changes fundamentally (`steps`/`currentStep` vs. `state`/`label`), so a new file keeps the build green through the migration tasks (7–12) while only the final swap in Task 13 needs to be atomic. The old name made sense for the per-row shape; `StepIndicator` is the more accurate name for the new horizontal shape.
- **§11.2 `VideoPlayerCard` filename**: kept as `VideoPlayer.tsx` rather than renamed to `VideoPlayerCard.tsx`. The exported component is the new richer Card-wrapped version; the file name preserves the existing import path. If a clean rename is preferred later, do `git mv` plus an import update.
- **§11.2 `RationaleCard` filename**: implemented inline inside `RationaleRail.tsx` rather than as a separate `RationaleCard.tsx` file. Each section is a `Card` with a forest `text-label` and `text-rationale` body — same visual outcome, one fewer file. Easy to factor out later if it gets reused.
- **§11.3 Header `step indicator`**: dropped per spec. The new StepIndicator lives only on the generating screen.
- **§11.1 `skeleton`, `tooltip`, `sonner`**: deferred per YAGNI — not used by any current screen. Add when first needed.
- **`outpaint_enabled` row in generating screen**: dropped from the new StepIndicator since the horizontal indicator has fixed steps. The flag is still passed to the API; only the visual indicator stops calling it out separately.
