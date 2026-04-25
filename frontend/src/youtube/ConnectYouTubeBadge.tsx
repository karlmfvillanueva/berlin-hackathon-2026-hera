import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { getYouTubeConnectUrl } from "@/api/youtube"
import { useYouTubeStatus } from "./useYouTubeStatus"

export function ConnectYouTubeBadge() {
  const { status, loading } = useYouTubeStatus()

  async function onConnect() {
    try {
      const url = await getYouTubeConnectUrl()
      window.location.assign(url)
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("connect failed", e)
    }
  }

  if (loading) {
    return <Badge variant="secondary">YouTube …</Badge>
  }
  if (!status?.connected) {
    return (
      <Button size="sm" variant="outline" onClick={onConnect}>
        Connect YouTube
      </Button>
    )
  }
  return (
    <Badge variant="secondary" title={status.channel_id ?? undefined}>
      YouTube · {status.channel_title ?? "connected"}
    </Badge>
  )
}
