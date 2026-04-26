import { useState } from "react"
import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import type { DashboardVideo } from "@/api/dashboard"

// Demo seed videos use synthetic `YT_<hex>` IDs (see migration 005). YouTube
// returns its 'no thumbnail' grey placeholder for those with HTTP 200, so the
// onError handler never fires — detect them up front instead.
function realThumbnailUrl(youtubeId: string | null): string | null {
  if (!youtubeId) return null
  if (youtubeId.startsWith("YT_")) return null
  return `https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`
}

function fallbackThumbnailUrl(videoId: string): string {
  return `https://picsum.photos/seed/${encodeURIComponent(videoId)}/640/360`
}

export function VideoListItem({ video }: { video: DashboardVideo }) {
  const initialSrc = realThumbnailUrl(video.youtube_video_id) ?? fallbackThumbnailUrl(video.id)
  const [src, setSrc] = useState(initialSrc)
  const [loaded, setLoaded] = useState(false)

  return (
    <Link to={`/dashboard/v/${video.id}`} className="block">
      <Card className="hover:bg-muted/40 flex items-center gap-4 p-4 transition-colors">
        <div className="bg-muted relative h-20 w-32 shrink-0 overflow-hidden rounded">
          <img
            src={src}
            alt=""
            loading="lazy"
            decoding="async"
            onLoad={() => setLoaded(true)}
            onError={() => {
              const fallback = fallbackThumbnailUrl(video.id)
              if (src !== fallback) {
                setSrc(fallback)
                setLoaded(false)
              }
            }}
            className={`h-full w-full object-cover transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
          />
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

export function VideoListItemSkeleton() {
  return (
    <Card className="flex animate-pulse items-center gap-4 p-4">
      <div className="bg-muted h-20 w-32 shrink-0 rounded" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="bg-muted h-4 w-2/3 rounded" />
        <div className="flex gap-2">
          <div className="bg-muted h-5 w-20 rounded-full" />
          <div className="bg-muted h-5 w-14 rounded-full" />
        </div>
      </div>
      <div className="space-y-2 text-right">
        <div className="bg-muted ml-auto h-6 w-16 rounded" />
        <div className="bg-muted ml-auto h-3 w-10 rounded" />
      </div>
    </Card>
  )
}
