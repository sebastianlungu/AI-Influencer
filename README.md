# AI Influencer - Prompt Lab

> **Lean prompt generation system for manual copy-paste workflow**

**Status**: ✅ **Prompt Lab Only** - Generate creative image & video prompts via Grok, copy to Leonardo/Veo

## Overview

A minimal prompt generation system that creates high-quality paired **image + video prompts** for fitness influencer content. Use Grok to generate creative prompts based on persona + diversity banks, then manually copy-paste to Leonardo (images) and Veo (videos) for external generation.

**Workflow**: Prompt Lab → Copy Prompts → Manual Generation (Leonardo/Veo)

**Tech Stack**:
- **AI Prompting**: xAI Grok (image prompts, motion prompts, social meta)
- **Backend**: Python 3.11+, FastAPI, UV package manager
- **Frontend**: React + Vite (single Prompt Lab view + Logs sidebar)
- **Storage**: Local filesystem (JSONL rolling window)

---

## ✨ Key Features

### Prompt Lab
- ✅ **Paired Prompt Generation**: Image prompts (950-1200 chars) + Video motion briefs (6s)
- ✅ **Identity Lock**: JSON-driven persona consistency (hair, eyes, body never drift)
- ✅ **Diversity Banks**: 1000+ variations across locations, wardrobe, lighting, poses, camera
- ✅ **Rolling Storage**: Keeps last 100 prompt bundles (JSONL format)
- ✅ **Copy-Paste Workflow**: Manual generation control (no automated API calls)
- ✅ **Social Meta**: Optional title, tags, hashtags generation

### Workflow Benefits
- ✅ **Full Control**: You control exact prompts used in Leonardo/Veo
- ✅ **Zero Automation**: No paid API calls beyond prompt generation
- ✅ **Cost Transparent**: Only pay for Grok prompting (~$0.002 per 15 variations)
- ✅ **Prompt Reuse**: Save and reference previous successful prompts

---

## 📋 Identity Lock & Diversity System

**Identity Lock** (`app/data/persona.json`):
- **Fixed traits** that never drift: hair, eyes, body, skin
- **Quality standards**: photorealistic, glamour lighting, shallow DOF, 35mm f/2.0
- **Negative constraints**: No text, logos, watermarks, extra fingers, warped limbs

**Diversity Banks** (`app/data/variety_bank.json`):
- **Settings**: 10+ countries/regions (Japan, Greece, Dubai, Maldives...)
- **Scenes**: 10+ ultra-detailed locations (luxury penthouse rooftop, beachfront villa deck...)
- **Wardrobe**: 3000 unified outfit phrases with materials and colors (Grok invents new ones, never reuses)
- **Accessories**: 12+ jewelry and accessories (minimalist gold studs, delicate necklaces...)
- **Lighting**: 10+ cinematic scenarios (golden hour backlight, soft diffused overcast...)
- **Camera**: 508 technical specs (24mm, 35mm, 50mm, 85mm with various apertures and movements)
- **Angles**: 363 compositions (low angle hero shot, Dutch tilt, eye-level portrait, overhead...)
- **Pose/Microaction**: 18+ specific actions (arched back stretch, sultry over-shoulder glance...)
- **Color palettes**: 10+ grading styles (warm golden sunset, cool steel-blue ambient...)

**Prompt Structure**:
Generated prompts combine identity lock + randomly sampled diversity elements to create unique, on-brand variations (950-1200 characters total: FOREVER prefix ~236 chars + LLM-generated text 750-950 chars).

---

## 🎯 User Workflow

### Step 1: Generate Prompts
```
1. Navigate to Prompt Lab (Ctrl+P)
   → Enter high-level setting (e.g., "luxury penthouse at golden hour")
   → Optionally add seed words (e.g., "confidence", "glamour")
   → Select count (1-5 prompt bundles)
   → Click Generate

2. System generates paired prompts via Grok:
   → 📷 IMAGE PROMPT: 950-1200 char ultra-detailed Leonardo prompt
     - FOREVER prefix (~236 chars): Fixed persona (hair, eyes, body, skin)
     - LLM-generated text (750-950 chars): Scene, wardrobe, pose, lighting, camera details
     - Enforces 864×1536 (9:16) vertical format
     - Character counter shows: 🟢 950-1100 (perfect), 🟠 1100-1200 (OK), 🔴 >1200 (warning)

   → 🎬 VIDEO MOTION BRIEF: 6-second cinematic motion instructions for Veo 3
     - Single-line format: "natural, realistic — [motion type] from [start] to [end], [subject action]; finish [final position]"
     - Example: "natural, realistic — handheld push-in from oblique to front, she resets a wrist wrap on a steady breath; finish eye-level three-quarter."
     - Duration: 6 seconds exactly

   → 📱 SOCIAL META (collapsible, optional):
     - Title (40-60 chars)
     - Tags (5-10 keywords)
     - Hashtags (8-12 with # prefix)

3. Copy prompt sections using copy buttons
   → System stores last 100 prompts (rolling window)
   → View recent prompts below generation form
```

### Step 2: External Generation (Manual)
```
4. Generate image in Leonardo.ai:
   → Paste IMAGE PROMPT into Leonardo
   → Use Leonardo Alchemy V2 model (or your preferred model)
   → Set dimensions to 864×1536 (9:16 vertical)
   → Download PNG

5. Generate video in Veo 3:
   → Upload PNG to Veo 3
   → Paste VIDEO MOTION BRIEF
   → Set duration to 6 seconds exactly
   → Download MP4 (includes SynthID watermark)
```

**That's it!** No upload, no validation, no review workflow - pure prompt generation.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **[UV](https://github.com/astral-sh/uv) package manager** ⚠️ NEVER use pip - UV ONLY
- **xAI Grok API key** (for prompt generation)

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
# Edit .env with your Grok API key:
# GROK_API_KEY=xai-your-key-here
```

### Running the System

```bash
# Development mode (Unix/Mac)
bash scripts/dev_run.sh

# OR run separately:
# Backend: uv run uvicorn app.main:app --reload --port 3590
# Frontend: cd frontend && npm run dev
```

**Access**:
- Frontend: http://localhost:3589
- Backend API: http://localhost:3590
- API Docs: http://localhost:3590/docs

### First Run

1. **Set Grok API Key** in `.env`:
   ```bash
   GROK_API_KEY=xai-your-key-here
   ```

2. **Navigate to Prompt Lab** (http://localhost:3589 or press Ctrl+P)

3. **Generate Prompts**:
   - Enter setting: "luxury penthouse rooftop at golden hour"
   - Click "Generate"
   - Copy IMAGE PROMPT and VIDEO MOTION sections

4. **Use Externally**:
   - Paste into Leonardo.ai for images (864×1536, 9:16)
   - Paste into Veo 3 for videos (6 seconds)

---

## 🔧 Configuration

### Required Settings

Set these in your `.env` file:

```bash
# LLM Provider (prompt generation)
LLM_PROVIDER=grok                       # Default: grok
GROK_API_KEY=your-grok-api-key-here     # Required
GROK_MODEL=grok-2-latest                # Default: grok-2-latest
GROK_TIMEOUT_S=30                       # Request timeout

# Data Paths
PERSONA_FILE=app/data/persona.json      # Identity lock (hair, eyes, body)
VARIETY_FILE=app/data/variety_bank.json # Diversity banks
PROMPTS_OUT_DIR=app/data/prompts        # Prompt bundle storage (JSONL)
```

**Cost**: ~$0.002 per 15 prompt bundles (Grok is very cheap)

### Character Configuration

**Identity Lock** (`app/data/persona.json`):
Edit this file to customize your character's fixed traits:

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

**Diversity Banks** (`app/data/variety_bank.json`):
Edit this file to customize variety options (sampled randomly per prompt):

```json
{
  "setting": ["Japan", "Greece", "Dubai", "Maldives", ...],
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

**How It Works**:
- `persona.json` defines **fixed identity** (appears in every prompt)
- `variety_bank.json` defines **diversity options** sampled randomly
- Grok combines identity + diversity to generate unique, on-brand prompts

**Note**: Wardrobe examples are for inspiration only - Grok is instructed to **invent new outfits** and **avoid repeating fabric types from examples**.

---

## 🏗️ Architecture

### Prompt Generation Flow

```
User → Prompt Lab (Ctrl+P) → POST /api/prompts/bundle
                                        ↓
                            Grok API generates bundle
                            ┌────────────────────────────┐
                            │ 📷 IMAGE PROMPT            │
                            │ - 950-1200 chars total     │
                            │ - FOREVER prefix (~236)    │
                            │ - LLM text (750-950)       │
                            │ - Diversity sampling       │
                            │ - 864×1536 (9:16) format   │
                            │                            │
                            │ 🎬 VIDEO MOTION BRIEF      │
                            │ - Camera motion            │
                            │ - Character action         │
                            │ - Environment notes        │
                            │ - 6-second duration        │
                            │                            │
                            │ 📱 SOCIAL META (optional)  │
                            │ - Title (40-60 chars)      │
                            │ - Tags (5-10 keywords)     │
                            │ - Hashtags (8-12)          │
                            └────────────────────────────┘
                                        ↓
                            Stored to JSONL (last 100)
                                        ↓
                            Returns bundle to UI
                                        ↓
                            User copies prompts
                                        ↓
                        Manual generation (Leonardo/Veo)
```

### System Components

**Grok Client** (`backend/app/grok/client.py`):
- `generate_prompt_bundle()`: Creates paired image + video prompts from setting + diversity banks
- `suggest_motion()`: Generates video motion brief for 6-second clips
- `generate_social_meta()`: Creates title, tags, hashtags for social posting

**LLM Abstraction Layer** (`backend/app/clients/llm_interface.py`):
- `LLMClient`: Abstract base class for provider-agnostic prompting
- `GrokAdapter`: Wraps GrokClient with LLMClient interface
- Future: `GeminiAdapter`, `GPTAdapter` (not yet implemented)

**Prompt Storage** (`backend/app/core/prompt_storage.py`):
- `append_prompt_bundle()`: JSONL format with rolling window (keeps last 100)
- `read_recent_prompts()`: Returns newest-first for UI display

**Fail-Loud Philosophy**:
```python
# ❌ NO silent failures
# ❌ NO mock modes
# ❌ NO degraded functionality

# ✅ Explicit validation
if not settings.grok_api_key:
    raise RuntimeError("GROK_API_KEY missing in .env")
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/prompts/bundle` | POST | Generate N prompt bundles (image + video + social) |
| `/api/prompts` | GET | Get recent prompt bundles (newest first, default: 20) |
| `/api/healthz` | GET | Health check with LLM provider status |
| `/api/logs/tail` | GET | Tail system logs (default: 100 lines) |

**POST /api/prompts/bundle Request**:
```json
{
  "setting": "luxury penthouse rooftop at golden hour",
  "seed_words": ["confidence", "glamour"],
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
        "final_prompt": "photorealistic vertical 9:16 image of a 28-year-old woman with...",
        "negative_prompt": "brunette, plastic skin, text, logos...",
        "width": 864,
        "height": 1536
      },
      "video_prompt": {
        "motion": "slow dolly-in with subtle parallax shift",
        "character_action": "arched back stretch reaching up",
        "environment": "golden hour backlight with warm rim glow",
        "duration_seconds": 6,
        "notes": "emphasize backlit rim lighting"
      }
    }
  ]
}
```

---

## 🔐 Security & Safety

### Financial Safety
- **No automation**: Only manual Grok API calls for prompting
- **Cost tracking**: Grok usage logged (very cheap: ~$0.002 per 15 prompts)
- **Fail-loud**: Missing API key raises immediately

### Prompt Quality
- **Character count enforcement**: 950-1200 chars (enforced minimum: 950, Leonardo API max: 1500)
- **FOREVER prefix**: Fixed ~236-char persona prefix prepended to all prompts
- **Fuzzy binding validation**: 80% token matching to tolerate grammar fixes (e.g., "from from" → "from")
- **Retry loop**: Up to 3 attempts if prompts violate length limits
- **Wardrobe binding**: ON by default (single coherent outfit phrase)
- **Wardrobe invention**: Grok instructed to invent new outfits, avoid repeating fabric types

---

## 🔬 Current Implementation Details

### FOREVER Prefix Architecture

The prompt generation system uses a **two-part architecture**:

1. **FOREVER Prefix** (~236 chars, client-side):
   ```
   "photorealistic vertical 9:16 image of a 28-year-old woman with
   [hair], [eyes], [body], [skin]"
   ```
   - Built from `persona.json` (identity lock)
   - Prepended client-side (not sent to Grok)
   - Ensures character consistency across all prompts
   - Length: ~236 characters (fixed)

2. **LLM-Generated Text** (750-950 chars, Grok):
   - Scene description with specific location details
   - Camera specs (lens, aperture, movement)
   - Wardrobe details (50-80 chars, invented per prompt)
   - Accessories (1-2 items)
   - Pose and micro-action (detailed body mechanics)
   - Lighting setup (specific lighting type and direction)
   - Environmental atmosphere
   - Length: 750-950 characters (target: ~850)

**Total Prompt Length**: 950-1200 characters (FOREVER prefix + LLM text)

### Binding System

**Binding Policy** (default settings):
- ✅ **Scene**: ON (exact location phrase from diversity bank)
- ✅ **Pose/Microaction**: ON (VERBATIM enforcement, strict matching)
- ✅ **Lighting**: ON (specific lighting setup)
- ✅ **Camera**: ON (lens, aperture, movement specs)
- ✅ **Angle**: ON (camera angle and composition)
- ✅ **Accessories**: ON (1-2 items depending on `single_accessory` flag)
- ✅ **Wardrobe**: ON (single coherent outfit phrase, 50-80 chars)

**Fuzzy Matching** (80% token threshold):
- Applied to all binding slots EXCEPT pose (which remains strict)
- Tolerates minor grammar fixes: "from from" → "from"
- Normalizes: lowercase, strips articles (a, an, the), collapses spaces
- Example: "arc slide from from marble colonnade" matches "arc slide from marble colonnade" (90% tokens matched)

**Validation Flow**:
```python
1. Grok generates prompt with bound elements
2. Client validates each bound phrase:
   - Pose: Strict exact matching (case-insensitive)
   - All others: Fuzzy matching (80% token threshold)
3. If ANY binding fails → mark as STILL_NONCOMPLIANT
4. If length out of range (950-1200) → retry up to 3 times
```

### Diversity Bank Sizes (Current)

**Regenerated banks** (as of latest commit):
- **Camera**: 508 unique technical specs (24mm-85mm lenses, f/1.4-f/2.8 apertures, movements)
- **Angle**: 363 unique compositions (overhead, eye-level, low angle, Dutch tilt, etc.)
- **Wardrobe**: 3000 unified outfit phrases (single coherent descriptions, not top+bottom split)
- **Scenes**: 10+ ultra-detailed location descriptions per setting
- **Lighting**: 10+ cinematic lighting scenarios
- **Accessories**: 12+ jewelry and accessory items
- **Pose/Microaction**: 18+ specific body mechanics and actions

**Legacy Banks** (not used):
- `wardrobe_top`: 1000 items (legacy, unused)
- `wardrobe_bottom`: 1000 items (legacy, unused)

Current system uses unified `wardrobe` array exclusively for coherent single-phrase outfit descriptions.

### Video Format

**Single-line motion prompt** (Veo 3 optimized):
```
"natural, realistic — [motion type] from [start position] to [end position],
[subject action]; finish [final camera position]."
```

**Example**:
```
"natural, realistic — handheld push-in from oblique to front,
she resets a wrist wrap on a steady breath; finish eye-level three-quarter."
```

**Format Requirements**:
- Single line only (no multi-field structure)
- Begins with "natural, realistic —"
- Specifies camera motion type (handheld, dolly, crane, etc.)
- Includes start and end positions
- Describes subject action during motion
- Ends with final camera position
- Duration: 6 seconds exactly

### Test Results (Latest Sanity Test)

**Configuration**: 10 bundles generated for Japan location with all bindings ON

**Results**:
- ✅ **Length compliance**: 10/10 (100%) in range 950-1200 chars
- ✅ **Binding validation**: 10/10 (100%) passed fuzzy matching
- ✅ **STILL_NONCOMPLIANT**: 0/10 (0%)
- ✅ **FOREVER prefix**: Intact in all prompts
- ✅ **Wardrobe binding**: Single coherent outfit phrases in all prompts

**Length distribution**:
- Average: ~1100 chars
- Min: ~1050 chars
- Max: ~1150 chars
- All within target range (950-1200)

**Commit History** (recent changes):
- `65974ce`: Remove obsolete VIDEO semicolon validation
- `093cbc4`: Implement streaming reliability with auto-reconnect
- `90ea37c`: Add video field enforcement and better error surfacing
- `08e03e4`: Add persona compression and smart prompt compressor
- `29855c1`: Add inline row details with horizontal two-column layout

---

## 🧪 Development

### UV Command Reference

| Action | Command |
|--------|---------|
| Install deps | `uv sync` |
| Add dependency | `uv add <package>` |
| Add dev dependency | `uv add --dev <package>` |
| Run backend | `uv run uvicorn app.main:app --reload --port 3590` |
| Run tests | `uv run pytest -q` |
| Lint | `uv run ruff check backend` |
| Type check | `uv run mypy backend` |
| Format | `uv run ruff format backend` |

### Project Structure

```
ai-influencer/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app (minimal lifespan)
│   │   ├── api/routes.py           # 4 API endpoints only
│   │   ├── clients/
│   │   │   ├── llm_interface.py    # LLM abstraction layer
│   │   │   ├── provider_selector.py # LLM provider selection
│   │   │   └── grok.py             # xAI Grok client (prompts only)
│   │   ├── grok/
│   │   │   ├── client.py           # Grok prompt generation logic
│   │   │   └── transport.py        # HTTP transport layer
│   │   └── core/
│   │       ├── config.py           # Pydantic settings (LLM only)
│   │       ├── prompt_storage.py   # JSONL rolling window
│   │       ├── logging.py          # Structured logging
│   │       └── concurrency.py      # No-op stub (grok_slot only)
│   └── pyproject.toml              # UV dependencies (lean)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Single view + logs sidebar
│   │   ├── PromptLab.jsx           # Prompt generation UI
│   │   ├── LogViewer.jsx           # Logs sidebar
│   │   └── api.js                  # 4 API helpers
│   └── package.json
├── app/data/
│   ├── persona.json                # Identity lock (hair, eyes, body)
│   ├── variety_bank.json           # Diversity banks
│   └── prompts/
│       └── prompts.jsonl           # Rolling window (last 100)
├── .env.example
├── CLAUDE.md                       # Engineering guidelines
└── README.md                       # This file
```

### Keyboard Shortcuts

- **Ctrl+P**: Focus Prompt Lab
- **Ctrl+L**: Toggle Logs sidebar

---

## 🐛 Troubleshooting

### "GROK_API_KEY missing"
**Cause**: API key not configured
**Fix**: Add `GROK_API_KEY=xai-...` to `.env`

### "Character limit violation"
**Cause**: Grok generated prompts outside 900-1500 char range
**Fix**: System retries automatically (up to 3 attempts). If still fails, try different setting/seed words.

### "No module named 'app'"
**Cause**: Not using UV or venv not activated
**Fix**: Run `uv sync` and `source .venv/bin/activate`

### Frontend "Cannot connect to backend"
**Cause**: Backend not running on port 3590
**Fix**: Run `uv run uvicorn app.main:app --reload --port 3590`

---

## 💡 Key Principles

**✅ PROMPT LAB ONLY**: No automation, no paid API calls beyond prompt generation
**✅ COPY-PASTE WORKFLOW**: Manual generation control (Leonardo/Veo)
**✅ IDENTITY LOCK**: Fixed traits (hair, eyes, body) never drift
**✅ DIVERSITY BANKS**: 200+ variations for creative prompts
**✅ FAIL LOUDLY**: Missing API key or config raises immediately
**✅ UV ONLY**: Never use pip - UV exclusively
**✅ LEAN STACK**: Minimal dependencies, no heavy ML libs

---

**Need Help?** Open an issue or check the troubleshooting section above.
