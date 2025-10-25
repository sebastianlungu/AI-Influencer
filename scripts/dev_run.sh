#!/usr/bin/env bash
set -euo pipefail

echo "Starting AI Influencer dev environment..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""

# Set PYTHONPATH
export PYTHONPATH=backend

# Start backend
cd backend
uvicorn app.main:app --reload --port 8000 &
PID1=$!

# Start frontend
cd ../frontend
npm run dev &
PID2=$!

# Cleanup on exit
trap "kill $PID1 $PID2 2>/dev/null || true" EXIT

echo "Running... Press Ctrl+C to stop"
wait
