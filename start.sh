#!/usr/bin/env bash
# =============================================================================
# start.sh — ProjectAgentEnterprise Startup Script
#
# Starts both the FastAPI backend and React frontend dev server.
# Run from the project root: bash start.sh
#
# Prerequisites:
#   - Python 3.10+ with miniconda3 available at ~/miniconda3
#   - Node.js 18+ available on PATH
#   - .env file configured at project root (copy from .env.example)
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"
LOG_DIR="$PROJECT_ROOT/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
PID_FILE="$LOG_DIR/pids.txt"
PYTHON="$HOME/miniconda3/bin/python3"
NPM="$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node/ 2>/dev/null | tail -1)/bin/npm"

# Fallback npm path detection
if ! command -v npm &>/dev/null 2>&1; then
  if [ -f "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.nvm"
    source "$NVM_DIR/nvm.sh"
  fi
fi

# Colours
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()   { echo -e "${GREEN}[START]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1";  }
error() { echo -e "${RED}[ERROR]${NC} $1";    }

# ── Preflight Checks ─────────────────────────────────────────────────────────

log "ProjectAgentEnterprise — Starting up..."
echo ""

mkdir -p "$LOG_DIR"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  warn ".env file not found. Copying from .env.example..."
  cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
  warn "Please edit .env and add your GROQ_API_KEY, then run start.sh again."
  exit 1
fi

if ! "$PYTHON" --version &>/dev/null 2>&1; then
  error "Python not found at $PYTHON"
  error "Please install miniconda3 or update the PYTHON path in start.sh"
  exit 1
fi

log "Python: $("$PYTHON" --version)"

# ── Database Initialisation ──────────────────────────────────────────────────

DATA_DIR="$PROJECT_ROOT/data"
DB_PATH="$DATA_DIR/openclaw.db"

mkdir -p "$DATA_DIR/docs"
mkdir -p "$DATA_DIR/chroma_db"

if [ ! -f "$DB_PATH" ]; then
  log "Database not found. Initialising SQLite schema..."
  PYTHONPATH="$PROJECT_ROOT" "$PYTHON" tools/init_sqlite_db.py
  log "Database initialised at $DB_PATH"
else
  log "Database found: $DB_PATH"
fi

# ── Start Backend (FastAPI) ──────────────────────────────────────────────────

log "Starting FastAPI backend on http://localhost:8000 ..."

PYTHONPATH="$PROJECT_ROOT/backend:$PROJECT_ROOT" \
  nohup "$PYTHON" -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  >> "$BACKEND_LOG" 2>&1 &

BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"
log "Backend PID: $BACKEND_PID (log: logs/backend.log)"

# Wait for backend to become healthy
MAX_WAIT=30
WAITED=0
printf "Waiting for backend"
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  printf "."
  sleep 1
  WAITED=$((WAITED + 1))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo ""
    error "Backend did not start within ${MAX_WAIT}s. Check logs/backend.log for errors."
    exit 1
  fi
done
echo ""
log "Backend is healthy ✅"

# ── Start Frontend (React/Vite) ──────────────────────────────────────────────

FRONTEND_DIR="$PROJECT_ROOT/frontend-react"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  log "Installing frontend npm dependencies..."
  (cd "$FRONTEND_DIR" && npm install >> "$FRONTEND_LOG" 2>&1)
  log "Frontend dependencies installed."
fi

log "Starting React frontend on http://localhost:5173 ..."

cd "$FRONTEND_DIR" && nohup node node_modules/vite/bin/vite.js < /dev/null >> "$FRONTEND_LOG" 2>&1 &

FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"
log "Frontend PID: $FRONTEND_PID (log: logs/frontend.log)"

sleep 3

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}  ProjectAgentEnterprise is running!                   ${NC}"
echo -e "${GREEN}=======================================================${NC}"
echo ""
echo -e "  🌐 Frontend:  ${GREEN}http://localhost:5173${NC}"
echo -e "  ⚙️  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  📖 API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  ❤️  Health:    ${GREEN}http://localhost:8000/health${NC}"
echo ""
echo -e "  📄 Logs:      logs/backend.log   logs/frontend.log"
echo -e "  🛑 To stop:   ${YELLOW}bash stop.sh${NC}"
echo ""
