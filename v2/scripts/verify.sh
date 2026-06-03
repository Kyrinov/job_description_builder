#!/usr/bin/env bash
# verify.sh — check the 5 Phase 10 success criteria. Exits 0 on pass.
set -uo pipefail

V2_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$V2_DIR"

# Pick an open port for the backend (8000 may be in use)
BACKEND_PORT=8765
DB_PATH="/tmp/verify-jd-$$.db"
PROJECT_ROOT="/tmp"

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /tmp/verify-out.log 2>&1; then
    echo "  ✓ $name"
    PASS=$((PASS+1))
  else
    echo "  ✗ $name"
    sed 's/^/      /' /tmp/verify-out.log | head -5
    FAIL=$((FAIL+1))
  fi
}

cleanup() {
  pkill -f "uvicorn app.main:app --port $BACKEND_PORT" 2>/dev/null || true
  pkill -f "uvicorn app.main:app --port 8000" 2>/dev/null || true
  pkill -f "vite" 2>/dev/null || true
  rm -f "$DB_PATH" 2>/dev/null || true
}
trap cleanup EXIT

# Pre-cleanup: kill any leftover uvicorn/vite from prior sessions so the
# script is self-contained (does not depend on a clean port state).
cleanup

echo ""
echo "=== Phase 10 verification ==="
echo ""

# Criterion 4 first: SQLite schema (doesn't need a running server)
echo "[Criterion 4: SQLite schema]"
check "DB_PATH is created on startup" \
  "cd $V2_DIR/backend && DB_PATH=$DB_PATH PROJECT_ROOT=$PROJECT_ROOT python -c 'from app.config import Settings; from app.db import get_connection, create_schema; s=Settings(); con=get_connection(s.db_path); create_schema(con); import sqlite3; rows=con.execute(\"SELECT name FROM sqlite_master WHERE type=\\\"table\\\"\").fetchall(); names={r[0] for r in rows}; assert \"work_descriptions\" in names and \"audit_log\" in names, names'"

# Criterion 5: Pydantic models
echo ""
echo "[Criterion 5: Pydantic models]"
check "5 models importable from app.models" \
  "cd $V2_DIR/backend && python -c 'from app.models import WorkDescription, DraftDuty, Classification, JESFactor, QualificationStandard; print(\"all 5 models OK\")'"

# Criterion 1: Backend /api/health
echo ""
echo "[Criterion 1: Backend /api/health]"
cd "$V2_DIR/backend"
DB_PATH="$DB_PATH" PROJECT_ROOT="$PROJECT_ROOT" nohup uvicorn app.main:app --port "$BACKEND_PORT" > /tmp/uvi-verify.log 2>&1 < /dev/null &
disown
UVI_PID=$!
# Wait for server to be ready
for i in {1..15}; do
  if curl -s "http://localhost:$BACKEND_PORT/api/health" > /dev/null 2>&1; then break; fi
  sleep 0.5
done
check "GET /api/health returns 200" \
  "curl -s -o /dev/null -w '%{http_code}' http://localhost:$BACKEND_PORT/api/health | grep -q '^200$'"
check "GET /api/health body is {status: ok}" \
  "curl -s http://localhost:$BACKEND_PORT/api/health | grep -q '\"status\":\"ok\"'"
kill $UVI_PID 2>/dev/null || true
wait $UVI_PID 2>/dev/null || true

# Criterion 2 + 3: Frontend dev server + Vite proxy
echo ""
echo "[Criterion 2: Vite dev server]"
cd "$V2_DIR/frontend"
nohup npm run dev > /tmp/vite-verify.log 2>&1 < /dev/null &
disown
VITE_PID=$!
for i in {1..30}; do
  if curl -s http://localhost:5173 > /dev/null 2>&1; then break; fi
  sleep 0.5
done
check "Vite serves on :5173" \
  "curl -s -o /dev/null -w '%{http_code}' http://localhost:5173 | grep -q '^200$'"
check "Vite serves index.html with 'JD Builder' title" \
  "curl -s http://localhost:5173 | grep -q 'JD Builder'"

# Criterion 3: Vite proxy
echo ""
echo "[Criterion 3: Vite proxy /api -> :8000]"
# Restart backend on 8000 for the proxy test
cd "$V2_DIR/backend"
DB_PATH="$DB_PATH" PROJECT_ROOT="$PROJECT_ROOT" nohup uvicorn app.main:app --port 8000 > /tmp/uvi-verify2.log 2>&1 < /dev/null &
disown
UVI_PID2=$!
for i in {1..15}; do
  if curl -s "http://localhost:8000/api/health" > /dev/null 2>&1; then break; fi
  sleep 0.5
done
check "Vite proxies /api/health to backend" \
  "curl -s http://localhost:5173/api/health | grep -q '\"status\":\"ok\"'"
kill $UVI_PID2 2>/dev/null || true
wait $UVI_PID2 2>/dev/null || true
kill $VITE_PID 2>/dev/null || true
wait $VITE_PID 2>/dev/null || true

echo ""
echo "=== Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
