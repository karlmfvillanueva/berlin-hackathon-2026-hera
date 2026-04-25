import { useEffect, useState, useCallback } from "react"
import { getYouTubeStatus, type YouTubeStatus } from "@/api/youtube"

export function useYouTubeStatus() {
  const [status, setStatus] = useState<YouTubeStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(() => {
    setLoading(true)
    getYouTubeStatus()
      .then((s) => setStatus(s))
      .catch(() => setStatus({ connected: false }))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { status, loading, refresh }
}
