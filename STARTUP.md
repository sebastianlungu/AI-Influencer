# Startup Guide

## Ports Configuration

- **Backend:** `http://localhost:5001` (FastAPI + uvicorn)
- **Frontend:** `http://localhost:5000` (React + Vite)

All startup scripts automatically kill any processes using these ports before starting.

---

## Quick Start (Both Services)

### Unix/Mac
```bash
bash scripts/dev_run.sh
```

### Windows
```cmd
scripts\dev_run.bat
```

This starts both backend and frontend in separate terminal windows with automatic port cleanup.

---

## Individual Services

### Backend Only

**Unix/Mac:**
```bash
bash scripts/start_backend.sh
```

**Windows:**
```cmd
scripts\start_backend.bat
```

### Frontend Only

**Unix/Mac:**
```bash
bash scripts/start_frontend.sh
```

**Windows:**
```cmd
scripts\start_frontend.bat
```

---

## What the Scripts Do

1. **Port Cleanup:**
   - Searches for any process using the target port
   - Kills the process if found (Windows: `taskkill`, Unix/Mac: `kill -9`)
   - Waits 1 second for cleanup

2. **Service Start:**
   - Backend: `uv run uvicorn app.main:app --reload --port 5001 --host 0.0.0.0`
   - Frontend: `npm run dev` (configured to use port 5000 in `vite.config.js`)

3. **Access Points:**
   - Frontend UI: `http://localhost:5000`
   - Backend API: `http://localhost:5001`
   - API Docs: `http://localhost:5001/docs`

---

## Troubleshooting

### Port Already in Use

If you see "Address already in use" errors:

1. **Automatic (Recommended):** Just run the startup script again - it will kill existing processes
2. **Manual Kill:**
   - **Windows:** `netstat -ano | findstr :5001` → `taskkill /F /PID <PID>`
   - **Unix/Mac:** `lsof -ti:5001 | xargs kill -9`

### Permission Denied (Unix/Mac)

Make scripts executable:
```bash
chmod +x scripts/start_backend.sh
chmod +x scripts/start_frontend.sh
chmod +x scripts/dev_run.sh
```

### uv Command Not Found

Install UV package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### npm Command Not Found

Install Node.js (includes npm):
- **Unix/Mac:** `brew install node` or download from https://nodejs.org
- **Windows:** Download from https://nodejs.org

---

## Development Workflow

**Typical startup sequence:**

1. **First time setup:**
   ```bash
   # Install dependencies
   uv sync                    # Backend
   cd frontend && npm install # Frontend
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start services:**
   ```bash
   bash scripts/dev_run.sh  # Unix/Mac
   scripts\dev_run.bat       # Windows
   ```

4. **Access UI:**
   - Open `http://localhost:5000` in browser
   - Backend auto-proxies through Vite (no CORS issues)

5. **Stop services:**
   - **Unix/Mac:** `Ctrl+C` in terminal
   - **Windows:** Close the terminal windows

---

## Alternative: Manual Start

If you prefer not to use the scripts:

**Backend:**
```bash
cd ai-influencer
uv run uvicorn app.main:app --reload --port 5001
```

**Frontend:**
```bash
cd ai-influencer/frontend
npm run dev
```

**Note:** Manual start does NOT kill existing processes - you'll need to do that yourself if ports are in use.
