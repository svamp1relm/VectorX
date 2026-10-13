#!/usr/bin/env bash
# Останавливает процессы, поднятые scripts/demo-up.sh (API, web) и гасит Postgres.
# Volume с данными не удаляется (без -v), чтобы демо-данные сохранялись между показами.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="$ROOT_DIR/.demo"

stop_pid_file() {
  local name="$1" pid_file="$RUN_DIR/$1.pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "==> Останавливаю $name (pid $pid)"
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
}

stop_pid_file api
stop_pid_file web

echo "==> Останавливаю Postgres (docker compose down, данные сохраняются)"
docker compose down

echo "Готово."
