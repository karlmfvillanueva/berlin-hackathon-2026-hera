import { Star } from "lucide-react"

import type { DemoListing } from "@/api/me"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface DemoListingPickerProps {
  listings: DemoListing[]
  /** Forwarded to AgentApp's handleGenerate. Card click triggers the same
   *  flow as pasting the URL into the (team-only) input. */
  onPick: (url: string) => void
  loading: boolean
  /** When true, the picker is the *only* way in (non-team users). When false,
   *  it sits above the URL input as a quick-start row for team members. */
  exclusive: boolean
}

export function DemoListingPicker({
  listings,
  onPick,
  loading,
  exclusive,
}: DemoListingPickerProps) {
  if (listings.length === 0) return null

  return (
    <section className="flex w-full flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-body font-semibold">
          {exclusive ? "Pick a listing to demo" : "Quick-start with a demo listing"}
        </h2>
        <span className="text-body-sm text-muted-foreground">
          {exclusive ? "Pre-loaded so the agent never gets blocked" : "Skip the URL paste"}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {listings.map((listing) => (
          <DemoListingCard
            key={listing.room_id}
            listing={listing}
            onPick={onPick}
            disabled={loading}
          />
        ))}
      </div>
    </section>
  )
}

function DemoListingCard({
  listing,
  onPick,
  disabled,
}: {
  listing: DemoListing
  onPick: (url: string) => void
  disabled: boolean
}) {
  return (
    <button
      type="button"
      onClick={() => onPick(listing.listing_url)}
      disabled={disabled}
      className={cn(
        "group text-left transition-transform",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        disabled ? "pointer-events-none opacity-60" : "hover:-translate-y-0.5",
      )}
    >
      <Card className="flex h-full flex-col overflow-hidden p-0">
        <div className="aspect-[4/3] w-full overflow-hidden bg-muted">
          {listing.cover_photo_url ? (
            <img
              src={listing.cover_photo_url}
              alt={listing.title}
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-body-sm text-muted-foreground">
              No preview
            </div>
          )}
        </div>
        <div className="flex flex-1 flex-col gap-2 p-4">
          <h3 className="line-clamp-2 text-body font-semibold leading-tight">
            {listing.title}
          </h3>
          {listing.location ? (
            <p className="line-clamp-1 text-body-sm text-muted-foreground">
              {listing.location}
            </p>
          ) : null}
          <div className="mt-auto flex items-center justify-between pt-2 text-body-sm text-muted-foreground">
            {listing.rating_overall !== null ? (
              <span className="inline-flex items-center gap-1">
                <Star className="h-3.5 w-3.5 fill-current text-foreground" />
                <span className="text-foreground">
                  {listing.rating_overall.toFixed(2)}
                </span>
                {listing.reviews_count !== null ? (
                  <span>· {listing.reviews_count} reviews</span>
                ) : null}
              </span>
            ) : (
              <span />
            )}
            <span className="text-primary opacity-0 transition-opacity group-hover:opacity-100">
              Make my film →
            </span>
          </div>
        </div>
      </Card>
    </button>
  )
}
