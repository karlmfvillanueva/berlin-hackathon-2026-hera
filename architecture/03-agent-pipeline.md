# Agent Pipeline Specification — StayMotion Creative Agent

## Purpose

The creative agent is the core differentiator of StayMotion. It is an LLM-based system that takes raw listing data and produces a complete Hera `create_video` API payload — making every editorial decision autonomously: what to show first, how to pace the video, what text to overlay, which style to use, and how to end with a compelling CTA.

The agent is "opinionated" — it has a defined point of view about what makes property videos perform well on social media. These opinions are encoded as beliefs that can be updated by real performance data over time.

---

## Agent input schema

The agent receives a single structured prompt containing three sections: listing data, available assets, and current beliefs.

### Section A: Listing data (from scraper)

```typescript
interface AgentInput_ListingData {
  platform: "airbnb" | "booking" | "vrbo"
  title: string                    // "Stunning Beachfront Villa with Infinity Pool"
  description: string              // Full listing description (truncated to 500 chars)
  location: {
    city: string                   // "Canggu"
    region: string                 // "Bali"
    country: string                // "Indonesia"
    coordinates: { lat: number, lng: number }
  }
  property_type: string            // "Entire villa"
  guest_capacity: number           // 8
  bedrooms: number                 // 4
  bathrooms: number                // 3
  amenities: string[]              // ["Infinity pool", "Ocean view", "Private chef", ...]
  rating: number                   // 4.92
  review_count: number             // 127
  top_reviews: Array<{
    text: string                   // "Best vacation of our lives! The pool is incredible..."
    rating: number
  }>
  price: {
    amount: number                 // 350
    currency: string               // "USD"
    period: string                 // "night"
  }
}
```

### Section B: Available assets (outpainted photos on Hera CDN)

```typescript
interface AgentInput_Assets {
  photos: Array<{
    hera_cdn_url: string           // URL returned by Hera upload_file
    original_caption?: string      // From Airbnb: "Living room with ocean view"
    category: string               // Assigned by photo ranker: "exterior", "pool", "interior", "bedroom", "view"
    visual_impact_rank: number     // 1 = most impactful, assigned by photo ranker
  }>
}
```

### Section C: Current agent beliefs (from performance DB)

```typescript
interface AgentInput_Beliefs {
  beliefs: Array<{
    rule_key: string               // "pool_hook_priority"
    rule_text: string              // "Pool shots as opening hook get 2.3× higher watch-through rate"
    confidence: number             // 0.85
  }>
}
```

---

## Agent processing steps

The agent processes the input in six sequential reasoning steps within a single LLM call. This is implemented as a chain-of-thought prompt where the agent must reason through each step before producing the final output.

### Step 1: Property classification

**Purpose:** Categorize the property to determine the overall creative direction.

**Categories:**
| Category | Signals | Creative direction |
|---|---|---|
| `beach` | Beach, ocean, sea, surf, coastal in amenities or location | Warm palette, relaxed pacing, nature emphasis |
| `mountain` | Mountain, ski, hiking, alpine, chalet | Earthy tones, dramatic reveals, landscape focus |
| `urban` | City center, downtown, metro, apartment | Clean minimal palette, fast cuts, lifestyle focus |
| `rural` | Countryside, farm, vineyard, retreat | Natural palette, slow pacing, tranquility emphasis |
| `luxury` | High price (>$500/night), "luxury" in title, premium amenities | Dark/gold palette, cinematic pacing, exclusivity focus |
| `unique` | Treehouse, boat, castle, cave, dome | Bold palette, curiosity-driven hook, uniqueness emphasis |

**The agent assigns a primary and optional secondary category.** A beachfront luxury villa gets `primary: "beach", secondary: "luxury"`.

### Step 2: USP extraction and ranking

**Purpose:** Identify the property's unique selling points and rank them by visual impact and marketing value.

**The agent considers:**
- Amenities that are visually impressive (pool, view, hot tub, rooftop)
- Location uniqueness (beachfront, city skyline, mountain peak)
- Social proof strength (high rating, review count, specific review quotes)
- Price positioning (luxury = exclusive, budget = "hidden gem")
- Unique features (private chef, spa, cinema room)

**Output:** Ordered list of 3–5 USPs with assigned priority:

```
1. Infinity pool with ocean view (hero visual)
2. Beachfront location in Canggu (location hook)
3. 4.92★ rating with 127 reviews (social proof)
4. Private chef available (luxury differentiator)
5. 4 bedrooms / 8 guests (capacity for groups)
```

### Step 3: Hook selection

**Purpose:** Choose the opening 2 seconds of the video — the single most important creative decision for social media performance.

**Hook strategy matrix:**

| USP type | Hook approach | Example |
|---|---|---|
| Pool/water feature | Aerial or wide shot of pool | Pool photo + "Your next escape" |
| Stunning view | Landscape/panorama shot | View photo + location tag "Bali, Indonesia" |
| Unique architecture | Exterior hero shot | Building photo + "This exists" |
| Location | Map pin or city skyline | Photo + "2 hours from [major city]" |
| Social proof | Rating badge animation | "4.92★ — 127 reviews" + best photo |

**The agent selects:**
- Which photo to use as the hook (by `visual_impact_rank` and beliefs)
- What text overlay to display in the first 2 seconds
- The hook "type" (question, statement, location reveal, social proof)

**Belief influence:** If the performance DB shows that pool hooks outperform view hooks for beach properties, the agent weights pool hooks higher when both are available.

### Step 4: Storyboard architecture

**Purpose:** Plan the complete scene sequence, timing, and transitions.

**Standard story arc template (15 seconds):**

```
[0.0s – 2.0s]  HOOK        — Hero shot + opening text
[2.0s – 3.0s]  REVEAL      — Second strong visual, property name
[3.0s – 6.0s]  HIGHLIGHTS  — Quick cuts of top amenities (0.8–1.0s each)
[6.0s – 9.0s]  LIFESTYLE   — Interior highlights, living spaces
[9.0s – 11.0s] PROOF       — Rating badge, review quote
[11.0s – 13.0s] DETAILS    — Price, guest capacity, location
[13.0s – 15.0s] CTA        — "Book now" + listing link or QR code
```

**The agent can modify this template based on:**
- Property category (luxury gets slower pacing, urban gets faster)
- Number of strong photos (fewer photos = longer per scene)
- Beliefs about optimal pacing for this category

**Per-scene specification:**

```typescript
interface Scene {
  start_seconds: number
  end_seconds: number
  photo_index: number              // which of the 5 photos to show
  transition: "cut" | "dissolve" | "slide" | "zoom"
  text_overlay?: {
    text: string                   // "Infinity pool with ocean view"
    position: "top" | "center" | "bottom"
    style: "headline" | "subtitle" | "badge" | "cta"
  }
  motion: "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "static"
  motion_intensity: "subtle" | "moderate" | "dramatic"
}
```

### Step 5: Style matching

**Purpose:** Map the property category to a Hera style and color palette.

**Style mapping table (pre-configured in Hera dashboard):**

| Property category | Hera style_id | Color palette | Typography | Music mood |
|---|---|---|---|---|
| `beach` | `beach-warm` | Amber, coral, sand, ocean blue | Rounded sans-serif | Tropical chill |
| `mountain` | `mountain-earth` | Forest green, warm brown, stone gray | Strong serif | Acoustic calm |
| `urban` | `urban-minimal` | White, charcoal, single bright accent | Geometric sans | Lo-fi beats |
| `rural` | `rural-natural` | Sage green, cream, warm wood | Soft serif | Folk acoustic |
| `luxury` | `luxury-dark` | Black, gold, cream, deep navy | Elegant serif | Cinematic ambient |
| `unique` | `unique-bold` | Vibrant primary colors, high contrast | Display/decorative | Upbeat electronic |

**If secondary category exists:** Blend attributes. A "beach + luxury" property uses `luxury-dark` style but with the warm color accents of `beach-warm`.

### Step 6: Hera prompt assembly

**Purpose:** Convert all previous decisions into a natural language prompt that Hera's AI understands, plus the structured API parameters.

**The Hera prompt is the most critical output.** It needs to be specific enough that Hera generates the intended video, but natural enough that Hera's AI can interpret creative direction.

**Prompt template structure:**

```
Create a [duration]-second motion graphics video showcasing a [property_type]
in [location].

VISUAL STYLE: [style description from Step 5]

SCENE BREAKDOWN:
- [0-2s]: Open with [hook description]. [Motion type]. Text overlay: "[hook text]"
  Use reference image [N].
- [2-3s]: [Reveal description]. Transition: [type]. Text: "[text]"
  Use reference image [N].
- [3-6s]: Quick montage of [amenity 1], [amenity 2], [amenity 3].
  Fast cuts, [timing]s each. Use reference images [N, N, N].
- [6-9s]: [Lifestyle description]. [Motion type]. Text: "[text]"
  Use reference image [N].
- [9-11s]: Social proof moment. Animate: "[rating] ★ — [review_count] reviews"
  Optional quote: "[review excerpt]"
- [11-13s]: Property details. "[bedrooms] BR · [bathrooms] BA · [capacity] guests
  · from $[price]/night"
- [13-15s]: Call to action. Text: "Book your stay" with [platform] branding.
  [CTA animation style].

TYPOGRAPHY: [font style], [weight], [color on what background]
COLOR PALETTE: Primary [hex], secondary [hex], accent [hex], text [hex]
TRANSITIONS: Prefer [transition style] between scenes.
OVERALL MOOD: [mood description]
PACING: [pacing description]
```

---

## Agent output schema

The agent outputs a single JSON object that maps directly to the Hera `create_video` API request, plus metadata for our own tracking.

```typescript
interface AgentOutput {
  // Hera API payload (sent directly to POST /videos)
  hera_payload: {
    prompt: string                 // The assembled natural language prompt (Step 6)
    reference_image_urls: string[] // Up to 5 Hera CDN URLs (ordered by scene usage)
    duration_seconds: number       // 15 (default) or agent-adjusted
    style_id: string               // From Step 5 style mapping
    assets: Array<{
      type: "image"
      url: string
    }>
    outputs: [{
      format: "mp4"
      aspect_ratio: "9:16"
      fps: "30"
      resolution: "1080p"
    }]
  }

  // Metadata for our tracking and transparency
  metadata: {
    category: {
      primary: string              // "beach"
      secondary?: string           // "luxury"
    }
    usps: Array<{
      text: string
      priority: number
    }>
    hook: {
      type: string                 // "pool_hero"
      photo_index: number
      text: string                 // "Your next escape"
      reasoning: string            // "Pool hooks have 2.3× watch-through for beach properties"
    }
    storyboard: Scene[]            // Full scene breakdown
    style: {
      style_id: string
      palette: string[]
      typography: string
      mood: string
    }
    beliefs_applied: string[]      // Which belief rule_keys influenced decisions
    confidence_score: number       // 0.0–1.0, agent's self-assessed confidence
  }
}
```

---

## System prompt implementation

The agent is implemented as a single Claude API call with a carefully structured system prompt.

### System prompt

```
You are StayMotion's Creative Director — an expert AI agent that creates
scroll-stopping property showcase videos for social media.

You have strong editorial opinions about what makes property videos perform.
Your decisions are informed by real performance data from previously published
videos. You never create generic content — every video is tailored to the
specific property's strengths and personality.

## Your creative process

You MUST think through these 6 steps IN ORDER before producing your output.
Show your reasoning for each step inside <thinking> tags.

### Step 1: Classify the property
Analyze the listing data and assign a primary category (and optional secondary):
beach | mountain | urban | rural | luxury | unique
Consider: location, amenities, price point, description language, property type.

### Step 2: Extract and rank USPs
Identify 3–5 unique selling points. Rank by visual impact × marketing value.
The #1 USP should be something you can SHOW, not just tell.

### Step 3: Choose the hook
The first 2 seconds determine whether someone watches or scrolls.
Pick the strongest photo + opening text combination.
Consider the performance beliefs — what hook types have worked best?

### Step 4: Build the storyboard
Plan every second of the video. Use the standard arc:
Hook → Reveal → Highlights → Lifestyle → Proof → Details → CTA
Adjust pacing based on property category and available photos.

### Step 5: Match the style
Select the Hera style_id and define color palette, typography, mood.
Available styles: beach-warm, mountain-earth, urban-minimal,
rural-natural, luxury-dark, unique-bold.

### Step 6: Assemble the Hera prompt
Write a detailed natural language prompt for Hera's video generation AI.
Be specific about timing, transitions, text overlays, and which reference
images to use for each scene.

## Output format

After your <thinking> block, output a single JSON object matching the
AgentOutput schema. No markdown, no explanation outside the JSON.

## Your beliefs (from performance data)

{beliefs_json}

Apply these beliefs when making creative decisions. Higher confidence =
stronger influence. Always note which beliefs you applied in the
metadata.beliefs_applied field.

## Style reference

| style_id | Category | Palette | Mood |
|---|---|---|---|
| beach-warm | Beach/tropical | Amber, coral, ocean | Relaxed, aspirational |
| mountain-earth | Mountain/alpine | Forest, brown, stone | Dramatic, peaceful |
| urban-minimal | City/urban | White, charcoal, accent | Modern, energetic |
| rural-natural | Countryside | Sage, cream, wood | Tranquil, authentic |
| luxury-dark | High-end | Black, gold, navy | Exclusive, cinematic |
| unique-bold | Unusual properties | Bright primaries | Curious, exciting |
```

### User prompt template

```
Generate a social media video for this property:

## Listing data
{listing_data_json}

## Available photos (already uploaded to Hera CDN, in 9:16 portrait format)
{photos_json}

## Current performance beliefs
{beliefs_json}

Think through all 6 steps, then produce the AgentOutput JSON.
```

---

## Prompt engineering guidelines for implementation

### Keep the Hera prompt concrete

Bad: "Create a nice video of a beach house"
Good: "Create a 15-second motion graphics video showcasing a luxury beachfront villa in Canggu, Bali. Open with a dramatic zoom-out on the infinity pool (reference image 1) with text overlay 'Your Next Escape' in cream Playfair Display on a semi-transparent dark overlay at the bottom third. At 2s, dissolve to the ocean view from the terrace (reference image 2) with location tag 'Canggu, Bali' in the top left..."

### Photo indexing in the prompt

The agent must explicitly reference which `reference_image_url` index to use for each scene. Hera maps reference images by order:
- Reference image 1 = `reference_image_urls[0]`
- Reference image 2 = `reference_image_urls[1]`
- etc.

The agent should order `reference_image_urls` in the payload to match scene order (hook photo first, CTA photo last).

### Duration flexibility

While 15 seconds is the default, the agent can adjust:
- **10 seconds:** If fewer than 3 strong photos are available
- **20 seconds:** If the property has 5+ strong USPs worth showing
- **30 seconds:** Only for luxury properties with exceptional content

The agent must justify any deviation from 15s in its reasoning.

### Text overlay constraints

- Maximum 8 words per overlay (must be readable at scroll speed)
- No more than 2 lines of text on screen simultaneously
- CTA text must include a clear action verb ("Book", "Explore", "Discover")
- All text in English (for MVP — localization is a future feature)

---

## Testing the agent

### Smoke test (run manually before hackathon demo)

1. Pick 5 diverse Airbnb listings:
   - Beach villa in Bali
   - City apartment in Berlin
   - Mountain chalet in Swiss Alps
   - Rural farmhouse in Tuscany
   - Unique treehouse somewhere

2. For each: run the full pipeline and verify:
   - Agent correctly classifies the property
   - Hook makes sense for the category
   - Storyboard timing adds up to duration_seconds
   - All photo indices are valid (within range of available photos)
   - Hera payload is valid JSON matching the API schema
   - Generated video actually looks good

### Automated validation (implement in code)

```typescript
function validateAgentOutput(output: AgentOutput): string[] {
  const errors: string[] = []

  // Check duration matches storyboard
  const lastScene = output.metadata.storyboard.at(-1)
  if (lastScene && lastScene.end_seconds !== output.hera_payload.duration_seconds) {
    errors.push("Storyboard timing doesn't match duration_seconds")
  }

  // Check photo indices are valid
  const maxIndex = output.hera_payload.reference_image_urls.length - 1
  for (const scene of output.metadata.storyboard) {
    if (scene.photo_index > maxIndex) {
      errors.push(`Scene references photo ${scene.photo_index} but only ${maxIndex + 1} photos available`)
    }
  }

  // Check required fields
  if (!output.hera_payload.prompt || output.hera_payload.prompt.length < 100) {
    errors.push("Hera prompt is too short (< 100 chars)")
  }
  if (!output.hera_payload.style_id) {
    errors.push("Missing style_id")
  }
  if (output.hera_payload.outputs[0]?.aspect_ratio !== "9:16") {
    errors.push("Output aspect ratio must be 9:16")
  }

  // Check beliefs were applied
  if (output.metadata.beliefs_applied.length === 0) {
    errors.push("No beliefs were applied — agent should reference at least 1 belief")
  }

  return errors
}
```

---

## Performance learning integration

### How beliefs flow into the agent

```
[Performance DB] → SELECT top 10 beliefs by confidence DESC
                 → Inject into system prompt as "Your beliefs" section
                 → Agent reads beliefs and applies them during Steps 3–5
                 → Agent logs which beliefs it used in metadata.beliefs_applied
```

### How agent decisions flow into performance tracking

```
[Agent output] → metadata.hook.type, metadata.storyboard, metadata.style
              → Stored in videos.agent_decisions (JSONB)
              → When video is published and gets analytics data:
                 → Correlate decisions with performance
                 → Update belief confidence scores
```

### Example belief evolution

**Week 1 (hardcoded):**
```json
{ "rule_key": "pool_hook_priority", "confidence": 0.80, "evidence_count": 0 }
```

**Week 4 (after 50 videos with performance data):**
```json
{ "rule_key": "pool_hook_priority", "confidence": 0.92, "evidence_count": 34 }
```
34 out of 50 beach property videos with pool hooks outperformed the average → confidence increased.

**Alternative scenario — belief gets weakened:**
```json
{ "rule_key": "slow_reveal_for_hero", "confidence": 0.45, "evidence_count": 28 }
```
Data shows fast cuts outperform slow reveals for hero shots → confidence dropped below 0.5, agent stops applying this belief.

---

## Fallback behavior

If the Claude API call fails or returns invalid JSON:

1. **First retry:** Same prompt, temperature 0.
2. **Second retry:** Simplified prompt with just the essential fields.
3. **Final fallback:** Use a hardcoded template:
   - Hook: photo with highest visual_impact_rank + property title
   - Arc: standard 15s template with even timing
   - Style: based on simple location keyword matching
   - Prompt: generic template filled with listing title and location

The fallback should still produce a decent video — just without the nuanced editorial decisions.

---

## Cost and latency budget

| Component | Estimated latency | Estimated cost |
|---|---|---|
| Claude API call (agent) | 3–8 seconds | ~$0.02–0.04 (Sonnet) |
| JSON parsing + validation | <100ms | Free |
| Hera upload_file (5 photos) | 2–5 seconds (parallel) | Free |
| Hera create_video | <1 second (submission) | Credits-based |
| Hera render (polling) | 30–90 seconds | Included in above |
| **Total agent + render** | **~40–100 seconds** | **~$0.02 + Hera credits** |

The agent itself is fast (~5s). The bottleneck is Hera rendering. Use the waiting time to show the user what the agent decided (property category, hook choice, storyboard preview) — this makes the wait feel shorter and builds trust in the product.
