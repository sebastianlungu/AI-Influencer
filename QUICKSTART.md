# Prompt Lab - Quick Start Guide

## Prerequisites
- Python 3.11+ with `uv` installed
- Node.js 18+ with npm
- Grok API key from xAI

## Setup (First Time)

### 1. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and set your Grok API key
# GROK_API_KEY=your-actual-key-here
```

### 2. Install Dependencies
```bash
# Backend (Python)
uv sync

# Frontend (React)
cd frontend
npm install
cd ..
```

## Run the App

### Terminal 1 - Backend
```bash
uv run uvicorn app.main:app --reload --port 8000
```

Expected output:
```
INFO: PROMPT_LAB_STARTUP mode=prompt_generation_only
INFO: PROMPT_LAB_READY prompts_dir=app/data/prompts
INFO: Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

Expected output:
```
VITE v5.x.x ready in XXX ms
➜ Local:   http://localhost:5173/
```

## Test the Prompt Lab

### 1. Open Browser
Navigate to: `http://localhost:5173`

### 2. Generate Your First Bundle
- **Setting:** Enter "Japan"
- **Seed Words:** (optional) Enter "dojo,dusk"
- **Count:** Leave as 1
- Click **"Generate Prompt Bundle(s)"**

### 3. Verify Output
You should see three sections:
- **📷 IMAGE PROMPT** - Full prompt for Leonardo (864×1536)
- **🎬 VIDEO MOTION BRIEF** - Motion description for Veo (6s)
- **📱 SOCIAL META** - Title, tags, hashtags (click "Show" to expand)

### 4. Copy Prompts
Click the **"Copy"** buttons for each section and paste into:
- Leonardo.ai (for image generation)
- Veo 3 (for video generation with motion)

## Verify Endpoints

### Health Check
```bash
curl http://localhost:8000/api/healthz
```

Expected response:
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

### Generate Bundle (CLI)
```bash
curl -X POST http://localhost:8000/api/prompts/bundle \
  -H "Content-Type: application/json" \
  -d '{"setting": "Japan", "seed_words": ["dojo"], "count": 1}'
```

### Recent Prompts
```bash
curl http://localhost:8000/api/prompts?limit=5
```

### Logs
```bash
curl http://localhost:8000/api/logs/tail?lines=20
```

### Verify Removed Endpoints Return 404
```bash
# These should all return 404:
curl http://localhost:8000/api/videos/pending
curl http://localhost:8000/api/scheduler/run-once
curl http://localhost:8000/api/images/pending
```

## Keyboard Shortcuts
- **Ctrl+P** - Focus Prompt Lab (always visible)
- **Ctrl+L** - Toggle Logs sidebar

## Troubleshooting

### "GROK_API_KEY missing" Error
- Check `.env` file exists in repo root
- Verify `GROK_API_KEY=your-key` is set (no quotes)
- Restart backend after changing `.env`

### "Module not found" Error
- Run `uv sync` in repo root
- Check Python version: `python --version` (should be 3.11+)

### Frontend Won't Start
- Check Node version: `node --version` (should be 18+)
- Run `npm install` in `frontend/` directory
- Delete `node_modules` and `package-lock.json`, then `npm install` again

### Backend Imports Fail
- Verify you're on `chore/prompt-lab-clean` branch: `git branch`
- Check deleted files are gone: `ls backend/app/clients/leonardo.py` (should not exist)

## Data Files

### Active Files (DO NOT DELETE)
- `app/data/persona.json` - Character identity
- `app/data/variety_bank.json` - Diversity banks
- `app/data/prompts/prompts.jsonl` - Generated prompt history (auto-created)
- `app/data/logs.txt` - Application logs

### Obsolete Files (Already Removed)
- `images.json`, `videos.json`, `video_queue.json`
- `history.json`, `diversity_usage.json`
- `posted/`, `deleted/`, `motion/` directories

## Next Steps

1. **Test the full workflow:**
   - Generate bundle for different settings (Santorini, Maldives, Tokyo)
   - Try seed words (sunset, golden hour, minimalist)
   - Copy prompts to Leonardo & Veo
   
2. **Customize persona:**
   - Edit `app/data/persona.json` to adjust character traits
   - Restart backend to apply changes

3. **Expand variety banks:**
   - Edit `app/data/variety_bank.json` to add new scenes/wardrobe
   - Add brand color palette (future feature)

4. **Review logs:**
   - Check `app/data/logs.txt` for API calls and errors
   - Use Logs sidebar in UI (Ctrl+L)

## Support

See `PROMPT_LAB_SUMMARY.md` for:
- Complete architecture documentation
- File changes summary
- API endpoint reference
- Troubleshooting guide

---

**Mode:** Prompt generation only (manual workflow)
**Zero automation. Fail-loud everywhere.**
