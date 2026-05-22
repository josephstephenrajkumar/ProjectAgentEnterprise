#!/usr/bin/env bash
# =============================================================================
# stop.sh — ProjectAgentEnterprise Shutdown Script
#
# Gracefully stops the FastAPI backend and React frontend dev server.
# Run from the project root: bash stop.sh
# =============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/logs/pids.txt"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[STOP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log "ProjectAgentEnterprise — Stopping all services..."
echo ""

kill_port() {
  local PORT=$1
  local LABEL=$2
  local PIDS
  PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -SIGTERM 2>/dev/null || true
    sleep 1
    # Force kill if still running
    PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
      echo "$PIDS" | xargs kill -SIGKILL 2>/dev/null || true
    fi
    log "$LABEL stopped (port $PORT)"
  else
    warn "$LABEL was not running on port $PORT"
  fi
}

# ── Stop from PID file ───────────────────────────────────────────────────────

if [ -f "$PID_FILE" ]; then
  while IFS= read -r PID; do
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      kill -SIGTERM "$PID" 2>/dev/null || true
      log "Sent SIGTERM to PID $PID"
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

# ── Also kill by port (belt-and-suspenders) ──────────────────────────────────

sleep 1
kill_port 8000 "FastAPI Backend"
kill_port 5173 "React Frontend (Vite)"

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
log "All services stopped."
echo ""
echo -e "  💡 Restart with: ${GREEN}bash start.sh${NC}"
echo ""
