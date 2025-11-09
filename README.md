# AI Influencer - Eva Joy

> Manual workflow system for fitness influencer content: AI-generated prompts + manual asset creation + human review + automated scheduling

**Status**: ✅ **Production Ready** - Manual workflow with prompt generation, validation, music workflow, and automated scheduling

## Overview

A manual workflow system for creating professional AI fitness influencer content for "Eva Joy". Generate high-quality paired image + video prompts, create assets externally (Leonardo for images, Veo for videos), upload with strict validation, review with music workflow, and schedule posts automatically.

**Workflow**: Prompt Lab → External Generation (Leonardo/Veo) → Upload & Validate → Review → Music → Auto-Schedule

**Tech Stack**:
- **AI Prompting**: xAI Grok (image prompts, motion prompts, captions, music)
- **Image Generation**: Leonardo.ai (user-operated, external)
- **Video Generation**: Google Veo 3 (user-operated, external, 6s with SynthID)
- **Music Generation**: Suno AI (6-second instrumental clips)
- **Video Editing**: Local ffmpeg (audio/video muxing)
- **Social Posting**: TikTok + Instagram (scheduler-only)
- **Backend**: Python 3.11+, FastAPI, UV package manager
- **Frontend**: React + Vite
- **Storage**: Local filesystem (JSON indices + media files)

---

## ✨ Key Features

### Production-Ready
- ✅ **Prompt Lab**: Generate paired image + video prompts from high-level settings
- ✅ **Identity Lock**: JSON-driven persona consistency (hair, eyes, body type never drift)
- ✅ **Diversity Banks**: 200+ variations across locations, wardrobe, lighting, poses, camera
- ✅ **Manual Asset Upload**: Upload externally generated images/videos with prompt linking
- ✅ **Strict Validation**: Enforces 864×1536 (9:16) images, 6.0±0.05s videos
- ✅ **Rolling Storage**: Keeps last 100 prompt bundles (JSONL format)
- ✅ **Rating System**: Image review (Dislike/Like) + Video review (Like/Dislike)
- ✅ **Auto-Caption**: Grok generates captions (1-2 sentences + 5-10 hashtags) on video like
- ✅ **Music Workflow**: Grok music briefs → Suno generation → ffmpeg muxing → Human approval
- ✅ **Scheduler-Only Posting**: Automated TikTok + Instagram posting (NO manual post buttons)
- ✅ **Security**: Path traversal protection, schema validation, fail-loud validation

### Workflow Benefits
- ✅ **Full Control**: User controls exact prompts used in Leonardo/Veo
- ✅ **Quality Gates**: Human review at every step (image → video → music → post)
- ✅ **Cost Transparent**: Only pay for what you approve
- ✅ **Prompt Reuse**: Save and reference previous successful prompts

---

## 📋 Identity Lock & Diversity System

**Identity Lock** (`app/data/persona.json`):
- **Fixed traits** that never drift: hair (medium-length wavy caramel-blonde), eyes (bright blue), body (athletic, curvy, muscular with defined abs)
- **Trigger word**: `evajoy` (consistent across all prompts)
- **Quality standards**: photorealistic, single lighting plan, shallow DOF, 35mm f/2.0
- **Negative constraints**: No text, logos, watermarks, extra fingers, warped limbs

**Diversity Banks** (`app/data/variety_bank.json`):
- **Setting examples**: 30+ ultra-detailed locations (Japan, Santorini, Scandinavian home gym...)
- **Wardrobe**: 25+ outfit combinations with materials and colors
- **Accessories**: 25+ jewelry, watches, minimal items
- **Lighting**: 25+ cinematic scenarios (golden hour, blue hour, rim light...)
- **Camera**: 25+ technical specs (35mm f/2.0, 40mm f/2.2, 85mm f/1.8...)
- **Angles**: 25+ compositions (low 3/4, eye-level, over-shoulder...)
- **Pose/Microaction**: 25+ specific actions (tightening ponytail, glancing over shoulder...)
- **Color palettes**: 25+ grading styles (warm amber + charcoal neutrals...)

**Prompt Structure**:
Generated prompts combine identity lock + randomly sampled diversity elements to create unique, on-brand variations that maintain character consistency while maximizing visual variety.

---

## 🎯 User Workflow (Manual Generation)

### Phase 1: Prompt Generation
```
1. Navigate to Prompt Lab ([P] tab)
   → Enter high-level setting (e.g., "Japan traditional garden at dawn")
   → Optionally add seed words (e.g., "meditation", "serenity")
   → Select count (1-5 prompt bundles)
   → Click Generate

2. System generates paired prompts:
   → IMAGE PROMPT: 200+ word ultra-detailed Leonardo prompt
     - Includes identity lock (hair, eyes, body)
     - Samples diversity banks (wardrobe, lighting, pose, camera)
     - Enforces 864×1536 (9:16) vertical format
   → VIDEO PROMPT: Cinematic motion instructions for Veo 3
     - Character action description
     - Environment notes
     - 6-second duration spec

3. Copy prompt bundle ID (e.g., pr_abc123...)
   → System stores last 100 prompts (rolling window)
   → View recent prompts below generation form
```

### Phase 2: External Generation (Leonardo + Veo)
```
4. Generate image in Leonardo.ai:
   → Paste image prompt into Leonardo
   → Use Leonardo Alchemy V2 model
   → Set dimensions to 864×1536 (9:16 vertical)
   → Download PNG

5. Generate video in Veo 3:
   → Upload image to Veo 3
   → Paste video/motion prompt
   → Set duration to 6 seconds exactly
   → Download MP4 (includes SynthID watermark)
```

### Phase 3: Upload & Validation
```
6. Upload image ([I] Image Review tab):
   → Enter prompt ID in upload form
   → Select PNG file (864×1536 required)
   → System validates dimensions exactly
   → On success: Image appears in review queue

7. Upload video ([V] Video Review tab):
   → Enter prompt ID in upload form
   → Select MP4 file (6.0±0.05s, 9:16 required)
   → System validates duration and aspect ratio
   → On success: Video appears in review queue
```

### Phase 4: Image & Video Review
```
8. Rate images ([I] tab):
   ❌ Dislike [1/J] → Deleted immediately
   ❤️ Like [2/K] → Saved (ready for direct posting, not implemented)

9. Rate videos ([V] tab):
   ❌ Dislike [1/J] → Deleted immediately
   ❤️ Like [2/K] → Caption auto-generated via Grok, advance to Music Review
```

### Phase 5: Music Generation & Approval
```
10. Liked videos enter Music Review workflow:
    → Suggest Music: Grok generates music brief (style, mood, prompt)
    → Generate Music: Suno creates 6-second instrumental track
    → Auto-mux: ffmpeg combines video + music
    → User rates result:
      ✅ Approve → Queued for scheduler (status: approved)
      🔄 Regenerate → Try different music style
      ⏭️ Skip Music → Queue without music (status: approved)
```

### Phase 6: Automated Posting (Scheduler-Only)
```
11. Scheduler posts approved videos automatically:
    → Runs every 20 minutes (configurable cron)
    → Only posts within posting window (09:00-21:00 local time)
    → Uses Grok-generated caption from Phase 4
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
- **Leonardo.ai account** (for external image generation)
- **Google Veo 3 access** (for external video generation)

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
# Edit .env with your API keys:
# - GROK_API_KEY (required for prompt generation)
# - SUNO_API_KEY (required for music generation)
# - Keep ALLOW_LIVE=false initially for testing
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

### First Workflow Run

1. **Generate Prompts**:
   - Navigate to Prompt Lab ([P] tab)
   - Enter setting: "Scandinavian home gym at sunrise"
   - Click "Generate" (requires `ALLOW_LIVE=true` for Grok API)
   - Copy prompt bundle ID (e.g., `pr_abc123...`)

2. **Generate Assets Externally**:
   - Open Leonardo.ai
   - Paste image prompt, set to 864×1536, generate
   - Download PNG
   - Open Veo 3
   - Upload image, paste motion prompt, set to 6s, generate
   - Download MP4

3. **Upload & Review**:
   - Return to app, navigate to Image Review ([I] tab)
   - Enter prompt ID, select PNG, upload
   - Rate image: Like [2/K]
   - Navigate to Video Review ([V] tab)
   - Enter prompt ID, select MP4, upload
   - Rate video: Like [2/K] → Caption auto-generated

4. **Add Music & Approve**:
   - Music Review panel appears
   - Click "Suggest Music" → "Generate Music" → "Mux"
   - Preview result, click "Approve"

5. **Enable Scheduler** (optional):
   - Set `ENABLE_SCHEDULER=true` in `.env`
   - Configure posting window and platform
   - Scheduler posts approved videos automatically

---

## 🔧 Configuration

### Required API Keys

Set these in your `.env` file:

| Provider | Variable | Purpose | Cost |
|----------|----------|---------|------|
| **Grok** | `GROK_API_KEY` | Prompt generation (image, motion, captions, music) | ~$0.02 per 5 bundles |
| **Suno** | `SUNO_API_KEY` | Music generation (6s instrumental) | ~$0.10 per track |
| **TikTok** | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | Automated posting | Free |
| **Instagram** | `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Automated posting | Free |

**External (User-Operated)**:
- **Leonardo.ai**: Image generation (user manages externally) | ~$0.02 per image
- **Google Veo 3**: Video generation (user manages externally) | ~$0.30 per 6s video

**Total cost per video with music**: ~$0.42 (Grok + Suno only; Leonardo + Veo paid separately)

**Note**: ffmpeg is used locally for audio/video muxing (no API cost)

### Manual Workflow Configuration

Set these in your `.env` file for manual workflow:

```bash
# Manual Workflow Directories
PROMPTS_OUT_DIR=app/data/prompts      # Prompt bundle storage (JSONL)
PERSONA_FILE=app/data/persona.json    # Identity lock (hair, eyes, body)
VARIETY_FILE=app/data/variety_bank.json  # Diversity banks
MANUAL_IMAGES_DIR=app/data/manual/images  # Uploaded images
MANUAL_VIDEOS_DIR=app/data/manual/videos  # Uploaded videos

# Enforced Formats (strict validation)
IMAGE_WIDTH=864                       # Exact width required
IMAGE_HEIGHT=1536                     # Exact height required (9:16)
VIDEO_MUST_BE_SECONDS=6               # Exact duration ±0.05s
VIDEO_ASPECT=9:16                     # Required aspect ratio
```

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

**Identity Lock** (`app/data/persona.json`):
Edit this file to customize Eva Joy's fixed traits (never drift):

```json
{
  "trigger": "evajoy",
  "hair": "medium-length wavy caramel-blonde",
  "eyes": "bright blue",
  "body": "athletic, curvy, muscular with defined abs and toned arms",
  "skin": "realistic skin with subtle post-workout sheen",
  "do": ["photorealistic", "single lighting plan", "clean composition", "shallow DOF", "35mm f/2.0"],
  "dont": ["brunette", "plastic skin", "over-smooth", "uncanny", "text", "logos", "watermarks"]
}
```

**Diversity Banks** (`app/data/variety_bank.json`):
Edit this file to customize variety options (sampled randomly per prompt):

```json
{
  "setting_examples": ["Japan", "Santorini", "Scandinavian home gym", ...],
  "wardrobe": ["orchid-purple cropped top + white shorts", ...],
  "accessories": ["minimalist gold studs", "black fitness watch", ...],
  "lighting": ["soft warm rim + neutral bounce fill", ...],
  "camera": ["35mm f/2.0 shallow DOF", "40mm f/2.2", ...],
  "angle": ["low 3/4 side angle", "eye-level editorial", ...],
  "pose_microaction": ["tightening ponytail", "glancing over shoulder", ...],
  "color_palette": ["sport-editorial with warm amber rim", ...],
  "negative": ["doll-like", "uncanny face", "plastic skin", ...]
}
```

**How It Works**:
- `persona.json` defines **fixed identity** (hair, eyes, body) that appear in every prompt
- `variety_bank.json` defines **diversity options** sampled randomly for each prompt bundle
- Grok combines identity lock + diversity samples to generate unique, on-brand prompts

---

## 🏗️ Architecture

### Manual Workflow Flow

```
User → Prompt Lab ([P] tab) → POST /api/prompts/bundle
                                        ↓
                            Grok generates paired prompts
                            ┌────────────────────────────┐
                            │ IMAGE PROMPT (200+ words)  │
                            │ - Identity lock (persona)  │
                            │ - Diversity sampling       │
                            │ - 864×1536 (9:16) format   │
                            │                            │
                            │ VIDEO PROMPT (motion)      │
                            │ - Character action         │
                            │ - Environment notes        │
                            │ - 6-second duration        │
                            └────────────────────────────┘
                                        ↓
                            Returns bundle with unique ID
                                        ↓
                            User copies prompt + ID
                                        ↓
                ┌───────────────────────────────────────────┐
                │ External Generation (User-Operated)       │
                ├───────────────────────────────────────────┤
                │ Leonardo.ai:                              │
                │ - Paste image prompt                      │
                │ - Set 864×1536 dimensions                 │
                │ - Generate & download PNG                 │
                │                                           │
                │ Veo 3:                                    │
                │ - Upload image                            │
                │ - Paste motion prompt                     │
                │ - Set 6s duration                         │
                │ - Generate & download MP4                 │
                └───────────────────────────────────────────┘
                                        ↓
            User uploads to Image Review ([I] tab)
                                        ↓
                        POST /api/assets/upload
                            ┌──────────────────┐
                            │ validate_image() │
                            │ - Check 864×1536 │
                            │ - Save to manual/│
                            │ - Index to DB    │
                            └──────────────────┘
                                        ↓
            User uploads to Video Review ([V] tab)
                                        ↓
                        POST /api/assets/upload
                            ┌──────────────────┐
                            │ validate_video() │
                            │ - Check 6.0±0.05s│
                            │ - Check 9:16     │
                            │ - Save to manual/│
                            │ - Index to DB    │
                            └──────────────────┘
                                        ↓
              User rates video: Like [2/K]
                                        ↓
              PUT /api/videos/{id}/rate
              → Grok generates caption (1-2 sentences + hashtags)
              → Status: liked
                                        ↓
              Music Review Panel appears
                                        ↓
          Suggest → Generate → Mux → Rate (Approve/Regenerate/Skip)
                                        ↓
          If Approve → Status: approved (queued for scheduler)
                                        ↓
          Scheduler posts when within posting window
```

### System Components

**Grok Client** (`clients/grok.py`):
- `generate_prompt_bundle()`: Creates paired image + video prompts from setting + diversity banks
- `generate_quick_caption()`: Generates captions (1-2 sentences + hashtags) on video like

**Validators** (`agents/validators.py`):
- `validate_image_dimensions()`: Strict 864×1536 check using PIL
- `validate_video_format()`: Duration (6.0±0.05s) and aspect ratio (9:16) using ffprobe

**Prompt Storage** (`core/prompt_storage.py`):
- `append_prompt_bundle()`: JSONL format with rolling window (keeps last 100)
- `read_recent_prompts()`: Returns newest-first for UI display
- `find_prompt_bundle()`: Lookup by ID for upload linking

**Suno Client** (`clients/suno.py`):
- `generate_clip()`: 6-second instrumental music generation

**FFmpeg Client** (`clients/ffmpeg_mux.py`):
- `mux()`: Combines video + music audio tracks locally

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

### Prompt Lab (Manual Workflow)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/prompts/bundle` | POST | Generate N prompt bundles (image + video prompts) |
| `/api/prompts` | GET | Get recent prompt bundles (newest first, default: 20) |
| `/api/assets/upload` | POST | Upload manually generated image or video with validation |

**POST /api/prompts/bundle Request**:
```json
{
  "setting": "Scandinavian home gym at sunrise",
  "seed_words": ["meditation", "serenity"],
  "count": 3
}
```

**Response**:
```json
{
  "ok": true,
  "bundles": [
    {
      "id": "pr_abc123...",
      "image_prompt": {
        "final_prompt": "photorealistic vertical 9:16 image of evajoy...",
        "negative_prompt": "doll-like, plastic skin...",
        "width": 864,
        "height": 1536
      },
      "video_prompt": {
        "motion": "slow push-in with subtle upward drift...",
        "character_action": "holding meditation pose...",
        "environment": "soft natural light through windows...",
        "duration_seconds": 6,
        "notes": "Maintain serene atmosphere..."
      }
    }
  ]
}
```

**POST /api/assets/upload Request** (multipart form-data):
- `file`: Image (PNG/JPEG) or video (MP4/MOV)
- `asset_type`: "image" or "video"
- `prompt_id`: Prompt bundle ID (e.g., "pr_abc123...")

### Image Review

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/images/pending` | GET | Fetch images awaiting review |
| `/api/images/{id}/rate` | PUT | Rate image (dislike/like) |
| `/api/images/liked` | GET | Fetch images queued for posting |

### Video Review

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/videos/pending` | GET | Fetch videos awaiting review |
| `/api/videos/{id}/rate` | PUT | Rate video (like/dislike) - auto-generates caption on like |
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

**Cost**: ~$0.002 per 15-variation batch (98% reduction with Grok-4-fast)

1. Get API key from [xAI](https://console.x.ai/)
2. Add to `.env`:
   ```bash
   GROK_API_KEY=xai-your-key-here
   GROK_MODEL=grok-4-fast-reasoning  # Default: grok-4-fast-reasoning
   ```

**Models**:
- `grok-4-fast-reasoning`: Best performance, 98% cost reduction, fastest inference
- `grok-4-fast-non-reasoning`: Quick responses without chain-of-thought
- `grok-2-latest`: Legacy model (higher cost, slower)

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

### app/data/persona.json
**Purpose**: Identity lock (fixed traits that never drift)

**Structure**:
```json
{
  "trigger": "evajoy",
  "hair": "medium-length wavy caramel-blonde",
  "eyes": "bright blue",
  "body": "athletic, curvy, muscular with defined abs and toned arms",
  "skin": "realistic skin with subtle post-workout sheen",
  "do": ["photorealistic", "single lighting plan", "shallow DOF"],
  "dont": ["brunette", "plastic skin", "text", "logos", "watermarks"]
}
```

### app/data/variety_bank.json
**Purpose**: Diversity options sampled randomly per prompt

**Structure**:
```json
{
  "setting_examples": ["Japan", "Santorini", "Scandinavian home gym", ...],
  "wardrobe": ["orchid-purple cropped top + white shorts", ...],
  "accessories": ["minimalist gold studs", "black fitness watch", ...],
  "lighting": ["soft warm rim + neutral bounce fill", ...],
  "camera": ["35mm f/2.0 shallow DOF", "40mm f/2.2", ...],
  "angle": ["low 3/4 side angle", "eye-level editorial", ...],
  "pose_microaction": ["tightening ponytail", "glancing over shoulder", ...],
  "color_palette": ["sport-editorial with warm amber rim", ...],
  "negative": ["doll-like", "uncanny face", "plastic skin", ...]
}
```

### app/data/prompts/prompts.jsonl
**Purpose**: Rolling window of prompt bundles (keeps last 100)

**Format** (one JSON object per line):
```jsonl
{"id":"pr_abc123...","setting":"Japan traditional garden","seed_words":["meditation","serenity"],"image_prompt":{...},"video_prompt":{...},"created_at":"2025-01-07T12:34:56Z"}
{"id":"pr_def456...","setting":"Santorini sunset terrace","seed_words":[],"image_prompt":{...},"video_prompt":{...},"created_at":"2025-01-07T13:00:00Z"}
```

### app/data/images.json
**Purpose**: Index of all uploaded images

**Schema**:
```json
[
  {
    "id": "img_abc123",
    "prompt_id": "pr_abc123",
    "image_path": "app/data/manual/images/img_abc123.png",
    "status": "pending_review|liked|deleted",
    "source": "manual_upload",
    "created_at": "2025-01-07T14:00:00Z",
    "rated_at": "2025-01-07T14:05:00Z"
  }
]
```

### app/data/videos.json
**Purpose**: Index of all uploaded/posted videos

**Schema**:
```json
[
  {
    "id": "vid_abc123",
    "prompt_id": "pr_abc123",
    "image_id": "img_abc123",
    "video_path": "app/data/manual/videos/vid_abc123.mp4",
    "status": "pending_review|liked|pending_review_music|approved|posted|deleted",
    "source": "manual_upload",
    "caption": "Generated caption with hashtags #fitness #motivation",
    "music": {
      "brief": "ambient cinematic fitness background",
      "style": "minimal electronic",
      "mood": "calm energizing",
      "audio_path": "app/data/generated/music_abc123.mp3",
      "music_status": "suggested|generated|approved|skipped"
    },
    "posted_platform": "tiktok",
    "posted_id": "7123456789012345678",
    "posted_at": "2025-01-07T18:00:00Z",
    "created_at": "2025-01-07T14:10:00Z",
    "rated_at": "2025-01-07T14:15:00Z"
  }
]
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
│   │   ├── api/routes.py           # API endpoints (manual workflow)
│   │   ├── agents/                 # Validation & helpers
│   │   │   ├── validators.py       # Image/video validation (PIL, ffprobe)
│   │   │   └── indexer.py          # Write to images.json / videos.json
│   │   ├── clients/                # API wrappers
│   │   │   ├── grok.py             # xAI Grok (prompts, captions, music)
│   │   │   ├── suno.py             # Suno music generation
│   │   │   ├── ffmpeg_mux.py       # Local ffmpeg operations
│   │   │   ├── tiktok.py           # TikTok posting
│   │   │   └── instagram.py        # Instagram posting
│   │   ├── core/                   # Infrastructure
│   │   │   ├── config.py           # Pydantic settings
│   │   │   ├── storage.py          # Atomic JSON I/O
│   │   │   ├── prompt_storage.py   # JSONL rolling window (last 100)
│   │   │   ├── ids.py              # Content hashing
│   │   │   ├── paths.py            # Safe path handling
│   │   │   └── scheduler.py        # APScheduler posting workflow
│   │   └── tests/
│   │       └── test_validators.py
│   └── pyproject.toml              # UV dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main component (5 tabs)
│   │   ├── PromptLab.jsx           # Prompt generation UI
│   │   ├── ImageReview.jsx         # Image rating + upload UI
│   │   ├── VideoReview.jsx         # Video rating + upload + Music workflow
│   │   ├── QueueView.jsx           # Queue status
│   │   ├── SchedulerSettings.jsx   # Scheduler controls
│   │   └── api.js                  # API helpers
│   └── package.json
├── app/data/
│   ├── persona.json                # Identity lock (hair, eyes, body)
│   ├── variety_bank.json           # Diversity banks (wardrobe, lighting, etc.)
│   ├── prompts/
│   │   └── prompts.jsonl           # Rolling window of prompt bundles
│   ├── images.json                 # Image index (all metadata)
│   ├── videos.json                 # Video index (all metadata)
│   ├── manual/
│   │   ├── images/                 # Uploaded images (validated)
│   │   └── videos/                 # Uploaded videos (validated)
│   ├── generated/                  # Music + muxed videos
│   ├── posted/                     # Published content
│   └── deleted/                    # Rejected content
├── .env.example
├── CLAUDE.md                       # Engineering guidelines
└── README.md                       # This file
```

### Adding Custom Diversity Options

1. Edit `app/data/variety_bank.json`
2. Add items to any diversity array:
   ```json
   {
     "wardrobe": [
       "existing outfit...",
       "your new ultra-detailed outfit with materials and colors..."
     ],
     "lighting": [
       "existing lighting...",
       "your new cinematic lighting scenario..."
     ]
   }
   ```
3. Restart backend (hot-reload picks up changes)
4. Next prompt generation will include new options

### Customizing Character Identity

Edit `app/data/persona.json` to change Eva Joy's fixed traits:

```json
{
  "trigger": "yourcharacter",
  "hair": "your hair description",
  "eyes": "your eye color",
  "body": "your body type description",
  "skin": "your skin description",
  "do": ["style guidelines..."],
  "dont": ["things to avoid..."]
}
```

**Note**: Changes to `persona.json` affect identity lock (appears in every prompt), while changes to `variety_bank.json` affect diversity sampling (varies per prompt).

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

### Phase 1: Manual Workflow ✅ (Complete)
- [x] Prompt Lab UI with prompt bundle generation
- [x] Grok paired prompt generation (image + video prompts)
- [x] Identity lock system (persona.json)
- [x] Diversity banks system (variety_bank.json)
- [x] Rolling prompt storage (JSONL, last 100)
- [x] Manual image upload with strict validation (864×1536)
- [x] Manual video upload with strict validation (6s, 9:16)
- [x] Image review UI (Dislike/Like)
- [x] Video review UI (Like/Dislike)
- [x] Auto-caption generation on video like (Grok)
- [x] Music workflow (Grok brief → Suno generation → ffmpeg mux)
- [x] Music review UI (Approve/Regenerate/Skip)
- [x] Scheduler-only posting (TikTok + Instagram)
- [x] Scheduler controls (run-once, dry-run)
- [x] Security: path traversal, schema validation, fail-loud validation

### Phase 2: Enhancements 📋 (Planned)
- [ ] Weighted diversity sampling (avoid recent combinations)
- [ ] Prompt favorites/bookmarking system
- [ ] Bulk prompt generation (10+ bundles at once)
- [ ] Prompt search and filtering
- [ ] Export/import prompt bundles
- [ ] Leonardo API integration for optional auto-generation
- [ ] Veo API integration for optional auto-generation

### Phase 3: Analytics & Optimization 📋 (Future)
- [ ] Performance dashboard (views, engagement per video)
- [ ] Cost analytics (spend tracking per video)
- [ ] Diversity metrics (bank usage heatmap, avoid repetition)
- [ ] A/B testing (compare prompt variations and music styles)
- [ ] Multi-platform posting analytics
- [ ] Dynamic posting schedule optimization (best times per platform)
- [ ] Automated hashtag optimization based on performance

---

## 📄 License

[Your License Here]

## 🤝 Contributing

[Contribution Guidelines]

---

## 💡 Key Principles (Non-Negotiables)

**❌ NO MOCK MODES**: Fail loudly on missing configs or API credentials
**❌ NO CAPTIONS, VOICE, SUBTITLES**: Character is non-speaking (captions generated for posting only)
**❌ NO WATERMARKS, OVERLAYS**: Pure visuals only (except Veo 3's invisible SynthID)
**✅ MANUAL WORKFLOW**: User generates images/videos externally (Leonardo/Veo)
**✅ STRICT VALIDATION**: Enforces exact dimensions (864×1536) and duration (6.0±0.05s)
**✅ IDENTITY LOCK**: Fixed traits (hair, eyes, body) never drift from persona.json
**✅ LIVE CALLS OFF BY DEFAULT**: Requires explicit `ALLOW_LIVE=true`
**✅ SCHEDULER OFF BY DEFAULT**: Requires explicit `ENABLE_SCHEDULER=true`
**✅ UV ONLY**: Never use pip - UV exclusively

---

**Need Help?** Open an issue or check the troubleshooting section above.
