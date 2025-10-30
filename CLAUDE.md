# CLAUDE.md — Engineering Guidelines & Conventions

This document sets the rules-of-the-road for building and maintaining the repo. Follow these so the system stays predictable, debuggable, and easy to extend.

## 0) Stack (locked)

- **Backend:** Python 3.11+, FastAPI, uvicorn
- **Scheduling:** APScheduler (cron + one-off triggers)
- **Frontend:** React + Vite (single-page "review-only" UI)
- **Storage:** Local filesystem under `/app/data` (JSON indices + media files)

### APIs:
- **Prompting:** Gemini 2.5 Pro
- **LoRA Training & Inference:** FAL.ai
- **Image:** Leonardo.ai API
- **Img→Vid:** Google Veo 3 on Vertex AI (with SynthID watermark)
- **Editing:** Shotstack API
- **Posting:** TikTok Content Posting API (Direct Post)

**Tooling:** **UV ONLY** (`uv sync` - NEVER pip), ruff, mypy, pytest

**Dev URLs:**
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

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
        scheduler.py             # APScheduler wiring (off by default)
      coordinator/
        orchestrator.py          # run_cycle() → dispatches agents
      agents/
        __init__.py
        prompting.py             # Variation proposals
        gen_image.py             # Image generation
        gen_video.py             # Image-to-video
        edit.py                  # Polish (music, effects; NO overlays)
        qa_style.py              # Blur detection, quality gates
        qa_safety.py             # SFW compliance gates
        indexer.py               # Index to videos.json
        posting.py               # TikTok publish (future)
      clients/
        __init__.py
        leonardo.py              # Leonardo.ai client
        veo.py                   # Google Veo 3 video generation client
        shotstack.py             # Shotstack client
        tiktok.py                # TikTok API client
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
      prompt_config.json
      videos.json
      history.json
      logs.txt
      generated/
      posted/
      deleted/
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

- **`prompt_config.json`** — character/context, video params, banks, API keys (as `env:VAR` references).
- **`history.json`** — `{"hashes": [...], "max_size": 5000}`; rolling window, append-only.
- **`videos.json`** — array of entries:

```json
{
  "id": "20251024-0001",
  "status": "generated|posted|deleted|failed",
  "mp4_path": "data/generated/clip_20251024_0001.mp4",
  "thumb_path": "data/generated/clip_20251024_0001.jpg",
  "meta": {
    "title": "...",
    "seed": 1234,
    "duration_s": 8,
    "captions": ["..."]
  },
  "created_at": "ISO8601"
}
```

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

- **Coordinator** (`coordinator/orchestrator.py`): Entry point for generation cycles. Validates configs, calls agents sequentially per variation, logs failures, continues batch.
- **Agents** (under `agents/`):
  - **prompting**: Proposes N variations from `prompt_config.json` + history dedupe.
  - **gen_image**: Generates PNG from variation payload.
  - **gen_video**: Converts PNG → MP4.
  - **edit**: Applies music/effects (NO text/captions/voice).
  - **qa_style**: Blur detection (Laplacian variance), quality gates.
  - **qa_safety**: SFW compliance checks.
  - **indexer**: Moves final MP4 to `generated/`, writes to `videos.json`.
  - **posting**: (future) Publishes to TikTok.

**Execution Model:**
- Agents run **sequentially** within each variation (dependencies: image → video → edit → QA → index).
- Multiple variations in a batch can be parallelized (up to `MAX_PARALLEL`), but this is controlled by the coordinator.
- Each agent is **fail-loud**: missing configs or API keys raise immediately; no silent fallbacks.

**Deterministic Outcomes:**
- IDs are content-hashed (prompt + seed).
- Re-running the same input produces the same ID (dedupe catches it).
- No global state outside JSON files.

## 5.2) Provider Abstraction

**Key Principle:** All external API vendors are hidden behind `clients/*` with stable method signatures.

- **Swappable Providers:** Changing from Leonardo → DALL·E, or Veo → Runway, or FAL → another LoRA host requires only updating `clients/provider_selector.py` and the specific client module.
- **Pipeline Unchanged:** `coordinator/orchestrator.py` and all agents call generic methods like `image_client().generate(payload)`. The pipeline never imports vendor-specific code directly.
- **Contracts:** Each client exposes:
  - `generate(payload: dict) -> str` (image path)
  - `img2vid(image: str, payload: dict) -> str` (video path)
  - `simple_polish(video: str, payload: dict) -> str` (edited video path)
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
- **Blur detection** (qa_style): Laplacian variance threshold; reject if too low.
- **Bitrate sanity** (qa_style): Reject if edited video is under minimal bitrate.
- **SFW check** (qa_safety): Placeholder for external classifier.

**Audit Logging:**
- All API calls, errors, and costs logged to `app/data/logs.txt`.
- **No secrets in logs.**

**Key Validation:**
- On startup or first live call: if required API key is missing, raise with clear message naming the missing env var.

## 6) Pipeline Contract (idempotent)

Each step returns a typed result; on failure, raise `AppError`.

1. **Propose variations** (`gemini_api.create_variations`)
   - Input: `PromptConfig`, `history_hashes[:500]`
   - Output: `list[Variation]` (10 items)

2. **Generate image** (`leonardo_api.generate_image`)
   - Input: `Variation` → Output: local PNG path

3. **Img→Vid** (`veo_client.img2vid`)
   - Input: PNG + duration params → Output: MP4 path (with SynthID watermark)

4. **Edit** (`shotstack_api.edit`)
   - Input: MP4 → Output: MP4 (music, optional effects)

5. **Index** (`storage.index_generated`)
   - Input: MP4 + meta → Output: `VideoRecord` added to `videos.json`

No global state outside JSON and file paths. Steps are re-runnable on the same inputs without duplicate outputs (use deterministic IDs).

## 7) FastAPI Endpoints (frozen)

- `GET /api/videos/next` → `{id, playback_url, meta}` (first `status=generated`)
- `POST /api/videos/{id}/post` → posts to TikTok; updates status to `posted`; moves file to `/data/posted/`
- `POST /api/videos/{id}/delete` → moves file to `/data/deleted/`; updates status to `deleted`
- `POST /api/cycle/generate` → triggers one full generation cycle (respect config batch size)
- **Health:** `GET /healthz` returns build info + counts

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

## 11) Scheduling

- **DISABLED BY DEFAULT:** Set `ENABLE_SCHEDULER=true` to activate.
- When enabled, APScheduler runs `run_cycle()` hourly.
- Respects `COORDINATOR_BATCH_SIZE` and `COORDINATOR_MAX_PARALLEL`.
- Never overlap runs: use APScheduler job coalescing (`max_instances=1`).
- **Rationale:** Prevents accidental spend; user must explicitly enable automated generation.

## 12) Frontend Rules

- One video at a time.
- Buttons: POST and DELETE only.
- Keyboard: `K` → POST, `J` → DELETE.
- Autoplay muted, loop.
- **❌ NO CAPTIONS, OVERLAYS, OR TEXT** displayed over video content.
- **❌ NO VOICE, NO SUBTITLES:** Character is non-speaking.
- Show minimal metadata (title, duration) below the video player.
- No extra settings in UI; all behavior driven by `prompt_config.json`.

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

- **Defaults:** 720×1280, 12 fps, 8s target (min 5, max 12).
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
- Backend on `http://localhost:8000`, frontend on `http://localhost:5173`
- Media served from `/app/data` via static route
- Never use `pip install` - UV only

## 20) Definition of Done (every change)

- [ ] All tests + lints pass.
- [ ] Manual smoke test: `POST /api/cycle/generate` produces ≥1 generated clip and UI displays it.
- [ ] README updated if any input/endpoint/flow changed.