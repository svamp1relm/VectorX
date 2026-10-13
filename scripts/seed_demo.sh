#!/usr/bin/env bash
# Наполняет поднятый стек (scripts/demo-up.sh) содержательными демо-данными:
# Monte Carlo baseline, 3 исторических бэктеста (BTC/ETH/SOL, с raw trades —
# для Statistical Analysis), один "быстрый" без raw trades (для контраста),
# batch sweep и прогон out-of-sample (результат OOS не хранится — печатаем
# готовые значения для формы в UI в конце).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="$ROOT_DIR/.demo"
if [[ -f "$RUN_DIR/demo.env" ]]; then
  # shellcheck disable=SC1091
  source "$RUN_DIR/demo.env"
fi

: "${VECTORX_API_PORT:=8000}"
: "${VECTORX_API_BASE:=http://127.0.0.1:${VECTORX_API_PORT}}"
export VECTORX_DATABASE_URL VECTORX_CORS_ORIGINS VECTORX_API_PORT VECTORX_WEB_PORT VITE_API_BASE VECTORX_API_BASE

if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

if ! curl -sf "$VECTORX_API_BASE/experiments" >/dev/null 2>&1; then
  echo "API на $VECTORX_API_BASE не отвечает — сначала scripts/demo-up.sh или задайте VECTORX_API_BASE." >&2
  exit 1
fi

# Берёт самый свежий id эксперимента с данным именем из GET /experiments.
experiment_id_by_name() {
  curl -sf "$VECTORX_API_BASE/experiments" | python3 -c "
import json, sys
name = sys.argv[1]
items = [item['id'] for item in json.load(sys.stdin) if item['name'] == name]
if items:
    print(max(items))
" "$1"
}

run_experiment_once() {
  local label="$1" config="$2" name="$3" existing_id
  existing_id="$(experiment_id_by_name "$name")"
  if [[ -n "$existing_id" ]]; then
    echo "==> $label: уже есть (id=$existing_id), пропускаю"
    return
  fi
  echo "==> $label"
  vectorx run "$config"
}

run_experiment_once \
  "Monte Carlo: expectancy_test.yaml" \
  configs/experiments/expectancy_test.yaml \
  baseline_expectancy

run_experiment_once \
  "Historical (с raw trades): btc_1h.yaml" \
  configs/experiments/btc_1h.yaml \
  btc_1h_ma_crossover

run_experiment_once \
  "Historical (с raw trades): eth_1h.yaml" \
  configs/experiments/eth_1h.yaml \
  eth_1h_ma_crossover

run_experiment_once \
  "Historical (с raw trades): sol_1h.yaml" \
  configs/experiments/sol_1h.yaml \
  sol_1h_ma_crossover

run_experiment_once \
  "Historical (без raw trades, для контраста): ma_crossover_example.yaml" \
  configs/experiments/ma_crossover_example.yaml \
  ma_crossover_btc_1h_demo

batch_hypothesis="MA crossover: чувствительность к fast/slow period на BTC 1h"
batch_id="$(curl -sf "$VECTORX_API_BASE/batches" | python3 -c "
import json, sys
hypothesis = sys.argv[1]
items = [item['id'] for item in json.load(sys.stdin) if item['hypothesis'] == hypothesis]
if items:
    print(max(items))
" "$batch_hypothesis")"

if [[ -n "$batch_id" ]]; then
  echo "==> Batch sweep: уже есть (id=$batch_id), пропускаю"
else
  echo "==> Batch sweep: fast/slow period 3x3 на BTC 1h"
  batch_id="$(curl -sf -X POST "$VECTORX_API_BASE/batches" \
    -H 'Content-Type: application/json' \
    -d '{
      "hypothesis": "MA crossover: чувствительность к fast/slow period на BTC 1h",
      "notes": "демо-батч для показа",
      "base": {
        "name": "btc_1h_sweep",
        "type": "historical_backtest",
        "data": {"path": "configs/experiments/data/btc_1h.csv", "symbol": "BTCUSDT", "timeframe": "1h"},
        "strategy": {"fast_period": 10, "slow_period": 30, "stop_loss_pct": 0.01},
        "portfolio": {"initial_capital": 10000, "risk_per_trade": 0.01}
      },
      "grid": {
        "strategy.fast_period": [5, 10, 15],
        "strategy.slow_period": [20, 30, 40]
      }
    }' | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"
  echo "   batch создан (id=$batch_id, 9 экспериментов)"
fi

hist_id="$(experiment_id_by_name btc_1h_ma_crossover)"
train_start="2024-09-27T00:00:00+00:00"
train_end="2025-09-26T23:00:00+00:00"
test_start="2025-09-27T00:00:00+00:00"
test_end="2026-09-27T19:00:00+00:00"

echo "==> Out-of-sample (проверка): BTC 1h, train/test non-overlapping split"
curl -sf -X POST "$VECTORX_API_BASE/out-of-sample" \
  -H 'Content-Type: application/json' \
  -d "{
    \"base\": {
      \"name\": \"btc_1h_oos\",
      \"type\": \"historical_backtest\",
      \"data\": {\"path\": \"configs/experiments/data/btc_1h.csv\", \"symbol\": \"BTCUSDT\", \"timeframe\": \"1h\"},
      \"strategy\": {\"fast_period\": 10, \"slow_period\": 30, \"stop_loss_pct\": 0.01},
      \"portfolio\": {\"initial_capital\": 10000, \"risk_per_trade\": 0.01}
    },
    \"train_start\": \"$train_start\",
    \"train_end\": \"$train_end\",
    \"test_start\": \"$test_start\",
    \"test_end\": \"$test_end\"
  }" > /dev/null
echo "   out-of-sample отработал без ошибок (результат derived, не хранится — см. ниже)"

mc_id="$(experiment_id_by_name baseline_expectancy)"
echo "==> Comparison: Monte Carlo vs Historical expectancy"
curl -sf -X POST "$VECTORX_API_BASE/comparisons/expectancy" \
  -H 'Content-Type: application/json' \
  -d "{\"monte_carlo_experiment_id\": $mc_id, \"historical_experiment_id\": $hist_id}" > /dev/null
echo "   сравнение посчитано"

cat <<EOF

Готово. Демо-данные засеяны:
  - Monte Carlo baseline (baseline_expectancy, id=$mc_id)
  - Historical с raw trades: BTC / ETH / SOL 1h (btc_1h_ma_crossover id=$hist_id и др.)
  - Historical без raw trades (ma_crossover_btc_1h_demo) — для контраста в Statistical Analysis
  - Batch: 3x3 sweep fast/slow period на BTC (id=$batch_id, вкладка Batches)
  - Comparison Monte Carlo vs Historical уже посчитан (откройте id=$mc_id или id=$hist_id →
    "Сравнение математического ожидания")

Для вкладки Out-of-Sample в UI (форма, результат не персистится — заполните вручную):
  base experiment id: $hist_id
  train_start:        $train_start
  train_end:           $train_end
  test_start:          $test_start
  test_end:            $test_end

Откройте web UI (URL см. в выводе scripts/demo-up.sh) и пройдитесь по вкладкам.
EOF
