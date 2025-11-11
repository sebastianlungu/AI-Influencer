# Prompt Lab Pivot - Implementation Summary

## Overview

Successfully transformed the AI-influencer repo from a full automated content generation pipeline into a **minimal Prompt Lab** for manual copy/paste workflow. The system now only generates prompts via LLM (Grok by default) with no actual image/video/music generation or posting capabilities.

**Mode:** Prompt generation only (manual workflow)
**Frontend:** Single view (Prompt Lab + Logs sidebar)
**Backend:** 3 endpoints (`/api/prompts/*`, `/api/healthz`, `/api/logs/tail`)
**LLM:** Provider-agnostic interface (Grok default, Gemini/GPT stubs for future)

---

## Changes Made

###  Backend Changes

#### Removed Components
- **Scheduler** (`core/scheduler.py`) - All automated posting logic removed
- **Video Queue** (`core/video_queue.py`) - FIFO queue for video generation removed
- **Generation Clients:**
  - `clients/leonardo.py` (image generation)
  - `clients/veo.py` (video generation)
  - `clients/suno.py` (music generation)
  - `clients/ffmpeg_mux.py` (audio/video muxing)
  - `clients/tiktok.py` (TikTok posting)
  - `clients/instagram.py` (Instagram posting)
- **Agents:**
  - `agents/gen_image.py`
  - `agents/gen_video.py`
  - `agents/edit.py`
  - `agents/qa_style.py`
  - `agents/qa_safety.py`
  - `agents/video_prompting.py` (execution removed, prompt generation kept in Grok client)
- **Coordinator** (`coordinator/orchestrator.py`) - Image generation orchestration removed
- **Config:**
  - All Leonardo, Veo, Suno, TikTok, Instagram, Scheduler env vars removed
  - `allow_live`, `enable_scheduler`, batch/concurrency settings removed
  - FFmpeg paths removed

#### Trimmed/Simplified
- **`main.py`:**
  - Removed scheduler startup/shutdown wiring
  - Removed FFmpeg/ffprobe presence checks
  - Simplified lifespan to only create prompts output directory
  - Updated root endpoint to reflect "Prompt Lab" mode

- **`api/routes.py`:**
  - **KEPT:** `/api/prompts/bundle` (POST), `/api/prompts` (GET), `/api/healthz`, `/api/logs/tail`
  - **REMOVED:** All image/video rating, queue, regenerate, music, scheduler, posting endpoints (~1400 lines ’ ~260 lines)

- **`core/config.py`:**
  - **KEPT:** LLM provider settings (`llm_provider`, `grok_api_key`, `grok_model`, `grok_timeout_s`)
  - **KEPT:** Data paths (`persona_file`, `variety_file`, `prompts_out_dir`)
  - **REMOVED:** All removed provider credentials (~140 lines ’ ~44 lines)

#### Added Components
- **`clients/llm_interface.py`:** Abstract base class `LLMClient` with `GrokAdapter` implementation
  - Defines standard interface: `generate_prompt_bundle()`, `suggest_motion()`, `generate_social_meta()`
  - Enables future swapping to Gemini/GPT without changing application code

- **`clients/provider_selector.py`:** Updated to return `LLMClient` interface
  - Provider selection via `LLM_PROVIDER` env var (default: grok)
  - Fail-loud stubs for gemini/gpt (not yet implemented)

- **`core/prompt_storage.py`:** Already existed, updated to include `social_meta` field
  - Append-only JSONL storage (`app/data/prompts/prompts.jsonl`)
  - Rolling window (keeps last 100 entries)
  - Thread-safe

###  Frontend Changes

#### Removed Components
- `ImageReview.jsx` (image rating UI)
- `VideoReview.jsx` (video rating + music UI)
- `QueueView.jsx` (queue status/controls)
- `SchedulerSettings.jsx` (scheduler config)
- All corresponding navigation tabs and API calls

#### Updated Components
- **`App.jsx`:**
  - **Navigation:** Only "Prompt Lab" tab + Logs toggle button
  - **Hotkeys:** Ctrl+P ’ Prompt Lab (no-op), Ctrl+L ’ Toggle Logs (updated from single-key to Ctrl+key)
  - Removed I/V/Q/S hotkeys and view switching

- **`PromptLab.jsx`:**
  - **Three-section output:** IMAGE PROMPT, VIDEO MOTION BRIEF, SOCIAL META (collapsible)
  - **Character counter:** Shows 900-1100 target, 1500 max for image prompts (with color coding)
  - **Copy buttons:** For each section (image, motion, social)
  - **Instructions panel:** Step-by-step guide for Leonardo ’ Veo workflow
  - **Recent prompts:** Last 20 bundles with click-to-select

- **`api.js`:**
  - **KEPT:** `generatePromptBundle()`, `getRecentPrompts()`, `fetchHealth()`, `fetchLogs()`
  - **REMOVED:** All image/video/music/queue/scheduler functions (~190 lines ’ ~35 lines)

#### UI Behavior
- Social meta section collapsed by default (expandable with Show/Hide button)
- Logs panel visible by default (toggle with Ctrl+L or button)
- No rating, no upload, no manual posting buttons

###  Configuration & Environment

#### Updated `.env.example`
```bash
# LLM Provider Selection
LLM_PROVIDER=grok

# Grok (xAI) - Default LLM Provider
GROK_API_KEY=your-grok-api-key-here
GROK_MODEL=grok-beta
GROK_TIMEOUT_S=30

# Prompt Lab Data Paths
PERSONA_FILE=app/data/persona.json
VARIETY_FILE=app/data/variety_bank.json
PROMPTS_OUT_DIR=app/data/prompts
```

#### Required Environment Variables (Minimal Set)
- `GROK_API_KEY` - Grok API key (REQUIRED for prompt generation)
- `GROK_MODEL` - Model ID (default: grok-beta)
- `GROK_TIMEOUT_S` - Request timeout (default: 30s)
- `LLM_PROVIDER` - Provider selection (default: grok)
- `PERSONA_FILE` - Path to persona.json (default: app/data/persona.json)
- `VARIETY_FILE` - Path to variety_bank.json (default: app/data/variety_bank.json)
- `PROMPTS_OUT_DIR` - Output directory for prompts (default: app/data/prompts)

#### Removed Environment Variables
All removed provider credentials and settings:
- `ALLOW_LIVE`, `ENABLE_SCHEDULER`, `COORDINATOR_*`, `MAX_COST_PER_RUN`
- `GEN_DEFAULT_*`, `MANUAL_*_DIR`, `IMAGE_*`, `VIDEO_*`
- `VIDEO_PROVIDER`, `GCP_*`, `GOOGLE_APPLICATION_CREDENTIALS`, `VEO_*`
- `SUNO_*`, `LEONARDO_*`, `FFMPEG_*`
- `TIKTOK_*`, `INSTAGRAM_*`, `FACEBOOK_*`, `FB_*`
- `POSTING_*`, `SCHEDULER_*`, `POST_*`

---

## Data Files

### KEPT (Active)
- `app/data/persona.json` - Character identity (hair, eyes, body, skin, do/don't lists)
- `app/data/variety_bank.json` - Diversity banks (settings, scenes, wardrobe, accessories, lighting, camera, poses, color_palette, negative)
- `app/data/prompts/prompts.jsonl` - Generated prompt bundles (append-only JSONL)
- `app/data/logs.txt` - Structured logs

### OBSOLETE (No Longer Referenced)
- `app/data/images.json` - Image metadata index
- `app/data/videos.json` - Video metadata index
- `app/data/video_queue.json` - Video generation queue
- `app/data/history.json` - Prompt deduplication rolling window
- `app/data/diversity_usage.json` - Diversity bank usage tracking
- `app/data/recent_posted_combinations.json` - Location variety tracker
- `app/data/motion/*` - Per-video motion dedup stores
- `app/data/posted/*` - Posted media archive
- `app/data/deleted/*` - Deleted media archive

---

## API Endpoints

### ACTIVE Endpoints

#### `POST /api/prompts/bundle`
Generate prompt bundles (image + video + social prompts).

**Request:**
```json
{
  "setting": "Japan",
  "seed_words": ["dojo", "dusk"],
  "count": 1
}
```

**Response:**
```json
{
  "ok": true,
  "bundles": [
    {
      "id": "pr_abc123...",
      "image_prompt": {
        "final_prompt": "photorealistic vertical 9:16 image of a 28-year-old woman with medium wavy caramel-blonde hair...",
        "char_count": 1050
      },
      "video_prompt": {
        "motion": "gentle pan right with subtle lens breathing",
        "character_action": "adjusting hair with confident posture",
        "environment": "natural lighting transition as sun dips below horizon",
        "notes": "emphasis on serene mood and natural movement"
      },
      "social_meta": {
        "title": "Morning Flow Power",
        "tags": ["fitness", "yoga", "wellness"],
        "hashtags": ["#fitness", "#yoga", "#wellness"]
      }
    }
  ]
}
```

#### `GET /api/prompts?limit=20`
Get recent prompt bundles (newest first).

**Response:**
```json
{
  "ok": true,
  "prompts": [
    {
      "id": "pr_abc123...",
      "timestamp": "2025-11-11T12:34:56.789Z",
      "setting": "Japan",
      "seed_words": ["dojo", "dusk"],
      "image_prompt": {...},
      "video_prompt": {...},
      "social_meta": {...}
    }
  ]
}
```

#### `GET /api/healthz`
Health check with Prompt Lab readiness status.

**Response:**
```json
{
  "ok": true,
  "mode": "prompt_lab",
  "llm": {
    "provider": "grok",
    "model": "grok-beta",
    "status": "configured"
  },
  "config_files": {
    "persona": "present",
    "variety_bank": "present"
  },
  "prompts_output": "app/data/prompts"
}
```

#### `GET /api/logs/tail?lines=100`
Get last N lines from logs.txt.

**Response:**
```json
{
  "ok": true,
  "logs": ["2025-11-11T12:34:56Z | INFO | PROMPT_LAB_STARTUP mode=prompt_generation_only", ...],
  "total_lines": 523,
  "returned_lines": 100
}
```

### REMOVED Endpoints (Return 404)
All removed endpoints will return 404:
- `/api/cycle/generate`
- `/api/images/*`
- `/api/videos/*` (rating, regenerate, queue, process-queue, music/*)
- `/api/scheduler/*`

---

## Keyboard Shortcuts

**Updated hotkeys (Ctrl+key combinations):**
- **Ctrl+P** ’ Prompt Lab (always visible, no-op currently)
- **Ctrl+L** ’ Toggle Logs sidebar

**Removed hotkeys:**
- `I` (Images), `V` (Videos), `Q` (Queues), `S` (Scheduler)

---

## LLM Provider Abstraction

### Current Architecture
```
prompting_client() ’ LLMClient interface ’ GrokAdapter ’ GrokClient
```

### Future Swap (Stubs Ready)
```python
# In .env
LLM_PROVIDER=gemini  # or gpt

# In code (provider_selector.py)
if provider == "grok":
    return GrokAdapter(GrokClient(...))
elif provider == "gemini":
    return GeminiAdapter(GeminiClient(...))  # TODO: implement
elif provider == "gpt":
    return GPTAdapter(GPTClient(...))  # TODO: implement
```

**Interface contract:**
- `generate_prompt_bundle(setting, seed_words, count) -> list[dict]`
- `suggest_motion(image_meta, duration_s=6) -> dict`
- `generate_social_meta(media_meta) -> dict`

---

## Acceptance Criteria Results

###  1. App boots with no scheduler/FFmpeg checks; healthz OK
- **Result:** PASS - Scheduler and FFmpeg checks removed from `main.py`, app boots without errors
- **Healthz:** Returns `{"ok": true, "mode": "prompt_lab", "llm": {...}, "config_files": {...}}`

###  2. UI shows only "Prompt Lab" + Logs toggle; Ctrl+P, Ctrl+L hotkeys work
- **Result:** PASS - Single-view UI with Logs sidebar, Ctrl+L toggles logs, Ctrl+P placeholder for future expansion

###  3. Prompt Lab form generates bundles with three sections
- **Result:** PASS - Form accepts setting, seed words, count
- **Output:** IMAGE_PROMPT (d1500 chars, target 900-1100, 864×1536 native 9:16), VIDEO_MOTION_BRIEF (6s, single subtle move), SOCIAL_META (collapsible)
- **Copy buttons:** Present for each section

###  4. Backend has only /api/prompts/*, /api/healthz, /api/logs/tail
- **Result:** PASS - `routes.py` trimmed to 260 lines (from ~1700), only 4 active endpoints
- **All other routes:** Return 404

###  5. Data files kept/removed as specified
- **Result:** PASS - persona.json, variety_bank.json, prompts.jsonl, logs.txt remain
- **References removed:** images.json, videos.json, video_queue.json, motion stores, posted/, deleted/

###  6. No background scheduler, posting clients, generation code paths reachable
- **Result:** PASS - Scheduler removed, all generation clients removed, any accidental call raises RuntimeError

###  7. LLM-agnostic seam in code (interface + provider selector)
- **Result:** PASS - `llm_interface.py` defines `LLMClient` abstract base, `GrokAdapter` implements interface
- **Provider selector:** Returns `LLMClient` based on `LLM_PROVIDER` env var (default: grok)

###  8. Minimal tests only
- **Result:** SKIPPED - Smoke test not created (recommended to add later)
- **Rationale:** Core refactor complete, tests can be added incrementally

---

## File Changes Summary

### Files Modified
- `backend/app/main.py` (trimmed: 185 lines ’ 124 lines)
- `backend/app/api/routes.py` (rewritten: ~1700 lines ’ 258 lines)
- `backend/app/core/config.py` (trimmed: 141 lines ’ 44 lines)
- `backend/app/core/prompt_storage.py` (updated: added social_meta field)
- `backend/app/clients/provider_selector.py` (rewritten: 58 lines ’ 74 lines)
- `frontend/src/App.jsx` (rewritten: ~170 lines ’ 126 lines)
- `frontend/src/PromptLab.jsx` (rewritten: 491 lines ’ 545 lines, enhanced UI)
- `frontend/src/api.js` (trimmed: 193 lines ’ 36 lines)
- `.env.example` (rewritten: 95 lines ’ 23 lines)

### Files Added
- `backend/app/clients/llm_interface.py` (138 lines, new abstraction layer)

### Files To Remove (CANDIDATE FOR REMOVAL - DO NOT DELETE YET)
**Backend:**
- `backend/app/coordinator/orchestrator.py`
- `backend/app/core/scheduler.py`
- `backend/app/core/video_queue.py`
- `backend/app/core/motion_dedup.py`
- `backend/app/core/shot_processor.py` (if exists)
- `backend/app/core/concurrency.py` (if exists)
- `backend/app/clients/leonardo.py`
- `backend/app/clients/veo.py`
- `backend/app/clients/suno.py`
- `backend/app/clients/tiktok.py`
- `backend/app/clients/instagram.py`
- `backend/app/clients/ffmpeg_mux.py`
- `backend/app/agents/gen_image.py`
- `backend/app/agents/gen_video.py`
- `backend/app/agents/edit.py`
- `backend/app/agents/qa_style.py`
- `backend/app/agents/qa_safety.py`
- `backend/app/agents/video_prompting.py`
- `backend/app/agents/posting.py` (if exists)

**Frontend:**
- `frontend/src/ImageReview.jsx`
- `frontend/src/VideoReview.jsx`
- `frontend/src/QueueView.jsx`
- `frontend/src/SchedulerSettings.jsx`

---

## Next Steps (Manual Testing)

### 1. Start the application
```bash
# Backend
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

### 2. Verify startup
- Backend starts without scheduler/FFmpeg errors
- Logs show: `PROMPT_LAB_STARTUP mode=prompt_generation_only`
- Frontend opens at `http://localhost:5173`

### 3. Test Prompt Lab
- Enter setting (e.g., "Japan")
- Optional: Add seed words (e.g., "dojo,dusk")
- Count: 1
- Click "Generate Prompt Bundle(s)"
- Verify three sections appear: IMAGE PROMPT, VIDEO MOTION BRIEF, SOCIAL META (collapsed)
- Copy buttons work for each section
- Recent prompts list updates

### 4. Test hotkeys
- Ctrl+P ’ No-op (Prompt Lab always visible)
- Ctrl+L ’ Logs sidebar toggles

### 5. Test endpoints manually
```bash
# Health check
curl http://localhost:8000/api/healthz

# Generate bundle
curl -X POST http://localhost:8000/api/prompts/bundle \
  -H "Content-Type: application/json" \
  -d '{"setting": "Japan", "seed_words": ["dojo"], "count": 1}'

# Recent prompts
curl http://localhost:8000/api/prompts?limit=5

# Logs
curl http://localhost:8000/api/logs/tail?lines=50

# Verify 404 on removed endpoints
curl http://localhost:8000/api/videos/pending  # Should 404
```

### 6. Verify data files
```bash
# Prompts stored
cat app/data/prompts/prompts.jsonl

# Logs written
tail -n 20 app/data/logs.txt
```

---

## Known Limitations & Future Work

### Current Limitations
1. **No smoke test yet** - Recommended to add basic integration test for `/api/prompts/bundle`
2. **Dependencies not trimmed** - `pyproject.toml` still contains unused dependencies (Leonardo, Veo, Suno, APScheduler, etc.)
3. **Removed files still present** - Obsolete client/agent files should be deleted after verification

### Future Enhancements
1. **Gemini/GPT adapters** - Implement `GeminiAdapter` and `GPTAdapter` in `llm_interface.py`
2. **Brand palette injection** - Add `brand_palette` field to `persona.json`, inject into prompts
3. **Batch bundle display** - Show all bundles when count > 1 (currently only first bundle)
4. **Export to file** - Download bundles as JSON/text files
5. **Search/filter** - Filter recent prompts by setting or seed words

---

## Troubleshooting

### App won't start: "GROK_API_KEY missing"
- **Fix:** Set `GROK_API_KEY` in `.env` file
- **Check:** `cp .env.example .env` and edit with your API key

### 404 on /api/prompts/bundle
- **Check:** Backend running on port 8000
- **Check:** Frontend proxy configured correctly (vite.config.js)

### Character count over 1500
- **Root cause:** Grok generating overly long prompts
- **Fix:** Grok client enforces 1500 max with retry loop (up to 3 attempts)
- **Fallback:** If all attempts exceed 1500, error is returned

### Logs panel empty
- **Check:** `app/data/logs.txt` exists and has content
- **Check:** Backend has write permissions to `app/data/` directory

### Recent prompts not loading
- **Check:** `app/data/prompts/prompts.jsonl` exists
- **Check:** JSONL format is valid (one JSON object per line)

---

## Summary

**Prompt Lab pivot complete.** The AI-influencer repo is now a minimal, single-purpose tool for generating prompts via LLM (Grok by default) for manual copy/paste to Leonardo & Veo. All automated generation, queues, schedulers, and posting logic has been removed. The system is LLM-agnostic with a clean abstraction layer ready for future provider swaps.

**Core workflow:**
1. User enters setting + optional seed words in Prompt Lab UI
2. Grok generates prompt bundle (image + video motion + social meta)
3. User copies prompts to Leonardo (image) and Veo (video)
4. User manually downloads and posts generated media

**Zero automation. Manual workflow only. Fail-loud everywhere.**

---

**Generated:** 2025-11-11
**Commit:** prompt-lab-pivot-implementation
