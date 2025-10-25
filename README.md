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

### Setup

1. **Clone and install dependencies:**
```bash
# Create and activate virtual environment with UV
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
uv pip install -r requirements.txt

# Install Node dependencies
cd frontend
npm install
cd ..
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and set your API keys
# IMPORTANT: Keep ALLOW_LIVE=false until you're ready for paid calls
```

3. **Run development servers:**
```bash
# On Unix/Mac:
bash scripts/dev_run.sh

# On Windows:
scripts\dev_run.bat
```

4. **Access the application:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

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
cd backend
PYTHONPATH=. pytest app/tests/test_security.py -v
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
