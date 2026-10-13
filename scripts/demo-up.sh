#!/usr/bin/env bash
# Поднимает весь стек VectorX одной командой: Postgres (docker compose) + миграции +
# API (uvicorn) + web (vite dev), оба процесса в фоне с логами в .demo/.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="$ROOT_DIR/.demo"
mkdir -p "$RUN_DIR"

: "${VECTORX_DATABASE_URL:=postgresql+psycopg://vectorx:vectorx@localhost:5432/vectorx}"
: "${VECTORX_API_PORT:=8000}"
: "${VECTORX_WEB_PORT:=5173}"
: "${VECTORX_CORS_ORIGINS:=http://localhost:${VECTORX_WEB_PORT},http://127.0.0.1:${VECTORX_WEB_PORT}}"
# Если VECTORX_API_PORT переопределён, фронтенд должен узнать об этом тем же способом —
# иначе он молча продолжит стучаться в дефолтный 8000 (Vite подхватывает VITE_* из env).
: "${VITE_API_BASE:=http://127.0.0.1:${VECTORX_API_PORT}}"
export VECTORX_DATABASE_URL VECTORX_CORS_ORIGINS VECTORX_API_PORT VECTORX_WEB_PORT VITE_API_BASE

demo_process_running() {
  local pid="$1" expected="$2" command_line state
  kill -0 "$pid" 2>/dev/null || return 1
  state="$(ps -p "$pid" -o stat= 2>/dev/null | tr -d ' ')"
  [[ -n "$state" && "$state" != Z* ]] || return 1
  command_line="$(ps -p "$pid" -o command= 2>/dev/null)"
  [[ "$command_line" == *"$expected"* ]]
}

if [[ -f "$RUN_DIR/api.pid" ]] && demo_process_running "$(cat "$RUN_DIR/api.pid")" "uvicorn api.main:app"; then
  echo "Похоже, демо уже запущено (api.pid живой). Сначала выполните scripts/demo-down.sh." >&2
  exit 1
fi
rm -f "$RUN_DIR/api.pid" "$RUN_DIR/web.pid"

# demo-up.sh и seed_demo.sh запускаются разными shell-процессами, поэтому сохраняем
# итоговые значения для последующего заполнения без ручного повторного export.
{
  printf 'export VECTORX_DATABASE_URL=%q\n' "$VECTORX_DATABASE_URL"
  printf 'export VECTORX_CORS_ORIGINS=%q\n' "$VECTORX_CORS_ORIGINS"
  printf 'export VECTORX_API_PORT=%q\n' "$VECTORX_API_PORT"
  printf 'export VECTORX_WEB_PORT=%q\n' "$VECTORX_WEB_PORT"
  printf 'export VITE_API_BASE=%q\n' "$VITE_API_BASE"
} >"$RUN_DIR/demo.env"

echo "==> Postgres (docker compose)"
docker compose up -d postgres

echo "==> Жду готовности Postgres..."
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U vectorx -d vectorx >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! docker compose exec -T postgres pg_isready -U vectorx -d vectorx >/dev/null 2>&1; then
  echo "Postgres не ответил за 30 секунд." >&2
  exit 1
fi

if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

echo "==> Alembic upgrade head"
alembic upgrade head

echo "==> Запускаю API (uvicorn) в фоне, лог: .demo/api.log"
# setsid (без --fork, без set -m) exec'ает команду напрямую — $! = PID самой команды,
# она же становится лидером своей process group (надёжный kill -PID в demo-down.sh).
setsid nohup uvicorn api.main:app --port "$VECTORX_API_PORT" >"$RUN_DIR/api.log" 2>&1 &
echo $! >"$RUN_DIR/api.pid"
disown

echo "==> Жду, пока API реально ответит (не только запустится)..."
api_up=
api_pid="$(cat "$RUN_DIR/api.pid")"
for _ in $(seq 1 20); do
  # Проверяем, что порт держит ИМЕННО наш pid, а не чужой/ранее запущенный процесс на том же
  # порту (curl бы достучался и до него — ложный "успех"; kill -0 тоже ненадёжен: сразу после
  # падения на bind-конфликте процесс недолго висит зомби и всё ещё отвечает на kill -0).
  if ss -ltnp 2>/dev/null | grep -q ":${VECTORX_API_PORT} .*pid=${api_pid}," \
     && curl -sf "http://127.0.0.1:${VECTORX_API_PORT}/experiments" >/dev/null 2>&1; then
    api_up=1
    break
  fi
  kill -0 "$api_pid" 2>/dev/null || break
  sleep 0.5
done
if [[ -z "$api_up" ]]; then
  echo "API не поднялся на http://127.0.0.1:${VECTORX_API_PORT} — последние строки лога:" >&2
  tail -n 20 "$RUN_DIR/api.log" >&2
  echo "Частая причина: порт уже занят другим процессом (своим же вручную запущенным uvicorn" >&2
  echo "или сторонним) — остановите его или переопределите VECTORX_API_PORT." >&2
  rm -f "$RUN_DIR/api.pid"
  exit 1
fi

echo "==> Запускаю web (vite dev) в фоне, лог: .demo/web.log"
# cd + exec в одной подоболочке: сама подоболочка подменяется на setsid/npm,
# лишнего висящего bash-процесса не остаётся; $! берётся снаружи, одним фоновым заданием.
(cd "$ROOT_DIR/web" && exec setsid nohup npm run dev -- --host 127.0.0.1 --port "$VECTORX_WEB_PORT" --strictPort >"$RUN_DIR/web.log" 2>&1) &
echo $! >"$RUN_DIR/web.pid"
disown

echo "==> Жду, пока web dev server выведет свой реальный URL..."
web_url=
for _ in $(seq 1 30); do
  web_url="$(grep -oE 'Local:\s+http://[^[:space:]]+' "$RUN_DIR/web.log" 2>/dev/null | head -1 | grep -oE 'http://[^[:space:]]+' || true)"
  [[ -n "$web_url" ]] && break
  sleep 0.5
done
if [[ -z "$web_url" ]]; then
  echo "Vite dev server не вывел URL за 15 секунд — последние строки лога:" >&2
  tail -n 20 "$RUN_DIR/web.log" >&2
  exit 1
fi

cat <<EOF

Стек поднят:
  API  http://127.0.0.1:${VECTORX_API_PORT}
  Web  $web_url

Логи: $RUN_DIR/api.log, $RUN_DIR/web.log
Заполнить демо-данными: scripts/seed_demo.sh
Остановить: scripts/demo-down.sh
EOF
