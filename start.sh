#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${TALENTNET_BACKEND_PORT:-8015}"
FRONTEND_PORT="${TALENTNET_FRONTEND_PORT:-3025}"
PYTHON_BIN="$ROOT/backend/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  "${PYTHON:-python3}" -m venv "$ROOT/backend/.venv"
fi
if ! "$PYTHON_BIN" -c 'import fastapi, docx, pypdf, openpyxl' 2>/dev/null; then
  "$PYTHON_BIN" -m pip install -r "$ROOT/backend/requirements.txt"
fi
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm ci)
fi

(cd "$ROOT/frontend" && NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$BACKEND_PORT" npm run build)

if command -v lsof >/dev/null 2>&1; then
  for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    if lsof -i ":$port" >/dev/null 2>&1; then
      echo "Port $port is already in use." >&2
      exit 1
    fi
  done
fi

(cd "$ROOT/backend" && TALENTNET_DATABASE_URL=sqlite:///./talentnet-local-demo.db "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT") &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT
echo "TalentNet: http://127.0.0.1:$FRONTEND_PORT"
echo "API health: http://127.0.0.1:$BACKEND_PORT/api/health"
(cd "$ROOT/frontend" && NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$BACKEND_PORT" npm run start -- --hostname 127.0.0.1 --port "$FRONTEND_PORT")
