# UI Flow Specification — StayMotion

## Product overview

StayMotion is a web application that allows vacation property owners (Airbnb, Booking.com, VRBO hosts) to generate scroll-stopping motion graphics videos for social media by simply pasting their listing URL. The user does not need any video editing skills, design knowledge, or understanding of social media best practices. The creative agent handles all editorial decisions autonomously.

**Core value proposition:** Paste a listing URL → get a publish-ready 9:16 motion graphics video for Instagram Reels / TikTok / YouTube Shorts in under 2 minutes.

---

## Screen-by-screen flow

### Screen 1: Landing / URL input

**Route:** `/`

**Layout:** Single centered card on a clean background. Hero headline at the top, URL input field prominently displayed, and a "Generate" CTA button.

**Elements:**

- **Headline:** "Turn your listing into a viral video" (or similar)
- **Subheadline:** "Paste your Airbnb, Booking, or VRBO link. Get a motion graphics video in 60 seconds."
- **URL input field:** Full-width text input. Accepts URLs from:
  - `airbnb.com/rooms/...`
  - `booking.com/hotel/...`
  - `vrbo.com/...`
- **Platform selector (optional):** Auto-detected from URL, but allow manual override with pill buttons: Instagram Reels | TikTok | YouTube Shorts. This sets the output aspect ratio (always 9:16) and adjusts minor formatting (safe zones, text placement).
- **"Generate video" button:** Primary CTA. Disabled until a valid URL is detected.
- **Gallery section below:** 3–4 example before/after cards showing listing → finished video previews to demonstrate quality.
- **Auth:** Not required for first generation. Prompt signup after the video is ready (to download or publish).

**Behavior on submit:**
1. Validate URL format client-side (regex for known listing platforms)
2. POST to `/api/generate` with the URL
3. Transition to Screen 2 (processing)

---

### Screen 2: Processing / progress

**Route:** `/generate/[jobId]`

**Layout:** Centered progress card showing real-time status updates. The user watches their video being built step by step.

**Progress steps displayed (with live status indicators):**

1. **"Analyzing your listing..."** — Scraper is running. Show for ~5–10 seconds.
2. **"Found 12 photos, 4.8★ rating, 23 amenities"** — Display extracted stats as they arrive. This builds trust and excitement.
3. **"Selecting best photos and optimizing for mobile..."** — Photo ranking + Nanobanana outpainting running. Show thumbnails appearing one by one as they're processed (landscape → portrait animation).
4. **"Crafting your story..."** — Creative agent is running. Show the property category badge ("Beach house" / "City loft") and the hook line the agent chose as they are determined.
5. **"Rendering your video..."** — Hera API create_video called. This is the longest step (~30–60s). Show an animated progress bar or a looping preview of the storyboard frames.
6. **"Almost there..."** — Polling Hera get_video. Transition to Screen 3 when status is `success`.

**Error handling:**
- If scraping fails: "We couldn't read this listing. Is the URL correct?" with retry button.
- If Hera render fails: "Video generation failed. Retrying..." with automatic retry (max 2 attempts) then manual retry button.
- Timeout after 3 minutes: "This is taking longer than expected. We'll email you when it's ready." (requires email input)

---

### Screen 3: Video preview + publish

**Route:** `/video/[videoId]`

**Layout:** Two-column on desktop (video left, controls right), stacked on mobile (video top, controls below).

**Left / Top section — Video preview:**
- Full-height 9:16 video player showing the rendered MP4
- Play/pause, mute/unmute, scrubber
- Loop playback by default
- "Powered by StayMotion" watermark on free tier (removed on paid)

**Right / Bottom section — Actions:**

- **"Download" button:** Downloads the MP4 directly. Requires signup/login.
- **"Post to Instagram" button:** Opens Instagram posting flow (OAuth → IG Graph API direct publish). Requires connected IG account.
- **"Post to TikTok" button:** Same pattern via TikTok for Business API.
- **"Copy link" button:** Generates a shareable preview link.
- **"Edit in Hera" link:** Opens Hera's project_url in a new tab for advanced editing. Shown as secondary/subtle action — this is the escape hatch for power users.
- **"Regenerate" button:** Re-runs the agent with different creative decisions (different hook, different pacing, different style). Costs one additional credit.

**Below the fold — Agent decisions transparency card:**
- "Why this video works" expandable section showing:
  - Hook choice: "We opened with your pool shot — pool hooks get 2.3× more watch-through"
  - Story arc: "Vibe → amenities → social proof → CTA"
  - Style: "Warm palette for beach properties"
  - Duration: "15 seconds — optimal for Reels engagement"
- This is both educational for the user and a differentiator for the hackathon demo.

---

### Screen 4: Dashboard (post-signup)

**Route:** `/dashboard`

**Layout:** Card grid showing all generated videos with performance metrics.

**Per-video card:**
- Thumbnail (first frame)
- Property name / listing title
- Generation date
- Performance metrics (if published through StayMotion):
  - Views, likes, saves, shares, watch-through rate
  - Trend indicator (up/down arrow vs. their average)
- Quick actions: Repost, regenerate, download, delete

**Top-level stats bar:**
- Total videos generated
- Total views across all videos
- Best-performing video highlight
- "Generate new video" prominent CTA

**Performance insights panel (stretch goal):**
- "Your pool-opening videos get 3× more saves than interior-opening videos"
- "15-second videos outperform your 30-second videos by 40%"
- These insights come from the performance learning pipeline and make the product stickier.

---

## Navigation and information architecture

```
/                       → Landing + URL input (Screen 1)
/generate/[jobId]       → Processing progress (Screen 2)
/video/[videoId]        → Preview + publish (Screen 3)
/dashboard              → All videos + analytics (Screen 4)
/settings               → Account, connected socials, billing
/login, /signup         → Auth flows (email + Google OAuth)
```

## Responsive behavior

- **Desktop (>1024px):** Two-column layouts where applicable. Video preview at native 9:16 aspect in a phone-frame mockup.
- **Tablet (768–1024px):** Single column, video preview scales down.
- **Mobile (<768px):** Full-width stacked. URL input gets full keyboard focus. Video preview is full-width 9:16 (fills the screen naturally).

## Authentication flow

- **Unauthenticated users:** Can generate one video as a trial. Video is watermarked. Download and publish require signup.
- **Signup:** Email + password or Google OAuth. Minimal friction — name and email only.
- **Social connections:** IG and TikTok OAuth handled in `/settings`. Required for direct publishing but not for generation.

## Key UX principles for hackathon implementation

1. **One input, one output.** The user provides a URL and gets a video. Every screen between those two points is either showing progress or presenting the result.
2. **No creative decisions required from the user.** The agent makes all choices. The user can override (regenerate, edit in Hera) but never has to.
3. **Transparency builds trust.** Show what the agent decided and why. This is educational and differentiating.
4. **Speed is the feature.** The progress screen should feel fast even when waiting. Real-time status updates and extracted data previews keep the user engaged.
5. **Social proof in the product.** The performance dashboard and "why this video works" card make users feel like they're getting expert-level social media strategy, not just a video generator.

---

## Hackathon MVP scope

For the 24-hour hackathon, implement:

- **Screen 1:** URL input (Airbnb only for MVP)
- **Screen 2:** Processing with at least 3 live status steps
- **Screen 3:** Video preview + download button
- **Skip:** Dashboard, auth, direct social posting, billing

The demo flow should be: Paste Airbnb URL → watch processing → see finished video → download. Total user interaction: one paste, one click.
