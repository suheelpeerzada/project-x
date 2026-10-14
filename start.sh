#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=== Project-X: starting ==="

# ---- Backend ----
cd backend
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

uvicorn app.main:app --reload &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null' EXIT INT TERM
cd ..

# ---- Frontend ----
cd frontend
if [ ! -d node_modules ]; then
  echo "Installing frontend packages..."
  npm install
fi
echo "Starting frontend..."
npm run dev
