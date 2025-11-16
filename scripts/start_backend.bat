@echo off
REM Backend startup script with port cleanup for Windows
REM Kills any process on port 8000, then starts FastAPI server

setlocal enabledelayedexpansion

set PORT=8000
set BACKEND_DIR=%~dp0..\backend

echo.
echo 🧹 Checking for processes on port %PORT%...

REM Find PID using port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% "') do (
    set PID=%%a
    if not "!PID!"=="" (
        if not "!PID!"=="0" (
            echo    Found process !PID! on port %PORT%, killing...
            taskkill /F /PID !PID! >nul 2>&1
        )
    )
)

REM Wait for cleanup
timeout /t 1 /nobreak >nul

echo    Port %PORT% is now free
echo.
echo 🚀 Starting backend on http://localhost:%PORT%
echo    Working directory: %BACKEND_DIR%
echo.

cd /d "%BACKEND_DIR%"

REM Start FastAPI with uvicorn
uv run uvicorn app.main:app --reload --port %PORT% --host 0.0.0.0
