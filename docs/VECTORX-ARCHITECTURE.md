# VectorX — текущая архитектура

Этот документ описывает состояние кода после remediation и improvement этапов. Исторические решения
и поэтапные отчёты остаются в исходных roadmap-документах.

## Назначение и границы

VectorX — локальная исследовательская платформа для Monte Carlo и historical backtesting. Она не
отправляет ордера и не подключается к биржам. FastAPI и Vue являются адаптерами над библиотекой,
а не источниками предметной логики.

## Основной data flow

```text
YAML / HTTP spec
       │
       ├── MonteCarloExperimentSpec ── derived RNG ── Trade[]
       │
       └── HistoricalBacktestExperimentSpec ── CSV ── Strategy ── Trade[]
                                                                  │
                                      PortfolioSimulator ─────────┘
                                             │
                                      Metrics / Summary
                                             │
                        ExperimentResult ────┴──── PostgreSQL
                                             │
                                   FastAPI read projections
                                             │
                                           Vue 3
```

Для OOS используется тот же runner на in-memory `MarketData`; отдельного backtest/statistics
конвейера не существует.

## Карта модулей

- `src/vectorx/core/` — immutable Trade/Metrics/Summary, ошибки, derived RNG.
- `src/vectorx/math/` — expectancy и общие R-функции.
- `src/vectorx/simulation/` — Monte Carlo и портфельное sizing/equity.
- `src/vectorx/marketdata/` — CSV snapshots, OHLCV validation, slicing, content hashes.
- `src/vectorx/strategy/` — Strategy Protocol, MA, Breakout, Buy&Hold, Random Entry.
- `src/vectorx/backtest/` — next-open historical execution.
- `src/vectorx/statistics/` — gross/net metrics, hist, CI, comparisons, risk-adjusted ratios.
- `src/vectorx/experiments/` — Pydantic specs, runner, sweep, OOS, export, versioning.
- `src/vectorx/robustness/` — sensitivity, walk-forward, by-run block bootstrap.
- `src/vectorx/storage/` — Protocol и PostgreSQL реализация с targeted reads.
- `api/` — сборка приложения, Pydantic HTTP-схемы, routers, serialization, data sandbox.
- `web/src/` — Vue-компоненты, typed fetch client, preferences и async analysis composable.

## HTTP-структура

`api/main.py` создаёт приложение, CORS и exception handler. Маршруты разделены:

- `api/routers/experiments.py` — CRUD, runs/equity, analysis, comparison, export;
- `api/routers/batches.py` — batches и sweep;
- `api/routers/robustness.py` — OOS, sensitivity, walk-forward, block bootstrap.

`api/data_paths.py` проверяет принадлежность CSV к `VECTORX_DATA_ROOT`; библиотечный CSV API остаётся
generic и не зависит от HTTP.

## PostgreSQL

Сущности: `experiment_batches`, `experiments`, `runs`, `trades`.

- Частые метрики хранятся колонками, остальные данные — JSONB.
- Raw trades создаются только при `storage.store_trades=true`.
- Список и batch detail используют summary-only SELECT и не загружают trades.
- Analysis читает один targeted SELECT: run index, gross R, net R.
- Raw trades вставляются bounded chunks.
- Batch и все его experiments записываются одной транзакцией.

## Версии и воспроизводимость

- package version — версия поставляемого продукта (`pyproject.toml`);
- `experiment_version=2` — схема и execution/metrics семантика;
- `analysis_version=2` — statistical/robustness алгоритмы;
- `code_version` — Git HEAD + hash фактических source inputs;
- `data_version` — SHA-256 именно обработанных CSV bytes;
- export содержит spec, summary, run results, source/data versions и dependency environment.

Полное окружение прямых и транзитивных зависимостей фиксируется в `uv.lock`.

## Тестовые уровни

- unit: math, simulation, strategies, statistics, robustness;
- integration: эфемерный PostgreSQL, round-trip, query count, bounded inserts;
- migration: upgrade/downgrade и чтение реальных v1 rows после upgrade;
- API: TestClient поверх реального PostgreSQL;
- frontend component: Vitest + Vue Test Utils;
- browser E2E: Playwright против изолированных PostgreSQL/API/Web на отдельных портах.
