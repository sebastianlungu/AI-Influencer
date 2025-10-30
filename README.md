# AI Influencer System

Automated video generation pipeline with fail-loud safety guards and no mock modes.

## Key Principles

**❌ NON-NEGOTIABLES:**
- **NO MOCK MODES:** Fail loudly on missing configs or API credentials
- **NO CAPTIONS, VOICE, SUBTITLES:** Character is non-speaking
- **NO WATERMARKS, OVERLAYS:** Pure visuals only
- **LIVE CALLS OFF BY DEFAULT:** Requires explicit `ALLOW_LIVE=true`
- **SCHEDULER OFF BY DEFAULT:** Requires explicit `ENABLE_SCHEDULER=true`

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [UV](https://github.com/astral-sh/uv) package manager

⚠️ **NEVER use pip - UV ONLY** ⚠️

### Setup

```bash
# Clone and enter project
git clone https://github.com/sebastianlungu/AI-Influencer.git
cd ai-influencer

# Create and sync environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Install Node dependencies
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env and set your API keys (keep ALLOW_LIVE=false initially)

# Run dev servers
bash scripts/dev_run.sh  # Unix/Mac
# OR
scripts\dev_run.bat      # Windows
```

**Access:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### ✅ UV Command Reference

| Action | Command |
|--------|---------|
| Install all deps | `uv sync` |
| Add new dep | `uv add <pkg>` |
| Add dev dep | `uv add --dev <pkg>` |
| Upgrade all deps | `uv sync --upgrade` |
| Run FastAPI | `uv run uvicorn app.main:app --reload --port 8000` |
| Run tests | `uv run pytest -q` |
| Lint | `uv run ruff check backend` |
| Type check | `uv run mypy backend` |

## Google Cloud Platform Setup (Veo 3)

The system uses **Google Veo 3** on Vertex AI for video generation. Follow these steps to configure GCP:

### 1. Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name your project (e.g., `ai-influencer-veo`)
4. Note your **Project ID** (not the name - the ID is auto-generated)

### 2. Enable Required APIs

1. Navigate to "APIs & Services" → "Enable APIs and Services"
2. Search and enable:
   - **Vertex AI API**
   - **Cloud Storage API** (for intermediate files)
3. Wait for APIs to activate (may take 2-3 minutes)

### 3. Create a Service Account

1. Navigate to "IAM & Admin" → "Service Accounts"
2. Click "Create Service Account"
3. Name: `veo-video-generator`
4. Grant roles:
   - **Vertex AI User** (`roles/aiplatform.user`)
   - **Storage Object Admin** (`roles/storage.objectAdmin`)
5. Click "Done"

### 4. Generate and Download Service Account Key

1. Click on your new service account
2. Go to "Keys" tab → "Add Key" → "Create new key"
3. Choose **JSON** format
4. Save the downloaded JSON file securely (e.g., `~/.gcp/ai-influencer-sa.json`)
5. **NEVER commit this file to git!**

### 5. Configure Environment Variables

Edit your `.env` file:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-actual-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account.json

# Veo 3 Settings (defaults shown)
VIDEO_PROVIDER=veo
VEO_MODEL_ID=veo-3.0-generate-001
VEO_ASPECT=9:16
VEO_DURATION_SECONDS=8
VEO_NUM_RESULTS=1

# Enable live API calls
ALLOW_LIVE=true
```

### 6. Verify Setup

```bash
# Check configuration
curl http://localhost:8000/api/healthz

# Expected response:
{
  "ok": true,
  "video_provider": "veo",
  "providers": {
    "veo": "configured",
    ...
  },
  "veo_config": {
    "gcp_project_id": "your-project-id",
    "credentials_file_exists": true,
    ...
  }
}
```

### Cost Estimates (Veo 3)

- **Per video**: ~$0.40 (8 seconds at $0.05/second)
- **Per cycle** (3 videos): ~$1.20
- Budget cap: `MAX_COST_PER_RUN=0.75` (adjust as needed)

⚠️ **SynthID Watermark**: Veo 3 automatically embeds an invisible provenance watermark (SynthID) in all generated videos. This cannot be disabled and is part of Google's responsible AI practices.

## Leonardo.ai Setup (Image Generation)

The system uses **Leonardo.ai** for AI image generation from prompts.

### 1. Create Leonardo.ai Account

1. Go to [Leonardo.ai](https://app.leonardo.ai/)
2. Sign up for an account
3. Choose a plan that includes API access

### 2. Get API Key

1. Navigate to your [User Menu → API Access](https://app.leonardo.ai/settings/api)
2. Generate a new API key
3. Copy the key securely

### 3. (Optional) Choose a Model

1. Browse available models in the Leonardo.ai interface
2. Note the Model ID if you want to use a specific model
3. Leave blank to use the platform default

### 4. Configure Environment Variables

Edit your `.env` file:

```bash
# Leonardo Configuration
LEONARDO_API_KEY=your-leonardo-api-key-here
# Optional: specify a model ID, or leave blank for default
LEONARDO_MODEL_ID=
```

### 5. Verify Setup

```bash
curl http://localhost:8000/api/healthz
```

Expected response:
```json
{
  "providers": {
    "leonardo": "configured",
    ...
  },
  "leonardo_config": {
    "model_id": "default"
  }
}
```

### Cost Estimates (Leonardo)

- **Per image**: ~$0.02
- Conservative estimate, actual costs may vary by model and resolution

## Shotstack Setup (Video Editing)

The system uses **Shotstack** for video editing (adding music and effects).

### 1. Create Shotstack Account

1. Go to [Shotstack Dashboard](https://dashboard.shotstack.io/)
2. Sign up for an account
3. Choose a plan that includes API access

### 2. Get API Key

1. Navigate to your dashboard
2. Find your API key in the account settings
3. Note your region (US or EU)

### 3. Prepare Licensed Soundtrack

⚠️ **IMPORTANT**: You must provide a publicly accessible URL to a licensed music track.

Options:
- Upload to Shotstack's asset storage
- Use a pre-signed URL from cloud storage (S3, GCS, etc.)
- Use any publicly accessible URL with proper licensing

### 4. Configure Environment Variables

Edit your `.env` file:

```bash
# Shotstack Configuration
SHOTSTACK_API_KEY=your-shotstack-api-key-here
# Region: us | eu (choose based on your account)
SHOTSTACK_REGION=us
# Licensed soundtrack URL (must be publicly accessible)
SOUNDTRACK_URL=https://your-storage.com/music/track.mp3
# Output resolution: HD (1280x720) | 1080 (1920x1080)
OUTPUT_RESOLUTION=HD
```

### 5. Verify Setup

```bash
curl http://localhost:8000/api/healthz
```

Expected response:
```json
{
  "providers": {
    "shotstack": "configured",
    ...
  },
  "shotstack_config": {
    "region": "us",
    "resolution": "HD",
    "soundtrack_url_configured": true
  }
}
```

### Cost Estimates (Shotstack)

- **Per video edit**: ~$0.02
- Conservative estimate for short renders
- Actual costs vary by render duration and complexity

### Important Notes

- **Audio Handling**: Shotstack strips the original video audio (volume: 0) and adds your licensed soundtrack
- **No Text Overlays**: The system is configured to NOT add text, captions, or watermarks
- **File Access**: Some Shotstack plans don't accept `file://` sources. If you encounter errors, pre-upload videos to cloud storage and use those URLs

## Architecture

### Service Model: Coordinator → Agents

The system uses a **Coordinator** that dispatches discrete **Agents**:

- **Coordinator** (`coordinator/orchestrator.py`): Entry point for generation cycles
- **Agents** (under `agents/`):
  - **prompting**: Proposes variations from `prompt_config.json`
  - **gen_image**: Generates PNG from variation
  - **gen_video**: Converts PNG → MP4
  - **edit**: Applies music/effects (NO overlays)
  - **qa_style**: Blur detection, quality gates
  - **qa_safety**: SFW compliance
  - **indexer**: Moves to `generated/`, writes to `videos.json`

### Provider Abstraction

All external APIs are behind `clients/*` with stable method signatures. Swap providers without touching `pipeline.py`.

### Cost & Safety Guards

- **Budget Cap**: `MAX_COST_PER_RUN` (default $0.75)
- **Concurrency**: `MAX_PARALLEL` (default 3)
- **Retries**: Max 2 per call, exponential backoff
- **Quality Gates**: Blur detection, bitrate sanity
- **Key Validation**: Fails immediately if required keys missing

## Usage

### Generate Videos (Manual)

```bash
# Via API (requires ALLOW_LIVE=true in .env)
curl -X POST http://localhost:8000/api/cycle/generate?n=1
```

### Generate Videos (Frontend)

1. Open http://localhost:5173
2. Click "Generate" button
3. Review video in player
4. Use keyboard shortcuts:
   - `K` to POST (publish)
   - `J` to DELETE

### Enable Automated Generation

⚠️ **WARNING:** This will consume API credits hourly.

```bash
# In .env:
ENABLE_SCHEDULER=true
ALLOW_LIVE=true
```

Restart the backend. The scheduler will run `run_cycle()` every hour.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOW_LIVE` | `false` | Enable paid API calls |
| `ENABLE_SCHEDULER` | `false` | Enable hourly auto-generation |
| `COORDINATOR_BATCH_SIZE` | `3` | Videos per cycle |
| `COORDINATOR_MAX_PARALLEL` | `3` | Max concurrent generations |
| `MAX_COST_PER_RUN` | `0.75` | Budget cap (USD) |
| `GEN_DEFAULT_SECONDS` | `8` | Video duration |
| `GEN_DEFAULT_FPS` | `12` | Video framerate |

### Prompt Configuration

Edit `app/data/prompt_config.json`:

```json
{
  "base_prompt": "your character description here",
  "negative_prompt": "things to avoid"
}
```

## Testing

```bash
cd backend
PYTHONPATH=. pytest -q
```

## Fail-Loud Examples

### Missing API Key
```
RuntimeError: LEONARDO_API_KEY is missing.
Set LEONARDO_API_KEY in .env to enable Leonardo API calls.
```

### Live Calls Disabled
```
RuntimeError: Live calls disabled (ALLOW_LIVE=false).
Set ALLOW_LIVE=true in .env to enable paid API calls.
```

### Budget Exceeded
```
RuntimeError: Budget exceeded: $0.82 > $0.75
```

## Directory Structure

```
ai-influencer/
├── backend/
│   └── app/
│       ├── agents/         # Generation pipeline agents
│       ├── clients/        # API provider clients
│       ├── coordinator/    # Orchestration logic
│       ├── core/          # Config, logging, storage, cost
│       └── api/           # FastAPI routes
├── frontend/
│   └── src/              # React + Vite UI
├── app/data/             # JSON indices + media files
└── scripts/              # Dev tooling

```

## API Endpoints

- `POST /api/cycle/generate?n=N` - Generate N videos
- `GET /api/healthz` - Health check
- `GET /docs` - Interactive API docs

## Logs

All activity logged to `app/data/logs.txt`:
```
2025-01-25T10:30:00 | INFO | ai-influencer | cycle_start n=1
2025-01-25T10:30:05 | INFO | ai-influencer | image_generated id=abc123 path=...
```

## Cost Safety

The system tracks estimated costs per cycle using `Decimal` for precision (no float drift). If you exceed `MAX_COST_PER_RUN`, the cycle stops immediately with a clear error message.

Each client should report costs via `app.core.cost.add_cost(Decimal("..."), "service_name")`.

## Security Features

### Financial Safety (P0)
- **Decimal Precision:** All cost calculations use `Decimal` to prevent float drift
- **Pre-call Validation:** Budget checked BEFORE API calls, not after
- **Hard Cap:** System refuses to exceed `MAX_COST_PER_RUN`

### Path Traversal Protection (P0)
- **safe_join():** All file paths validated to block `..` components
- Prevents attackers from writing files outside `app/data/`
- Applied to all indexer, posting, and deletion operations

### Media Validation (P0)
- **FFprobe Validation:** All video containers validated before indexing
- **OpenCV Check:** Frame readability verified
- **Blur Detection:** Laplacian variance threshold prevents low-quality outputs

### Request Protection (P0)
- **Rate Limiting:** 5 requests/minute per client on `/cycle/generate`
- **Body Size Limit:** 2MB max to prevent DoS
- **CORS:** Restricted to `http://localhost:5173` in development
- **Security Headers:**
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`

### Data Integrity (P1)
- **Schema Validation:** Required fields enforced on all `videos.json` writes
- **Atomic Writes:** Temp file + rename pattern prevents corruption
- **Thread Safety:** All JSON operations protected by locks

### Secret Handling (P0/P1)
- **No Logging:** API keys never logged (verified by tests)
- **Healthz Safety:** `/healthz` shows provider status without exposing keys
- **Env Only:** All secrets via `.env`, never committed to git

### Frontend Safety (P1)
- **ID Sanitization:** All video IDs validated as alphanumeric before URL construction
- **No XSS:** No `dangerouslySetInnerHTML` usage
- **Defense-in-Depth:** Server-generated IDs are already safe (SHA256), but frontend validates anyway

## Running Security Tests

```bash
# Run security test suite
uv run pytest backend/app/tests/test_security.py -v

# Run all tests
uv run pytest -q
```

**Tests cover:**
- Decimal precision and budget caps
- Path traversal blocking
- Schema validation
- Deterministic ID generation
- Secret handling

## Troubleshooting

**"ALLOW_LIVE=false" error:**
- This is intentional! Set `ALLOW_LIVE=true` in `.env` when ready for paid calls.

**"prompt_config.json not found":**
- Ensure `app/data/prompt_config.json` exists with `base_prompt` and `negative_prompt`.

**Frontend can't connect to backend:**
- Ensure backend is running on `http://localhost:8000`
- Check vite proxy config in `frontend/vite.config.js`

## Contributing

See [CLAUDE.md](./CLAUDE.md) for full engineering conventions and standards.

**Key Rules:**
- 100% typed Python (mypy clean)
- No mock modes, fail loudly
- No captions, voice, watermarks, or overlays
- Provider abstraction via `clients/*`
- All tests must pass before commit

## License

MIT
