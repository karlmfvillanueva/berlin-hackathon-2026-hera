import { authedFetch, BACKEND_URL } from "./client"

export type Me = {
  user_id: string
  email: string | null
  require_auth: boolean
}

export async function getMe(): Promise<Me> {
  const res = await authedFetch(`${BACKEND_URL}/api/me`)
  if (!res.ok) throw new Error(`getMe failed: ${res.status}`)
  return res.json() as Promise<Me>
}
