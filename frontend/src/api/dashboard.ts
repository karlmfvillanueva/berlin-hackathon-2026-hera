import { authedFetch, BACKEND_URL } from "./client"

export type DashboardVideo = {
  id: string
  listing_url: string
  listing_title: string | null
  persona: string | null
  youtube_video_id: string | null
  published_at: string | null
  is_demo_seed: boolean
  latest_view_count: number | null
  latest_like_count: number | null
}

export type DashboardAggregate = {
  total_videos: number
  total_published: number
  total_views: number
  top_performer_id: string | null
}

export type DashboardResponse = {
  videos: DashboardVideo[]
  aggregate: DashboardAggregate
}

export async function getDashboard(includeDemo = true): Promise<DashboardResponse> {
  const res = await authedFetch(
    `${BACKEND_URL}/api/dashboard?include_demo=${includeDemo}`,
  )
  if (!res.ok) throw new Error(`dashboard ${res.status}`)
  return res.json() as Promise<DashboardResponse>
}

export type TimeseriesPoint = {
  observed_at: string
  view_count: number | null
  like_count: number | null
  comment_count: number | null
  avg_view_duration_s: number | null
  retention_50pct: number | null
}

export async function getTimeseries(internalVideoId: string): Promise<TimeseriesPoint[]> {
  const res = await authedFetch(`${BACKEND_URL}/api/videos/${internalVideoId}/timeseries`)
  if (!res.ok) throw new Error(`timeseries ${res.status}`)
  return res.json() as Promise<TimeseriesPoint[]>
}

export type BeliefEvolutionItem = {
  rule_key: string
  rule_text: string
  current_confidence: number
  new_confidence: number
  sample_size: number
  retention_delta: number
  rationale: string
  is_demo: boolean
}

export type BeliefEvolutionResponse = {
  items: BeliefEvolutionItem[]
  is_demo_data: boolean
}

export async function getBeliefEvolution(): Promise<BeliefEvolutionResponse> {
  const res = await authedFetch(`${BACKEND_URL}/api/beliefs/evolution`)
  if (!res.ok) throw new Error(`belief evolution ${res.status}`)
  return res.json() as Promise<BeliefEvolutionResponse>
}
