# AI Influencer - Eva Joy

> Automated AI-generated fitness influencer content pipeline with Grok AI prompting, Suno music generation, and scheduler-only posting workflow

**Status**: ✅ **Production Ready** - Complete pipeline with music workflow and automated scheduling

## Overview

An end-to-end system for generating professional AI fitness influencer content for "Eva Joy" - from AI-generated image briefs and motion prompts to TikTok-ready videos with music. Built with fail-loud safety guards, provider abstraction, and comprehensive human review gates.

**Tech Stack**:
- **AI Prompting**: xAI Grok (image briefs, motion, music, social meta)
- **Image Generation**: Leonardo.ai
- **Video Generation**: Google Veo 3 (6 seconds, Vertex AI) with SynthID watermark
- **Music Generation**: Suno AI (6-second instrumental clips)
- **Video Editing**: Local ffmpeg (audio/video muxing)
- **Social Posting**: TikTok + Instagram (scheduler-only)
- **Backend**: Python 3.11+, FastAPI, UV package manager
- **Frontend**: React + Vite
- **Storage**: Local filesystem (JSON indices + media files)

---

## ✨ Key Features

### Production-Ready
- ✅ **Ultra-Detailed Prompts**: 200-250 word cinematic prompts via Grok
- ✅ **8 Diversity Banks**: 200+ variations across locations, poses, outfits, lighting, camera, props, twists
- ✅ **Intelligent Dedupe**: SHA256 content hashing + per-video motion deduplication
- ✅ **Cost Tracking**: Decimal-based budget caps (~$0.54/video)
- ✅ **Security**: Path traversal protection, schema validation, rate limiting
- ✅ **End-to-End Pipeline**: Grok → Leonardo → Veo 3 (6s) → ffmpeg → Music → Posting
- ✅ **Rating System**: Image review (Dislike/Like/Super-like) + Video review (Like/Dislike/Regenerate)
- ✅ **Music Workflow**: Grok music briefs → Suno generation → ffmpeg muxing → Human approval
- ✅ **Motion Prompting**: Cinematic camera movements from image metadata (with per-video deduplication)
- ✅ **Scheduler-Only Posting**: Automated TikTok + Instagram posting (NO manual post buttons)
- ✅ **Social Metadata**: Grok-generated captions and hashtags at posting time

### Planned
- 📋 **Weighted Diversity**: Track recent combinations, avoid repetition across pipeline
- 📋 **Analytics Dashboard**: Track performance, costs, diversity metrics
- 📋 **A/B Testing**: Compare prompt variations and music styles

---

## 🎯 User Workflow (Production)

### Phase 1: Image Generation & Review
```
1. System generates image variations
   → Grok creates ultra-detailed prompts from diversity banks
   → Leonardo generates high-res images
   → Images appear in Review UI ([I] tab)

2. User rates each image:
   ❌ Dislike [1] → Deleted immediately
   ❤️ Like [2] → Queued for direct image posting (not implemented)
   ⭐ Super-like [3] → Queued for video generation
```

### Phase 2: Video Generation & Review
```
3. Super-liked images automatically generate videos
   → Grok creates cinematic motion prompt from image metadata
   → Veo 3 converts image to 6-second video (with SynthID watermark)
   → ffmpeg trims to exactly 6 seconds
   → Videos appear in Video Review UI ([V] tab)

4. User rates each video:
   ❌ Dislike [1] → Deleted (motion history cleared)
   ❤️ Like [2] → Advance to Music Review panel
   🔄 Regenerate [R] → Re-create with different motion (avoids previous prompts)
```

### Phase 3: Music Generation & Approval
```
5. Liked videos enter Music Review workflow
   → Suggest Music: Grok generates music brief (style, mood, prompt)
   → Generate Music: Suno creates 6-second instrumental track
   → Auto-mux: ffmpeg combines video + music
   → User rates result:
     ✅ Approve → Queued for scheduler (status: approved)
     🔄 Regenerate → Try different music style
     ⏭️ Skip Music → Queue without music
```

### Phase 4: Automated Posting (Scheduler-Only)
```
6. Scheduler posts approved videos automatically
   → Runs every 20 minutes (configurable cron)
   → Only posts within posting window (09:00-21:00 local time)
   → Grok generates social metadata (caption + hashtags) at posting time
   → Posts to TikTok or Instagram (configurable platform)
   → Tracked in videos.json with post IDs
   → NO MANUAL POST BUTTONS (scheduler-only workflow)
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
| **Grok** | `GROK_API_KEY` | Prompting (image, motion, music, social) | ~$0.12/video |
| **Leonardo** | `LEONARDO_API_KEY` | Image generation | ~$0.02 |
| **Google Cloud** | `GOOGLE_APPLICATION_CREDENTIALS` | Veo 3 video generation (6s) | ~$0.30 |
| **Suno** | `SUNO_API_KEY` | Music generation (6s instrumental) | ~$0.10 |
| **TikTok** | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | Automated posting | Free |
| **Instagram** | `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Automated posting | Free |

**Total cost per video with music**: ~$0.54

**Note**: ffmpeg is used locally for audio/video muxing (no API cost)

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

# Scheduler configuration (when enabled)
SCHEDULER_CRON_MINUTES=20           # Run every 20 minutes
POSTING_WINDOW_LOCAL=09:00-21:00   # Only post between these hours
DEFAULT_POSTING_PLATFORM=tiktok     # tiktok or instagram
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
        │    → Veo 3 img2vid (6 seconds)    │
        │    → SynthID watermark embedded   │
        │                                   │
        │ 4. edit.polish()                  │
        │    → ffmpeg trim to exactly 6s    │
        │    → NO MUSIC (added later)       │
        │                                   │
        │ 5. qa_style.ensure()              │
        │    → Container validation only    │
        │    → Blur QA DISABLED             │
        │                                   │
        │ 6. indexer.index()                │
        │    → Write to videos.json         │
        │    → Move to generated/           │
        │    → Status: pending_review       │
        └───────────────────────────────────┘
                        ↓
              Returns video metadata
                        ↓
          Frontend displays in Video Review ([V] tab)
                        ↓
          User rates: Dislike [1] / Like [2] / Regenerate [R]
                        ↓
          If Like → Music Review Panel
                        ↓
          Suggest → Generate → Mux → Rate (Approve/Regenerate/Skip)
                        ↓
          If Approve → Status: approved (queued for scheduler)
                        ↓
          Scheduler posts when within posting window
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

### Image Review

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/images/pending` | GET | Fetch images awaiting review |
| `/api/images/{id}/rate` | PUT | Rate image (dislike/like/superlike) |
| `/api/images/liked` | GET | Fetch images queued for posting |
| `/api/images/superliked` | GET | Fetch images awaiting video generation |

### Video Review

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/videos/pending` | GET | Fetch videos awaiting review |
| `/api/videos/{id}/rate` | PUT | Rate video (like/dislike) |
| `/api/videos/{id}/regenerate` | POST | Re-create video with new motion prompt |
| `/api/videos/generate/{image_id}` | POST | Generate video from super-liked image |
| `/api/videos/approved` | GET | Fetch videos approved and queued for scheduler |

### Music Workflow

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/videos/{id}/music/suggest` | POST | Generate music brief via Grok |
| `/api/videos/{id}/music/generate` | POST | Generate music audio via Suno (6s) |
| `/api/videos/{id}/music/mux` | POST | Mux video + music via ffmpeg |
| `/api/videos/{id}/music/rate` | PUT | Rate music (approve/regenerate/skip) |

### Scheduler Control (Scheduler-Only Posting)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scheduler/run-once` | POST | Execute posting cycle immediately (requires ALLOW_LIVE=true) |
| `/api/scheduler/dry-run` | POST | Preview next video to be posted without executing |

**Note**: There are NO manual post buttons. Posting is scheduler-only.

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
VEO_DURATION_SECONDS=6
GEN_SECONDS=6  # Default generation duration
```

⚠️ **SynthID Watermark**: Veo 3 embeds invisible provenance watermark automatically (cannot be disabled).

### 4. Suno - Music Generation

**Cost**: ~$0.10 per 6-second instrumental

1. Create account at [Suno](https://suno.com/)
2. Get API key from account settings
3. Add to `.env`:
   ```bash
   SUNO_API_KEY=your-key-here
   SUNO_MODEL=chirp-v3-5  # Default: chirp-v3-5
   SUNO_CLIP_SECONDS=6    # Must match VEO_DURATION_SECONDS
   ```

**Models**:
- `chirp-v3-5`: Latest, best quality
- `chirp-v3`: Previous generation

⚠️ **Duration**: Suno clip duration must match Veo duration (both 6 seconds)

### 5. ffmpeg - Local Video Editing

**Cost**: Free (local processing)

**Installation**:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or `winget install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` or `sudo yum install ffmpeg`

**Verify**:
```bash
ffmpeg -version
ffprobe -version
```

**Usage**: ffmpeg is used for:
- Trimming videos to exactly 6 seconds
- Muxing video + music audio tracks
- Container validation

### 6. Verify Setup

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
    "suno": "configured",
    "tiktok": "configured",
    "instagram": "configured"
  },
  "scheduler_enabled": false,
  "scheduler_config": {
    "platform": "tiktok",
    "cron": "*/20 minutes",
    "window": "09:00-21:00",
    "timezone": "Europe/Paris"
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

**Schema** (production):
```json
[
  {
    "id": "abc123",
    "status": "pending_review|liked|approved|posted|deleted",
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
      "seed": 1234,
      "duration_s": 6
    },
    "video_meta": {
      "motion_prompt": "slow push-in...",
      "regeneration_count": 0
    },
    "music_meta": {
      "music_brief": {
        "prompt": "energetic upbeat electronic...",
        "style": "electronic pop",
        "mood": "energetic"
      },
      "music_path": "data/generated/music_abc123.mp3",
      "music_rating": null|"approve"|"regenerate"|"skip"
    },
    "social_meta": {
      "caption": "Generated caption for TikTok/Instagram",
      "hashtags": ["#fitness", "#motivation"]
    },
    "created_at": "ISO8601",
    "rated_at": "ISO8601",
    "music_approved_at": "ISO8601",
    "posted_at": "ISO8601",
    "post_id": "tiktok_video_id or instagram_media_id"
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
- **QA gates**: Container validation only (blur detection DISABLED - identity QA handled by human review)
- **Safety boundaries**: SFW constraints in referral_prompts.json
- **Negative prompts**: Explicit exclusions (nudity, exaggerated proportions, etc.)
- **Human review**: All videos reviewed by human before approval for posting

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
│   │   ├── api/routes.py           # API endpoints (all workflows)
│   │   ├── coordinator/            # Orchestration
│   │   ├── agents/                 # Pipeline steps
│   │   │   ├── prompting.py        # Grok image prompts
│   │   │   ├── gen_image.py        # Leonardo
│   │   │   ├── gen_video.py        # Veo 3
│   │   │   ├── video_prompting.py  # Grok motion prompts
│   │   │   ├── edit.py             # ffmpeg trim
│   │   │   └── indexer.py          # Write to videos.json
│   │   ├── clients/                # API wrappers
│   │   │   ├── grok.py             # xAI Grok (all prompting)
│   │   │   ├── leonardo.py         # Image generation
│   │   │   ├── veo.py              # Veo 3 video
│   │   │   ├── suno.py             # Suno music generation
│   │   │   ├── ffmpeg_mux.py       # Local ffmpeg operations
│   │   │   ├── tiktok.py           # TikTok posting
│   │   │   ├── instagram.py        # Instagram posting
│   │   │   └── provider_selector.py # DI + fail-loud guards
│   │   ├── core/                   # Infrastructure
│   │   │   ├── config.py           # Pydantic settings
│   │   │   ├── cost.py             # Budget tracking
│   │   │   ├── storage.py          # Atomic JSON I/O
│   │   │   ├── ids.py              # Content hashing
│   │   │   ├── paths.py            # Safe path handling
│   │   │   ├── scheduler.py        # APScheduler posting workflow
│   │   │   └── motion_dedup.py     # Per-video motion tracking
│   │   └── tests/
│   │       ├── test_pipeline_smoke.py
│   │       └── test_new_architecture.py  # 17 comprehensive tests
│   └── pyproject.toml              # UV dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main component (4 tabs)
│   │   ├── ImageReview.jsx         # Image rating UI
│   │   ├── VideoReview.jsx         # Video + Music workflow
│   │   ├── QueueView.jsx           # Queue status
│   │   ├── SchedulerSettings.jsx   # Scheduler controls
│   │   └── api.js                  # API helpers
│   └── package.json
├── app/data/
│   ├── referral_prompts.json       # Eva Joy persona + style
│   ├── history.json                # Dedupe hashes
│   ├── videos.json                 # Video index (all metadata)
│   ├── motion/                     # Per-video motion history
│   ├── generated/                  # Output videos + music
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

### Suno "API key invalid"
**Cause**: `SUNO_API_KEY` missing or incorrect
**Fix**: Verify API key from Suno account settings

### "ffmpeg not found"
**Cause**: ffmpeg not installed or not in PATH
**Fix**: Install ffmpeg (see Provider Setup section), verify with `ffmpeg -version`

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

### Phase 1: Core Pipeline ✅ (Complete)
- [x] Grok ultra-detailed prompt generation (200+ words)
- [x] Leonardo image generation with polling
- [x] Veo 3 video generation (6 seconds) with SynthID watermark
- [x] ffmpeg video trimming and muxing
- [x] QA style gates (container validation, blur disabled)
- [x] Cost tracking with budget caps
- [x] Security: path traversal, schema validation, rate limiting
- [x] Image review UI (Dislike/Like/Super-like)
- [x] Video review UI (Like/Dislike + Regenerate)
- [x] Queue management UI (all queues visible)
- [x] Video motion prompting agent (Grok-powered)
- [x] Per-video motion deduplication
- [x] Music workflow (Grok brief → Suno generation → ffmpeg mux)
- [x] Music review UI (Approve/Regenerate/Skip)
- [x] Scheduler-only posting (TikTok + Instagram)
- [x] Social metadata generation (Grok captions + hashtags)
- [x] Scheduler controls (run-once, dry-run)

### Phase 2: Optimization & Analytics 📋 (Planned)
- [ ] Weighted diversity sampling (anti-repetition across pipeline)
- [ ] Performance dashboard (views, engagement)
- [ ] Cost analytics (spend per video, ROI)
- [ ] Diversity metrics (bank usage heatmap)
- [ ] A/B testing (compare prompt variations and music styles)
- [ ] Multi-platform posting analytics

### Phase 3: Advanced Features 📋 (Future)
- [ ] Dynamic posting schedule optimization (best times per platform)
- [ ] Automated hashtag optimization based on performance
- [ ] LoRA training integration for consistent character appearance
- [ ] Multiple character profiles support
- [ ] Batch video generation workflows

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
