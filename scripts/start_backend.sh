#!/usr/bin/env bash
# Backend startup script with port cleanup
# Kills any process on port 8765, then starts FastAPI server

set -e  # Exit on error

PORT=8765
BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🧹 Checking for processes on port $PORT..."

# Find and kill process on port (macOS/Linux compatible)
if command -v lsof &> /dev/null; then
  # macOS/Linux with lsof
  PID=$(lsof -ti:$PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "   Found process $PID on port $PORT, killing..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
  else
    echo "   Port $PORT is free"
  fi
else
  # Fallback for Linux without lsof (use fuser)
  if command -v fuser &> /dev/null; then
    fuser -k ${PORT}/tcp 2>/dev/null || true
    sleep 1
  fi
fi

echo ""
echo "🚀 Starting backend on http://localhost:$PORT"
echo "   Working directory: $BACKEND_DIR"
echo ""

cd "$BACKEND_DIR"

# Start FastAPI with uvicorn
uv run uvicorn app.main:app --reload --port $PORT --host 0.0.0.0
