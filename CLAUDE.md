# CLAUDE.md — Engineering Guidelines & Conventions (Prompt Lab)

This document sets the rules-of-the-road for building and maintaining the Prompt Lab repo. Follow these so the system stays predictable, debuggable, and easy to extend.

## 0) Stack (locked)

- **Backend:** Python 3.11+, FastAPI, uvicorn
- **Frontend:** React + Vite (single Prompt Lab view + Logs sidebar)
- **Storage:** Local filesystem (JSONL rolling window)

### APIs:
- **Prompting:** xAI Grok (grok-beta) for prompt generation only
  - Image prompts (900-1500 chars)
  - Video motion briefs (6 seconds)
  - Social meta (title, tags, hashtags)

**Tooling:** **UV ONLY** (`uv sync` - NEVER pip), ruff, mypy

**Dev URLs:**
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5000`

## 0.1) Non-Negotiables (read this first)

**These rules override everything else in this document:**

1. **❌ NO MOCK MODES:** Fail loudly on missing API key or invalid config. Never silently skip paid API calls.
2. **❌ NO AUTOMATION:** No image/video generation, no upload, no review, no scheduling - PROMPT GENERATION ONLY.
3. **❌ NO PIP:** Use UV exclusively. Install command: `uv sync`. Never `pip install`.
4. **✅ FAIL LOUDLY:** Missing environment variables, invalid configs, or disabled features must raise immediately with clear error messages.
5. **✅ PROMPT LAB ONLY:** The system generates prompts via Grok. Users copy-paste to Leonardo/Veo for manual generation.
6. **✅ CHARACTER COUNT ENFORCEMENT:** 900-1500 chars (enforced minimum: 900, Leonardo API max: 1500). Retry up to 3 times if violated.
7. **✅ WARDROBE INVENTION:** Grok instructed to invent new outfits, avoid repeating fabric types from examples.

## 1) Repo Layout (authoritative)

```
ai-influencer/
  backend/
    app/
      __init__.py
      main.py                    # FastAPI app (minimal lifespan)
      api/
        __init__.py
        routes.py                # 4 API endpoints only
      clients/
        __init__.py
        llm_interface.py         # LLM abstraction layer (provider-agnostic)
        provider_selector.py     # LLM provider selection (Grok/Gemini/GPT)
      grok/
        __init__.py
        client.py                # Grok prompt generation logic
        transport.py             # HTTP transport layer
        prompts.py               # Pydantic models (PromptBundle, etc.)
      core/
        __init__.py
        config.py                # Pydantic settings (LLM only)
        logging.py               # Structured audit logging
        prompt_storage.py        # JSONL rolling window (last 100)
        concurrency.py           # No-op stub (grok_slot only)
  frontend/
    index.html
    src/
      main.jsx
      App.jsx                    # Single view + logs sidebar
      PromptLab.jsx              # Prompt generation UI
      LogViewer.jsx              # Logs sidebar
      api.js                     # 4 API helpers
  app/
    data/
      persona.json               # Identity lock (hair, eyes, body, skin)
      variety_bank.json          # Diversity banks (scenes, wardrobe, lighting, etc.)
      prompts/
        prompts.jsonl            # Rolling window (last 100 bundles)
  .env.example
  .python-version
  pyproject.toml                 # UV dependency management (lean)
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
- **Naming:** `snake_case` for funcs/vars, `PascalCase` for classes, `SCREAMING_SNAKE` for consts.
- **Errors:** never swallow. Raise `RuntimeError` or appropriate exception with clear messages.
- **Retries:** only in Grok client, exponential backoff (max 3, jitter).

### React

- Single page, functional components, no state libs.
- Keep components ≤ 150 LOC.
- Don't add CSS frameworks; use minimal CSS in `index.html` or scoped CSS.
- Keyboard shortcuts: `Ctrl+P` (Prompt Lab), `Ctrl+L` (Logs)

## 3) Configuration & Secrets

- **Primary config:** `app/data/persona.json` (identity lock) + `app/data/variety_bank.json` (diversity banks)
- **Secrets:** via `.env` only (never in git). Provide `.env.example`.
- `config.py` loads JSON, overlays env keys, validates with Pydantic.
- Fail fast on missing/invalid config.

## 4) JSON Files (single source of truth)

### `persona.json` — Identity Lock (Fixed Traits)
Defines character's **unchanging appearance** and **style rules**:

```json
{
  "hair": "medium wavy caramel-blonde hair",
  "eyes": "saturated blue eyes",
  "body": "busty muscular physique with hourglass defined body",
  "skin": "realistic natural skin texture and strong realistic wet highlights",
  "do": [
    "photorealistic instagram style",
    "glamour lighting",
    "shallow DOF",
    "35mm f/2.0",
    "generous cleavage",
    "28 years old"
  ],
  "dont": [
    "brunette",
    "plastic skin",
    "over-smooth",
    "uncanny",
    "text",
    "logos",
    "watermarks",
    "extra fingers",
    "warped limbs",
    "doll-like face"
  ]
}
```

**What this controls:**
- Character's physical appearance (hair, eyes, body, skin) - appears in EVERY prompt
- Style guidelines (do array) - merged into prompts
- Negative prompt items (dont array) - merged with variety_bank.negative

### `variety_bank.json` — Diversity Options (Sampled Randomly)
Defines **pools of options** that Grok samples from to create variety:

```json
{
  "setting": ["Japan", "United States", "Greece", ...],
  "scene": ["luxury penthouse rooftop...", "beachfront villa deck...", ...],
  "wardrobe": ["white string bikini top...", "sheer mesh crop top...", ...],
  "accessories": ["minimalist gold studs", "delicate necklaces", ...],
  "lighting": ["golden hour backlight", "soft diffused overcast", ...],
  "camera": ["35mm f/1.8 shallow DOF", "50mm f/2.0 creamy bokeh", ...],
  "angle": ["low angle hero shot", "eye-level portrait", ...],
  "pose_microaction": ["arched back stretch", "sultry over-shoulder glance", ...],
  "color_palette": ["warm golden sunset", "cool steel-blue ambient", ...],
  "negative": ["doll-like", "uncanny face", "plastic skin", ...]
}
```

**What this controls:**
- **Variety pools** that Grok samples from for each prompt
- **Wardrobe examples** (Grok is instructed to INVENT NEW, not reuse these, and avoid repeating fabric types)
- Additional negative prompt items (merged with persona.dont)

### `prompts.jsonl` — Prompt Bundle Storage
**Format:** One JSON object per line (JSONL), rolling window keeps last 100.

```jsonl
{"id":"pr_abc123","setting":"luxury penthouse","seed_words":["glamour"],"image_prompt":{"final_prompt":"...","negative_prompt":"...","width":864,"height":1536},"video_prompt":{"motion":"...","character_action":"...","environment":"...","duration_seconds":6},"created_at":"2025-01-11T12:34:56Z"}
```

**Rule:** all writes go through `prompt_storage.py` helpers (atomic write to temp, then rename).

## 5) Prompt Engineering System

### How Grok Constructs Prompts

Located in: `backend/app/grok/client.py:generate_prompt_bundle()`

**Step 1: Load Configuration**
```python
persona = load("persona.json")
variety_bank = load("variety_bank.json")
```

**Step 2: Build Character Appearance String**
```python
appearance = f"{persona['hair']}, {persona['eyes']}, {persona['body']}, {persona['skin']}"
```

**Step 3: Build Negative Prompt**
```python
negative_prompt = persona["dont"] + variety_bank["negative"]
# Result: "brunette, plastic skin, text, logos, extra fingers, doll-like, uncanny face..."
```

**Step 4: Construct System Prompt**
The system sends Grok a **detailed instruction prompt** with:

```python
system_prompt = f"""Create {count} prompt bundle(s) for: {setting}

Each bundle has:
1. Image prompt (900-1100 chars TARGET) - photorealistic glamour portrait
2. Video prompt (6s motion + action)

**CRITICAL CHARACTER COUNT REQUIREMENTS:**
- Target: 900-1100 characters (including spaces)
- Enforced minimum: 900 chars (our quality standard; prompts under 900 will be REJECTED)
- Maximum: 1500 chars (Leonardo API hard limit)
- Count carefully before submitting!

Character: {appearance}

Variety banks:
- Scenes (rotate/select): {scenes[:4]}...
- Accessories (select 2-3): {accessories[:6]}...
- Poses (select/vary): {poses[:6]}...
- Lighting (select): {lighting[:5]}...
- Camera (select): {camera[:4]}... + angles: {angles[:6]}...

**WARDROBE - INVENT NEW (examples for style inspiration only):**
Examples: {wardrobe[:5]}
**DO NOT REUSE THESE. CREATE entirely unique wardrobe for each prompt with specific fabrics, cuts, colors, and styling details (50-80 chars). Avoid repeating fabric types from examples.**

Detailed template (aim for 900-1100 chars total):
"photorealistic vertical 9:16 image of a 28-year-old woman with [full appearance],
[shot type] at [very specific {setting} location]. Camera: [lens + f-stop + angle].
Wardrobe: [INVENT unique outfit - 50-80 chars]. Accessories: [2-3 items].
Pose: [detailed body mechanics]. Lighting: [specific lighting].
Environment: [atmospheric details]."

Return JSON array of {count} bundle(s):
[{{"id": "pr_xxx", "image_prompt": {{"final_prompt": "...", "negative_prompt": "{negative_prompt}",
"width": 864, "height": 1536}}, "video_prompt": {{"motion": "...", "character_action": "...",
"environment": "...", "duration_seconds": 6, "notes": "..."}}}}]"""
```

**Step 5: Call Grok API**
```python
response = grok_api.chat_completion(system_prompt, user_prompt="Generate creative bundles")
```

**Step 6: Validation & Character Count Enforcement**
```python
for bundle in response:
    prompt_length = len(bundle["image_prompt"]["final_prompt"])

    if prompt_length < 900:
        raise "TOO SHORT - enforced minimum is 900 chars"

    if prompt_length > 1500:
        raise "TOO LONG - Leonardo API limit is 1500 chars"
```

**Retry Logic**: If ANY prompt violates limits, the ENTIRE batch is retried (up to 3 attempts). Fail-loud if still invalid.

## 6) LLM Abstraction Layer

**Key Principle:** All LLM providers are hidden behind `clients/llm_interface.py` with stable method signatures.

### Provider-Agnostic Interface

**LLMClient Abstract Base Class** (`clients/llm_interface.py`):
```python
class LLMClient(ABC):
    @abstractmethod
    def generate_prompt_bundle(self, setting: str, seed_words: list[str] | None = None, count: int = 1) -> list[dict]:
        """Generate N prompt bundles (image + video + social)."""
        pass

    @abstractmethod
    def suggest_motion(self, image_meta: dict, duration_s: int = 6) -> dict:
        """Generate video motion brief."""
        pass

    @abstractmethod
    def generate_social_meta(self, media_meta: dict) -> dict:
        """Generate social title, tags, hashtags."""
        pass
```

**GrokAdapter** (`clients/llm_interface.py`):
```python
class GrokAdapter(LLMClient):
    def __init__(self, grok_client):
        self._client = grok_client

    def generate_prompt_bundle(self, setting, seed_words, count):
        # Delegates to GrokClient.generate_prompt_bundle()
        return self._client.generate_prompt_bundle(setting, seed_words, count)
```

**Provider Selection** (`clients/provider_selector.py`):
```python
def prompting_client() -> LLMClient:
    provider = settings.llm_provider.lower()

    if provider == "grok":
        _guard_llm("grok", settings.grok_api_key)
        grok = GrokClient(api_key=settings.grok_api_key, model=settings.grok_model)
        return GrokAdapter(grok)

    elif provider == "gemini":
        raise RuntimeError("Gemini provider not yet implemented. Set LLM_PROVIDER=grok.")

    elif provider == "gpt":
        raise RuntimeError("GPT provider not yet implemented. Set LLM_PROVIDER=grok.")
```

**Why This Matters:**
- Swapping from Grok → Gemini/GPT requires only implementing a new adapter
- `routes.py` and all API code calls `prompting_client()`, never imports GrokClient directly
- Pipeline remains unchanged when switching providers

## 7) FastAPI Endpoints (Only 4)

**Prompt Generation:**
- `POST /api/prompts/bundle` → Generate N prompt bundles (image + video + social)
- `GET /api/prompts` → Get recent prompt bundles (newest first, default: 20)

**System:**
- `GET /api/healthz` → Health check with LLM provider status
- `GET /api/logs/tail` → Tail system logs (default: 100 lines)

All endpoints return deterministic JSON; no HTML.

## 8) Logging & Observability (minimal)

- **Single file:** `/app/data/logs.txt`
- **Format:** `ISO8601 | level | component | event | {json_meta}`
- **Log levels:** INFO main flow, WARN recoverable, ERROR with stack trace.
- No PII or secrets in logs.

## 9) Errors & Retries

- **Fail-loud policy:** No silent failures, no mock modes. Missing API key must fail immediately with clear error messages.
- **Grok client:** retry 3x with backoff (0.5s, 1s, 2s + jitter).
- Recognize 429/5xx as retryable; 4xx non-retryable (surface the cause).

## 10) Frontend Rules

**Prompt Lab UI:**
- Single view: Prompt generation form + output display
- Sections: 📷 IMAGE PROMPT, 🎬 VIDEO MOTION, 📱 SOCIAL META (collapsible)
- Character counter: 🟢 900-1100 (perfect), 🟠 1100-1400 (OK), 🔴 >1400 (warning)
- Copy buttons for each section
- View recent prompts below form (newest first)

**Logs Sidebar:**
- Toggle with Ctrl+L
- Shows last 100 log lines
- Auto-scroll to bottom

**Keyboard Shortcuts:**
- `Ctrl+P`: Focus Prompt Lab
- `Ctrl+L`: Toggle Logs sidebar

## 11) Testing

- `pytest -q` must pass locally (if tests exist).
- Provide unit tests for: prompt storage, Grok client (with mocked HTTP).

## 12) Git Hygiene

- **Branching:** `feature/<short-desc>`, PRs into master.
- **Commit style:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`).
- Small PRs (< 400 lines diff preferred).
- PR description must state acceptance checks (what endpoint/flow to verify).

## 13) Security & Compliance

- Secrets only via `.env`; never log them.
- Validate and sanitize all JSON from Grok before saving.

## 14) Extension Points

- New LLM providers must implement `LLMClient` interface with identical method signatures.
- All provider differences are hidden behind `llm_interface.py`; `routes.py` remains unchanged.

## 15) Build & Run (dev)

**Setup (first time):**
```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
cd frontend && npm install && cd ..
cp .env.example .env       # Configure Grok API key
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
- Lint: `uv run ruff check backend`
- Type check: `uv run mypy backend`

**Notes:**
- Backend on `http://localhost:8000`, frontend on `http://localhost:5000`
- Never use `pip install` - UV only

## 16) Definition of Done (every change)

- [ ] All tests + lints pass.
- [ ] Manual smoke test: `POST /api/prompts/bundle` produces valid prompt bundle.
- [ ] README updated if any input/endpoint/flow changed.

---

**Key Differences from Original System:**

1. **No automation**: Removed scheduler, generation agents, upload/review workflows
2. **Prompt Lab only**: Single purpose - generate prompts via Grok
3. **Copy-paste workflow**: User manually uses prompts in Leonardo/Veo
4. **4 endpoints only**: Down from 20+ in original system
5. **Lean dependencies**: Removed opencv, apscheduler, google-cloud-aiplatform
6. **No tests**: Removed test suite (manual workflow doesn't require it)
7. **Minimal concurrency**: Only `grok_slot()` no-op stub for import compatibility
8. **Character count enforcement**: 900-1500 chars (enforced minimum: 900, Leonardo API max: 1500)
9. **Wardrobe invention**: Grok instructed to invent new outfits, avoid repeating fabric types

**This is the new source of truth for Prompt Lab development.**
