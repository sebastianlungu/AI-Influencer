#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT=5001
FRONTEND_PORT=5000

echo "🧹 Cleaning up ports..."

# Kill processes on backend port
if command -v lsof &> /dev/null; then
  PID=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "   Killing process on port $BACKEND_PORT..."
    kill -9 $PID 2>/dev/null || true
  fi

  # Kill processes on frontend port
  PID=$(lsof -ti:$FRONTEND_PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "   Killing process on port $FRONTEND_PORT..."
    kill -9 $PID 2>/dev/null || true
  fi
elif command -v fuser &> /dev/null; then
  fuser -k ${BACKEND_PORT}/tcp 2>/dev/null || true
  fuser -k ${FRONTEND_PORT}/tcp 2>/dev/null || true
fi

sleep 1

echo ""
echo "🚀 Starting AI Influencer dev environment..."
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Start backend
cd "$ROOT_DIR"
uv run uvicorn app.main:app --reload --port $BACKEND_PORT --host 0.0.0.0 &
PID1=$!

# Start frontend
cd "$ROOT_DIR/frontend"
npm run dev &
PID2=$!

# Cleanup on exit
trap "kill $PID1 $PID2 2>/dev/null || true" EXIT

echo "✅ Running... Press Ctrl+C to stop"
wait
