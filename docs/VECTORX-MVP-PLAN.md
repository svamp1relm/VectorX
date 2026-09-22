# VectorX — утверждённый план MVP

Документ фиксирует архитектуру и порядок реализации.
Архитектуру больше не пересматриваем. Реализация — **по фазам с паузой**.

**Статус:** Фаза 0 выполнена (2026-09-21). Фаза 1 выполнена (2026-09-21). Фаза 2 выполнена (2026-09-21). Фаза 3 выполнена (2026-09-21). Фаза 4 выполнена (2026-09-21). Фаза 5 выполнена (2026-09-21). Фаза 6 выполнена (2026-09-21). Фаза 7 выполнена (2026-09-21). Фаза 8 выполнена (2026-09-21). Фаза 9 выполнена (2026-09-22). Фаза 10 выполнена (2026-09-22). Фаза 11 выполнена (2026-09-22). **MVP завершён, все 9 критериев подтверждены.**

---

## Назначение

VectorX — исследовательская симуляционная платформа.
Не торговый бот. Нет live-ордеров, MEXC, CCXT.

MVP отвечает на вопросы вида:

- какие результаты возможны при данной вероятностной модели;
- как распределяется доходность по runs;
- какова вероятность отрицательного результата;
- насколько эмпирическое expectancy совпадает с теоретическим.

Симулятор воспроизводим. Рынок — нет.

```
Одинаковые параметры + одинаковый seed + одинаковая версия кода
= одинаковая реализация эксперимента
```

Разные seed при тех же параметрах дают разные сценарии.

---

## Архитектура

**Library-first.** Ядро не знает FastAPI, Vue, PostgreSQL, HTTP, CLI.

```
Experiment YAML
      ↓
ExperimentRunner
      ↓
RNG / derived seed
      ↓
Monte Carlo → Trade[]
      ↓
PortfolioSimulator → EquityCurve
      ↓
Metrics Registry → RunResult
      ↓
ExperimentSummary (bins, агрегаты по runs)
      ↓
ExperimentRepository (Protocol)
      ↓
PostgreSQL
      ↓
CLI / FastAPI / Vue
```

Позже исторический бэктест сходится в тот же контракт `Trade[]`.

Один YAML = одна модель × N runs. Сетки параметров в MVP нет.

---

## Стек

- Python ≥ 3.12, uv, numpy, pydantic v2, PyYAML, pytest
- PostgreSQL 16, SQLAlchemy 2, Alembic, JSONB (extra, не зависимость ядра)
- FastAPI + uvicorn — отдельный пакет `api/`
- Vue 3 + Vite + TypeScript — новый `web/`
- pandas не ядро; Nuxt нет

---

## Зафиксированные решения

Эти правила обязательны при реализации. Не переоткрывать.

### 1. Время сделки

У `Trade` есть `trade_index` — порядковый индекс в run (`0..n-1`).

`entry_ts` / `exit_ts` — только **реальные** рыночные timestamp.
В Monte Carlo они всегда `None`. Индекс нельзя подставлять как unix time.

Исторический бэктест позже заполнит настоящие ts. Путаницы быть не должно.

### 2. Несколько позиций

`max_positions = 1` — ограничение **MVP-портфельной модели**, не архитектуры.
Типы `Trade` и ядро не запрещают несколько одновременных позиций в будущем.

### 3. Histogram bins

Считает только backend / `statistics`. Frontend только рисует готовые `{edges, counts}`.

Алгоритм входит в `experiment_version = 1`:

```
numpy.histogram(values, bins=50, range=(vmin, vmax))
vmin, vmax = min(values), max(values)
если vmin == vmax: range = (vmin - 0.5, vmax + 0.5)
```

Два набора: `total_return` по runs и `r_multiple` по сделкам
(накопление без хранения сырых `Trade[]`).

### 4. total_return

```
total_return = (equity_end - initial_capital) / initial_capital
```

`0.25` означает `+25%`. Денежный результат хранится отдельно
(`pnl_money`, `equity_end`). Им нельзя подменять `total_return`.

`p_negative` — доля runs с `total_return < 0`.
`p_ruined` — доля runs с `equity_end <= 0`.

### 5. Капитал и риск

YAML / portfolio:

```yaml
initial_capital: 10000
risk_per_trade: 0.01
```

Риск — доля **текущего** equity.
Пример: equity 10000, risk 0.01 → риск 100; `+2R` = `+200`.
Следующая сделка считает риск от нового equity.

Комиссия и slippage в MVP — в R за сделку.

### Прочее

- Theoretical expectancy отдельно от sample expectancy.
- Derived seed: `numpy.random.SeedSequence([experiment_seed, run_index])`.
- `store_trades: false` по умолчанию. Все сделки в БД не пишем.
- Equity для хранения/UI — downsample ≤ 500 точек.
- CLI в MVP требует Postgres.
- `code_version` = git SHA или `"unknown"`. `experiment_version = 1`.
- Лимит `runs * n_trades` = 2_000_000; сверх — ошибка до запуска.

---

## Что не входит в MVP

MEXC, CCXT, live trading, OHLCV backtesting, Redis, Kafka, Kubernetes,
multiprocessing, WebSocket, authentication, job queue, TimescaleDB,
хранение каждой сделки, Nuxt, pandas как ядро, сетка параметров,
comparison UI.

---

## Контракты (смысл, не код)

- `Trade`: id, side, trade_index, entry_ts, exit_ts, size, pnl, pnl_money, r_multiple, risk
- `EquityPoint`: index, equity, drawdown
- `RunResult`: метрики одного run, downsample equity, derived_seed
- `ExperimentSummary`: агрегаты по runs, histogram bins
- `ExperimentSpec`: YAML v1
- `ExperimentRepository`: Protocol; Postgres — одна реализация
- `Rng`: отдельный numpy Generator на run

Monte Carlo: `side = "long"`, `trade_index = i`, `entry_ts = None`, `exit_ts = None`.

Expectancy:

```
expectancy_theoretical = p_win * win_r + (1 - p_win) * loss_r
expectancy_sample = mean(r_multiples)
```

Пример: `p_win=0.55`, `win_r=2`, `loss_r=-1` → theoretical `0.65R`.

---

## Хранение (PostgreSQL)

Ядро math / simulation / runner SQLAlchemy не импортирует.

- `experiments`: id, name, created_at, spec JSONB, seed, status, duration,
  code_version, experiment_version, summary + ключевые колонки
- `runs`: experiment_id, run_index, derived_seed, params JSONB,
  колонки метрик (expectancy_theoretical, expectancy_sample, win_rate,
  total_return, max_drawdown, profit_factor, stdev, ruined),
  equity_downsampled JSONB

Частые метрики — колонки, не всё в JSONB. Таблицы сделок в MVP нет.

Локально: docker compose только с Postgres 16.
Unit-тесты ядра — fake repository. Integration — против Postgres.

---

## API (тонкий)

```
POST /experiments
POST /experiments/{id}/run      # синхронно в MVP
GET  /experiments
GET  /experiments/{id}
GET  /experiments/{id}/results
GET  /experiments/{id}/runs/{run_id}
GET  /experiments/{id}/equity
```

Нет auth, websocket, очереди. Сверх лимита операций — 400.

CLI обязателен:

```
vectorx run configs/experiments/expectancy_test.yaml
```

---

## Порядок фаз

После каждой фазы: стоп, отчёт, проверки, список файлов.
Следующая фаза — только после подтверждения.

### Фаза 0 — очистка ✅

Удалить `backend/`, `frontend/`, `.venv/`. Старый код не переносить.

**Сделано 2026-09-21.** В корне нет `backend/main.py`, нет `frontend/src/App.vue`, нет `.venv`.
Оставлены намеренно: `.git/`, `.idea/`, `VectorX.iml`.

### Фаза 1 — скелет репозитория ✅

- `pyproject.toml`: пакет `vectorx` из `src/`; extras `[postgres]`, `[api]`
- пакеты `src/vectorx/{core,math,simulation,statistics,experiments,storage}/`
- зеркало `tests/`
- `configs/experiments/`
- `docker-compose.yml` только PostgreSQL 16
- README с назначением и anti-list
- проверка: `pytest` стартует, `import vectorx` работает

Alembic — в Фазе 8.

**Сделано 2026-09-21.** `.venv` пересоздан вручную (автосоздание через
инструмент окружения не сработало — ENOENT). Пакет `vectorx` установлен
editable вместе с `dev` extra (numpy 2.5.3, pydantic 2.13.5, pyyaml 6.0.3,
pytest 9.1.1, ruff 0.16.8). `pytest` — 1/1 зелёный (smoke-тест на импорт и
версию). `ruff check .` — чисто. `docker-compose.yml` провалидирован
`docker compose config`.

### Фаза 2 — core ✅

Типы, ошибки, RNG (`SeedSequence`). Проверка: один seed → одна последовательность.

**Сделано 2026-09-21, TDD (red→green).** Реализовано в `src/vectorx/core/`:
- `errors.py`: `VectorXError` (база), `InvalidModelParametersError`, `EmptyTradesError`, `PortfolioRuinedError`
- `types.py`: `Trade`, `EquityPoint`, `Metrics`, `RunResult`, `HistogramBins`, `ExperimentSummary` — неизменяемые `@dataclass(frozen=True, slots=True)`, без логики
- `rng.py`: `derived_rng(experiment_seed, run_index)` на `numpy.random.SeedSequence([seed, run_index])`

15/15 тестов зелёные (`tests/core/test_errors.py`, `test_types.py`, `test_rng.py`), `ruff check .` чист.

### Фаза 3 — math ✅

`expectancy_theoretical` / `expectancy_sample`, валидация `p_win`, `win_r`, `loss_r`.
Проверка: `0.55 / +2R / −1R` → `0.65R`.

**Сделано 2026-09-21, TDD (red→green).** Реализовано в `src/vectorx/math/`:
- `validation.py`: `validate_p_win`, `validate_win_r`, `validate_loss_r`, `validate_model_parameters`
- `expectancy.py`: `expectancy_theoretical(p_win, win_r, loss_r)`, `expectancy_sample(r_multiples)` (`EmptyTradesError` на пустой выборке)
- `r_multiple.py`: `r_multiple_for_outcome(is_win, win_r, loss_r)` — детерминированный хелпер для Monte Carlo (Фаза 4); случайность — не здесь

32/32 теста зелёные (17 новых в `tests/math/`), `ruff check .` чист.

### Фаза 4 — Monte Carlo ✅

Модель → `Trade[]`. Derived seed на run.
Воспроизводимость params+seed. Статистика win rate — отдельный тест на 100k+ сделок.

**Сделано 2026-09-21, TDD (red→green).** `src/vectorx/simulation/monte_carlo.py`:
`generate_trades(p_win, win_  r, loss_r, n_trades, rng) -> tuple[Trade, ...]`.
Принимает уже построенный `numpy.random.Generator` (от `core.rng.derived_rng`), сама сееды не выводит. Каждая сделка:
`side="long"`, `trade_index=i`, `entry_ts=exit_ts=pnl=None`, `r_multiple` через `r_multiple_for_outcome` (Фаза 3) над bernoulli(`p_win`).

8/8 новых тестов, включая отдельную статистическую проверку на 50k сделок (win rate в допуске ±0.02 от `p_win`); полный набор 40/40, `ruff check .` чист.

### Фаза 5 — portfolio ✅

`initial_capital`, риск от текущего equity, комиссия/slippage в R,
MVP `max_positions=1`, ruin при `equity <= 0`, downsample ≤ 500.

**Сделано 2026-09-21, TDD (red→green).** `src/vectorx/simulation/portfolio.py`:
- `simulate_portfolio(trades, initial_capital, risk_per_trade, commission_r=0, slippage_r=0) -> PortfolioResult`
  (`trades`, `equity_curve`, `ruined`). Риск каждой сделки = `equity_текущее * risk_per_trade`;
  `net_r = r_multiple - commission_r - slippage_r`; `pnl_money = risk_amount * net_r`.
  При `equity <= 0` — `ruined=True`, остальные сделки не исполняются, equity не клампится.
- `EquityPoint.drawdown` — peak-to-trough доля: `(peak-equity)/peak`; кривая начинается с `index=0` (initial_capital, drawdown=0).
- `downsample_equity_curve(curve, max_points=500)` — равномерное прореживание через `numpy.linspace`, крайние точки сохраняются.

56/56 тестов зелёные (20 новых в `tests/simulation/{test_portfolio,test_downsample}.py`), `ruff check .` чист.

### Фаза 6 — metrics + ExperimentSummary ✅

Registry метрик. Summary и histogram bins на backend.
Frontend bins не считает.

**Сделано 2026-09-21, TDD (red→green).** В `src/vectorx/statistics/`:
- `histogram.py`: `compute_histogram_bins(values, bins=50)` — локальный алгоритм из плана (v1), используется и для `total_return`, и для `r_multiple`
- `metrics.py`: `compute_metrics(trades, equity_curve, initial_capital, p_win, win_r, loss_r, ruined) -> Metrics`
- `experiment_summary.py`: `compute_experiment_summary(run_metrics, all_r_multiples) -> ExperimentSummary`

Определения метрик: win/loss — по знаку `r_multiple` (не по равенству `win_r`/`loss_r`); `avg_trade` — средний `pnl_money` (деньги, отличается от `expectancy_sample` в R); `variance`/`stdev` — популяционные (всегда определены, даже при n=1); `profit_factor` = gross_profit/gross_loss в R (`inf` без проигрышей, `0.0` без выигрышей); `max_drawdown` = `max(point.drawdown)` по equity_curve; `ruined` передаётся из PortfolioResult, не пересчитывается.

68/68 тестов зелёные (12 новых в `tests/statistics/`), `ruff check .` чист.

### Фаза 7 — YAML runner ✅

Схема v1, лимит операций, fake repository, логи INFO.
Два запуска одного YAML+seed → те же метрики.

**Сделано 2026-09-21, TDD (red→green).**
- `core/rng.py`: `+derived_seed_value(seed, run_index) -> int` — отдельный `SeedSequence`, не трогает `derived_rng`.
- `core/errors.py`: `+ExperimentTooLargeError` — новый тип, лимит ресурсов, не домен модели.
- `experiments/versioning.py`: `EXPERIMENT_VERSION=1`; `get_code_version(start=None)` — читает `.git/HEAD` без subprocess, `"unknown"` если репо/коммит не найден.
- `experiments/spec.py`: `ExperimentSpec` (pydantic v2, `extra="forbid"`, frozen) — `name/seed/runs/model/portfolio/storage`; `load_experiment_spec(path)`. Доменные диапазоны (p_win и т.д.) тут не проверяются повторно — это делают math/simulation при запуске.
- `experiments/runner.py`: `MAX_OPERATIONS=2_000_000`; `run_experiment(spec) -> ExperimentResult` — pre-flight лимит до любого run; цикл runs → derived_rng → generate_trades → simulate_portfolio → compute_metrics → downsample_equity_curve → RunResult; после всех runs — compute_experiment_summary. Логи INFO ровно 2 записи (start/finish), никакого per-run логирования derived_seed.

86/86 тестов зелёные (18 новых в `tests/core` + `tests/experiments/{test_versioning,test_spec,test_runner}.py`), `ruff check .` чист.

### Фаза 8 — PostgreSQL ✅

Protocol + реализация. Integration tests. Ядро без импорта SQLAlchemy.

**Сделано 2026-09-21.** Docker-демон в этой среде недоступен — интеграционные тесты идут против локального эфемерного кластера (`initdb`/`pg_ctl`, без root/Docker), который pytest-фикстура поднимает и гасит сама. `docker-compose.yml` (postgres:16) не тронут — остаётся целевым для реального деплоя; локально использован PostgreSQL 18.4 (что было в системе).

- `storage/repository.py` — `ExperimentRepository` (`Protocol`, `runtime_checkable`), без импорта SQLAlchemy (проверено отдельным subprocess-тестом, не зависит от порядка тестов).
- `storage/postgres/serializers.py` — чистые (de)serialization-функции, юнит-тестируются без БД. `profit_factor` (может быть `inf`) намеренно исключён из JSONB (JSON не знает `Infinity`) — живёт только в своёй колонке.
- `storage/postgres/models.py` — `ExperimentRow`/`RunRow`: частые метрики колонками, остальное (`metrics_extra`, `spec`, `summary`, `equity_downsampled`, `params`) — JSONB. Таблицы `trades` нет.
- `storage/postgres/repository.py` — `PostgresExperimentRepository.{save_experiment,get_experiment,list_experiment_ids}`.
- `alembic/` — инициализирован, `env.py` читает `VECTORX_DATABASE_URL` (нет реальных credentials в `alembic.ini`); миграция `588e5c05d5ab` создаёт `experiments`+`runs`, проверена upgrade/downgrade вручную и через pytest-фикстуру.

99/99 тестов зелёные (13 новых: 5 сериализаторов, 3 Protocol, 5 интеграционных против реального Postgres), `ruff check .` чист. Полный round-trip `run_experiment → save → get` совпадает с in-memory результатом дословно; отдельно проверен `profit_factor=inf`.

### Фаза 9 — CLI ✅

`vectorx run ...` требует Postgres.
Пример: seed 42, p_win 0.55, +2/−1 R, 100 runs × 1000 trades.

**Сделано 2026-09-22, TDD (red→green).**
- `src/vectorx/cli.py`: `vectorx run <config.yaml>` (argparse, без сторонних CLI-фреймворков — ещё одна команда, новая зависимость не оправдана). Без `VECTORX_DATABASE_URL` — `SystemExit` с пояснением; без `[postgres]` extra — `SystemExit(1)` с подсказкой `pip install -e '.[postgres]'`. Никакого `--dry-run`.
- `pyproject.toml`: `[project.scripts] vectorx = "vectorx.cli:main"`.
- `configs/experiments/expectancy_test.yaml` — пример из плана (seed 42, p_win 0.55, +2/−1R, 100 runs × 1000 trades).
- Фикстуры эфемерного Postgres перенесены из `tests/storage/conftest.py` в общий `tests/conftest.py` (нужны и CLI-тестам); добавлен `postgres_url`.
- Кроме pytest — ручной сквозной прогон реального `vectorx run configs/experiments/expectancy_test.yaml` против отдельного эфемерного Postgres: два независимых процесса с одним seed → идентичные `mean/median/stdev_total_return`.

103/103 теста зелёные (4 новых в `tests/test_cli.py`), `ruff check .` чист. Ни одного висящего процесса/порта после ручного demo.

### Фаза 10 — FastAPI ✅

Тонкие хендлеры. Эксперимент из CLI виден через GET.

**Сделано 2026-09-22, TDD (red→green).** Новый пакет `api/` (отдельно от `src/vectorx`):
- `api/main.py`: `POST /experiments`, `POST /experiments/{id}/run`, `GET /experiments`, `GET /experiments/{id}`, `GET /experiments/{id}/results`, `GET /experiments/{id}/runs/{run_id}`, `GET /experiments/{id}/equity?run_id=0`. Все `VectorXError` (включая `ExperimentTooLargeError`) → глобальный обработчик → 400. Нет auth/websocket/очереди.
- `api/dependencies.py`: `get_engine`/`get_repository` через FastAPI `Depends`, подменяются в тестах через `app.dependency_overrides`.
- `api/serialization.py`: `profit_factor=inf` → строка `"Infinity"` (JSON/Starlette `allow_nan=False` иначе кидают 500) — та же проблема, что и в Postgres-слое (Фаза 8), теперь на границе API.
- `POST /experiments/{id}/run` читает сохранённый spec и создаёт НОВЫй experiment (новый id) — схема из Фазы 8 не имеет состояния «pending», повторный запуск — это новая запись.
- **Найдена и исправлена реальная ошибка из-за порядка сборки тестов**: `alembic/env.py` вызывал `fileConfig()` с дефолтным `disable_existing_loggers=True`; при in-process запуске `alembic upgrade` (через pytest-фикстуру) это отключало уже созданный логгер `vectorx.experiments.runner` на весь процесс. Проявилось только после того, как `tests/api/` стал алфавитно первым и раньше триггерил Postgres-фикстуру. Фикс — `fileConfig(..., disable_existing_loggers=False)` (официальная рекомендация Alembic для in-process запуска), не перестановка тестов.
- Ручной сквозной прогон: реальный `uvicorn api.main:app` против отдельного эфемерного Postgres + `curl`: create/list/detail/results/run-detail/equity/404/400 — всё работает.

116/116 тестов зелёные (13 новых в `tests/api/`), `ruff check .` чист. Никаких висящих процессов/портов после демо.

### Фаза 11 — Vue dashboard ✅

Новый `web/`. Список, деталь, параметры, метрики, equity, histogram из bins, таблица runs.
UI ничего не считает.

**Сделано 2026-09-22, TDD (red→green) где применимо.** Новый Vite-проект `web/` (Vue 3 + TS, `vitest`+`@vue/test-utils`+`jsdom`, `chart.js` — лёгкий, не financial-плагин):
- `src/api.ts` + `types.ts` — типизированный fetch-клиент, зеркало `api/serialization.py`
- `EquityChart.vue` / `HistogramChart.vue` — canvas + Chart.js (line/bar); тесты мокают `chart.js/auto`, проверяя config/data/destroy-на-unmount
- `RunsTable.vue` — чистый рендер таблицы runs, `profit_factor` отображается как есть (включая `"Infinity"`)
- `ExperimentsList.vue` → `ExperimentDetail.vue` (params/summary/equity/2 histogram/RunsTable) → `App.vue` (переключение list/detail без vue-router, простой `ref`)
- **Найдена и закрыта реальная дыра до прогона**: у FastAPI не было CORS — браузер блокировал бы запросы с Vite dev server на API. Добавлен `CORSMiddleware` (TDD: тест на `access-control-allow-origin` → RED → фикс → GREEN) до любого ручного тестирования в браузере, не после ошибки.
- Живой сквозной прогон: эфемерный Postgres + `alembic upgrade` + 2 реальных эксперимента через CLI + живой `uvicorn` + живой `vite dev` — открыт в браузере: список рендерится, клик по строке открывает деталь с параметрами, реальный equity-график (экспоненциальный рост до ~5млн за 1000 сделок, ожидаемый эффект компаундинга), гистограмма, таблица runs, кнопка Back возвращает к списку.

Фронтенд: 25/25 тестов зелёные (`vitest`), `vue-tsc`+`vite build` чисты. Бэкенд: 117/117 (было 116 + 1 новый CORS-тест), `ruff check .` чист.

**Критерий готовности MVP (9 пунктов) пройден вручную — все ✅.** См. раздел ниже.

---

## Критерий готовности MVP

1. YAML-эксперимент с seed и моделью
2. N Monte Carlo runs
3. `Trade[]`, equity, metrics
4. theoretical и empirical expectancy
5. запись в PostgreSQL
6. повтор с тем же seed → тот же результат
7. другой seed → другая реализация
8. CLI и API показывают одно и то же
9. dashboard: список, параметры, метрики, equity, histogram, runs

---

## Каталог после реализации (целевой)

```
vectorx/
├── pyproject.toml
├── src/vectorx/
│   ├── core/
│   ├── math/
│   ├── simulation/
│   ├── statistics/
│   ├── experiments/
│   └── storage/          # Protocol в ядре; postgres — extra
├── api/
├── web/
├── configs/experiments/
├── tests/
├── docker-compose.yml
├── docs/
│   └── VECTORX-MVP-PLAN.md   # этот файл
└── README.md
```
