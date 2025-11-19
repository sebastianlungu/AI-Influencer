# CLAUDE.md — Engineering Guidelines & Conventions

**Purpose:** Rules-of-the-road for building and maintaining the Prompt Lab repo. Follow these to keep the system predictable, debuggable, and easy to extend.

## Non-Negotiables (READ THIS FIRST)

🚫 **IMPORTANT: NEVER regenerate variety banks by calling Grok inside Python scripts.**
**ALL variety-bank generation MUST be done by Claude directly using parallel agents and written into JSON files.**
**No scripts should contain Grok API calls for bank-generation anymore.**

1. **❌ NO MOCK MODES:** Fail loudly on missing API key or invalid config. Never silently skip paid API calls.
2. **❌ NO AUTOMATION:** No image/video generation, no upload, no review, no scheduling - PROMPT GENERATION ONLY.
3. **❌ NO PIP:** Use UV exclusively (`uv sync`). Never `pip install`.
4. **✅ FAIL LOUDLY:** Missing env vars, invalid configs, or disabled features must raise immediately.
5. **✅ PROMPT LAB ONLY:** System generates prompts via Grok. Users copy-paste to Leonardo/Veo.
6. **✅ FOREVER PREFIX:** Fixed persona prefix (~236 chars) prepended client-side. LLM writes only scene/details. Total: 950-1200 chars.
7. **✅ FUZZY BINDING:** Wardrobe bound by default. Validation uses 80% token matching to tolerate grammar fixes.

## Stack (Locked)

- **Backend:** Python 3.11+, FastAPI, uvicorn
- **Frontend:** React + Vite (single Prompt Lab view + Logs sidebar)
- **Storage:** Local filesystem (JSONL rolling window)
- **LLM:** xAI Grok (grok-2-latest) for prompts only
- **Tooling:** UV ONLY, ruff, mypy

**Dev URLs:**
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5000`

## Repo Layout (Authoritative)

```
ai-influencer/
  backend/app/
    main.py                    # FastAPI app
    api/routes.py              # 4 endpoints only
    clients/
      llm_interface.py         # LLM abstraction (provider-agnostic)
      provider_selector.py     # Provider selection
    grok/
      client.py                # Prompt generation logic
      transport.py             # HTTP transport
    core/
      config.py                # Pydantic settings
      logging.py               # Structured logging
      prompt_storage.py        # JSONL rolling window
  frontend/src/
    App.jsx                    # Main view
    PromptLab.jsx              # Prompt UI
    LogViewer.jsx              # Logs sidebar
    api.js                     # API helpers
  app/data/
    persona.json               # Identity lock (hair, eyes, body, skin)
    variety_bank.json          # Diversity banks (scenes, wardrobe, etc.)
    prompts/prompts.jsonl      # Rolling window (last 100 bundles)
```

## Coding Standards

### Python
- **Typing:** 100% typed public functions; `from __future__ import annotations`
- **Style:** ruff + black defaults
- **Imports:** stdlib → third-party → local (blank-line separated)
- **Function size:** Pure helpers ≤40 LOC, API handlers ≤60 LOC
- **Naming:** `snake_case` funcs/vars, `PascalCase` classes, `SCREAMING_SNAKE` consts
- **Errors:** Never swallow. Raise `RuntimeError` or appropriate exception with clear messages
- **Retries:** Only in Grok client, exponential backoff (max 3, jitter)

### React
- Single page, functional components, no state libs
- Keep components ≤150 LOC
- No CSS frameworks; minimal CSS in `index.html` or scoped
- Keyboard shortcuts: `Ctrl+P` (Prompt Lab), `Ctrl+L` (Logs)

## Configuration

- **Config files:** `app/data/persona.json` (identity lock) + `app/data/variety_bank.json` (diversity banks)
- **Secrets:** `.env` only (never in git). Provide `.env.example`
- **Loading:** `config.py` loads JSON, overlays env vars, validates with Pydantic
- **Policy:** Fail fast on missing/invalid config

## Key Files

- **`persona.json`**: Fixed character traits (hair, eyes, body, skin), style rules (`do` array), negative prompt (`dont` array)
- **`variety_bank.json`**: Diversity pools sampled randomly (scenes, wardrobe, lighting, camera, angle, pose, accessories). Wardrobe examples are inspiration only - Grok invents new outfits.
- **`prompts.jsonl`**: One JSON object per line, rolling window (last 100). All writes via `prompt_storage.py` helpers (atomic write to temp, then rename).

## Prompt Engineering Flow

**Location:** `backend/app/grok/client.py:generate_prompt_bundle()`

1. Load `persona.json` + `variety_bank.json`
2. Build FOREVER prefix (~236 chars): `"photorealistic vertical 9:16 image of a 28-year-old woman with [hair], [eyes], [body], [skin]"`
3. Tell Grok to write ONLY what comes AFTER the prefix (target: 750-950 chars)
4. Client-side prepends FOREVER prefix to LLM response → final prompt (950-1200 chars total)
5. Validate: length (950-1200), bindings (80% fuzzy token match), retry up to 3x if fail

**Key:** FOREVER prefix never sent to Grok, prepended client-side to ensure consistency.

## LLM Abstraction Layer

- **Interface:** `clients/llm_interface.py` defines `LLMClient` abstract base class
- **Adapters:** `GrokAdapter` wraps `GrokClient` with stable interface
- **Selection:** `clients/provider_selector.py` returns appropriate adapter based on `LLM_PROVIDER` env var
- **Rule:** `routes.py` never imports `GrokClient` directly, always uses `prompting_client()`

**Why:** Swapping Grok → Gemini/GPT requires only implementing new adapter, pipeline unchanged.

## API Endpoints (Only 4)

- `POST /api/prompts/bundle` → Generate N prompt bundles
- `GET /api/prompts` → Get recent prompts (newest first, default 20)
- `GET /api/healthz` → Health check with LLM provider status
- `GET /api/logs/tail` → Tail logs (default 100 lines)

All return JSON only, no HTML.

## Logging

- **File:** `app/data/logs.txt`
- **Format:** `ISO8601 | level | component | event | {json_meta}`
- **Levels:** INFO (main flow), WARN (recoverable), ERROR (with stack trace)
- **Policy:** No PII or secrets in logs

## Errors & Retries

- **Fail-loud:** No silent failures, no mock modes. Missing API key raises immediately.
- **Grok retries:** 3x with exponential backoff (0.5s, 1s, 2s + jitter)
- **HTTP status:** 429/5xx retryable, 4xx non-retryable (surface cause)

## Frontend

- **UI:** Single view (prompt form + output display)
- **Sections:** 📷 IMAGE, 🎬 VIDEO, 📱 SOCIAL (collapsible)
- **Character counter:** 🟢 950-1100, 🟠 1100-1200, 🔴 >1200
- **Logs:** Toggle with Ctrl+L, shows last 100 lines, auto-scroll

## Testing

- `pytest -q` must pass
- Unit tests for: prompt storage, Grok client (mocked HTTP)

## Git Hygiene

- **Branching:** `feature/<desc>`, PRs into master
- **Commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`)
- **PR size:** <400 lines diff preferred
- **PR description:** Must state acceptance checks

## Security

- Secrets via `.env` only, never log them
- Validate and sanitize all JSON from Grok before saving

## Extension Points

- New LLM providers implement `LLMClient` interface
- All provider differences hidden behind `llm_interface.py`
- `routes.py` unchanged when switching providers

## Build & Run

**Setup:**
```bash
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
cd frontend && npm install && cd ..
cp .env.example .env  # Add GROK_API_KEY
```

**Run:**
```bash
bash scripts/dev_run.sh  # Unix/Mac
# OR
scripts\dev_run.bat      # Windows
```

**Commands:**
- Backend: `uv run uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Lint: `uv run ruff check backend`
- Type check: `uv run mypy backend`

## Definition of Done

- [ ] All tests + lints pass
- [ ] Manual smoke test: `POST /api/prompts/bundle` produces valid bundle
- [ ] README updated if any input/endpoint/flow changed

---

## Current Implementation Status

1. **FOREVER Prefix**: Fixed 236-char persona prefix prepended client-side (no drift)
2. **Length Targets**: 950-1200 chars total (FOREVER ~236 + LLM 750-950)
3. **Wardrobe**: Bound by default, single unified outfit phrase
4. **Fuzzy Validation**: 80% token matching (STILL_NONCOMPLIANT: 33% → 0%)
5. **Banks**: Camera (508), Angle (363), Wardrobe (3000) - regenerated, clean
6. **Video Format**: Single-line `"line": "natural, realistic — [motion]..."`
7. **Test Results**: 10/10 bundles in range, 0/10 noncompliant

**For detailed implementation, architecture, and examples, see README.md**
