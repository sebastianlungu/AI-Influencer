@echo off
setlocal enabledelayedexpansion

set BACKEND_PORT=5001
set FRONTEND_PORT=5000

echo.
echo 🧹 Cleaning up ports...

REM Kill process on backend port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% "') do (
    set PID=%%a
    if not "!PID!"=="" (
        if not "!PID!"=="0" (
            echo    Killing process on port %BACKEND_PORT%...
            taskkill /F /PID !PID! >nul 2>&1
        )
    )
)

REM Kill process on frontend port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT% "') do (
    set PID=%%a
    if not "!PID!"=="" (
        if not "!PID!"=="0" (
            echo    Killing process on port %FRONTEND_PORT%...
            taskkill /F /PID !PID! >nul 2>&1
        )
    )
)

timeout /t 1 /nobreak >nul

echo.
echo 🚀 Starting AI Influencer dev environment...
echo    Backend:  http://localhost:%BACKEND_PORT%
echo    Frontend: http://localhost:%FRONTEND_PORT%
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..

REM Start backend in new window
start "Backend (Port %BACKEND_PORT%)" cmd /k "cd /d "%ROOT_DIR%" && uv run uvicorn app.main:app --reload --port %BACKEND_PORT% --host 0.0.0.0"

REM Start frontend in new window
start "Frontend (Port %FRONTEND_PORT%)" cmd /k "cd /d "%ROOT_DIR%\frontend" && npm run dev"

echo.
echo ✅ Running... Close the terminal windows to stop
echo.
