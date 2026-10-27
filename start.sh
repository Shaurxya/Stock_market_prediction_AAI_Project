#!/bin/bash
# Run the existing app. Analytics batches are intentionally separate.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PYTHON="$PROJECT_DIR/backend/venv/bin/python"
BACKEND_PID=''
FRONTEND_PID=''

if [ ! -x "$BACKEND_PYTHON" ] || [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
    echo 'Dependencies are missing. Run make install first (Python 3.11 required).'
    exit 1
fi
for port in 8000 5173; do
    if lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Port $port is already in use. Stop that server before starting this app."
        exit 1
    fi
done

cleanup() {
    trap - EXIT INT TERM
    [ -z "$BACKEND_PID" ] || kill "$BACKEND_PID" 2>/dev/null || true
    [ -z "$FRONTEND_PID" ] || kill "$FRONTEND_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$PROJECT_DIR"
"$BACKEND_PYTHON" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
ready=0
for attempt in {1..30}; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo 'Backend failed to start. Check the error above.'
        exit 1
    fi
    if curl --silent --fail http://127.0.0.1:8000/api/health >/dev/null; then
        ready=1
        break
    fi
    sleep 1
done
if [ "$ready" -ne 1 ]; then
    echo 'Backend did not become healthy within 30 seconds.'
    exit 1
fi

(cd "$PROJECT_DIR/frontend" && exec npm run dev -- --host 127.0.0.1 --strictPort) &
FRONTEND_PID=$!
echo 'StockAI: http://localhost:5173 · API docs: http://localhost:8000/docs'
echo 'Market Analytics: http://localhost:5173/analytics · Ctrl+C stops both servers.'
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
    sleep 1
done
echo 'A server stopped; shutting down the other server.'
exit 1
