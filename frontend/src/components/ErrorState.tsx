// src/components/ErrorState.tsx
import { AlertTriangle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

const ERROR_MESSAGES: Record<string, string> = {
  scrape_blocked:
    "Airbnb blocked us on that listing. Try a different one, or paste a listing we've seen before.",
  scrape_failed: "We couldn't read that listing. The page may have changed. Try again.",
  fixture_not_found: "We don't have a fixture for that listing yet.",
  classifier_failed: "The agent couldn't read this listing. Try another.",
  hera_submission_failed: "Video generation failed. Try again.",
  hera_unreachable: "Video generation failed. Try again.",
  timeout: "This is taking longer than expected.",
}

function parseMessage(raw: string): string {
  try {
    const parsed: unknown = JSON.parse(raw)
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "detail" in parsed &&
      parsed.detail !== null &&
      typeof parsed.detail === "object" &&
      "error" in parsed.detail &&
      typeof (parsed.detail as Record<string, unknown>).error === "string"
    ) {
      const code = (parsed.detail as Record<string, string>).error
      if (code in ERROR_MESSAGES) {
        return ERROR_MESSAGES[code]
      }
    }
  } catch {
    // not JSON — fall through
  }
  return raw
}

interface ErrorStateProps {
  message: string
  onRetry: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="flex w-full max-w-md flex-col gap-4 p-6">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="size-4" />
          <span className="text-label">Something went wrong</span>
        </div>
        <p className="text-rationale">
          {parseMessage(message) || "We couldn't generate the video. Try again."}
        </p>
        <Button onClick={onRetry} variant="outline" className="self-start">
          Try again
        </Button>
      </Card>
    </div>
  )
}
