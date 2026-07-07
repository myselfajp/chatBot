#!/usr/bin/env bash
# Deploy the ChatBot Platform on a single public port.
# Builds the React panel into the backend's static tree (so the backend serves
# panel + API + widget on one port), then brings up Postgres + the app via
# docker compose (production).
#
# Requires: node/npm, docker + compose, and backend/.env (with BASE_URL + APP_PORT).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$ROOT/backend/.env" ]; then
  echo "ERROR: backend/.env is missing. Create it first (see backend/.env.example)."
  exit 1
fi

# The panel is served by the backend, so it uses same-origin API calls
# (VITE_API_BASE=""). This makes the build portable across host/port/proxy.
echo "==> Building panel (same-origin) ..."
cd "$ROOT/panel"
npm install --no-audit --no-fund
VITE_API_BASE="" npm run build -- \
  --outDir "$ROOT/backend/app/static/panel" --emptyOutDir

echo "==> Building & starting containers ..."
cd "$ROOT/backend"
docker compose -f docker-compose.prod.yml up --build -d

echo "==> Waiting for health ..."
APP_PORT="$(grep -E '^APP_PORT=' .env | cut -d= -f2- | tr -d '[:space:]' || true)"
APP_PORT="${APP_PORT:-8000}"
for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${APP_PORT}/v1/health" >/dev/null 2>&1; then
    echo "==> Healthy. App is live on port ${APP_PORT}."
    exit 0
  fi
  sleep 2
done
echo "WARN: health check did not pass yet; check: docker compose -f docker-compose.prod.yml logs -f app"
