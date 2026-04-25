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

    // eslint-disable-next-line react-hooks/set-state-in-effect
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
