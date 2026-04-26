import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { Plus } from "lucide-react"
import { getDashboard, getBeliefEvolution } from "@/api/dashboard"
import type {
  BeliefEvolutionItem,
  DashboardAggregate,
  DashboardVideo,
} from "@/api/dashboard"
import { MetricsCard } from "@/components/MetricsCard"
import { VideoListItem } from "@/components/VideoListItem"
import { BeliefEvolutionCard } from "@/components/BeliefEvolutionCard"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ConnectYouTubeBadge } from "@/youtube/ConnectYouTubeBadge"

export function Dashboard() {
  const [videos, setVideos] = useState<DashboardVideo[] | null>(null)
  const [aggregate, setAggregate] = useState<DashboardAggregate | null>(null)
  const [beliefs, setBeliefs] = useState<BeliefEvolutionItem[]>([])
  const [beliefDemo, setBeliefDemo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const ytConnected = searchParams.get("youtube_connected")
  const ytError = searchParams.get("youtube_error")

  useEffect(() => {
    getDashboard()
      .then((res) => {
        setVideos(res.videos)
        setAggregate(res.aggregate)
      })
      .catch((e) => setError(String(e)))
    getBeliefEvolution()
      .then((res) => {
        setBeliefs(res.items)
        setBeliefDemo(res.is_demo_data)
      })
      .catch(() => {
        // Silent — beliefs panel just stays empty.
      })
  }, [])

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 p-8">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-display">Dashboard</h1>
          <p className="text-body-sm text-muted-foreground">
            Posts, performance, and belief shifts.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ConnectYouTubeBadge />
          <Link
            to="/app"
            className="inline-flex items-center gap-1.5 rounded-sm bg-primary px-4 py-2 text-body-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            New film
          </Link>
        </div>
      </header>

      {ytConnected && (
        <Card className="border-primary/30 bg-primary/5 p-4">
          <p className="text-body-sm">YouTube connected. Future renders can auto-deploy.</p>
        </Card>
      )}
      {ytError && (
        <Card className="border-destructive/30 bg-destructive/5 p-4">
          <p className="text-body-sm">
            YouTube connection issue: <b>{ytError}</b>
            {ytError === "no_channel" && " — visit studio.youtube.com to create a channel."}
          </p>
        </Card>
      )}
      {error && (
        <Card className="border-destructive/30 bg-destructive/5 p-4">
          <p className="text-body-sm">Could not load dashboard: {error}</p>
        </Card>
      )}

      {aggregate && (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <MetricsCard
            label="Total videos"
            value={aggregate.total_videos.toLocaleString()}
            hint={`${aggregate.total_published} published to YouTube`}
          />
          <MetricsCard
            label="Total views"
            value={aggregate.total_views.toLocaleString()}
            hint="across all snapshots"
          />
          <MetricsCard
            label="Top performer"
            value={aggregate.top_performer_id ? "see list ↓" : "—"}
          />
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-body font-semibold">Posts</h2>
        {videos === null && <p className="text-body-sm text-muted-foreground">Loading…</p>}
        {videos !== null && videos.length === 0 && (
          <Card className="flex flex-col items-start gap-3 p-6">
            <p className="text-body-sm text-muted-foreground">
              No videos yet. Drop an Airbnb URL and let the agent direct one.
            </p>
            <Link
              to="/app"
              className="inline-flex items-center gap-1.5 rounded-sm bg-primary px-4 py-2 text-body-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              <Plus className="h-4 w-4" />
              Make my first film
            </Link>
          </Card>
        )}
        {videos?.map((v) => <VideoListItem key={v.id} video={v} />)}
      </section>

      {beliefs.length > 0 && (
        <section className="flex flex-col gap-3">
          <header className="flex items-center gap-3">
            <h2 className="text-body font-semibold">Belief evolution</h2>
            {beliefDemo && <Badge variant="secondary">Demo data</Badge>}
          </header>
          <p className="text-body-sm text-muted-foreground">
            Each card maps a seed belief to retention against the baseline. Direction and magnitude
            here are the signal the agent would learn from over time.
          </p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {beliefs.map((item) => (
              <BeliefEvolutionCard key={item.rule_key} item={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
