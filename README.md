# AI Influencer - Eva Joy

> Automated AI-generated fitness influencer content pipeline with ultra-detailed Grok prompts, manual review workflow, and intelligent diversity tracking

**Status**: 🚧 **Active Development** - Core pipeline operational, rating/queue system in progress

## Overview

An end-to-end system for generating professional AI fitness influencer content for "Eva Joy" - from ultra-detailed 200+ word prompts to TikTok-ready videos. Built with fail-loud safety guards, provider abstraction, and no mock modes.

**Tech Stack**:
- **Prompting**: xAI Grok API (200+ word ultra-detailed prompts)
- **Image Generation**: Leonardo.ai
- **Video Generation**: Google Veo 3 (Vertex AI) with SynthID watermark
- **Video Editing**: Shotstack
- **Backend**: Python 3.11+, FastAPI, UV package manager
- **Frontend**: React + Vite
- **Storage**: Local filesystem (JSON indices + media files)

---

## ✨ Key Features

### Current (Production-Ready)
- ✅ **Ultra-Detailed Prompts**: 200-250 word cinematic prompts via Grok
- ✅ **8 Diversity Banks**: 200+ variations across locations, poses, outfits, lighting, camera, props, twists
- ✅ **Intelligent Dedupe**: SHA256 content hashing prevents duplicate generations
- ✅ **Cost Tracking**: Decimal-based budget caps (~$0.54/video)
- ✅ **Security**: Path traversal protection, schema validation, rate limiting
- ✅ **End-to-End Pipeline**: Grok → Leonardo → Veo 3 → Shotstack → indexed video

### In Progress (Essential for Launch)
- 🚧 **Rating System**: 3-tier image rating (Dislike/Like/Super-like)
- 🚧 **Video Queue**: Convert super-liked images to videos
- 🚧 **Motion Prompting**: Generate cinematic camera movements from image metadata
- 🚧 **Weighted Diversity**: Track recent combinations, avoid repetition

### Planned
- 📋 **TikTok Integration**: Automated posting with rate limits
- 📋 **Video Regeneration**: Re-create videos with different motion on dislike
- 📋 **Analytics Dashboard**: Track performance, costs, diversity metrics

---

## 🎯 User Workflow (Full Vision)

### Phase 1: Image Generation
```
1. System generates 10-20 image variations
   → Grok creates ultra-detailed prompts from diversity banks
   → Leonardo generates high-res images
   → Images appear in Review UI

2. User rates each image:
   ❌ Dislike → Deleted immediately
   ❤️ Like → Queued for direct posting to TikTok
   ⭐ Super-like → Queued for video generation
```

### Phase 2: Video Generation
```
3. Super-liked images automatically generate videos
   → System creates motion prompt from image metadata
   → Veo 3 converts image to 8-second cinematic video
   → Shotstack adds licensed music
   → Videos appear in Video Review UI

4. User rates each video:
   ❤️ Like → Posted to TikTok
   ❌ Dislike → Regenerated with different camera movement
```

### Phase 3: Posting
```
5. Liked content auto-posts to TikTok
   → Respects platform rate limits
   → No captions, hashtags, or overlays (pure visuals)
   → Tracked in videos.json with post URLs
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **[UV](https://github.com/astral-sh/uv) package manager** ⚠️ NEVER use pip - UV ONLY

### Installation

```bash
# Clone repository
git clone https://github.com/sebastianlungu/AI-Influencer.git
cd AI-Influencer

# Backend setup
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Frontend setup
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys (keep ALLOW_LIVE=false initially)
```

### Running the System

```bash
# Development mode
bash scripts/dev_run.sh  # Unix/Mac
scripts\dev_run.bat      # Windows

# OR run separately:
# Backend: uv run uvicorn app.main:app --reload --port 5001
# Frontend: cd frontend && npm run dev
```

**Access**:
- Frontend: http://localhost:5000
- Backend API: http://localhost:5001
- API Docs: http://localhost:5001/docs

### First Generation

1. Set `ALLOW_LIVE=true` in `.env` (enables paid API calls)
2. Click "Generate" in frontend
3. Wait 2-3 minutes for full pipeline
4. Review generated video in player

---

## 🔧 Configuration

### Required API Keys

Set these in your `.env` file:

| Provider | Variable | Purpose | Cost/Video |
|----------|----------|---------|------------|
| **Grok** | `GROK_API_KEY` | Ultra-detailed prompt generation | ~$0.09/batch |
| **Leonardo** | `LEONARDO_API_KEY` | Image generation | ~$0.02 |
| **Google Cloud** | `GOOGLE_APPLICATION_CREDENTIALS` | Veo 3 video generation | ~$0.40 |
| **Shotstack** | `SHOTSTACK_API_KEY` | Audio replacement | ~$0.03 |
| **TikTok** | `TIKTOK_CLIENT_KEY` | Posting (optional) | Free |

**Total cost per video**: ~$0.54

### Safety Guards

```bash
# Default: All paid API calls disabled
ALLOW_LIVE=false

# Enable paid APIs (required for generation)
ALLOW_LIVE=true

# Budget cap per cycle (default: $0.75 for 1 video)
MAX_COST_PER_RUN=0.75

# Automated scheduling (disabled by default)
ENABLE_SCHEDULER=false
```

### Character Configuration

Edit `app/data/prompt_config.json` to customize Eva Joy's profile and diversity banks:

```json
{
  "character_profile": {
    "name": "Eva Joy",
    "physical": {
      "body_type": "muscular, defined, athletic, curvy, feminine",
      "hair": "long, slightly wavy, dark brown (brunette)",
      "eyes": "expressive green eyes",
      ...
    },
    "style": {...},
    "fitness_focus": [...]
  },
  "diversity_banks": {
    "locations": [30 ultra-detailed venues],
    "poses": [25 specific body positions],
    "outfits": [25 garments with materials/colors],
    "accessories": [25 items with placement],
    "lighting": [25 cinematic scenarios],
    "camera": [25 technical specs],
    "props": [25 environmental elements],
    "creative_twists": [25 unexpected elements]
  }
}
```

---

## 🏗️ Architecture

### Pipeline Flow

```
User → Frontend → POST /api/cycle/generate
                        ↓
              Coordinator.run_cycle(n)
                        ↓
        ┌───────────────────────────────────┐
        │ Agent Pipeline (Sequential)       │
        ├───────────────────────────────────┤
        │ 1. prompting.propose()            │
        │    → Grok 200+ word prompts       │
        │    → Diversity bank sampling      │
        │    → Dedupe vs history.json       │
        │                                   │
        │ 2. gen_image.generate()           │
        │    → Leonardo.ai API              │
        │    → Downloads PNG                │
        │                                   │
        │ 3. gen_video.from_image()         │
        │    → Veo 3 img2vid                │
        │    → SynthID watermark            │
        │                                   │
        │ 4. edit.polish()                  │
        │    → Shotstack audio replace      │
        │                                   │
        │ 5. qa_style.ensure()              │
        │    → Blur detection               │
        │                                   │
        │ 6. indexer.index()                │
        │    → Write to videos.json         │
        │    → Move to generated/           │
        └───────────────────────────────────┘
                        ↓
              Returns video metadata
                        ↓
          Frontend displays in player
```

### Provider Abstraction

All external APIs hidden behind `clients/` with stable interfaces:

```python
# agents/prompting.py
grok = prompting_client()  # Returns GrokClient
variations = grok.generate_variations(profile, banks, n)

# agents/gen_image.py
leonardo = image_client()  # Returns LeonardoClient
image_path = leonardo.generate(payload)

# agents/gen_video.py
veo = video_client()  # Returns VeoVideoClient
video_path = veo.img2vid(image_path, motion_prompt)
```

**Why**: Swapping Leonardo → DALL·E or Veo → Runway requires only updating `clients/` directory, pipeline code unchanged.

### Fail-Loud Philosophy

```python
# ❌ NO silent failures
# ❌ NO mock modes
# ❌ NO degraded functionality

# ✅ Explicit validation
if not settings.allow_live:
    raise RuntimeError("ALLOW_LIVE=false. Set ALLOW_LIVE=true in .env")

if not api_key:
    raise RuntimeError(f"{PROVIDER}_API_KEY missing in .env")
```

**Why**: Prevents accidental spend, surfaces config issues immediately.

---

## 🎨 Grok Prompt Generation

### Ultra-Detailed Format (200+ Words)

Grok generates prompts following this structure:

```
photorealistic vertical 9:16 image of Eva Joy, [physical description with muscle
definition emphasis] [detailed pose with body positioning, gaze, emotion] in
[ultra-detailed location with architectural/environmental specifics]. Her defined,
muscular yet curvy feminine build is outlined by [specific lighting type creating
rim light/wet reflections/natural warmth on shoulders and arms]. She wears
[specific garment] in [material like suede/silk/cashmere] [specific color]
[how it catches light with realistic sheen/texture]. Accessories: [specific items
with materials and how they catch light]. Camera captures [specific angle and
perspective with emotional impact]. [Prop with placement and light interaction].
Background: [environmental details]. [Ultra-detailed lighting with color grading -
mention color temperature shifts, atmospheric tones]. [Focal length]mm lens at
f/[aperture], [DOF description], [composition rule], cinematic color balance
[color temperature description], composed for vertical framing with [headroom/
leading lines/negative space notes].
```

### Example Output

```
photorealistic vertical 9:16 image of Eva Joy, muscular yet feminine build with
defined abs and sculpted shoulders, rests one hand on terrace railing and looks
back over shoulder toward lens with confident gaze in rooftop terrace at sunset
above glowing modern city skyline with floor-to-ceiling glass railings. Her defined,
muscular yet curvy feminine build is outlined by golden-hour light wrapping scene
in amber tones with soft rim light giving very wet realistic skin reflections and
natural warmth on shoulders and arms. She wears structured cropped blazer in deep
terracotta suede over minimalist cream bralette, paired with wide-leg high-waisted
trousers in burnt saffron silk that catch light with realistic sheen. Accessories:
gold sculptural earrings with geometric design catching light, stacked thin bangles
on wrist. Camera captures low angle slightly below waist level looking up, 35mm at
f/2.2, creates powerful perspective. Glass of sparkling water with citrus slices
sits on railing beside subject, catching glint of sunlight. Golden-hour light wraps
scene in amber tones with faint lens flare across frame, cinematic color balance
shifting from orange warmth to cool violet shadows, composed for vertical framing
with balanced headroom and diagonal skyline lines guiding focus.
```

### Diversity Bank System

**8 Categories × 25-30 Items = 200+ Unique Combinations**

| Category | Examples | Purpose |
|----------|----------|---------|
| **Locations** | "rooftop terrace at sunset", "Maldives overwater villa deck" | Travel/gym/beach variety |
| **Poses** | "looks back over shoulder", "warrior II yoga pose" | Body positioning + emotion |
| **Outfits** | "terracotta suede blazer + saffron silk trousers" | Materials, colors, fit |
| **Accessories** | "gold sculptural earrings, thin bangles" | Jewelry, hair, footwear |
| **Lighting** | "golden-hour with lens flare", "blue hour twilight" | Color grading, atmosphere |
| **Camera** | "35mm f/2.0 low angle", "85mm f/1.8 bokeh" | Technical specs, composition |
| **Props** | "glass with citrus", "yoga mat" | Environmental storytelling |
| **Creative Twists** | "lens flare", "wet skin reflections" | Unexpected cinematic elements |

**Weighted Sampling** (in progress):
- Tracks last 50 combinations in `diversity_usage.json`
- Assigns inverse weights: never used = 1.0, used 3+ times = 0.2
- Grok receives preference hints to avoid repetition

---

## 📡 API Endpoints

### Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cycle/generate` | POST | Trigger generation cycle (rate limited 1/min) |
| `/api/healthz` | GET | Provider readiness check |

### Image Review (In Progress)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/images/pending` | GET | Fetch images awaiting review |
| `/api/images/{id}/rate` | PUT | Rate image (dislike/like/superlike) |
| `/api/images/liked` | GET | Fetch images queued for posting |
| `/api/images/superliked` | GET | Fetch images awaiting video generation |

### Video Review (In Progress)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/videos/pending` | GET | Fetch videos awaiting review |
| `/api/videos/{id}/rate` | PUT | Rate video (like/dislike) |
| `/api/videos/{id}/regenerate` | POST | Re-create video with new motion prompt |
| `/api/videos/generate/{image_id}` | POST | Generate video from super-liked image |

### Posting (Planned)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/videos/{id}/post` | POST | Publish to TikTok, move to posted/ |

---

## 🔐 Provider Setup

### 1. Grok (xAI) - Prompt Generation

**Cost**: ~$0.09 per 15-variation batch

1. Get API key from [xAI](https://console.x.ai/)
2. Add to `.env`:
   ```bash
   GROK_API_KEY=xai-your-key-here
   GROK_MODEL=grok-2-1212  # Default: grok-2-1212
   ```

**Models**:
- `grok-2-1212`: Best quality, high creativity
- `grok-beta`: Latest experimental features
- `grok-2-vision-1212`: Image understanding (not currently used)

### 2. Leonardo.ai - Image Generation

**Cost**: ~$0.02 per image

1. Create account at [Leonardo.ai](https://app.leonardo.ai/)
2. Get API key from [Settings → API Access](https://app.leonardo.ai/settings/api)
3. (Optional) Choose a model ID from the gallery
4. Add to `.env`:
   ```bash
   LEONARDO_API_KEY=your-key-here
   LEONARDO_MODEL_ID=  # Leave blank for default
   ```

### 3. Google Cloud Platform - Veo 3 Video

**Cost**: ~$0.40 per 8-second video

#### A. Create GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project (e.g., `ai-influencer-veo`)
3. Note your **Project ID** (auto-generated, not the display name)

#### B. Enable APIs

1. Navigate to "APIs & Services" → "Enable APIs and Services"
2. Search and enable:
   - **Vertex AI API**
   - **Cloud Storage API**
3. Wait 2-3 minutes for activation

#### C. Create Service Account

1. "IAM & Admin" → "Service Accounts" → "Create Service Account"
2. Name: `veo-video-generator`
3. Grant roles:
   - **Vertex AI User** (`roles/aiplatform.user`)
   - **Storage Object Admin** (`roles/storage.objectAdmin`)

#### D. Generate Key

1. Click service account → "Keys" tab → "Add Key" → "Create new key"
2. Choose **JSON** format
3. Save to secure location (e.g., `~/.gcp/ai-influencer-sa.json`)
4. **NEVER commit to git!**

#### E. Configure .env

```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

VIDEO_PROVIDER=veo
VEO_MODEL_ID=veo-3.0-generate-001
VEO_ASPECT=9:16
VEO_DURATION_SECONDS=8
```

⚠️ **SynthID Watermark**: Veo 3 embeds invisible provenance watermark automatically (cannot be disabled).

### 4. Shotstack - Video Editing

**Cost**: ~$0.03 per edit

1. Create account at [Shotstack](https://dashboard.shotstack.io/)
2. Get API key from dashboard
3. Upload licensed music to cloud storage (S3/GCS) or use Shotstack asset storage
4. Add to `.env`:
   ```bash
   SHOTSTACK_API_KEY=your-key-here
   SHOTSTACK_REGION=us  # or eu
   SOUNDTRACK_URL=https://your-storage.com/music/track.mp3
   OUTPUT_RESOLUTION=HD  # HD (1280x720) or 1080 (1920x1080)
   ```

⚠️ **Music Licensing**: You must own or license the soundtrack. Shotstack strips original audio (volume: 0) and replaces with your track.

### 5. Verify Setup

```bash
curl http://localhost:5001/api/healthz
```

Expected response:
```json
{
  "ok": true,
  "video_provider": "veo",
  "providers": {
    "grok": "configured",
    "leonardo": "configured",
    "veo": "configured",
    "shotstack": "configured"
  },
  "veo_config": {
    "gcp_project_id": "your-project-id",
    "credentials_file_exists": true
  }
}
```

---

## 💾 Data Files

### app/data/prompt_config.json
**Purpose**: Character profile + diversity banks (single source of truth)

**Structure**:
- `character_profile`: Eva Joy's physical traits, style, fitness focus
- `diversity_banks`: 8 categories with 25-30 detailed options each
- `negative_prompt`: Quality/safety constraints
- `quality_standards`: Format, resolution, photography style
- `safety_boundaries`: Clothing, proportions, content guidelines

### app/data/history.json
**Purpose**: Rolling window of generated content hashes for deduplication

**Format**:
```json
{
  "hashes": ["abc123...", "def456..."],
  "max_size": 5000
}
```

### app/data/videos.json
**Purpose**: Index of all generated/posted/deleted videos

**Schema** (current):
```json
[
  {
    "id": "abc123",
    "path": "app/data/generated/abc123.mp4",
    "seed": 1234567890,
    "status": "generated",
    "ts": 1706140800
  }
]
```

**Schema** (in progress - rating system):
```json
[
  {
    "id": "abc123",
    "status": "pending_review|liked|superliked|posted|deleted",
    "rating": null|"dislike"|"like"|"superlike",
    "image_path": "data/generated/img_abc123.png",
    "video_path": "data/generated/vid_abc123.mp4",
    "meta": {
      "prompt": "full 200+ word prompt",
      "diversity_meta": {
        "location": "rooftop terrace...",
        "pose": "over shoulder...",
        "outfit": "terracotta blazer...",
        ...
      },
      "seed": 1234
    },
    "video_meta": {
      "motion_prompt": "slow push-in...",
      "regeneration_count": 0
    },
    "created_at": "ISO8601",
    "rated_at": "ISO8601",
    "posted_at": "ISO8601"
  }
]
```

### app/data/diversity_usage.json (In Progress)
**Purpose**: Track recent combinations for weighted sampling

**Format**:
```json
{
  "recent_combinations": [
    {
      "location": "rooftop terrace",
      "outfit_style": "terracotta blazer",
      "lighting": "golden hour",
      "used_at": "ISO8601"
    }
  ],
  "element_usage_count": {
    "locations": {"rooftop terrace": 3, "Bali gym": 1},
    "outfits": {"terracotta blazer combo": 2}
  },
  "max_window": 50
}
```

---

## 🛡️ Security & Safety

### Financial Safety
- **Decimal-based cost tracking**: No float precision drift
- **Budget caps**: `MAX_COST_PER_RUN` enforced before each variation
- **Fail-loud on overspend**: Raises immediately if budget exceeded
- **No mock modes**: Missing API keys or disabled ALLOW_LIVE raise errors

### Path Safety
- **`safe_join()` wrapper**: Prevents path traversal attacks
- **Schema validation**: Pydantic models for all JSON files
- **Atomic writes**: Temp file + rename pattern prevents corruption

### Rate Limiting
- **`/api/cycle/generate`**: 1 request/minute
- **Grok client**: 2 requests/second
- **Retries**: Exponential backoff for 429/5xx errors (max 3 attempts)

### Content Safety
- **QA gates**: Blur detection via Laplacian variance
- **Safety boundaries**: SFW constraints in prompt_config.json
- **Negative prompts**: Explicit exclusions (nudity, exaggerated proportions, etc.)

---

## 🧪 Development

### UV Command Reference

| Action | Command |
|--------|---------|
| Install deps | `uv sync` |
| Add dependency | `uv add <package>` |
| Add dev dependency | `uv add --dev <package>` |
| Run backend | `uv run uvicorn app.main:app --reload --port 5001` |
| Run tests | `uv run pytest -q` |
| Lint | `uv run ruff check backend` |
| Type check | `uv run mypy backend` |
| Format | `uv run ruff format backend` |

### Project Structure

```
ai-influencer/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── api/routes.py           # API endpoints
│   │   ├── coordinator/            # Orchestration
│   │   ├── agents/                 # Pipeline steps
│   │   │   ├── prompting.py        # Grok integration
│   │   │   ├── gen_image.py        # Leonardo
│   │   │   ├── gen_video.py        # Veo 3
│   │   │   ├── edit.py             # Shotstack
│   │   │   └── video_prompting.py  # Motion prompts (in progress)
│   │   ├── clients/                # API wrappers
│   │   │   ├── grok.py
│   │   │   ├── leonardo.py
│   │   │   ├── veo.py
│   │   │   └── shotstack.py
│   │   ├── core/                   # Infrastructure
│   │   │   ├── config.py           # Pydantic settings
│   │   │   ├── cost.py             # Budget tracking
│   │   │   ├── storage.py          # Atomic JSON I/O
│   │   │   ├── ids.py              # Content hashing
│   │   │   └── paths.py            # Safe path handling
│   │   └── tests/
│   └── pyproject.toml              # UV dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main component
│   │   ├── ImageReview.jsx         # Rating UI (in progress)
│   │   ├── VideoReview.jsx         # Video rating (in progress)
│   │   └── QueueManagement.jsx     # Queues (in progress)
│   └── package.json
├── app/data/
│   ├── prompt_config.json          # Character + diversity banks
│   ├── history.json                # Dedupe hashes
│   ├── videos.json                 # Video index
│   ├── diversity_usage.json        # Weighted sampling (in progress)
│   ├── generated/                  # Output videos
│   ├── posted/                     # Published content
│   └── deleted/                    # Rejected content
├── .env.example
├── CLAUDE.md                       # Engineering guidelines
└── README.md                       # This file
```

### Adding Custom Diversity Options

1. Edit `app/data/prompt_config.json`
2. Add items to any diversity bank:
   ```json
   "locations": [
     "existing location...",
     "your new ultra-detailed location with architectural specifics..."
   ]
   ```
3. Restart backend (hot-reload picks up changes)
4. Next generation will include new options

### Customizing Character Profile

Edit `character_profile` in `prompt_config.json`:

```json
{
  "character_profile": {
    "name": "Your Character",
    "physical": {
      "body_type": "your description",
      "hair": "color and style",
      "eyes": "eye color",
      ...
    },
    "style": {...},
    "fitness_focus": [...]
  }
}
```

---

## 🐛 Troubleshooting

### "ALLOW_LIVE=false" Error
**Cause**: Safety guard preventing paid API calls
**Fix**: Set `ALLOW_LIVE=true` in `.env`

### "GROK_API_KEY missing"
**Cause**: API key not configured
**Fix**: Add `GROK_API_KEY=xai-...` to `.env`

### Leonardo "Model not found"
**Cause**: Invalid `LEONARDO_MODEL_ID`
**Fix**: Leave blank or use valid model ID from Leonardo.ai gallery

### Veo "Credentials not found"
**Cause**: `GOOGLE_APPLICATION_CREDENTIALS` path incorrect or file missing
**Fix**: Verify path exists and service account JSON is valid

### Shotstack "Asset not accessible"
**Cause**: `SOUNDTRACK_URL` not publicly accessible
**Fix**: Use pre-signed URL or upload to Shotstack asset storage

### "Budget exceeded"
**Cause**: Cumulative cost > `MAX_COST_PER_RUN`
**Fix**: Increase budget cap: `MAX_COST_PER_RUN=1.50` in `.env`

### Frontend "Cannot load video"
**Cause**: Static media serving not configured
**Fix**: Backend should serve `/media/generated/` route (in progress)

### "No module named 'app'"
**Cause**: Not using UV or venv not activated
**Fix**: Run `uv sync` and `source .venv/bin/activate`

---

## 📈 Roadmap

### Phase 1: Core Pipeline ✅
- [x] Grok ultra-detailed prompt generation (200+ words)
- [x] Leonardo image generation with polling
- [x] Veo 3 video generation with SynthID watermark
- [x] Shotstack audio replacement
- [x] QA style gates (blur detection)
- [x] Cost tracking with budget caps
- [x] Security: path traversal, schema validation, rate limiting

### Phase 2: Rating/Queue System 🚧 (In Progress)
- [ ] Image review UI (Dislike/Like/Super-like)
- [ ] Video review UI (Like/Dislike + Regenerate)
- [ ] Queue management UI (Liked/Super-liked queues)
- [ ] Video motion prompting agent
- [ ] Weighted diversity sampling (anti-repetition)
- [ ] API endpoints for rating workflow

### Phase 3: TikTok Integration 📋 (Planned)
- [ ] TikTok Content Posting API client
- [ ] OAuth authentication flow
- [ ] Rate limit handling (respect platform limits)
- [ ] Post tracking with TikTok URLs

### Phase 4: Analytics 📋 (Future)
- [ ] Performance dashboard (views, engagement)
- [ ] Cost analytics (spend per video, ROI)
- [ ] Diversity metrics (bank usage heatmap)
- [ ] A/B testing (compare prompt variations)

---

## 📄 License

[Your License Here]

## 🤝 Contributing

[Contribution Guidelines]

---

## 💡 Key Principles (Non-Negotiables)

**❌ NO MOCK MODES**: Fail loudly on missing configs or API credentials
**❌ NO CAPTIONS, VOICE, SUBTITLES**: Character is non-speaking
**❌ NO WATERMARKS, OVERLAYS**: Pure visuals only (except Veo 3's invisible SynthID)
**✅ LIVE CALLS OFF BY DEFAULT**: Requires explicit `ALLOW_LIVE=true`
**✅ SCHEDULER OFF BY DEFAULT**: Requires explicit `ENABLE_SCHEDULER=true`
**✅ UV ONLY**: Never use pip - UV exclusively

---

**Need Help?** Open an issue or check the troubleshooting section above.
