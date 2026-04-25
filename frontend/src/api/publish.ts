import { authedFetch, BACKEND_URL } from "./client"

export type PublishResponse = {
  youtube_video_id: string
  youtube_channel_id: string | null
  visibility: string
  published_at: string | null
}

export async function publishVideo(
  internalVideoId: string,
  visibility: "unlisted" | "public" | "private" = "unlisted",
): Promise<PublishResponse> {
  const res = await authedFetch(
    `${BACKEND_URL}/api/videos/${internalVideoId}/publish`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ visibility }),
    },
  )
  if (!res.ok) {
    const body = await res.text()
    throw new Error(body || `publish failed: ${res.status}`)
  }
  return res.json() as Promise<PublishResponse>
}

export type MetricsRefreshResponse = {
  view_count: number
  like_count: number
  comment_count: number
  observed_at: string
}

export async function refreshMetrics(internalVideoId: string): Promise<MetricsRefreshResponse> {
  const res = await authedFetch(
    `${BACKEND_URL}/api/videos/${internalVideoId}/metrics/refresh`,
    { method: "POST" },
  )
  if (!res.ok) throw new Error(`refresh metrics ${res.status}`)
  return res.json() as Promise<MetricsRefreshResponse>
}
