# Agent Pipeline Specification — Airbnb Listing Video Agent

## Purpose

The agent is the system's only interesting layer. Everything else is plumbing. Its job: read an Airbnb listing, pick **one** editorial angle, build a visual argument for that angle, and write a Hera prompt that bakes the argument into a 15-second 9:16 video. The reasoning is surfaced to the user in plain English.

The agent has *opinions*. It is not a templating system. It will:
- Refuse to hedge — exactly one angle per listing.
- Defend its choice in 2–3 sentences the user actually reads.
- Apply learned beliefs (Phase 2 onward) to weight decisions, and log which beliefs it applied.

---

## Phase reminder

| Phase | Agent behavior |
|---|---|
| Phase 1 (built) | Single Gemini call. Hardcoded angle taxonomy in `angles.py`. Beliefs hardcoded inline. No persistence. |
| Phase 2 | Same call. Beliefs read from Supabase (top 10 by confidence). Optional outpainted photos passed in. New `beliefs_applied` field on `AgentDecision`. |
| Phase 3 | Beliefs auto-update from real social-media performance data. Agent stops applying low-confidence beliefs. |

The agent's *interface* is stable across phases. Only its inputs (beliefs from DB vs. inline) and image source (live scrape + optional outpaint vs. fixtures) change.

---

## The two taxonomies

The agent uses **two** classification systems that operate at different levels. They do not compete — one drives editorial choice, the other drives visual style.

### 1. Angle (intent-based, primary, drives editorial)

This is the angle the agent picks. It comes from the MVP and is locked. Each angle has a prompt template and a set of priority keywords for image scoring.

| `angle_id` | Label | Trigger signals |
|---|---|---|
| `urban_escape` | City Escape | Urban location, rooftop/balcony/view, walkable, arts/food district |
| `beach_retreat` | Beach Retreat | Coastal/waterfront location, pool, outdoor shower, surfboards |
| `remote_work` | Remote Work Base | Dedicated desk/workspace, fast wifi, quiet, near coworking |
| `entertainer` | Entertainer's Dream | Large kitchen, dining table, outdoor grill, guest count > 4 |
| `romantic_getaway` | Romantic Getaway | Couples framing, hot tub/jacuzzi, fireplace, private setting |
| `family_base` | Family Base | Multiple bedrooms, crib/high chair, yard, near attractions |

The agent **must** pick exactly one angle per listing. Ties are broken by `confidence` — the agent reports both in its JSON output. If the top angle's confidence is below 0.6, the agent defaults to `urban_escape` (most universally applicable) and notes the lower confidence in the rationale.

### 2. Property category (type-based, secondary, drives visual style only)

This was the architecture doc's original taxonomy. It is **demoted** to a style-mapping helper. The agent computes it as a side observation about the property's physical type and uses it only to pick a Hera `style_id`, color palette, and pacing — never to override the angle.

| `category` | Signals | Hera `style_id` (Phase 2) | Palette | Pacing |
|---|---|---|---|---|
| `beach` | Beach, ocean, coastal in location/amenities | `beach-warm` | Amber, coral, ocean blue | Relaxed |
| `mountain` | Mountain, ski, alpine, chalet | `mountain-earth` | Forest green, brown, stone | Dramatic |
| `urban` | City center, downtown, metro, apartment | `urban-minimal` | White, charcoal, single accent | Fast |
| `rural` | Countryside, farm, vineyard | `rural-natural` | Sage, cream, warm wood | Slow |
| `luxury` | Price > $500/night, "luxury" in title, premium amenities | `luxury-dark` | Black, gold, navy | Cinematic |
| `unique` | Treehouse, boat, castle, cave, dome | `unique-bold` | Vibrant primaries | Bold |

**Why both:** angles capture *who the trip is for* (intent). Categories capture *what the place is* (type). A loft in Mitte with a dedicated workspace is `angle = remote_work, category = urban` — the video pitches productivity (angle) in a clean minimal palette (category). Same loft framed as `angle = romantic_getaway` would be wrong even though the category is identical.

If category and angle conflict on visual cues (e.g. `angle = remote_work, category = beach`), the **angle wins for editorial**, the **category wins for style**. The agent renders the workspace narrative against a warm palette.

Pre-hackathon: Hera dashboard styles must be created with the IDs above. They don't exist by default.

---

## Agent input

The agent receives a single structured prompt. Three sections:

### Section A: Listing data

```python
class Photo(BaseModel):
    url: str
    label: str | None         # alt text or filename hint, e.g. "bedroom-with-view"

class ScrapedListing(BaseModel):
    url: str
    title: str
    description: str
    amenities: list[str]
    photos: list[Photo]       # ordered as they appear on the page
    location: str | None
    price_display: str | None
```

Phase 2 may extend this with `rating`, `review_count`, and `top_reviews` once the live scraper lands. Phase 1 ships without reviews — too noisy to parse in a sprint, and the angle classification works without them.

### Section B: Available photos (post-scoring, post-outpaint)

The 5 highest-scoring photos for the chosen angle. URLs are either original Airbnb CDN (Phase 1, or Phase 2 with toggle off) or Nanobanana CDN (Phase 2 with toggle on). The agent does not need to know which.

```python
class ScoredPhoto(BaseModel):
    url: str
    label: str | None
    score: int                # from image_scorer.py
    rank: int                 # 1 = strongest fit for the chosen angle
```

### Section C: Beliefs (Phase 2 onward)

```python
class Belief(BaseModel):
    rule_key: str             # "pool_hook_priority"
    rule_text: str            # human-readable rule
    confidence: float         # 0.0–1.0
```

Phase 1: an empty list. The angle prompt templates already encode reasonable defaults, so the agent runs fine without external beliefs.

---

## Agent output: `AgentDecision`

The Pydantic model that already lives in `backend/src/agent/models.py`:

```python
class AgentDecision(BaseModel):
    angle_id: str                       # one of the 6 angle IDs
    angle_label: str
    confidence: float                   # 0.0–1.0
    rationale: str                      # plain English, shown to user
    hera_prompt: str                    # constructed prompt sent to Hera
    selected_image_urls: list[str]      # top 5, ranked
    # Phase 2 additive fields:
    # category: str | None              # for style_id selection
    # style_id: str | None              # Hera style mapped from category
    # beliefs_applied: list[str]        # which rule_keys influenced the decision
```

Phase 2 fields are additive and optional. Phase 1 callers continue to work.

---

## Internal pipeline

The agent module orchestrates four steps. Only step 3 calls an external API.

```
orchestrator.run(listing: ScrapedListing) -> AgentDecision
   │
   ├─ 1. image_scorer.score(listing, candidate_angles)
   │       deterministic, fast, no LLM
   │       returns: dict[angle_id, list[ScoredPhoto]]
   │
   ├─ 2. classifier.classify(listing, scored_photos, beliefs)
   │       single Gemini call, structured JSON output
   │       returns: { angle_id, confidence, rationale, beliefs_applied }
   │
   ├─ 3. prompt_builder.build(angle, listing, top_photos)
   │       fill the chosen angle's prompt template
   │       returns: str (the Hera prompt)
   │
   └─ 4. assemble AgentDecision
```

### Step 1: Image scoring

For each of the 6 angles, score every photo against that angle's `priority_keywords`:

- Exact match on alt text / URL filename → `+3`
- General quality signal (view, light-filled, staged) → `+1`
- Mismatch (bathroom, storage, street-level) → `-1`

Output: per-angle ranked photo list. The classifier sees the top 5 of every angle's list (so it can reason about whether the property has the visual evidence to support the angle it's leaning toward).

This is **deterministic Python**, not an LLM. Auditable, fast, free.

### Step 2: Classification

Single Gemini call. System instruction establishes the role and the 6 angles. User prompt includes the listing summary, photo labels, the per-angle scored photos, and the (Phase 2) beliefs.

The model returns:

```json
{
  "angle_id": "remote_work",
  "confidence": 0.84,
  "rationale": "The title emphasizes a dedicated workspace and the description references fast fiber wifi. Three of the top five photos show a well-lit desk and quiet interior. This listing speaks to travelers who need to be productive, not just relax.",
  "beliefs_applied": ["dedicated_workspace_hook"]
}
```

Use Gemini's `response_schema` (JSON mode). No regex parsing. Schema validation in Python via Pydantic; on validation failure, retry once at temperature 0.

**Model selection:** `gemini-2.5-pro` via the google-genai SDK. 2.5-Pro is fast enough (~10–20s with reasoning enabled) for the synchronous request path and accurate enough for a single classification call. The Gemini 3.x preview models are a drop-in replacement once the project's API key has quota for them — only the model id needs to change.

### Step 3: Prompt building

The chosen angle has a prompt template in `angles.py`. Fill the slots from listing fields. Templates are hardcoded for the hackathon — no runtime prompt engineering.

Example (`remote_work`):

```
Create a 15-second vertical motion graphics video for an Airbnb listing.

Angle: Remote Work Base.
Hook (0-3s): Show the workspace setup — emphasize calm, productive atmosphere.
Middle (3-12s): Highlight [amenities: desk, wifi, quiet, natural light].
Close (12-15s): Location pull-back, end card with listing title "[TITLE]".

Style: clean, modern, natural light. Avoid party/nightlife imagery.
Mood: focused, aspirational, calm.
Reference images: [photo labels joined].

Property category for style: urban → urban-minimal palette (white, charcoal, single accent).
Pacing: fast cuts on amenities, slow reveal on workspace and view.
```

The category line at the bottom is Phase 2. Phase 1 templates omit it.

### Step 4: Assemble decision

Combine angle metadata, classifier output, top 5 image URLs, and the Hera prompt string into an `AgentDecision`. Return.

---

## Phase 2 additions: hook, storyboard, scenes (advanced)

Phase 1 ships with the prompt templates above — concise, angle-specific, and the agent does not produce per-scene timing. The video's beat structure lives entirely inside Hera's interpretation of the prompt.

Phase 2 upgrades the agent to produce a **structured storyboard** alongside the prompt. This makes the transparency card (see `01-ui-flow.md`, "Why this video works") substantive instead of generic. None of this lands until Phase 1 is stable.

### Standard 15-second story arc (Phase 2 default)

```
[0.0s – 2.0s]  HOOK         hero shot + opening text
[2.0s – 3.0s]  REVEAL       second strong visual, listing name
[3.0s – 6.0s]  HIGHLIGHTS   quick cuts of top amenities (0.8–1.0s each)
[6.0s – 9.0s]  LIFESTYLE    interior highlights, living spaces
[9.0s – 11.0s] PROOF        rating badge or review quote (Phase 2 needs reviews scraped)
[11.0s – 13.0s] DETAILS     price, capacity, location
[13.0s – 15.0s] CTA         "Book your stay" + listing link or QR
```

The agent may modify the arc for category-specific pacing:
- Luxury → slower scenes (1.5–2s each), longer hold on hero.
- Urban → faster cuts (0.6–0.8s on highlights).
- Beach → 1s settle on hero shot before the title appears.

### Hook strategy matrix (Phase 2)

The first 2 seconds determine watch-through. Hook choice is angle-aware:

| Angle | Hook approach | Example text overlay |
|---|---|---|
| `urban_escape` | Rooftop or skyline pan | "Berlin from above" |
| `beach_retreat` | Aerial pool or shoreline | "Your next escape" |
| `remote_work` | Desk + window in natural light | "Work from anywhere" |
| `entertainer` | Wide kitchen or dining setup | "Built for guests" |
| `romantic_getaway` | Bath, fireplace, or twilight exterior | "Just the two of you" |
| `family_base` | Yard, multi-bed, or kids' amenity | "Room for everyone" |

The agent picks the photo (by `image_scorer` rank within the chosen angle) plus the text. Beliefs adjust which hook style wins when multiple are available.

### Per-scene structure (Phase 2)

```python
class Scene(BaseModel):
    start_seconds: float
    end_seconds: float
    photo_index: int                      # which of selected_image_urls to show
    transition: Literal["cut", "dissolve", "slide", "zoom"]
    text_overlay: TextOverlay | None
    motion: Literal["zoom_in", "zoom_out", "pan_left", "pan_right", "static"]
    motion_intensity: Literal["subtle", "moderate", "dramatic"]

class TextOverlay(BaseModel):
    text: str                             # max 8 words
    position: Literal["top", "center", "bottom"]
    style: Literal["headline", "subtitle", "badge", "cta"]
```

The Phase 2 `AgentDecision` adds a `storyboard: list[Scene]` field. The Hera prompt is then assembled from the storyboard rather than from a static template, giving the agent finer control.

### Text overlay constraints

- Max 8 words per overlay (must read at scroll speed).
- Max 2 lines on screen at once.
- CTA must include a verb ("Book", "Explore", "Discover").
- English only for Phase 2; localization is post-Phase-3.

---

## System prompt (Phase 1, simplified)

The Phase 1 agent uses a compact system prompt:

```
You are the editorial director of an Airbnb video agent. Given a listing,
you pick exactly one of six angles and explain why in 2–3 sentences a real
person would read.

The six angles, with the kind of property each fits:
  urban_escape       — city listings with rooftops, views, walkable arts/food
  beach_retreat      — coastal/waterfront with pool, outdoor shower, beach access
  remote_work        — dedicated desk, fast wifi, quiet, near coworking
  entertainer        — large kitchen, dining table, outdoor grill, sleeps 4+
  romantic_getaway   — couples-coded, hot tub, fireplace, private
  family_base        — multiple bedrooms, kid amenities, near family attractions

Pick exactly one. If you genuinely cannot decide between two, pick the one
with stronger photographic evidence in the top 5 photos.

If your top angle's confidence is below 0.6, default to urban_escape and
say so in the rationale.

Output JSON only:
  {
    "angle_id": "...",
    "confidence": 0.0–1.0,
    "rationale": "2–3 sentences explaining your pick",
    "beliefs_applied": []
  }
```

User prompt (filled per request):

```
Listing: {title}
Description: {description_truncated_500_chars}
Location: {location}
Amenities: {amenities_joined}

Top photos per angle (each is a list of (rank, label) for the top 5):
{per_angle_photo_summary}
```

Phase 2 adds a "Your beliefs" block to the system prompt:

```
## Your beliefs (from real performance data)

Apply these when relevant. Higher confidence = stronger influence.
Always log which rule_keys you applied in beliefs_applied.

{beliefs_json}
```

---

## Initial seed beliefs (Phase 2 first deploy)

Loaded into `agent_beliefs` on the first Phase 2 deploy. Confidence values are starting points — they evolve from Phase 3 onward as real performance data flows in.

```json
[
  { "rule_key": "hook_with_hero_shot", "rule_text": "Open with the single most visually striking photo (pool, view, exterior)", "confidence": 0.85 },
  { "rule_key": "duration_15s", "rule_text": "15 seconds is optimal for Reels and TikTok engagement", "confidence": 0.80 },
  { "rule_key": "cta_at_end", "rule_text": "End every video with a clear CTA showing the listing link or QR code", "confidence": 0.90 },
  { "rule_key": "location_in_first_frame", "rule_text": "Show city or neighborhood within the first 2 seconds", "confidence": 0.70 },
  { "rule_key": "social_proof_before_cta", "rule_text": "Place a rating badge or review quote just before the CTA", "confidence": 0.75 },
  { "rule_key": "warm_palette_for_beach", "rule_text": "Beach and tropical properties should use warm palettes (amber, coral, gold)", "confidence": 0.80 },
  { "rule_key": "minimal_palette_for_urban", "rule_text": "Urban properties should use clean minimal palettes (white, gray, single accent)", "confidence": 0.75 },
  { "rule_key": "fast_cuts_for_amenities", "rule_text": "Amenity showcase sequences should use quick cuts (0.8–1.2s per scene)", "confidence": 0.70 },
  { "rule_key": "slow_reveal_for_hero", "rule_text": "Hero shots get longer screen time (2–3s) with subtle zoom or pan", "confidence": 0.80 },
  { "rule_key": "music_over_voiceover", "rule_text": "Background music with text overlays outperforms voiceover for property videos", "confidence": 0.65 },
  { "rule_key": "dedicated_workspace_hook", "rule_text": "For remote_work angle, open on the desk + window combo, not the bedroom", "confidence": 0.70 },
  { "rule_key": "couples_framing_first", "rule_text": "For romantic_getaway angle, show the intimate detail (tub, fireplace) before the wide shot", "confidence": 0.65 }
]
```

The last two are angle-specific. Add more as we learn.

---

## Validation

Server-side validation runs after every classifier call and after every Phase 2 storyboard assembly. Failures retry once at temperature 0; a second failure triggers the fallback.

```python
def validate_decision(decision: AgentDecision, photos: list[ScoredPhoto]) -> list[str]:
    errors = []

    if decision.angle_id not in VALID_ANGLE_IDS:
        errors.append(f"unknown angle_id: {decision.angle_id}")
    if not 0.0 <= decision.confidence <= 1.0:
        errors.append(f"confidence out of range: {decision.confidence}")
    if len(decision.rationale) < 40:
        errors.append("rationale too short (< 40 chars)")
    if len(decision.hera_prompt) < 100:
        errors.append("hera_prompt too short (< 100 chars)")
    if not (0 < len(decision.selected_image_urls) <= 5):
        errors.append("selected_image_urls must have 1–5 entries")

    photo_urls = {p.url for p in photos}
    for url in decision.selected_image_urls:
        if url not in photo_urls:
            errors.append(f"selected URL not in candidate photos: {url}")

    return errors
```

Phase 2 adds storyboard validation:
- Sum of scene durations must equal `duration_seconds` (default 15).
- Every `scene.photo_index` must fall inside `selected_image_urls`.
- At least one belief must be referenced in `beliefs_applied` if beliefs were provided.

---

## Fallback behavior

If the classifier fails twice, the orchestrator returns a deterministic fallback decision rather than 500ing the whole request:

1. **Angle:** `urban_escape` (most universally applicable).
2. **Confidence:** `0.5`.
3. **Rationale:** `"The agent couldn't reach a confident editorial choice for this listing. Defaulting to a city escape framing — listings with strong visuals and a walkable location read well in this register."`
4. **Top photos:** the 5 with the highest deterministic score against `urban_escape` keywords.
5. **Hera prompt:** the `urban_escape` template filled from listing fields.

The fallback still produces a watchable video. It's a graceful degradation, not an error surface.

The frontend gets a normal `200` with this decision. The backend logs the underlying classifier failure for debugging.

---

## Cost and latency budget

| Component | Phase 1 latency | Phase 1 cost | Phase 2 latency | Phase 2 cost |
|---|---|---|---|---|
| Image scoring (deterministic Python) | <50ms | free | <50ms | free |
| Classifier (Gemini 2.5 Pro) | 10–20s | ~$0.01 | 10–20s | ~$0.01 |
| Prompt building | <10ms | free | <10ms | free |
| Beliefs SELECT (Supabase) | — | — | <100ms | rounding error |
| **Agent total (request path)** | **1–3s** | **~$0.005** | **1–3s** | **~$0.005** |
| Outpainting (Phase 2, toggle on, 5 photos parallel) | — | — | 5–15s | $0.10–0.25 |
| Hera render | 90–150s | credits | 90–150s | credits |
| **End-to-end wall time** | **~95–155s** | **$0.005 + credits** | **~100–170s** | **~$0.025–0.27 + credits** |

The agent is cheap and fast. The bottleneck is Hera rendering, and that's where the demo strategy (pre-render the demo video, let the reasoning card carry the live audience) earns its keep.

---

## Performance learning loop (Phase 3)

Out of scope until Phase 2 is in production with real users publishing videos. The mechanics:

1. When a video is published to a connected social account (`publications` row), start tracking it.
2. Every 6 hours, pull `performance_snapshots` for each publication via the platform API.
3. After 24 hours of post-publication data, correlate the agent's decisions (`videos.agent_decision`) with performance metrics.
4. Update `agent_beliefs.confidence`:
   - Beach properties with pool hooks consistently beating average watch-through → `pool_hook_priority` confidence climbs.
   - Slow reveals on hero shots underperforming fast cuts → `slow_reveal_for_hero` confidence drops.
5. Beliefs that fall below `0.5` confidence stop being injected into the system prompt (they're filtered out at SELECT time).

A belief that started at `0.80` and falls to `0.45` after 28 pieces of evidence is the agent learning. That's the long-term moat.
