#!/usr/bin/env bash
# Запускает изолированный demo-стек на отдельных портах и выполняет browser E2E.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export COMPOSE_PROJECT_NAME=vectorx-e2e
export VECTORX_DEMO_RUN_DIR="$ROOT_DIR/.demo-e2e"
export VECTORX_POSTGRES_PORT=56432
export VECTORX_DATABASE_URL="postgresql+psycopg://vectorx:vectorx@localhost:${VECTORX_POSTGRES_PORT}/vectorx"
export VECTORX_API_PORT=8002
export VECTORX_WEB_PORT=5183
export VITE_API_BASE="http://127.0.0.1:${VECTORX_API_PORT}"
export E2E_API_BASE="$VITE_API_BASE"
export E2E_WEB_URL="http://127.0.0.1:${VECTORX_WEB_PORT}"

cleanup() {
  "$ROOT_DIR/scripts/demo-down.sh" >/dev/null 2>&1 || true
}
cleanup
trap cleanup EXIT

./scripts/demo-up.sh
./scripts/seed_demo.sh
cd web
npm run test:e2e
