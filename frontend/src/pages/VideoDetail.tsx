import { useEffect, useState } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"
import { getDashboard, getTimeseries } from "@/api/dashboard"
import type { DashboardVideo, TimeseriesPoint } from "@/api/dashboard"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Header } from "@/components/Header"
import { MetricsCard } from "@/components/MetricsCard"
import { MetricsSparkline } from "@/components/MetricsSparkline"
import { PublishButton } from "@/youtube/PublishButton"

export function VideoDetail() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const justMade = searchParams.get("just_made") === "1"
  const [video, setVideo] = useState<DashboardVideo | null>(null)
  const [series, setSeries] = useState<TimeseriesPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    // Resolve via dashboard list (cheap; one network call covers both demo + user videos).
    getDashboard()
      .then((res) => {
        const found = res.videos.find((v) => v.id === id)
        if (!found) throw new Error("Video not found")
        setVideo(found)
      })
      .catch((e) => setError(String(e)))
    getTimeseries(id)
      .then(setSeries)
      .catch((e) => setError(String(e)))
  }, [id])

  if (error) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <Card className="border-destructive/30 bg-destructive/5 p-6">
          <p className="text-body-sm">{error}</p>
        </Card>
      </div>
    )
  }
  if (!video) {
    return (
      <div className="mx-auto max-w-4xl p-8 text-muted-foreground">Loading…</div>
    )
  }

  const latest = series.length > 0 ? series[series.length - 1] : null
  const latestRetention = latest?.retention_50pct ?? null

  const decision = video.agent_decision
  const canPublish = !video.is_demo_seed && !video.youtube_video_id

  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <Header />
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-8">
        <header className="flex flex-col gap-2">
          <Link to="/dashboard" className="text-body-sm text-muted-foreground underline">
            ← Back to dashboard
          </Link>
          <h1 className="text-display">{video.listing_title ?? "Video detail"}</h1>
          <div className="flex flex-wrap gap-2">
            {video.persona && <Badge variant="secondary">{video.persona}</Badge>}
            {video.is_demo_seed && <Badge variant="secondary">Demo data</Badge>}
            {video.youtube_video_id && <Badge variant="secondary">Published</Badge>}
          </div>
        </header>

        {justMade && (
          <Card className="border-primary/30 bg-primary/5 p-4">
            <p className="text-body-sm">
              Saved to your library. Reload-safe — bookmark this URL.
            </p>
          </Card>
        )}

        {/* Player priority: rendered MP4 from Hera (always available once
            generation finished), then YouTube embed if published. Demo seeds
            without a video_url fall through to a 'still rendering' message. */}
        {video.video_url ? (
          <div className="overflow-hidden rounded-lg border bg-black">
            <video
              src={video.video_url}
              controls
              playsInline
              className="mx-auto block max-h-[640px] w-auto"
            />
          </div>
        ) : video.youtube_video_id ? (
          <div className="aspect-video w-full overflow-hidden rounded-lg border">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${video.youtube_video_id}`}
              title={video.listing_title ?? "video"}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        ) : (
          <Card className="p-6">
            <p className="text-body-sm text-muted-foreground">
              Still rendering. Refresh in a minute.
            </p>
          </Card>
        )}

        {decision?.hook && (
          <Card className="flex flex-col gap-3 p-5">
            <span className="text-label text-muted-foreground">Hook</span>
            <p className="text-body">{decision.hook}</p>
            {decision.angle && (
              <>
                <span className="text-label text-muted-foreground">Angle</span>
                <p className="text-body-sm text-muted-foreground">{decision.angle}</p>
              </>
            )}
          </Card>
        )}

        {canPublish && id && (
          <Card className="flex flex-col gap-3 p-5">
            <span className="text-label text-muted-foreground">Publish</span>
            <PublishButton internalVideoId={id} />
          </Card>
        )}

        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricsCard
          label="Latest views"
          value={(latest?.view_count ?? 0).toLocaleString()}
          hint={latest ? new Date(latest.observed_at).toLocaleDateString() : undefined}
        />
        <MetricsCard
          label="Likes"
          value={(latest?.like_count ?? 0).toLocaleString()}
        />
        <MetricsCard
          label="50% retention"
          value={
            latestRetention !== null
              ? `${(latestRetention * 100).toFixed(0)}%`
              : "—"
          }
        />
      </section>

        <Card className="flex flex-col gap-3 p-5">
          <p className="text-label text-secondary">Views over time</p>
          <MetricsSparkline
            values={series.map((s) => s.view_count ?? 0)}
            width={520}
            height={80}
          />
          <p className="text-body-sm text-muted-foreground">
            {series.length} snapshots
          </p>
        </Card>
      </div>
    </div>
  )
}
