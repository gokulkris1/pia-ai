#!/usr/bin/env bash
# ── run.sh ───────────────────────────────────────────────────────────────────
# One-command startup for PIA local dev
# Usage: ./run.sh

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
VENV="$ROOT/.venv"
ENV_FILE="$ROOT/.env"

# ── 1. Copy .env if needed ────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "⚙  .env not found — copying from .env.example"
  cp "$ROOT/.env.example" "$ENV_FILE"
  echo "✏  Edit .env and add your API keys, then re-run this script."
  exit 1
fi

# ── 2. Create venv if needed ──────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
  echo "🐍  Creating virtual environment…"
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo "📦  Installing dependencies…"
pip install -q -r "$ROOT/requirements.txt"

# ── 4. Add avatar placeholder if needed ──────────────────────────────────────
AVATAR="$ROOT/frontend/avatar.jpg"
if [ ! -f "$AVATAR" ]; then
  echo "🖼  No avatar.jpg found in frontend/ — using initials placeholder."
  echo "    To add your photo: drop avatar.jpg into the frontend/ folder."
fi

# ── 5. Launch server ──────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🟢  PIA is starting…"
echo "  Open: http://localhost:8000"
echo "  Stop: Ctrl+C"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$BACKEND"
exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
