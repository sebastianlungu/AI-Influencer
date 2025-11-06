@echo off
REM Frontend startup script with port cleanup for Windows
REM Kills any process on port 5173, then starts Vite dev server

setlocal enabledelayedexpansion

set PORT=5173
set FRONTEND_DIR=%~dp0..\frontend

echo.
echo 🧹 Checking for processes on port %PORT%...

REM Find PID using port 5000
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
echo 🚀 Starting frontend on http://localhost:%PORT%
echo    Working directory: %FRONTEND_DIR%
echo.

cd /d "%FRONTEND_DIR%"

REM Start Vite dev server
npm run dev
