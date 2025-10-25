@echo off
echo Starting AI Influencer dev environment...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.

set PYTHONPATH=backend

start "Backend" cmd /k "cd backend && uvicorn app.main:app --reload --port 8000"
start "Frontend" cmd /k "cd frontend && npm run dev"

echo Running... Close the terminal windows to stop
