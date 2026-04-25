import { authedFetch, BACKEND_URL } from "./client"

export type YouTubeStatus = {
  connected: boolean
  channel_id?: string | null
  channel_title?: string | null
  expires_soon?: boolean
}

export async function getYouTubeStatus(): Promise<YouTubeStatus> {
  const res = await authedFetch(`${BACKEND_URL}/api/youtube/status`)
  if (!res.ok) throw new Error(`youtube status ${res.status}`)
  return res.json() as Promise<YouTubeStatus>
}

export async function getYouTubeConnectUrl(): Promise<string> {
  const res = await authedFetch(`${BACKEND_URL}/api/youtube/connect-url`)
  if (!res.ok) throw new Error(`connect-url ${res.status}`)
  const data = (await res.json()) as { url: string }
  return data.url
}

export async function disconnectYouTube(): Promise<void> {
  const res = await authedFetch(`${BACKEND_URL}/api/youtube/disconnect`, {
    method: "POST",
  })
  if (!res.ok) throw new Error(`disconnect ${res.status}`)
}
