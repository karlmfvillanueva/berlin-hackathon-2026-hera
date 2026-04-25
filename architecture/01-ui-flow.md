# UI Flow Specification — Airbnb Listing Video Agent

## Product overview

Paste an Airbnb listing URL, get a 15-second 9:16 motion graphics video that sells the listing from its single strongest editorial angle. The agent decides the angle, explains why, and the user watches the video without making any creative choices.

**Core value proposition:** One paste, one click, one video — with the agent's reasoning surfaced as the differentiator. The output is editorial judgment; the video is proof.

**Phase boundaries used throughout this document:**

| Phase | Status | Scope |
|---|---|---|
| Phase 1 (MVP, shipped) | Built | Single-screen state machine. Stateless. Airbnb fixtures only. Hardcoded beliefs. |
| Phase 2 (post-MVP) | Planned | Live scraping, Nanobanana outpainting toggle, Supabase persistence, performance learning loop, transparency card upgrade, regenerate, download. |
| Phase 3 (later) | Speculative | Multi-platform (Booking.com, VRBO), dashboard, auth, social posting (IG/TikTok), analytics. |

---

## Stack

- **Frontend:** Vite + React + TypeScript, dev server on `:5173`. Plain `useState` + `useEffect`. No router (single screen). No state library.
- **Backend:** FastAPI (Python, `uv`) on `:8000`. Holds `HERA_API_KEY` and `ANTHROPIC_HACKATHON_KEY`.
- **Frontend ↔ Backend:** Frontend reads `VITE_BACKEND_URL` and talks only to FastAPI. The Hera key never reaches the browser.
- **Status updates:** HTTP polling of `GET /api/videos/{video_id}` every 5s. SSE is documented as an optional Phase 3 upgrade — polling is the baseline because Phase 1 already runs on it and the wait is short enough that streamed status frames don't change UX much.

---

## Phase 1 — Single screen, four states

The MVP is one screen, one component tree, transitioned by an internal state machine. There is no client-side routing. URLs do not encode jobs (matches MVP — there is nothing to bookmark since there is no persistence).

### State machine

```
idle ── submit URL ──▶ generating ── poll success ──▶ done
                            │
                            └── poll fail / timeout ──▶ error
                                                          │
                                                          └── retry ──▶ idle
```

### State: `idle`

- **Layout:** Centered card. Headline, single URL input, optional toggle row, primary CTA.
- **Headline:** "Turn an Airbnb listing into a 15-second video."
- **Subheadline:** "Paste the listing link. The agent picks the angle and tells you why."
- **URL input:** Full-width, validates against `airbnb.com/rooms/...` regex.
- **Toggle: Outpaint photos to 9:16 (Phase 2).** Default off. When on, photos are routed through Nanobanana outpainting before being passed to Hera as references. See `02-architecture.md` Layer 4 for the runtime cost. The toggle is a no-op stub in Phase 1 (UI present, backend ignores) — wire it up the same day Nanobanana is integrated. Tooltip copy: "Extends each photo to vertical without cropping. Slower, but better mobile composition."
- **CTA:** "Generate video." Disabled until the URL passes regex.
- **Submit behavior:** call `POST /api/listing` (not `/api/generate` — see below). On success, transition to `generating` immediately and show the reasoning card from the response.

### State: `generating`

The two-call pattern is the load-bearing UX choice and matches the live MVP backend:

1. `POST /api/listing` returns instantly (Anthropic call, ~1–3s). Response includes the full `AgentDecision` (angle label, rationale, confidence, selected reference images, constructed Hera prompt). Render the **reasoning card the moment this returns**.
2. Frontend then calls `POST /api/generate` with the decision. Backend submits to Hera and returns `{ video_id, decision }` (decision echoed for convenience).
3. Frontend polls `GET /api/videos/{video_id}` every 5s. Hard cap 3 minutes; surface timeout error past that.
4. Stop polling on `status === "success"` (transition to `done`) or `status === "failed"` (transition to `error`).

**Layout:**
- Reasoning card occupies the hero position. Treat it like a chat bubble or a verdict, not a sidebar widget.
- Loading affordance below the card with three stage labels:
  1. "Reading the listing…"
  2. "Picking the angle…"
  3. "Rendering the video…"
- Animated progress strip — not a generic spinner. The 30–150s wait is the user's first impression of the agent's work.
- Frontend `useEffect` cleanup must cancel polling on unmount.

**Reasoning card contents (rendered as soon as `/api/listing` returns):**
- Angle badge (e.g. "Remote Work Base") — the label from `AgentDecision.angle_label`.
- Confidence indicator (subtle dots or bar) — from `AgentDecision.confidence`. Visual only, no number.
- Rationale text — 2–3 plain English sentences, written by the agent in `AgentDecision.rationale`. Not post-processed.

### State: `done`

- **Layout:** Reasoning card stays visible. Inline 9:16 video player appears beside (desktop) or below (mobile).
- Player: HTML5 `<video>` with `autoplay`, `muted`, `loop`, `playsInline`. Source is `outputs[0].file_url` from the Hera GET response.
- Phase 1 has no download button, no regenerate, no share. Phase 2 adds download + regenerate.

### State: `error`

- Friendly message keyed by error code from the backend response body:
  - `fixture_not_found` → "We don't have a fixture for that listing yet."
  - `classifier_failed` → "The agent couldn't read this listing. Try another."
  - `hera_submission_failed` / `hera_unreachable` → "Video generation failed. Try again."
  - `timeout` (frontend-side, polling > 3 min) → "This is taking longer than expected."
- Single "Try again" button → resets to `idle`. No retry-with-backoff in Phase 1.

---

## Phase 1 component layout

```
frontend/src/
  App.tsx                # state machine + layout
  components/
    UrlInput.tsx         # URL field + outpaint toggle (Phase 2 wires the toggle)
    ReasoningCard.tsx    # angle badge, label, rationale, confidence dots
    VideoPlayer.tsx      # 9:16 inline player
    LoadingState.tsx     # stage labels + animated strip
    ErrorState.tsx       # error copy + retry
  api/
    client.ts            # postListing, postGenerate, pollStatus
  types.ts               # mirrors Pydantic models from backend.src.agent.models
```

The actual MVP repo already has this shape. Phase 2 adds new components, it does not restructure.

---

## Phase 2 — UI additions

These are layered on top of the same single-screen state machine. They do not introduce routes.

### Outpaint toggle (wired)

- Already present as a no-op in Phase 1. Phase 2 wires it through to the backend.
- When on: the listing endpoint returns reference image URLs that have already been outpainted to 9:16 by Nanobanana (see `02-architecture.md` Layer 4). When off: Hera receives the original 4:3 / 16:9 CDN URLs. Per the user direction, this is exposed as a user-facing toggle so the demo can show before/after on the same listing.
- Default state: **off** until we have data showing the outpainted version performs better. Then flip the default.

### Transparency card (upgraded reasoning)

The Phase 1 reasoning card is two sentences. Phase 2 expands it into a "Why this video works" expandable section, visible after the video is rendered:
- Hook choice — which photo opens the video and why.
- Story arc — the scene-by-scene structure.
- Style — palette and pacing rationale.
- Beliefs applied — which performance rules influenced this video (Phase 2 only, since beliefs come from the DB).

This is both educational for the user and the strongest demo asset.

### Regenerate

- Button on the `done` state. Re-runs `/api/generate` with the same decision but a different random seed (or with a user-selected alternate angle once the agent surfaces alternates — Phase 3 territory).
- Costs no extra API design — it's a re-submit.

### Download

- Direct download of `outputs[0].file_url` (Hera S3 pre-signed URL, 24h expiry). No auth gate in Phase 2.
- If the URL has expired (user comes back later — only possible once persistence lands), the backend re-fetches via `GET /videos/{video_id}` to refresh the URL.

### Live scrape replaces fixtures

UI flow does not change. Backend swaps the fixture loader for a Playwright scraper (see `02-architecture.md` Layer 3). Failure modes get one new error code: `scrape_blocked` → "Airbnb wouldn't let us read this one. Try a different listing."

---

## Phase 3 — Multi-screen, auth, dashboard

Reserved for after Phase 2 ships and we have published-video performance data flowing in. The structure below is captured for the record but is **not** scoped to be built next.

| Route | Component | When it lights up |
|---|---|---|
| `/` | Single-screen flow above | Phase 1 onward |
| `/dashboard` | Card grid of generated videos with per-video performance metrics | Phase 3 |
| `/settings` | Connected social accounts, billing | Phase 3 |
| `/login`, `/signup` | Email + Google OAuth | Phase 3 |

Phase 3 also adds:
- Direct posting to Instagram (IG Graph API) and TikTok (TikTok for Business API) from the `done` state.
- Performance insights panel summarizing what the agent has learned across the user's videos.
- Multi-platform listing input (Booking.com, VRBO) — only after Airbnb works end-to-end and the parser/agent generalizes cleanly.
- Watermark on free-tier videos, removed on paid tier.

None of this is started until Phase 2 is in production.

---

## Responsive behavior

- **Desktop (>1024px):** Reasoning card and video side-by-side. Video at native 9:16 in a phone-frame mockup.
- **Tablet (768–1024px):** Single column, video scales to viewport width.
- **Mobile (<768px):** Full-width stacked. URL input gets autofocus and full keyboard. Video fills width at native 9:16.

Phase 1 ships with "doesn't break on mobile" only. Phase 2 polishes.

---

## UX principles (apply at every phase)

1. **One input, one output.** Every screen between paste and play is either showing progress or presenting the result.
2. **No creative choices required from the user.** The agent decides. The user can override (regenerate, edit in Hera) but never has to.
3. **The reasoning is the product, not the video.** The reasoning card paints first, occupies hero position, and stays visible while the video plays.
4. **Speed is the feature even when the wait is long.** Stage labels and the instant reasoning card make 90 seconds feel acceptable.
5. **The transparency card is a moat.** A generic AI video tool cannot explain its choices. This one can.
