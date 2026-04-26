import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"

import { finalizeVideo } from "@/api/dashboard"
import { useMe } from "@/auth/useMe"
import { DemoListingPicker } from "@/components/DemoListingPicker"
import { ErrorState } from "@/components/ErrorState"
import { Header } from "@/components/Header"
import { RationaleRail } from "@/components/RationaleRail"
import { StepIndicator } from "@/components/StepIndicator"
import { Storyboard } from "@/components/Storyboard"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { UrlInput } from "@/components/UrlInput"
import { VideoPlayer } from "@/components/VideoPlayer"
import { ConnectYouTubeBadge } from "@/youtube/ConnectYouTubeBadge"
import { PublishButton } from "@/youtube/PublishButton"

import { postGenerate, postListing, postRegenerate, pollJob, pollStatus } from "../api/client"
import type { AgentDecision, AppState, Overrides, Phase1Decision, ScrapedListing } from "../types"

const POLL_INTERVAL_MS = 5000
// Hera renders can take 130-200s on a clear day, more under hackathon-load
// on the upstream. 3 min was cutting it tight whenever Hera queued.
const POLL_TIMEOUT_MS = 5 * 60 * 1000

const GENERATING_STEPS = [
  "Analyze",
  "Draft",
  "Render",
  "Finalize",
] as const

export function AgentApp() {
  const [state, setState] = useState<AppState>({ screen: "idle" })
  const [listingUrl, setListingUrl] = useState(
    "https://www.airbnb.com/rooms/kreuzberg-loft-demo",
  )
  const [searchParams, setSearchParams] = useSearchParams()
  const deepLinkHandled = useRef(false)
  const [submitting, setSubmitting] = useState(false)
  const me = useMe()
  // Treat unknown (loading) team status as non-team — picker renders, URL
  // input stays hidden. The URL input flashes in for team members once /api/me
  // resolves; that's the right tradeoff vs. a hidden picker for everyone else.
  const isTeam = me?.is_team_member ?? false
  // Demo mode is the default for everyone. Team members can toggle it off to
  // get the free-text URL input back; non-team users never see the toggle, so
  // their state is effectively pinned to ON.
  const [demoMode, setDemoMode] = useState(true)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [scriptStep, setScriptStep] = useState(0)
  const [outpaintEnabled, setOutpaintEnabled] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState(false)
  // Inline notice on the picker, shown when a non-team user lands here with a
  // pasted URL (the live-scrape path is gated to team members, so the backend
  // would 403 demo_mode_only and the user would see a raw error otherwise).
  const [demoNotice, setDemoNotice] = useState<string | null>(null)

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
    // Optimistic transition: leave the picker immediately so the user sees
    // forward motion. Phase-1 takes ~10–20s and a silent grey-out on the
    // picker reads like a broken click.
    setState({ screen: "preparing", listing_url: url })
    try {
      const { listing, phase1 } = await postListing(url, outpaintEnabled)
      const overrides: Overrides = {
        language: phase1.suggested_language,
        tone: phase1.suggested_tone,
        emphasis: [],
        deemphasis: [],
        hook_id: "auto",
      }
      setState({ screen: "storyboard", listing, phase1, overrides })
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch listing."
      // Backend rejects non-fixture URLs for non-team users with this error.
      // Surface as a picker-side notice rather than a stack-trace error screen.
      if (message.includes("demo_mode_only")) {
        setDemoNotice(
          "You're in demo mode — live Airbnb scraping is team-only for now. Pick one of these listings to see how the agent thinks.",
        )
        setState({ screen: "idle" })
      } else {
        setState({ screen: "error", message })
      }
    } finally {
      setSubmitting(false)
    }
  }

  // Deep-link from the Landing CTA: /app?url=<encoded>. Wait for /api/me to
  // resolve before acting — non-team users can't use the live-scrape path, so
  // we'd otherwise just shove them into a preparing screen that resolves to a
  // 403. Instead, intercept and route them to the picker with a friendly
  // notice. queueMicrotask defers the state-flipping handleGenerate out of the
  // effect body so the render commit completes first.
  useEffect(() => {
    if (deepLinkHandled.current) return
    const url = searchParams.get("url")
    if (!url) return
    if (!me) return // wait for /api/me

    deepLinkHandled.current = true
    setSearchParams({}, { replace: true })

    if (!me.is_team_member) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDemoNotice(
        "You're in demo mode — live Airbnb scraping is team-only for now. Pick one of these listings to see how the agent thinks.",
      )
      return
    }

    queueMicrotask(() => void handleGenerate(decodeURIComponent(url)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me])

  async function handleRender(
    listing: ScrapedListing,
    phase1: Phase1Decision,
    overrides: Overrides,
  ) {
    // Optimistic flip into the loading screen — postGenerate (~30–60s) shouldn't
    // leave the user staring at the storyboard form with a disabled button.
    setState({ screen: "starting", listing, phase1, overrides })
    try {
      // Async kickoff — backend returns immediately with the internal id.
      // Phase 2 + Hera POST run as a background task; we poll /api/jobs/{id}.
      const { internal_video_id } = await postGenerate(
        listingUrl,
        listing,
        phase1,
        overrides,
      )
      setState({
        screen: "generating",
        listing,
        phase1,
        overrides,
        internalVideoId: internal_video_id,
        decision: null,
        heraVideoId: null,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start generation."
      // Backend can fail to reach Hera in two ways:
      //   - hera_unreachable / 502 → connect-level failure (retried 3×, still nothing)
      //   - hera_submission_failed → Hera returned 4xx/5xx (rate limit, queue full, etc.)
      // Both surface to the user as "Hera is busy" — there's nothing to do but wait.
      const heraDown =
        message.includes("hera_unreachable") ||
        message.includes("hera_submission_failed") ||
        message.includes("502") ||
        message.includes("503") ||
        message.includes("504")
      setState({
        screen: "error",
        message: heraDown
          ? "Hera's video service is busy right now. Give it a minute and try again."
          : message,
      })
    }
  }

  async function handleRegenerate() {
    if (state.screen !== "done") return
    const { listing, phase1, overrides, decision } = state
    setRegenerating(true)
    try {
      // Async kickoff like postGenerate — backend registers a tracker job
      // (NOT a new DB row), returns the new internal id, fires Hera POST
      // in the background. Decision is unchanged; only the render is fresh.
      const { internal_video_id: newJobId } = await postRegenerate(
        listingUrl,
        listing,
        decision,
      )
      setState({
        screen: "generating",
        listing,
        phase1,
        overrides,
        internalVideoId: newJobId,
        // Pre-populate decision so polling effect doesn't have to wait.
        decision,
        heraVideoId: null,
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

  function updateOverrides(next: Overrides) {
    if (state.screen !== "storyboard") return
    setState({ ...state, overrides: next })
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

  // Step indicator + elapsed timer. Starts when the user clicks Render
  // (state="starting") and persists through the polling phase
  // (state="generating") so the counter doesn't reset when postGenerate
  // resolves and we transition starting→generating.
  const isRendering = state.screen === "starting" || state.screen === "generating"
  useEffect(() => {
    if (!isRendering) return
    pollStartRef.current = Date.now()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setScriptStep(1)
    const step2Timer = window.setTimeout(() => setScriptStep(2), 1000)
    const tick = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - pollStartRef.current) / 1000))
    }, 1000)
    return () => {
      window.clearTimeout(step2Timer)
      window.clearInterval(tick)
    }
  }, [isRendering])

  useEffect(() => {
    if (state.screen !== "generating") return
    const { internalVideoId, listing, phase1, overrides } = state

    let cancelled = false
    // Latest decision/heraVideoId from the job — fill in as the server gets
    // them. We carry these into the "done" state when render finishes.
    let latestDecision: AgentDecision | null = state.decision
    let latestHeraVideoId: string | null = state.heraVideoId

    async function doPoll() {
      if (cancelled) return

      if (Date.now() - pollStartRef.current >= POLL_TIMEOUT_MS) {
        clearPolling()
        if (!cancelled) {
          setState({ screen: "error", message: "Generation timed out after 5 minutes." })
        }
        return
      }

      try {
        const data = await pollJob(internalVideoId)
        if (cancelled) return

        // Mirror server-side state into our local view as the job progresses.
        // Decision becomes available after phase 2; heraVideoId after Hera POST.
        if (data.decision && !latestDecision) {
          latestDecision = data.decision
        }
        if (data.hera_video_id && !latestHeraVideoId) {
          latestHeraVideoId = data.hera_video_id
        }

        if (data.state === "success") {
          clearPolling()
          if (!latestDecision) {
            // Server lost the decision somehow — bail with a useful message
            // rather than crashing the done screen on a missing field.
            setState({
              screen: "error",
              message: "Render finished but the agent decision was missing. Try again.",
            })
            return
          }
          const fileUrl = data.file_url ?? ""
          setState({
            screen: "done",
            listing,
            phase1,
            overrides,
            decision: latestDecision,
            fileUrl,
            videoId: latestHeraVideoId ?? "",
            internalVideoId,
          })
          // Persist video_url to Supabase so reloads + dashboard list work.
          // Best-effort: the done screen still renders if this no-ops.
          if (internalVideoId && fileUrl) {
            void finalizeVideo(internalVideoId, fileUrl)
          }
        } else if (data.state === "failed") {
          clearPolling()
          setState({
            screen: "error",
            message: data.error ?? "Hera reported a failure.",
          })
        }
        // state==="planning" or "rendering" → keep polling.
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
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.screen === "generating" ? state.internalVideoId : null])

  // Map state → which step the horizontal indicator highlights.
  // Analyze flashes briefly; Draft sits ~5s; Render takes most of the time;
  // Finalize lights up in the last seconds before status flips to "success".
  const generatingCurrent =
    scriptStep < 2
      ? 1
      : elapsedSeconds < 5
        ? 2
        : elapsedSeconds < 75
          ? 3
          : 4

  /** Pill toggle for team members to flip between curated demo cards and the
   *  free-text URL flow. Inline component because nothing else needs it. */
  function DemoModeToggle({
    value,
    onChange,
    disabled,
  }: {
    value: boolean
    onChange: (v: boolean) => void
    disabled?: boolean
  }) {
    return (
      <div
        className="inline-flex items-center gap-1 rounded-full border border-border bg-card p-1 text-body-sm"
        role="tablist"
        aria-label="Input mode"
      >
        <button
          type="button"
          role="tab"
          aria-selected={value}
          onClick={() => onChange(true)}
          disabled={disabled}
          className={
            "rounded-full px-3 py-1.5 transition-colors " +
            (value
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          Demo listings
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={!value}
          onClick={() => onChange(false)}
          disabled={disabled}
          className={
            "rounded-full px-3 py-1.5 transition-colors " +
            (!value
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          Custom URL
        </button>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <Header />

      {/* idle */}
      {state.screen === "idle" && (
        <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center gap-10 px-6 py-12">
          <div className="flex w-full flex-col items-center gap-3 text-center">
            <h1 className="text-display-xl">
              Turn an Airbnb listing into a 15-second video.
            </h1>
            <p className="text-body max-w-prose text-muted-foreground">
              {demoMode
                ? "Pick a demo listing. The agent picks the hook, the angle, and the pacing."
                : "Paste a link. The agent picks the hook, the angle, and the pacing."}
            </p>
            {isTeam && (
              <DemoModeToggle
                value={demoMode}
                onChange={setDemoMode}
                disabled={submitting}
              />
            )}
          </div>

          {demoNotice ? (
            <div
              role="status"
              className="w-full max-w-3xl rounded-lg border border-primary/40 bg-primary/10 px-4 py-3 text-body-sm text-foreground"
            >
              {demoNotice}
            </div>
          ) : null}

          {demoMode && me ? (
            <DemoListingPicker
              listings={me.demo_listings}
              onPick={(url) => {
                setDemoNotice(null)
                void handleGenerate(url)
              }}
              loading={submitting}
              exclusive={!isTeam}
            />
          ) : null}

          {!demoMode && isTeam && (
            <UrlInput
              onSubmit={handleGenerate}
              loading={submitting}
              outpaintEnabled={outpaintEnabled}
              onOutpaintChange={setOutpaintEnabled}
            />
          )}
        </main>
      )}

      {/* preparing — phase 1 (storyboard generation) is running */}
      {state.screen === "preparing" && (
        <PreparingScreen listingUrl={state.listing_url} onCancel={goIdle} />
      )}

      {/* storyboard */}
      {state.screen === "storyboard" && (
        <Storyboard
          listing={state.listing}
          phase1={state.phase1}
          overrides={state.overrides}
          onChange={updateOverrides}
          onRender={() =>
            void handleRender(state.listing, state.phase1, state.overrides)
          }
          onBack={goIdle}
          submitting={submitting}
        />
      )}

      {/* starting (postGenerate in flight) + generating (polling Hera) — same UI */}
      {(state.screen === "starting" || state.screen === "generating") && (
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
            <div className="flex flex-col items-center gap-6">
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
              <PublishCard internalVideoId={state.internalVideoId} />
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

/** Wraps the YouTube publish CTA on the done screen. Three states:
 *   - persistence missed (no internalVideoId): show 'not saved' note, no button
 *   - YouTube not connected: show ConnectYouTubeBadge so a single click flow
 *     authorises and returns the user here
 *   - YouTube connected + saved: show PublishButton (one-click upload) */
function PublishCard({ internalVideoId }: { internalVideoId: string | null }) {
  return (
    <Card className="flex w-full max-w-[420px] flex-col gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-label text-muted-foreground">Publish</span>
        <ConnectYouTubeBadge />
      </div>
      {internalVideoId ? (
        <PublishButton internalVideoId={internalVideoId} />
      ) : (
        <p className="text-body-sm text-muted-foreground">
          Saving to your library failed — publish from{" "}
          <a href="/dashboard" className="underline hover:text-foreground">
            the dashboard
          </a>{" "}
          once it shows up.
        </p>
      )}
    </Card>
  )
}

/** Phase-1 loading screen. Cycles through scripted status lines so the user
 *  has a sense of forward motion instead of staring at a static spinner for
 *  ~15s while the multi-agent pipeline runs. The pacing is decoupled from the
 *  actual backend progress (we don't get progress events) — it's an *honest*
 *  list of stages the agent goes through, just timed to look right. */
function PreparingScreen({
  listingUrl,
  onCancel,
}: {
  listingUrl: string
  onCancel: () => void
}) {
  const STAGES = [
    "Reading the listing…",
    "Watching the photos…",
    "Parsing the reviews…",
    "Finding your guest…",
    "Drafting the storyboard…",
  ] as const
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const interval = window.setInterval(() => {
      setStage((s) => (s + 1 < STAGES.length ? s + 1 : s))
    }, 3500)
    return () => window.clearInterval(interval)
  }, [STAGES.length])

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-8 px-6 py-16">
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-label text-muted-foreground">Phase 1</p>
        <h2 className="text-display-lg">Building your storyboard.</h2>
        <p className="text-body text-muted-foreground">
          Multi-agent pipeline in motion. Usually 10–20 seconds.
        </p>
      </div>

      <Card className="w-full max-w-lg p-6">
        <ul className="flex flex-col gap-3">
          {STAGES.map((label, i) => {
            const done = i < stage
            const active = i === stage
            return (
              <li key={label} className="flex items-center gap-3">
                <span
                  className={
                    "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border " +
                    (done
                      ? "border-primary bg-primary text-primary-foreground"
                      : active
                        ? "border-primary text-primary"
                        : "border-border text-muted-foreground")
                  }
                  aria-hidden
                >
                  {done ? (
                    <svg viewBox="0 0 12 12" className="h-3 w-3 fill-current">
                      <path d="M10.28 3.22a.75.75 0 0 1 0 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0L2.22 6.28a.75.75 0 1 1 1.06-1.06l1.97 1.97 3.97-3.97a.75.75 0 0 1 1.06 0z" />
                    </svg>
                  ) : active ? (
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                  ) : null}
                </span>
                <span
                  className={
                    "text-body-sm " +
                    (done
                      ? "text-foreground"
                      : active
                        ? "text-foreground"
                        : "text-muted-foreground")
                  }
                >
                  {label}
                </span>
              </li>
            )
          })}
        </ul>
        <p className="mt-5 truncate border-t border-border pt-4 text-body-sm text-muted-foreground">
          <span className="text-foreground">Listing:</span> {listingUrl}
        </p>
      </Card>

      <Button onClick={onCancel} variant="link">
        Cancel
      </Button>
    </main>
  )
}
