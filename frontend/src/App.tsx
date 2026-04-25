import { useEffect, useRef, useState } from "react";
import "./index.css";
import type { AppState, AgentDecision, ScrapedListing } from "./types";
import { postListing, postGenerate, pollStatus, postRegenerate } from "./api/client";
import { Header } from "./components/Header";
import { UrlInput } from "./components/UrlInput";
import { AttributeCard } from "./components/AttributeCard";
import { StatusRow } from "./components/StatusRow";
import { VideoPlayer } from "./components/VideoPlayer";
import { RationaleRail } from "./components/RationaleRail";
import { ErrorState } from "./components/ErrorState";

const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS = 3 * 60 * 1000;


export default function App() {
  const [state, setState] = useState<AppState>({ screen: "idle" });
  const [listingUrl, setListingUrl] = useState(
    "https://www.airbnb.com/rooms/kreuzberg-loft-demo",
  );
  const [submitting, setSubmitting] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [scriptStep, setScriptStep] = useState(0);
  const [outpaintEnabled, setOutpaintEnabled] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(false);

  const pollIntervalRef = useRef<number | null>(null);
  const pollStartRef = useRef<number>(0);

  function clearPolling() {
    if (pollIntervalRef.current !== null) {
      window.clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }

  function goIdle() {
    clearPolling();
    setElapsedSeconds(0);
    setScriptStep(0);
    setOutpaintEnabled(false);
    setDownloadError(false);
    setState({ screen: "idle" });
  }

  async function handleGenerate(url: string) {
    setListingUrl(url);
    setSubmitting(true);
    try {
      const { listing, decision } = await postListing(url, outpaintEnabled);
      setState({ screen: "reviewing", listing, decision });
    } catch (err) {
      setState({
        screen: "error",
        message: err instanceof Error ? err.message : "Failed to fetch listing.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleContinue(listing: ScrapedListing, decision: AgentDecision) {
    setSubmitting(true);
    setScriptStep(0);
    setElapsedSeconds(0);
    try {
      const { video_id } = await postGenerate(listingUrl, listing, decision);
      setState({ screen: "generating", listing, decision, videoId: video_id, outpaint_enabled: outpaintEnabled });
    } catch (err) {
      setState({
        screen: "error",
        message: err instanceof Error ? err.message : "Failed to start generation.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegenerate() {
    if (state.screen !== "done") return;
    const { listing, decision } = state;
    setRegenerating(true);
    try {
      const { video_id, decision: newDecision } = await postRegenerate(listingUrl, listing, decision);
      setState({ screen: "generating", listing, decision: newDecision, videoId: video_id, outpaint_enabled: outpaintEnabled });
    } catch (err) {
      setState({
        screen: "error",
        message: err instanceof Error ? err.message : "Failed to regenerate.",
      });
    } finally {
      setRegenerating(false);
    }
  }

  async function handleDownload() {
    if (state.screen !== "done") return;
    setDownloadError(false);
    setDownloading(true);

    async function fetchAndTrigger(fileUrl: string): Promise<boolean> {
      const res = await fetch(fileUrl);
      if (!res.ok) return false;
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = "hera-video.mp4";
      a.click();
      URL.revokeObjectURL(objectUrl);
      return true;
    }

    try {
      const ok = await fetchAndTrigger(state.fileUrl);
      if (!ok) {
        // Refresh the file URL via polling and retry once
        const data = await pollStatus(state.videoId);
        const freshUrl = data.outputs[0]?.file_url ?? "";
        if (freshUrl) {
          const retryOk = await fetchAndTrigger(freshUrl);
          if (!retryOk) setDownloadError(true);
        } else {
          setDownloadError(true);
        }
      }
    } catch {
      setDownloadError(true);
    } finally {
      setDownloading(false);
    }
  }

  // Polling: keyed to the videoId so it re-runs only when a new job starts
  useEffect(() => {
    if (state.screen !== "generating") return;
    const { videoId, listing, decision } = state;

    let cancelled = false;
    pollStartRef.current = Date.now();

    setScriptStep(1);
    const step2Timer = window.setTimeout(() => {
      if (!cancelled) setScriptStep(2);
    }, 1000);

    async function doPoll() {
      if (cancelled) return;

      const elapsed = Date.now() - pollStartRef.current;
      setElapsedSeconds(Math.floor(elapsed / 1000));

      if (elapsed >= POLL_TIMEOUT_MS) {
        clearPolling();
        if (!cancelled) {
          setState({ screen: "error", message: "Generation timed out after 3 minutes." });
        }
        return;
      }

      try {
        const data = await pollStatus(videoId);
        if (cancelled) return;

        if (data.status === "success") {
          clearPolling();
          const fileUrl = data.outputs[0]?.file_url ?? "";
          setState({ screen: "done", listing, decision, fileUrl, videoId });
        } else if (data.status === "failed") {
          clearPolling();
          setState({
            screen: "error",
            message: data.outputs[0]?.error ?? "Hera reported a failure.",
          });
        }
      } catch (err) {
        if (!cancelled) {
          clearPolling();
          setState({
            screen: "error",
            message: err instanceof Error ? err.message : "Polling failed.",
          });
        }
      }
    }

    void doPoll();
    pollIntervalRef.current = window.setInterval(doPoll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearPolling();
      window.clearTimeout(step2Timer);
    };
    // videoId is stable for the lifetime of a generation job; listing/decision don't change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.screen === "generating" ? state.videoId : null]);

  const estRemaining = Math.max(0, 90 - elapsedSeconds);

  return (
    <div className="min-h-screen bg-white flex flex-col font-sans">
      <Header />

      {/* Screen 1 — idle */}
      {state.screen === "idle" && (
        <main className="flex-1 flex items-center justify-center">
          <UrlInput
            onSubmit={handleGenerate}
            loading={submitting}
            outpaintEnabled={outpaintEnabled}
            onOutpaintChange={setOutpaintEnabled}
          />
        </main>
      )}

      {/* Screen 2 — reviewing */}
      {state.screen === "reviewing" && (
        <main className="flex-1 flex flex-col px-8 pt-10 pb-8 gap-6 max-w-[1280px] mx-auto w-full">
          <div className="flex flex-col gap-1">
            <h2 className="text-[28px] font-bold text-black leading-[1.2] m-0">
              Here's what we found.
            </h2>
            <p className="text-[14px] font-normal text-[#666666] leading-[1.4] max-w-[640px] m-0">
              Our agent scraped the listing and picked these attributes. Approve each card or edit before we generate.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-5">
            <AttributeCard label="TITLE">
              <span className="line-clamp-3">{state.listing.title}</span>
            </AttributeCard>

            <AttributeCard label="LOCATION">
              <span className="line-clamp-3">{state.listing.location}</span>
            </AttributeCard>

            <AttributeCard label="VIBES / TAGS">
              <span className="line-clamp-3">{state.decision.vibes}</span>
            </AttributeCard>

            <AttributeCard label={`HERO IMAGES (${state.decision.selected_image_urls.length})`}>
              <div className="flex flex-col gap-2">
                <div className="flex gap-2 overflow-hidden">
                  {state.decision.selected_image_urls.slice(0, 4).map((url, i) => (
                    <div
                      key={i}
                      className="w-[88px] h-[88px] bg-[#E5E5E5] shrink-0 overflow-hidden"
                    >
                      <img
                        src={url}
                        alt=""
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = "none";
                        }}
                      />
                    </div>
                  ))}
                  {state.decision.selected_image_urls.length === 0 && (
                    <div className="w-[88px] h-[88px] bg-[#E5E5E5]" />
                  )}
                </div>
                {state.decision.selected_image_urls.length > 4 && (
                  <span className="text-[12px] font-normal text-[#9CA3AF]">
                    +{state.decision.selected_image_urls.length - 4} more · agent picked these as strongest
                  </span>
                )}
              </div>
            </AttributeCard>

            <AttributeCard label="BEDROOMS / SLEEPS">
              <span className="line-clamp-3">{state.listing.bedrooms_sleeps}</span>
            </AttributeCard>

            <AttributeCard label="PRICE / NIGHT">
              <span className="line-clamp-3">{state.listing.price_display}</span>
            </AttributeCard>
          </div>

          <div className="flex justify-between items-center pt-2">
            <button
              onClick={goIdle}
              className="bg-white border border-black text-[12px] font-normal text-black px-[18px] py-3 cursor-pointer hover:bg-[#FAFAFA] transition-colors duration-100"
            >
              Back
            </button>
            <button
              onClick={() => handleContinue(state.listing, state.decision)}
              disabled={submitting}
              className="bg-black text-white text-[14px] font-bold px-7 py-3.5 cursor-pointer hover:bg-[#1A1A1A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-100"
            >
              {submitting ? "Starting..." : "Continue → Generate video"}
            </button>
          </div>
        </main>
      )}

      {/* Screen 3 — generating */}
      {state.screen === "generating" && (
        <main className="flex-1 flex flex-col items-center justify-center px-8 py-16 gap-6">
          <h2 className="text-[32px] font-bold text-black text-center m-0">
            Generating your video...
          </h2>
          <p className="text-[15px] font-normal text-[#666666] leading-[1.4] max-w-[560px] text-center m-0">
            Our agent is making editorial calls (hook, pacing, emphasis). Hang tight.
          </p>

          <div className="w-[520px] bg-white border border-black p-6 flex flex-col gap-4">
            <StatusRow
              state={scriptStep >= 1 ? "done" : "pending"}
              label="Analyzed listing"
            />
            {state.outpaint_enabled && (
              <StatusRow state="active" label="Outpainting photos to 9:16…" />
            )}
            <StatusRow
              state={scriptStep >= 2 ? "done" : scriptStep === 1 ? "active" : "pending"}
              label="Drafted script with hook + pacing"
            />
            <StatusRow
              state="active"
              label="Rendering motion graphics with Hera"
              suffix={`~${estRemaining}s`}
            />
            <StatusRow state="pending" label="Finalizing" />
          </div>

          <p className="text-[12px] font-normal text-[#9CA3AF] text-center m-0">
            Usually takes 60–90 seconds. You can leave this tab.
          </p>

          <button
            onClick={goIdle}
            className="text-[13px] font-normal text-[#555555] underline cursor-pointer bg-transparent border-none hover:text-black transition-colors duration-100 p-0"
          >
            Cancel
          </button>
        </main>
      )}

      {/* Screen 4 — done */}
      {state.screen === "done" && (
        <main className="flex-1 flex gap-8 p-8 max-w-[1280px] mx-auto w-full">
          <div className="flex-1 flex flex-col gap-5 min-w-0">
            <div className="flex flex-col gap-1.5">
              <span className="text-[26px] font-bold text-black">Your video</span>
              <span className="text-[13px] font-normal text-[#666666]">
                15s · 1080p · 9:16 · MP4
              </span>
            </div>

            <div className="flex justify-center">
              <VideoPlayer fileUrl={state.fileUrl} />
            </div>

            <div className="flex gap-3 flex-col">
              {downloadError ? (
                <p className="text-[13px] text-black">Download failed. Try regenerating.</p>
              ) : (
                <div className="flex gap-3">
                  <button
                    onClick={() => void handleDownload()}
                    disabled={downloading}
                    className="bg-black text-white text-[14px] font-bold px-6 py-3.5 border border-black hover:bg-[#1A1A1A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-100 inline-flex items-center cursor-pointer"
                  >
                    ↓&nbsp;&nbsp;{downloading ? "Downloading..." : "Download MP4"}
                  </button>
                  <button
                    onClick={() => void handleRegenerate()}
                    disabled={regenerating}
                    className="bg-white border border-black text-[14px] font-normal text-black px-6 py-3.5 cursor-pointer hover:bg-[#FAFAFA] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-100"
                  >
                    ↻&nbsp;&nbsp;{regenerating ? "Regenerating..." : "Regenerate"}
                  </button>
                </div>
              )}
              <button
                onClick={() => void navigator.clipboard.writeText(state.fileUrl)}
                className="bg-white border border-black text-[14px] font-normal text-black px-6 py-3.5 cursor-pointer hover:bg-[#FAFAFA] transition-colors duration-100"
              >
                ↗&nbsp;&nbsp;Share link
              </button>
            </div>
          </div>

          <RationaleRail decision={state.decision} />
        </main>
      )}

      {/* Error */}
      {state.screen === "error" && (
        <ErrorState message={state.message} onRetry={goIdle} />
      )}
    </div>
  );
}
