import { authedFetch, BACKEND_URL } from "./client"

export type DemoListing = {
  room_id: string
  listing_url: string
  title: string
  location: string
  cover_photo_url: string | null
  rating_overall: number | null
  reviews_count: number | null
}

export type Me = {
  user_id: string
  email: string | null
  require_auth: boolean
  is_team_member: boolean
  demo_listings: DemoListing[]
}

export async function getMe(): Promise<Me> {
  const res = await authedFetch(`${BACKEND_URL}/api/me`)
  if (!res.ok) {
    throw new Error(`/api/me ${res.status}`)
  }
  return res.json() as Promise<Me>
}
