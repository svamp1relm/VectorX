# VectorX — HTTP API

Базовый адрес локального demo: `http://127.0.0.1:8001`. OpenAPI доступен по `/docs` и `/openapi.json`.

## Общие правила

- JSON request/response; доменные ошибки — 400 с `{"detail":"..."}`.
- Pydantic validation и type mismatch — 422.
- Отсутствующий experiment/batch/run — 404.
- CSV path вне `VECTORX_DATA_ROOT` — 403.
- Тяжёлые операции синхронные; derived OOS/comparison/robustness результаты не сохраняются в БД.

## Experiments

- `POST /experiments` — запустить spec и сохранить эксперимент, 201.
- `POST /experiments/{id}/run` — повторить сохранённый spec как новый experiment, 201.
- `GET /experiments?offset=0&limit=100` — summary list, максимум 100 за страницу.
- `GET /experiments/{id}` — spec, metadata и summary.
- `GET /experiments/{id}/results?offset=0&limit=100` — метрики runs без equity.
- `GET /experiments/{id}/runs/{run_id}` — один run с downsampled equity.
- `GET /experiments/{id}/equity?run_id=0` — одна equity curve.
- `GET /experiments/{id}/analysis?seed=0&confidence=0.95` — gross/net CI, significance и
  risk-adjusted metrics. Требуется `store_trades=true`.
- `GET /experiments/{id}/export?format=json|markdown` — deterministic experiment report.

Monte Carlo YAML/JSON без `type` обратно совместимы и получают `type=monte_carlo`. Historical spec
использует `type=historical_backtest`, секции `data`, `strategy`, `portfolio`, `storage`.

## Batches

- `POST /batches` — сгенерировать sweep, выполнить и атомарно сохранить группу.
- `GET /batches` — список batches и число experiments.
- `GET /batches/{id}` — batch hypothesis/notes и summary входящих experiments.

Batch/sweep принимает `hypothesis`, optional `notes`, `base` и `grid` с dotted keys:

```json
{
  "hypothesis": "MA sensitivity",
  "base": {"type":"historical_backtest"},
  "grid": {"strategy.fast_period":[8,10,12]}
}
```

Пустые grid values и превышение preflight/aggregate limits отклоняются до запуска.

## OOS и comparisons

- `POST /out-of-sample` — historical `base`, train/test диапазоны с timezone. Возвращает два
  scored experiments, comparison, source/slice hashes и `executable_spec=false`.
- `POST /comparisons/expectancy` — `monte_carlo_experiment_id`, `historical_experiment_id`,
  `reference_risk_fraction`. Deltas вычисляются на общей шкале риска.

## Robustness

- `POST /robustness/sensitivity` — тот же `SweepSpec`, но без сохранения batch/experiments.
  Возвращает gross/net expectancy и Sharpe для каждой комбинации.
- `POST /robustness/walk-forward` — `base`, `start`, `end`, `train_window_days`,
  `test_window_days`, `step_days`, `reference_risk_fraction`.
- `GET /experiments/{id}/robustness/block-bootstrap` — параметры:
  - `block_size` — обязательный, помещается в каждый run;
  - `seed>=0`;
  - `0<confidence<1`;
  - `1<=n_resamples<=20000`;
  - `cost_basis=gross_r|net_r`.

Analysis/bootstrap имеют work budget; превышение возвращает 400 до ресэмплинга.

## Ограничения доступа

Auth и WebSocket отсутствуют по local research design. Не публикуйте API напрямую в сеть. PostgreSQL
demo bind — `127.0.0.1`; API CSV sandbox не заменяет полноценную внешнюю security-конфигурацию.
