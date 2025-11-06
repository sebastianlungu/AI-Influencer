#!/usr/bin/env bash
# Frontend startup script with port cleanup
# Kills any process on port 5173, then starts Vite dev server

set -e  # Exit on error

PORT=5173
FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

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
echo "🚀 Starting frontend on http://localhost:$PORT"
echo "   Working directory: $FRONTEND_DIR"
echo ""

cd "$FRONTEND_DIR"

# Start Vite dev server
npm run dev
