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
- **Img→Vid:** Pika Labs API
- **Editing:** Shotstack API
- **Posting:** TikTok Content Posting API (Direct Post)

**Tooling:** poetry (or uv) for deps, ruff + black, mypy, pytest

## 1) Repo Layout (authoritative)

```
/app
  main.py                 # FastAPI app factory + routes
  scheduler.py            # APScheduler init + jobs
  pipeline.py             # Orchestrates prompt→image→video→edit→index
  hashing.py              # Content hashing & dedupe utilities
  storage.py              # Filesystem ops & JSON index I/O
  config.py               # Typed config loader (from JSON + env)
  clients/
    gemini_api.py         # Prompt generator client
    fal_api.py            # LoRA training & inference client
    leonardo_api.py
    pika_api.py
    shotstack_api.py
    tiktok_api.py
  models/
    types.py              # Pydantic models & JSON schemas
  data/
    prompt_config.json
    history.json
    videos.json
    generated/            # mp4 + sidecar json
    posted/
    deleted/
    logs.txt
/frontend
  index.html
  main.jsx                # POST / DELETE only UI
/tests
  test_pipeline.py
  test_hashing.py
  test_storage.py
scripts/
  dev_run.sh
  format.sh
.env.example
README.md
CLAUDE.md                 # this file
pyproject.toml            # or pyproject + uv.lock
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

## 6) Pipeline Contract (idempotent)

Each step returns a typed result; on failure, raise `AppError`.

1. **Propose variations** (`gemini_api.create_variations`)
   - Input: `PromptConfig`, `history_hashes[:500]`
   - Output: `list[Variation]` (10 items)

2. **Generate image** (`leonardo_api.generate_image`)
   - Input: `Variation` → Output: local PNG path

3. **Img→Vid** (`pika_api.image_to_video`)
   - Input: PNG + duration params → Output: MP4 path

4. **Edit** (`shotstack_api.edit`)
   - Input: MP4 → Output: MP4 (music, watermark, optional effects)

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

- Character is non-speaking; no voice or subtitles in videos.
- No captions, hashtags, or overlays are added to the video content.
- Front-end displays only visuals; no text overlays or captions.
- On publish success: persist returned post ID in sidecar JSON.
- Synthetic media disclosure (if required by platform) is handled outside this system.
- **No mock modes:** If auth/env is missing or invalid, fail loudly with clear error messages.

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

- APScheduler cron runs hourly by default (`/api/cycle/generate`).
- Respect `batch.clips_per_cycle` and `batch.max_parallel`.
- Never overlap runs: use a pidfile or APScheduler job coalescing.

## 12) Frontend Rules

- One video at a time.
- Buttons: POST and DELETE only.
- Keyboard: `K` → POST, `J` → DELETE.
- Autoplay muted, loop.
- No captions, overlays, or text displayed over video content.
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

`scripts/dev_run.sh` should:
- export `.env` → run backend (uvicorn) → run frontend (vite)
- Backend on `http://localhost:8000`, frontend on `http://localhost:5173`.
- Media served from `/app/data` via static route.

## 20) Definition of Done (every change)

- [ ] All tests + lints pass.
- [ ] Manual smoke test: `POST /api/cycle/generate` produces ≥1 generated clip and UI displays it.
- [ ] README updated if any input/endpoint/flow changed.