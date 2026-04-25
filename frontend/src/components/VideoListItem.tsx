import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import type { DashboardVideo } from "@/api/dashboard"

function thumbnailUrl(youtubeId: string | null): string | null {
  if (!youtubeId) return null
  return `https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`
}

export function VideoListItem({ video }: { video: DashboardVideo }) {
  const thumb = thumbnailUrl(video.youtube_video_id)
  return (
    <Link to={`/dashboard/v/${video.id}`} className="block">
      <Card className="hover:bg-muted/40 flex items-center gap-4 p-4 transition-colors">
        <div className="bg-muted relative h-20 w-32 shrink-0 overflow-hidden rounded">
          {thumb ? (
            <img src={thumb} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="text-body-sm text-muted-foreground flex h-full items-center justify-center">
              Not yet on YT
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-body truncate font-medium">
            {video.listing_title ?? video.listing_url}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {video.persona && (
              <Badge variant="secondary">{video.persona}</Badge>
            )}
            {video.is_demo_seed && (
              <Badge variant="secondary">Demo</Badge>
            )}
            {video.published_at && (
              <span className="text-body-sm text-muted-foreground">
                {new Date(video.published_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-display">
            {(video.latest_view_count ?? 0).toLocaleString()}
          </p>
          <p className="text-body-sm text-muted-foreground">views</p>
        </div>
      </Card>
    </Link>
  )
}
