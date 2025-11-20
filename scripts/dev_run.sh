#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT=3590
FRONTEND_PORT=3589

echo "🧹 Cleaning up ports..."

# Function to kill process on a port (cross-platform)
kill_port() {
  local PORT=$1
  local PORT_NAME=$2

  if command -v lsof &> /dev/null; then
    # Unix/Mac
    PID=$(lsof -ti:$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
      echo "   Killing process on port $PORT ($PORT_NAME)..."
      kill -9 $PID 2>/dev/null || true
    fi
  elif command -v fuser &> /dev/null; then
    # Linux
    fuser -k ${PORT}/tcp 2>/dev/null || true
  elif command -v netstat &> /dev/null; then
    # Windows (Git Bash)
    PID=$(netstat -ano | grep ":$PORT " | grep "LISTENING" | awk '{print $5}' | head -1)
    if [ -n "$PID" ] && [ "$PID" != "0" ]; then
      echo "   Killing process on port $PORT ($PORT_NAME)..."
      taskkill //F //PID "$PID" 2>/dev/null || true
    fi
  fi
}

# Kill processes on both ports
kill_port $BACKEND_PORT "backend"
kill_port $FRONTEND_PORT "frontend"

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
cd "$ROOT_DIR/backend"
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
