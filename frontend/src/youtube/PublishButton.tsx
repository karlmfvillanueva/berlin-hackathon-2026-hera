import { useState } from "react"
import { Button } from "@/components/ui/button"
import { publishVideo } from "@/api/publish"
import { useYouTubeStatus } from "./useYouTubeStatus"

type Props = {
  internalVideoId: string
  onPublished?: (youtubeVideoId: string) => void
}

export function PublishButton({ internalVideoId, onPublished }: Props) {
  const { status } = useYouTubeStatus()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  if (!status?.connected) {
    return (
      <p className="text-body-sm text-muted-foreground">
        Connect YouTube on the dashboard to publish.
      </p>
    )
  }

  async function onClick() {
    setSubmitting(true)
    setError(null)
    try {
      const res = await publishVideo(internalVideoId, "unlisted")
      setDone(true)
      onPublished?.(res.youtube_video_id)
    } catch (e) {
      setError(String(e))
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return <p className="text-body-sm">Published as unlisted on YouTube.</p>
  }

  return (
    <div className="flex flex-col gap-2">
      <Button onClick={onClick} disabled={submitting}>
        {submitting ? "Uploading…" : "Publish to YouTube"}
      </Button>
      {error && (
        <p className="text-body-sm text-destructive">{error}</p>
      )}
    </div>
  )
}
