#!/bin/bash
# ============================================================
#  Stock Market Prediction System — Start Script
#  Runs both backend (FastAPI) and frontend (Vite) together.
#
#  Usage:   ./start.sh
#  Stop:    Ctrl+C (kills both servers)
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Colors for pretty output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  📈 Stock Market Prediction System${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Kill any existing process on port 8000 ───────────────────
if lsof -ti:8000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8000 in use. Killing existing process...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# ── Trap Ctrl+C to kill both processes ───────────────────────
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✅ All servers stopped.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Start Backend ────────────────────────────────────────────
echo -e "${GREEN}🚀 Starting Backend (FastAPI on port 8000)...${NC}"
(
    cd "$BACKEND_DIR"
    source venv/bin/activate
    uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

# Give the backend a moment to start
sleep 2

# ── Start Frontend ───────────────────────────────────────────
echo -e "${GREEN}🚀 Starting Frontend (Vite dev server)...${NC}"
(
    cd "$FRONTEND_DIR"
    npm run dev
) &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Both servers are running!${NC}"
echo -e "${CYAN}  Backend  → http://localhost:8000${NC}"
echo -e "${CYAN}  Frontend → http://localhost:5173${NC}"
echo -e "${CYAN}  API Docs → http://localhost:8000/docs${NC}"
echo -e "${YELLOW}  Press Ctrl+C to stop both servers${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
