# CLAUDE.md — Engineering Guidelines & Conventions

This document sets the rules-of-the-road for building and maintaining the repo. Follow these so the system stays predictable, debuggable, and easy to extend.

## 0) Stack (locked)

- **Backend:** Python 3.11+, FastAPI, uvicorn
- **Scheduling:** APScheduler (cron + one-off triggers)
- **Frontend:** React + Vite (single-page "review-only" UI)
- **Storage:** Local filesystem under `/app/data` (JSON indices + media files)

### APIs:
- **Prompting:** xAI Grok (grok-4-fast-reasoning) for all AI prompting (image briefs, motion, music, social meta)
- **LoRA Training & Inference:** FAL.ai
- **Image:** Leonardo.ai API
- **Img→Vid:** Google Veo 3 on Vertex AI (6 seconds, with SynthID watermark)
- **Music:** Suno AI (chirp-v3, 6-second instrumental clips)
- **Editing:** Local ffmpeg (audio/video muxing, replaces Shotstack)
- **Posting:** TikTok Content Posting API (Direct Post) + Instagram Graph API (Reels)

**Tooling:** **UV ONLY** (`uv sync` - NEVER pip), ruff, mypy, pytest

**Dev URLs:**
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5000`

## 0.1) Non-Negotiables (read this first)

**These rules override everything else in this document:**

1. **❌ NO MOCK MODES:** Fail loudly on missing configs or API credentials. Never silently skip paid API calls.
2. **❌ NO CAPTIONS, VOICE, SUBTITLES:** Character is non-speaking. Videos contain zero text overlays.
3. **❌ NO WATERMARKS:** Any synthetic media disclosure is handled externally by the platform, not this system. Exception: Veo 3 embeds an invisible SynthID watermark automatically (cannot be disabled).
4. **❌ NO OVERLAYS:** Front-end displays only pure visuals.
5. **❌ NO PIP:** Use UV exclusively. Install command: `uv sync`. Never `pip install`.
6. **✅ FAIL LOUDLY:** Missing environment variables, invalid configs, or disabled features must raise immediately with clear error messages.
7. **✅ LIVE CALLS OFF BY DEFAULT:** Require explicit `ALLOW_LIVE=true` to enable any paid API calls.
8. **✅ SCHEDULER OFF BY DEFAULT:** Require explicit `ENABLE_SCHEDULER=true` to enable automated generation cycles.

## 1) Repo Layout (authoritative)

```
ai-influencer/
  backend/
    app/
      __init__.py
      main.py                    # FastAPI app factory + lifecycle hooks
      api/
        __init__.py
        routes.py                # API endpoints
      core/
        config.py                # Pydantic settings + env validation
        logging.py               # Structured audit logging
        ids.py                   # Deterministic hashing for dedupe
        cost.py                  # Budget tracking & spend guards
        storage.py               # Thread-safe JSON I/O
        scheduler.py             # APScheduler posting workflow (off by default)
        motion_dedup.py          # Per-video motion prompt deduplication
        video_queue.py           # FIFO video generation queue
      coordinator/
        orchestrator.py          # run_cycle() → dispatches agents
      agents/
        __init__.py
        prompting.py             # Variation proposals (Grok-based)
        image_indexer.py         # Image indexing to images.json
        gen_image.py             # Image generation (Leonardo)
        video_prompting.py       # Motion prompt generation (Grok)
        gen_video.py             # Image-to-video (Veo 3, 6s)
        edit.py                  # Polish (ffmpeg muxing; NO music during generation)
        qa_style.py              # Container/format QA (blur disabled)
        qa_safety.py             # SFW compliance gates
        indexer.py               # Video indexing to videos.json
      clients/
        __init__.py
        grok.py                  # xAI Grok client (image briefs, motion, music, social meta)
        leonardo.py              # Leonardo.ai client
        veo.py                   # Google Veo 3 video generation client (6s)
        suno.py                  # Suno AI music generation client
        ffmpeg_mux.py            # ffmpeg audio/video muxing (replaces Shotstack)
        tiktok.py                # TikTok Content Posting API client
        instagram.py             # Instagram Graph API client (Reels)
        provider_selector.py     # Dependency injection + live guards
      tests/
        test_pipeline_smoke.py
  frontend/
    index.html
    src/
      main.jsx
      App.jsx
      api.js
  app/
    data/
      prompt_config.json       # Character & diversity banks (deprecated, replaced by referral_prompts.json)
      referral_prompts.json    # Eva Joy persona, style, banks for Grok
      videos.json              # Video metadata with music & social fields
      images.json              # Image metadata
      history.json             # Dedupe tracking
      logs.txt                 # Structured logging
      generated/               # Generated media files
      posted/                  # Posted media archive
      deleted/                 # Deleted media archive
      motion/                  # Per-video motion dedup stores
  scripts/
    dev_run.sh
  .env.example
  .python-version
  pyproject.toml                 # UV dependency management (source of truth)
  uv.lock                        # UV lockfile (auto-generated)
  package.json
  README.md
  CLAUDE.md                      # this file
```

## 2) Coding Standards

### Python

- **Typing:** 100% typed public functions; `from __future__ import annotations`.
- **Style:** ruff + black default configs.
- **Imports:** stdlib → third-party → local, separated by blank lines.
- **Function size:**
  - Pure helpers: ≤ 40 LOC
  - API handlers: ≤ 60 LOC
  - Pipeline steps: ≤ 80 LOC (split otherwise)
- **Naming:** `snake_case` for funcs/vars, `PascalCase` for classes, `SCREAMING_SNAKE` for consts.
- **Errors:** never swallow. Raise `AppError` subclasses with `code:str` and `hint:str`.
- **Retries:** only in API clients, exponential backoff (max 3, jitter).
- **Rate limits:** clients must expose `RATE_LIMIT_HZ` guard or sleep.

### React

- Single page, functional components, no state libs.
- Keep components ≤ 150 LOC.
- Don't add CSS frameworks; use minimal CSS in `index.html` or scoped CSS.
- Only two actions in UI: POST and DELETE. Keyboard shortcuts: `K` (post), `J` (delete).

## 3) Configuration & Secrets

- **Primary config:** `/app/data/prompt_config.json` (authoritative).
- **Secrets:** via `.env` only (never in git). Provide `.env.example`.
- `config.py` loads JSON, overlays env keys, validates with Pydantic.
- Fail fast on missing/invalid config.

## 4) JSON Files (single source of truth)

- **`prompt_config.json`** — Character profile (Eva Joy's physical traits, style, fitness focus), diversity banks (locations, poses, outfits, activities, props, accessories, lighting, camera angles), negative prompt, quality standards, and safety boundaries. Used by Grok to generate creative, varied fitness content prompts.
- **`history.json`** — `{"hashes": [...], "max_size": 5000}`; rolling window, append-only dedupe tracking.
- **`videos.json`** — array of entries:

```json
{
  "id": "20251024-0001",
  "image_id": "img_abc123",
  "status": "pending_review|liked|pending_review_music|approved|posted|deleted|failed",
  "video_path": "app/data/generated/video_20251024_0001.mp4",
  "thumb_path": "app/data/generated/video_20251024_0001.jpg",
  "created_at": "2025-10-24T12:34:56.789Z",
  "video_meta": {
    "motion_prompt": "gentle pan right with subtle lens breathing",
    "duration_s": 6,
    "seed": 1234
  },
  "music": {
    "brief": "ambient cinematic fitness background",
    "style": "minimal electronic",
    "mood": "calm energizing",
    "audio_path": "app/data/generated/music_20251024_0001.mp3",
    "music_status": "suggested|generated|approved|skipped",
    "previous_briefs": []
  },
  "social": {
    "title": "Morning Flow Power",
    "tags": ["fitness", "yoga", "wellness", "motivation"],
    "hashtags": ["#fitness", "#yoga", "#wellness", "#motivation"]
  },
  "posted_platform": "tiktok",
  "posted_id": "7123456789012345678",
  "posted_at": "2025-10-24T14:00:00.000Z",
  "posting_error": null
}
```

**Status Flow:**
1. `pending_review` → Video generated, awaiting user review
2. `liked` → User liked video (triggers music suggestion)
3. `pending_review_music` → Music added, awaiting approval
4. `approved` → Ready for scheduler to post
5. `posted` → Published to platform
6. `deleted` → User disliked (can regenerate with different motion)
7. `failed` → Generation or posting failed

**Music Field** (added after user likes video):
- `brief`: Grok-generated music description
- `style`, `mood`: Music characteristics
- `audio_path`: Local path to generated music file (Suno)
- `music_status`: Workflow state
- `previous_briefs`: For regeneration deduplication

**Social Field** (added by scheduler before posting):
- `title`: 40-60 char engaging title (Grok-generated)
- `tags`: 5-10 plain keywords
- `hashtags`: 8-12 platform-safe hashtags (with # prefix)

**Posted Fields** (added after successful posting):
- `posted_platform`: "tiktok" or "instagram"
- `posted_id`: Platform-specific post/media ID
- `posted_at`: ISO8601 timestamp
- `posting_error`: Error message if posting failed

**Rule:** all writes go through `storage.py` helpers (atomic write to temp, then rename).

## 5) Hashing & Dedupe

```python
content_hash = sha256(name + prompt + str(seed_hint)).hexdigest()
```

- Before enqueuing a variation, check `history.json`; skip duplicates.
- After successful render → append hash; if `len > max_size`, drop oldest.

## 5.1) Coordinator & Agents Architecture

**Service Modeling Convention:**

The system is organized as a **Coordinator** that dispatches discrete **Agents** (logical service units):

- **Coordinator** (`coordinator/orchestrator.py`): Entry point for IMAGE generation cycles. Validates configs, calls agents sequentially per variation, logs failures, continues batch.
- **Video Queue** (`core/video_queue.py`): FIFO queue for video generation jobs. Processes superliked images one at a time to avoid overwhelming Veo API.
- **Scheduler** (`core/scheduler.py`): Automated posting workflow. Posts approved videos to TikTok/Instagram on configurable cron schedule (default: every 20 minutes).
- **Agents** (under `agents/`):
  - **prompting**: Uses Grok API to generate N diverse, creative IMAGE briefs from persona + diversity banks in `referral_prompts.json`. Deduplicates against `history.json`. Returns structured payloads with base prompts, metadata (location, pose, outfit, activity, lighting, camera), and deterministic IDs.
  - **image_indexer**: Saves generated image metadata to `images.json` with status `pending_review`.
  - **gen_image**: Generates PNG from variation payload using Leonardo.
  - **video_prompting**: Uses Grok API to generate cinematic MOTION prompts for 6-second videos. Deduplicates per-video using `motion_dedup.py`.
  - **gen_video**: Converts PNG → 6-second MP4 using Veo 3 with motion prompt.
  - **edit**: Ensures exact 6-second duration using ffmpeg. **NO MUSIC** added during generation (music added later via Music Review workflow).
  - **qa_style**: Container/format validation. **Blur detection DISABLED** (identity QA handled by human superlike gate).
  - **qa_safety**: SFW compliance checks.
  - **indexer**: Moves final MP4 to `generated/`, writes to `videos.json` with status `pending_review`.

**Execution Model:**
- Agents run **sequentially** within each variation (dependencies: image → video → edit → QA → index).
- Multiple variations in a batch can be parallelized (up to `MAX_PARALLEL`), but this is controlled by the coordinator.
- Each agent is **fail-loud**: missing configs or API keys raise immediately; no silent fallbacks.

**Deterministic Outcomes:**
- IDs are content-hashed (prompt + seed).
- Re-running the same input produces the same ID (dedupe catches it).
- No global state outside JSON files.

**Music Review Workflow** (Post-Generation):
Music is added AFTER video generation, not during. User flow:
1. User **likes** video → status changes to `liked`
2. POST `/videos/{id}/music/suggest` → Grok generates music brief based on image metadata + motion
3. POST `/videos/{id}/music/generate` → Suno generates 6s instrumental audio
4. POST `/videos/{id}/music/mux` → ffmpeg muxes video + audio → status changes to `pending_review_music`
5. User rates:
   - **Approve** → status changes to `approved` (ready for scheduler)
   - **Regenerate** → back to `liked`, brief stored in `previous_briefs` for deduplication
   - **Skip** → status changes to `approved` without music

**Posting Workflow** (Scheduler-Only):
**NO MANUAL POSTING ENDPOINTS**. Scheduler is the ONLY way to post. User flow:
1. Video reaches status `approved` (either with or without music)
2. Scheduler runs on cron schedule (default: every 20 minutes)
3. If within posting window (default: 09:00-21:00), scheduler:
   - Selects ONE approved video (FIFO)
   - Generates social meta via Grok if missing (title, tags, hashtags)
   - Posts to configured platform (TikTok or Instagram)
   - Updates status to `posted` with platform post ID
4. On failure: error logged, video stays `approved` for manual retry via `/scheduler/run-once`

**Manual Scheduler Control:**
- POST `/scheduler/run-once` → Execute posting cycle immediately (requires `ALLOW_LIVE=true`)
- POST `/scheduler/dry-run` → Preview what would be posted without executing

## 5.2) Provider Abstraction

**Key Principle:** All external API vendors are hidden behind `clients/*` with stable method signatures.

- **Swappable Providers:** Changing from Leonardo → DALL·E, or Veo → Runway, or FAL → another LoRA host requires only updating `clients/provider_selector.py` and the specific client module.
- **Pipeline Unchanged:** `coordinator/orchestrator.py` and all agents call generic methods like `prompting_client()`, `image_client().generate(payload)`, etc. The pipeline never imports vendor-specific code directly.
- **Contracts:** Each client exposes:
  - **Prompting** (`grok.py`):
    - `generate_variations(...)` → list of image briefs with metadata
    - `suggest_motion(image_meta, duration_s=6)` → motion prompt for Veo 3
    - `suggest_music(image_meta, motion_spec)` → music brief for Suno
    - `generate_social_meta(media_meta)` → title, tags, hashtags for posting
  - **Image** (`leonardo.py`): `generate(payload) -> str` → image path
  - **Video** (`veo.py`): `img2vid(image, payload) -> str` → 6s video path
  - **Music** (`suno.py`): `generate_clip(music_brief, seconds=6) -> str` → audio path
  - **Editing** (`ffmpeg_mux.py`): `mux(video, audio, out_path, seconds=6) -> str` → muxed video path
  - **Posting** (`tiktok.py`, `instagram.py`): `upload_video/upload_reel(video_path, caption) -> str` → post/media ID
- **Guards:** `provider_selector.py` enforces `ALLOW_LIVE=true` and validates API keys before returning a client instance.

## 5.3) Cost & Safety Guards (implemented in core/cost.py)

**Budget Caps:**
- `MAX_COST_PER_RUN` (default $0.75): Coordinator tracks cumulative spend; stops cycle if exceeded.
- Each client call reports estimated cost to `cost.py`.

**Concurrency Limits:**
- `MAX_PARALLEL` (default 3): Max simultaneous generation calls.

**Retries:**
- Max 2 retries per API call, exponential backoff (0.5s, 1s).
- 429/5xx: retryable. 4xx: fail immediately with error message.

**Quality Gates:**
- **Blur detection** (qa_style): DISABLED (identity QA handled by human gate via superlike)
- **Container validation** (qa_style): FFprobe validates video container format and readability
- **SFW check** (qa_safety): Placeholder for external classifier.

**Audit Logging:**
- All API calls, errors, and costs logged to `app/data/logs.txt`.
- **No secrets in logs.**

**Key Validation:**
- On startup or first live call: if required API key is missing, raise with clear message naming the missing env var.

## 6) Pipeline Contract (idempotent)

Each step returns a typed result; on failure, raise `AppError`.

1. **Propose variations** (`prompting.propose`)
   - Input: N (number of variations)
   - Uses: Character profile + diversity banks from `prompt_config.json`, history dedupe from `history.json`
   - Calls: Grok API via `prompting_client()` to generate diverse, creative prompts
   - Output: `list[dict]` with keys: `base` (prompt), `neg` (negative), `variation` (description), `meta` (location/pose/outfit/activity/lighting/camera), `seed`, `id`

2. **Generate image** (`leonardo_api.generate_image`)
   - Input: Variation dict → Output: local PNG path

3. **Img→Vid** (`veo_client.img2vid`)
   - Input: PNG + duration params → Output: MP4 path (with SynthID watermark)

4. **Edit** (`edit.polish`)
   - Input: MP4 → Output: MP4 (trimmed to exactly 6s using ffmpeg, NO MUSIC)

5. **Index** (`storage.index_generated`)
   - Input: MP4 + meta → Output: `VideoRecord` added to `videos.json`

No global state outside JSON and file paths. Steps are re-runnable on the same inputs without duplicate outputs (use deterministic IDs).

## 7) FastAPI Endpoints

**Image Generation:**
- `POST /api/cycle/generate` → Triggers image generation cycle (respects batch size)

**Image Review:**
- `GET /api/images/pending` → Get next image pending review
- `PUT /api/images/{id}/rate` → Rate image (dislike/like/superlike)

**Video Generation:**
- `POST /api/videos/process-queue` → Process next video in generation queue (FIFO)
- `GET /api/videos/queue/status` → Get queue status and counts

**Video Review:**
- `GET /api/videos/pending` → Get next video pending review
- `PUT /api/videos/{id}/rate` → Rate video (dislike/like)
- `POST /api/videos/{id}/regenerate` → Regenerate video with different motion

**Music Review** (post-generation):
- `POST /api/videos/{id}/music/suggest` → Generate music brief via Grok
- `POST /api/videos/{id}/music/generate` → Generate music audio via Suno
- `POST /api/videos/{id}/music/mux` → Mux video with music via ffmpeg
- `PUT /api/videos/{id}/music/rate` → Rate music (approve/regenerate/skip)

**Scheduler Control** (ONLY way to post):
- `POST /api/scheduler/run-once` → Execute posting cycle immediately (requires `ALLOW_LIVE=true`)
- `POST /api/scheduler/dry-run` → Preview next video to be posted without executing

**Health:**
- `GET /api/healthz` → Returns provider status, config, and queue counts

All endpoints return deterministic JSON; no HTML.

## 8) TikTok Posting Rules

- **❌ NO CAPTIONS, HASHTAGS, OR OVERLAYS:** Videos contain zero text.
- **❌ NO VOICE OR SUBTITLES:** Character is non-speaking.
- **❌ NO WATERMARKS:** Any synthetic media disclosure is handled externally.
- Front-end displays only visuals; no text overlays or captions.
- On publish success: persist returned post ID in sidecar JSON.
- **✅ FAIL LOUDLY:** If auth/env is missing or invalid, raise immediately with clear error messages naming the missing env var.

## 9) Logging & Observability (minimal)

- **Single file:** `/app/data/logs.txt`
- **Format:** `ISO8601 | level | component | event | {json_meta}`
- **Log levels:** INFO main flow, WARN recoverable, ERROR with stack trace.
- No PII or secrets in logs.

## 10) Errors & Retries

- **Fail-loud policy:** No silent failures, no mock modes. Missing configs or API credentials must fail immediately with clear error messages.
- **API clients:** retry 3x with backoff (0.5s, 1s, 2s + jitter).
- Recognize 429/5xx as retryable; 4xx non-retryable (surface the cause).
- Pipeline should mark failed with reason in `videos.json` and continue other items.

## 11) Scheduling (Posting Workflow Only)

**Purpose:** Scheduler handles POSTING ONLY (not content generation). It's the ONLY way to post to TikTok/Instagram.

**Configuration:**
- **DISABLED BY DEFAULT:** Set `ENABLE_SCHEDULER=true` to activate automated posting.
- **Cron Schedule:** `SCHEDULER_CRON_MINUTES` (default: `*/20` = every 20 minutes)
- **Posting Window:** `POSTING_WINDOW_LOCAL` (default: `09:00-21:00` in `SCHEDULER_TIMEZONE`)
- **Platform:** `DEFAULT_POSTING_PLATFORM` (tiktok or instagram)

**Behavior:**
- When enabled, APScheduler runs `run_posting_cycle()` on cron schedule
- Posts ONE approved video per run (FIFO from `videos.json`)
- Only posts within configured posting window
- Generates social meta via Grok if missing (title, tags, hashtags)
- Updates video status to `posted` with platform post ID
- Never overlap runs: job coalescing (`max_instances=1`)

**Manual Control:**
- POST `/scheduler/run-once` → Execute posting cycle immediately (requires `ALLOW_LIVE=true`)
- POST `/scheduler/dry-run` → Preview next video to be posted without executing

**Rationale:**
- Prevents accidental posting; user must explicitly enable
- Respects posting windows for optimal engagement
- Gradual rollout (one video per cycle)

## 12) Frontend Rules

**Video Review:**
- One video at a time
- Buttons: **Like / Dislike** (NO manual post button)
- Keyboard: `K` → Like, `J` → Dislike
- Autoplay muted, loop
- **❌ NO CAPTIONS, OVERLAYS, OR TEXT** displayed over video content
- **❌ NO VOICE, NO SUBTITLES:** Character is non-speaking
- Show minimal metadata (title, duration) below video player

**Music Review Panel** (appears after user clicks "Like"):
- Flow: Suggest → Generate → Preview → Approve/Regenerate/Skip
- Buttons:
  - **Suggest Music** → Calls `/videos/{id}/music/suggest`
  - **Generate** → Calls `/videos/{id}/music/generate` (after suggestion)
  - **Approve** → Calls `/videos/{id}/music/rate` with rating="approve"
  - **Regenerate** → Calls `/videos/{id}/music/rate` with rating="regenerate"
  - **Skip Music** → Calls `/videos/{id}/music/rate` with rating="skip"
- Shows music brief, style, mood after generation
- Video preview updates after mux

**Scheduler Settings View:**
- Toggle `ENABLE_SCHEDULER` on/off
- Configure posting window (HH:MM-HH:MM)
- Set timezone
- Set cadence (cron presets: every 15/20/30/60 mins)
- Select default platform (TikTok / Instagram)
- Show platform readiness (API keys configured)
- Preview next run time & approved video count
- Manual controls: Run Once, Dry Run buttons

**Navigation:**
- Keyboard: `I` → Image Review, `V` → Video Review, `M` → Music Review, `S` → Scheduler Settings

**Behavior:**
- All settings driven by backend config (no form inputs for API keys)
- Posting ONLY via scheduler (no manual post buttons)

## 13) Testing

- `pytest -q` must pass locally.
- Provide unit tests for: hashing, storage atomic writes, pipeline happy path (with mocked clients).
- Provide contract tests for each client (fake HTTP server / fixtures with canned JSON).

## 14) CI / Pre-commit

- Pre-commit hooks: ruff, black, mypy, `pytest -q`.
- GitHub Actions (or simple script) to run the same on PRs.
- No failing tests or lints on main.

## 15) Git Hygiene

- **Branching:** `feature/<short-desc>`, PRs into main.
- **Commit style:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`).
- Small PRs (< 400 lines diff preferred).
- PR description must state acceptance checks (what endpoint/flow to verify).

## 16) Security & Compliance (baseline)

- SFW-only defaults in prompts (user may change privately).
- Synthetic media disclosure is handled outside this system (if required by platform).
- Secrets only via `.env`; never log them.
- Validate and sanitize all JSON from models before saving.

## 17) Performance & Cost Guardrails

- **Defaults:** 720×1280, 12 fps, **6s exact** (no longer configurable, enforced by Veo 3 and ffmpeg).
- **Parallelism:** max per `batch.max_parallel` (default 3).
- **Timeouts:**
  - Prompting: 15s
  - Image gen: 60s
  - Img→Vid: 120s
  - Edit: 60s
  - Post: 60s

If an API times out: mark item failed with `timeout:true` and continue.

## 18) Extension Points

- New providers must be added as a new client module with identical method signatures.
- All provider differences are hidden behind clients; `pipeline.py` remains unchanged.

## 19) Build & Run (dev)

**Setup (first time):**
```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
cd frontend && npm install && cd ..
cp .env.example .env       # Configure API keys
```

**Run:**
```bash
bash scripts/dev_run.sh    # Unix/Mac
# OR
scripts\dev_run.bat        # Windows
```

**Direct commands:**
- Backend: `uv run uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check backend`
- Type check: `uv run mypy backend`

**Notes:**
- Backend on `http://localhost:8000`, frontend on `http://localhost:5000`
- Media served from `/app/data` via static route
- Never use `pip install` - UV only

## 20) Definition of Done (every change)

- [ ] All tests + lints pass.
- [ ] Manual smoke test: `POST /api/cycle/generate` produces ≥1 generated clip and UI displays it.
- [ ] README updated if any input/endpoint/flow changed.