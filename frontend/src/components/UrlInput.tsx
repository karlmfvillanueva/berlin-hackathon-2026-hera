// src/components/UrlInput.tsx
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

const FIXTURE_URL = "https://www.airbnb.com/rooms/kreuzberg-loft-demo"

interface UrlInputProps {
  onSubmit: (url: string) => void
  loading: boolean
  outpaintEnabled: boolean
  onOutpaintChange: (v: boolean) => void
}

export function UrlInput({
  onSubmit,
  loading,
  outpaintEnabled,
  onOutpaintChange,
}: UrlInputProps) {
  const [value, setValue] = useState(FIXTURE_URL)
  const [validationError, setValidationError] = useState<string | null>(null)

  function handleSubmit() {
    setValidationError(null)
    try {
      new URL(value)
    } catch {
      setValidationError("Enter a valid URL.")
      return
    }
    onSubmit(value)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit()
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-8 px-6 py-16">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-display-xl">Turn an Airbnb listing into a 15-second video.</h1>
        <p className="text-body max-w-prose text-muted-foreground">
          Paste a link. Our agent picks the hook, the angle, and the pacing.
        </p>
      </div>

      <Card className="flex w-full flex-col gap-4 p-6">
        <span className="text-label text-muted-foreground">Listing URL</span>
        <div className="flex gap-3">
          <Input
            type="url"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={FIXTURE_URL}
            aria-label="Airbnb listing URL"
          />
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Loading…" : "Generate Video"}
          </Button>
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-body-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={outpaintEnabled}
            onChange={(e) => onOutpaintChange(e.target.checked)}
            className="h-4 w-4 cursor-pointer"
          />
          Outpaint photos to 9:16
        </label>

        {validationError ? (
          <p className="text-body-sm text-destructive">{validationError}</p>
        ) : (
          <p className="text-body-sm text-muted-foreground/80">
            Example: airbnb.com/rooms/12345
          </p>
        )}
      </Card>
    </div>
  )
}
