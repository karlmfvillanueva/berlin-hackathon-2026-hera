// src/components/VideoPlayer.tsx
import { Download, RotateCw, Share2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

interface VideoPlayerProps {
  fileUrl: string
  /** Optional caption shown below the player (e.g. the agent's hook). */
  caption?: string
  onDownload?: () => void
  onRegenerate?: () => void
  onShare?: () => void
  downloading?: boolean
  regenerating?: boolean
  downloadError?: boolean
}

export function VideoPlayer({
  fileUrl,
  caption,
  onDownload,
  onRegenerate,
  onShare,
  downloading,
  regenerating,
  downloadError,
}: VideoPlayerProps) {
  return (
    <Card className="flex w-full max-w-md flex-col overflow-hidden p-0">
      <div className="aspect-[9/16] max-h-[560px] w-full bg-foreground/5">
        <video
          src={fileUrl}
          autoPlay
          muted
          loop
          controls
          className="h-full w-full object-contain"
        />
      </div>

      <div className="flex flex-col gap-3 p-5">
        <div>
          <p className="text-label text-muted-foreground">Output · 15 sec · 9:16</p>
          {caption && <p className="text-rationale mt-1">{caption}</p>}
        </div>

        {downloadError ? (
          <p className="text-body-sm text-destructive">
            Download failed. Try regenerating.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button onClick={onDownload} disabled={downloading}>
              <Download />
              {downloading ? "Downloading…" : "Download MP4"}
            </Button>
            <Button onClick={onRegenerate} variant="outline" disabled={regenerating}>
              <RotateCw />
              {regenerating ? "Regenerating…" : "Regenerate"}
            </Button>
            <Button onClick={onShare} variant="outline">
              <Share2 />
              Share link
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}
