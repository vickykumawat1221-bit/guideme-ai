#!/usr/bin/env bash
# Start GuideMe AI: Django API + a static frontend server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pick_port() {
  local port="$1"
  while lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  echo "$port"
}

BACKEND_PORT="$(pick_port "${BACKEND_PORT:-8000}")"
FRONTEND_PORT="$(pick_port "${FRONTEND_PORT:-5501}")"

cd "$ROOT/django-backend"

if ! python3 -c "import django, sentence_transformers" >/dev/null 2>&1; then
  echo "Installing dependencies…"
  python3 -m pip install -r requirements.txt
fi

python3 manage.py migrate --noinput
python3 manage.py seed_demo

# Tell the static frontend which API origin to use.
cat > "$ROOT/frontend/config.js" <<EOF
window.GM_API_BASE = "http://127.0.0.1:${BACKEND_PORT}";
EOF

echo ""
echo "  API      → http://127.0.0.1:${BACKEND_PORT}/api/"
echo "  Frontend → http://127.0.0.1:${FRONTEND_PORT}/index.html"
echo ""
echo "  Demo login: demo@guideme.ai / demo12345"
echo ""

python3 manage.py runserver "127.0.0.1:${BACKEND_PORT}" &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
python3 -m http.server "$FRONTEND_PORT" --bind 127.0.0.1
