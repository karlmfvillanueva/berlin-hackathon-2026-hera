import { useEffect, useRef, useState } from "react";
import "./App.css";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

type JobStatus = "in-progress" | "success" | "failed";

type GetVideoResponse = {
  video_id: string;
  project_url?: string | null;
  status: JobStatus;
  outputs: Array<{
    status: JobStatus;
    file_url?: string | null;
    error?: string | null;
  }>;
};

function App() {
  const [prompt, setPrompt] = useState(
    "A bright animated lower-third revealing the title 'Berlin 2026'.",
  );
  const [submitting, setSubmitting] = useState(false);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFileUrl(null);
    setStatus(null);
    setVideoId(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/videos`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
      const data = (await res.json()) as { video_id: string };
      setVideoId(data.video_id);
      setStatus("in-progress");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!videoId || status !== "in-progress") return;
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(`${BACKEND_URL}/api/videos/${videoId}`);
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data = (await res.json()) as GetVideoResponse;
        if (cancelled) return;
        setStatus(data.status);
        if (data.status === "success") {
          setFileUrl(data.outputs[0]?.file_url ?? null);
        } else if (data.status === "failed") {
          setError(data.outputs[0]?.error ?? "Hera reported failure");
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    }
    pollRef.current = window.setInterval(poll, 4000);
    void poll();
    return () => {
      cancelled = true;
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [videoId, status]);

  return (
    <main className="container">
      <h1>Hera Video Studio</h1>
      <p className="muted">Berlin Hackathon 2026 · Vite + FastAPI + Hera</p>

      <form onSubmit={submit}>
        <label htmlFor="prompt">Prompt</label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          required
        />
        <button type="submit" disabled={submitting || status === "in-progress"}>
          {submitting ? "Submitting" : status === "in-progress" ? "Rendering" : "Generate"}
        </button>
      </form>

      {videoId && (
        <section className="job">
          <div>
            <span className="label">Video ID</span>
            <code>{videoId}</code>
          </div>
          <div>
            <span className="label">Status</span>
            <span>{status ?? "—"}</span>
          </div>
          {fileUrl && <video src={fileUrl} controls autoPlay loop className="output" />}
        </section>
      )}

      {error && <p className="error">{error}</p>}
    </main>
  );
}

export default App;
