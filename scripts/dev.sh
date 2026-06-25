#!/usr/bin/env bash
# dev.sh — start backend + frontend concurrently. Ctrl-C tears down both.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Trap Ctrl-C to kill both children
cleanup() {
  echo ""
  echo "Stopping..."
  kill "${BACKEND_PID:-0}" 2>/dev/null || true
  kill "${FRONTEND_PID:-0}" 2>/dev/null || true
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

# Start backend
echo "Starting backend on :8000..."
(cd backend && uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on :5173..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "✓ Backend:  http://localhost:8000/api/health"
echo "✓ Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl-C to stop both."

# Wait for either to exit
wait
