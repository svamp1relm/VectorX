# VectorX — Research Platform Roadmap (Фазы 18+)

Документ фиксирует согласованный roadmap после завершения Фазы 17 (`docs/VECTORX-POST-MVP-ROADMAP.md`).
Как и в предыдущих документах — реализация по фазам с паузой. После каждой фазы: стоп, отчёт, проверки,
список файлов. Следующая фаза — только после подтверждения.

**Статус:** Фаза 17 завершена (2026-09-30). Roadmap 18+ согласован (2026-10-02).
Фазы 18a, 18b, 18c, 19, 20, 21, 22, 23, 24 реализованы (2026-10-02, TDD red→green,
по указанию пользователя — без паузы между фазами). **"VectorX Research Platform v1"
достигнут** (18a+18b+18c+19+20+21+24 — см. определение ниже); Фаза 22
(generalization litmus test) и Фаза 23 (unification pass) сделаны тоже.
309 backend тестов + 42 frontend теста зелёные, `ruff check .` и `vue-tsc --noEmit`
чисты. Детали реализации — в конце каждой фазы ниже.

---

## Назначение этого этапа

VectorX — research/scientific-analytical platform, НЕ торговый бот. Реальная торговля, подключение к
биржам, API-ключи, live orders — не входят в этот этап и не рассматриваются до его завершения.

Цель — довести платформу до состояния, в котором честно можно провести полный исследовательский цикл:

```
гипотеза → подготовка данных → выбор стратегии/модели → эксперимент → simulation/backtest
→ statistical analysis → robustness checks → out-of-sample validation → comparison
→ interpretation → reproducible result/report
```

После завершения research-платформы (отдельное будущее решение, не часть этого документа):
paper trading, market data infrastructure, risk/order management, exchange adapters — trading platform.
Ещё позже: blockchain / on-chain analytics / wallets / DeFi / Web3. Эти этапы сознательно не
рассматриваются и не проектируются сейчас — смешивать их с research-платформой не нужно.

## Критическая оценка состояния после Фазы 17

Архитектура `Trade[] → PortfolioSimulator → Metrics → ExperimentSummary` и дисциплина версионирования
(`experiment_version`, locked histogram algorithm) — прочное основание. Но для research-платформы не
хватает не "фич", а **трёх инфраструктурных примитивов**, отсутствие которых иначе потребует
переделки storage/schema в середине фаз 19-21:

1. **Raw trade persistence.** Поле `storage.store_trades: bool` существует в `ExperimentSpec`
   (`src/vectorx/experiments/spec.py`), но нигде не используется в `runner.py`/`repository.py`.
   Таблицы `trades` не существует (`tests/storage/test_postgres_repository.py::test_no_trades_table_exists`
   закрепляет это явно). Сохраняются только агрегаты: `Metrics` (скаляры), downsampled equity curve,
   50-bin histogram. Bootstrap/permutation-статистика над уже сохранённым экспериментом невозможна.
2. **Time-range slicing.** `MarketData`/`DataSource` не имеют примитива выбора подпериода
   (`slice(start, end)` или аналог). Нужен и для Out-of-Sample (train/test), и для Robustness
   (walk-forward).
3. **Experiment batching/sweep.** `runs` для historical жёстко `Literal[1]` (Фаза 16a, пункт 4
   зафиксированных решений). Нет возможности прогнать сетку параметров или несколько
   инструментов/периодов под одной исследовательской гипотезой.

Дополнительно: нет `data_version` (content-hash CSV) — есть только `code_version` (git SHA) и
`experiment_version` (схема). Если исходный CSV перезапишут новым снэпшотом, старые эксперименты
станут невоспроизводимыми молча, без какого-либо сигнала. Нет benchmark-стратегий (Buy&Hold,
Random-entry) — `Strategy` protocol уже это позволяет, но пока существует только одна стратегия
(MA Crossover), и statistical significance не с чем сравнивать.

## Архитектурная идея

```
Фаза 18a (raw trades + data_version)   ──┐
Фаза 18b (time-range slicing)          ──┼──→ Фаза 18c (batches/sweep + hypothesis)
                                           │
                                           ↓
                              Фаза 19 (statistical toolkit + benchmarks)
                                           ↓
                              Фаза 20 (Out-of-Sample Validation)
                                           ↓
                              Фаза 21 (Robustness Testing)
                                           ↓
                              Фаза 22 (Multiple Strategies — лакмус генерализуемости)
                                           ↓
                              Фаза 23 (Research Dashboard — unification pass)
                                           ↓
                              Фаза 24 (Reproducible Research / Export)
```

18a и 18b независимы друг от друга (можно в любом порядке или параллельно); оба обязательны до 18c.
Дальше — строго последовательно. Ни одна фаза не должна требовать возврата в архитектуру предыдущей —
это явная цель данного порядка (см. "Критика исходного порядка" ниже).

## Критика исходного порядка (зафиксировано для истории решения)

Исходная черновая идея пользователя: `18 Research Experiments → 19 Statistical Analysis →
20 Robustness → 21 Out-of-Sample → 22 Strategies+Benchmarks → 23 Dashboard → 24 Export`.
После разбора — три изменения, все приняты:

1. **18 раскрыта и разбита на 18a/18b/18c.** "Research Experiments" как название было расплывчатым;
   реально нужны три независимых примитива (raw trades, time-slicing, sweep engine), и объединять их
   в одну фазу рискованно — разбиение по аналогии с Фазами 16a/16b.
2. **Out-of-Sample (было 21) переставлена перед Robustness (было 20).** OOS — один time-split,
   частный случай той же техники, что Robustness (walk-forward = серия OOS-сплитов). Простой случай
   раньше сложного снижает архитектурный риск и почти полностью переиспользует `expectancy_comparison`
   из Фазы 17.
3. **Benchmark-стратегии (Buy&Hold, Random-entry) перенесены из Фазы 22 в Фазу 19.** Statistical
   Analysis без baseline для сравнения неполноценна — нужны они рано, а не в конце.
4. **Research Dashboard (23) превращена из "первого появления UI" в unification/polish pass.**
   UI растягивается инкрементально по каждой фазе 18c-22 (минимальный, но рабочий), чтобы сохранить
   принцип "после каждой фазы — демонстрируемая система" (как в Фазах 16a/16b).

---

## Фаза 18a — Raw Trade Persistence & Data Versioning

**Цель.** Сделать сырые per-trade R-мультипликаторы и провенанс исходных данных частью хранимого
состояния эксперимента.

**Решает.** Без сырых trades невозможна никакая post-hoc статистика (bootstrap CI, permutation tests)
над уже сохранённым экспериментом — только над свежепосчитанным. Без версии данных реальная
воспроизводимость эксперимента неполна (есть code_version/experiment_version, но не data_version).

**Что появляется.**
- Новая таблица `trades` (per-run, per-trade: `r_multiple`, `pnl`, `pnl_money`, `entry_ts`, `exit_ts`,
  `side`, `trade_index`), FK на `runs`.
- `storage.store_trades` наконец читается в `runner.py`/`repository.py` и реально управляет записью
  в `trades` (по умолчанию `false` — объём данных).
- `data_version`: content-hash (sha256) исходного CSV, вычисляется при загрузке и сохраняется в
  спеке/эксперименте (для historical; для Monte Carlo данных нет — поле `None`).

**Используются существующие компоненты.** `run_experiment()`, `simulate_portfolio()` (без изменений),
`ExperimentRepository` (расширяется, не переписывается).

**Backend.** Новая Alembic-миграция (таблица `trades`); `storage/postgres/models.py` — `TradeRow`;
`storage/postgres/repository.py` — запись/чтение trades по флагу; `marketdata/csv_source.py` или
`experiments/runner.py` — вычисление `data_version`.

**Frontend.** Не требуется (данные не отображаются в UI на этом этапе).

**Данные для хранения.** См. схему `trades` выше; `data_version` — колонка на `experiments` (или
в JSONB `spec`, если решено не менять схему таблицы — зафиксировать явно в начале фазы).

**Тесты.** Round-trip таблицы `trades` (запись → чтение → побитовое совпадение с тем, что вычислено);
`data_version` меняется при изменении содержимого CSV и не меняется при неизменном содержимом;
`store_trades=false` по-прежнему не создаёт строк в `trades` (regression на существующем инварианте).

**Критерии завершения.** Для эксперимента с `store_trades=true` все `Trade[]` восстановимы из БД
побитово идентично тому, что было вычислено при запуске. `data_version` детерминирован и стабилен.

**Не входит.** Sweep/batch (18c), UI (нигде в 18a), статистические методы поверх trades (19).

**Сделано 2026-10-02, TDD (red→green).** Новая таблица `trades` (миграция
`c7e2a4f91b36`) + `experiments.data_version` (String, nullable). `TradeRow` в
`storage/postgres/models.py`; `ExperimentResult` получил поля `data_version: str | None`
и `run_trades: tuple[tuple[Trade,...],...] | None` (заполняется только при
`storage.store_trades=true`, выровнено по порядку с `run_results`).
`compute_data_version()` (sha256 hex) в `marketdata/csv_source.py`. Репозиторий
пишет/читает `trades` только когда `run_trades is not None`; `store_trades=false`
по-прежнему не создаёт строк (regression-тест). 11 новых тестов.

---

## Фаза 18b — Time-Range Slicing

**Цель.** Дать `MarketData`/`DataSource` примитив выбора подпериода по времени.

**Решает.** Out-of-Sample (20) и Robustness/walk-forward (21) оба нуждаются в разбиении одного
набора исторических данных на непересекающиеся временные интервалы — без общего примитива это будет
написано дважды, по-разному.

**Что появляется.** Метод/функция среза `MarketData` по `(start: datetime, end: datetime)` →
новый `MarketData` с тем же `symbol`/`timeframe` и подмножеством `candles`.

**Используются существующие компоненты.** `MarketCandle`/`MarketData` (не меняются по форме),
`validate_market_data()` (применяется к срезу так же, как к полному набору).

**Backend.** `marketdata/types.py` или новый `marketdata/slicing.py`.

**Frontend.** Не требуется.

**Данные для хранения.** Ничего нового не персистится — чистая функция над уже загруженными данными.

**Тесты.** Срез на границах (точное совпадение `start`/`end` с существующей свечой), пустой срез
(нет свечей в интервале → явная ошибка, не молчаливый пустой результат), срез не мутирует исходный
`MarketData`.

**Критерии завершения.** Два непересекающихся среза одного `MarketData` в сумме дают исходный набор
свечей без потерь и дублирования на границе.

**Не входит.** Автоматическое определение "хорошей" точки разбиения (train/test, walk-forward окна) —
это логика Фаз 20/21, здесь только примитив среза.

**Сделано 2026-10-02, TDD (red→green).** `marketdata/slicing.py::slice_market_data(data, start, end)` —
оба конца **включительно** (не half-open): два среза строятся на соседних реальных
таймстемпах свечей, без дублирования/пропуска на границе. `InvalidMarketDataError`
на `start > end` и на пустой срез. 5 тестов.

---

## Фаза 18c — Experiment Batches / Sweep Engine

**Цель.** Группировать много `ExperimentSpec` под одной исследовательской гипотезой и породить их
автоматически из параметрической сетки.

**Решает.** "Один YAML = один прогон" не даёт статистической базы для сравнения параметров/активов.
Нет способа зафиксировать, зачем вообще была запущена группа экспериментов.

**Что появляется.**
- `ExperimentBatch` — новая сущность: `hypothesis: str`, `notes: str | None`, `created_at`.
- Sweep-спецификация: декартово произведение параметров стратегии / список инструментов / список
  CSV-путей → N конкретных `ExperimentSpec`. Каждый выполняется существующим `run_experiment()` —
  новый execution engine не создаётся.
- Входящие в batch эксперименты **форсируют `store_trades=true`** (без этого Фазы 19-21 не будут
  работать для batch-экспериментов) — решение явное, не оставлено на усмотрение YAML.
- Resource-guard на размер batch (max экспериментов × max операций на эксперимент) — явное число
  фиксируется в начале фазы, по аналогии с `MAX_OPERATIONS`/`MAX_HISTORICAL_CANDLES`.

**Используются существующие компоненты.** `ExperimentSpec`, `run_experiment()`, вся storage-
инфраструктура, `trades` (18a).

**Backend.** Новая таблица `experiment_batches` (`id`, `hypothesis`, `notes`, `created_at`) + колонка
`batch_id` (nullable FK) на `experiments`; новый модуль sweep-generator (чистая функция: sweep-spec →
`tuple[ExperimentSpec, ...]`); `run_experiment()` не меняется.

**Frontend.** Минимально: страница/секция "Batch" со списком входящих экспериментов и общей таблицей
метрик рядом (переиспользование паттернов `ExperimentsList`/`RunsTable`).

**Данные для хранения.** `experiment_batches` (см. выше), `experiments.batch_id`.

**Тесты.** Sweep-generator (комбинаторика параметров → ожидаемое число `ExperimentSpec`);
resource-guard блокирует превышение лимита до запуска; batch forces `store_trades=true` для всех
входящих экспериментов (regression-тест на инвариант).

**Критерии завершения.** Один batch-YAML с гипотезой и сеткой параметров порождает N экспериментов,
все видны как группа в API/UI, для каждого из них сохранены сырые trades.

**Не входит.** Статистические методы поверх батча (19), heatmap/визуализация sweep (21/23).

**Сделано 2026-10-02, TDD (red→green).** `experiments/sweep.py::SweepSpec`/`generate_sweep_specs`
(чистая функция, декартово произведение по dotted-key grid, `MAX_BATCH_EXPERIMENTS=100`
resource-guard, форсирует `storage.store_trades=true`). `experiments/batch.py::ExperimentBatch`
(чистый dataclass). Storage: таблица `experiment_batches` + `experiments.batch_id`
(nullable FK, `ondelete=SET NULL`), миграция `d8f3b6c20a51`; `save_batch`/`get_batch`/
`list_batch_ids` на репозитории и в Protocol. API: `POST/GET /batches`, `GET /batches/{id}`
(оркестрация sweep+run+save живёт в самом route, не в `vectorx.experiments` — пакет
остаётся storage-agnostic). Frontend: `BatchesList.vue`/`BatchDetail.vue`, таб
"Batches" в `App.vue`. 15 backend + 3 frontend теста.

---

## Фаза 19 — Statistical Analysis Toolkit + Benchmark-стратегии

**Цель.** Дать инструменты отвечать на вопрос "значим ли результат", не только "какой он".

**Решает.** Expectancy/profit factor сейчас — точечные оценки без доверительных интервалов; нет
способа сказать "это лучше случайности/рынка".

**Что появляется.**
- Bootstrap confidence intervals на expectancy (требует raw trades, 18a).
- Sharpe/Sortino/Calmar как дополнительные метрики.
- Простой significance-тест: sample expectancy vs 0, и vs benchmark-эксперимент.
- `BuyAndHoldStrategy`, `RandomEntryStrategy` (seeded RNG) — обе реализуют существующий `Strategy`
  protocol без изменений в нём.
- `analysis_version` — версионирование статистических алгоритмов, по аналогии с locked
  `experiment_version`/histogram algorithm.

**Используются существующие компоненты.** `trades` (18a), `Metrics`/`ExperimentSummary` (не меняются),
`expectancy_comparison` (переиспользуется как механизм сравнения с benchmark-экспериментом),
`Strategy` protocol (не меняется).

**Backend.** Новые модули `statistics/confidence.py` (bootstrap CI), `statistics/risk_adjusted.py`
(Sharpe/Sortino/Calmar); `strategy/benchmarks.py` (`BuyAndHoldStrategy`, `RandomEntryStrategy`).

**Frontend.** Доверительные интервалы рядом с точечными оценками в `ExperimentDetail.vue`.

**Данные для хранения.** CI/risk-adjusted метрики — пересчитываются из `trades` (18a) по запросу, или
кэшируются в `metrics_extra` JSONB (решить в начале фазы — зависит от стоимости пересчёта).

**Тесты.** Известные аналитические случаи (нормальное распределение trades → известный CI);
regression на детерминированном seed для bootstrap; benchmark-стратегии дают ожидаемый `Trade[]` на
фикстурных данных.

**Критерии завершения.** Для любого эксперимента с сохранёнными trades можно получить CI на
expectancy и Sharpe с фиксированным seed воспроизводимо; benchmark-стратегии доступны наравне с
MA Crossover через тот же `ExperimentSpec`.

**Не входит.** Walk-forward (21), out-of-sample (20), ML, сложная оптимизация параметров.

**Сделано 2026-10-02, TDD (red→green).** `strategy/benchmarks.py`: `BuyAndHoldStrategy`,
`RandomEntryStrategy` (seeded, собственное `_in_position` состояние). `HistoricalStrategySpec`
стал discriminated union (`moving_average_crossover` default | `buy_and_hold` | `random_entry`),
`runner.py::_build_strategy` диспетчеризует. `statistics/confidence.py::bootstrap_confidence_interval`,
`statistics/risk_adjusted.py::compute_risk_adjusted_metrics` (Sharpe/Sortino/Calmar,
unannualized, `None` вместо inf/nan), `statistics/significance.py` (vs zero, vs benchmark —
bootstrap mean-difference). `statistics/versioning.py::ANALYSIS_VERSION=1`. API:
`GET /experiments/{id}/analysis` (считается on-demand из `run_trades`, не кэшируется;
400 если `store_trades=false`). Frontend: секция "Statistical analysis" в
`ExperimentDetail.vue` (скрыта, если анализ недоступен). 46 backend + 2 frontend теста.

---

## Фаза 20 — Out-of-Sample Validation

**Цель.** Один явный train/test time-split: работает ли то же самое на невиданных данных.

**Решает.** Любой параметр, подобранный на всей истории, подозрителен на overfitting.

**Что появляется.** `OutOfSampleSpec` (train-период + test-период, одна и та же стратегия/параметры);
сравнение двух `ExperimentSummary` через уже существующий `compare_expectancy()` (Фаза 17) — тот же
механизм "сравнить два источника", только оба historical, разделённые по времени вместо типа модели.

**Используются существующие компоненты.** Time-range slicing (18b), `expectancy_comparison` (17),
`run_experiment()` (без изменений).

**Backend.** Новая тонкая функция `run_out_of_sample(spec, train_range, test_range)`: два вызова
`run_experiment()` + один `compare_expectancy()`. Новой core-логики не создаётся.

**Frontend.** Страница "train vs test" side-by-side, переиспользует `ExpectancyComparison.vue`.

**Данные для хранения.** Результат OOS — пара обычных `experiments` + обычный comparison result;
новая персистентная сущность не обязательна (как и в Фазе 17, comparison — derived, не хранится).

**Тесты.** На синтетических данных с известным сдвигом поведения между периодами — comparison
корректно показывает расхождение; граничные случаи среза (18b) корректно обрабатываются.

**Критерии завершения.** Train/test сравнение для одного инструмента/стратегии воспроизводимо и
детерминировано.

**Не входит.** Множественные сплиты (это Robustness/walk-forward, 21); автоматический выбор
"лучших" параметров по OOS — решение осознанно остаётся за исследователем, не автоматизируется.

**Сделано 2026-10-02, TDD (red→green).** `experiments/out_of_sample.py::OutOfSampleSpec`
(train/test обязательно непересекающиеся — `test_start > train_end` строго)
+ `run_out_of_sample()`: грузит CSV, режет `slice_market_data` (18b), пишет срезы
во временные CSV (`marketdata/csv_source.py::write_market_data_csv`, новая функция),
два вызова `run_experiment()` на train/test-спеках, сравнение через новую
`statistics/expectancy_comparison.py::compare_train_test_expectancy` (не переиспользует
`compare_expectancy` буквально — тот хардкодит роли "monte_carlo vs historical";
новая функция обобщает "сравнить два источника" на train/test, с новым
`core.types.OutOfSampleComparisonResult`). Результат derived, не персистится. API:
`POST /out-of-sample`. 15 тестов.

---

## Фаза 21 — Robustness Testing

**Цель.** Устойчивость результата к небольшим изменениям параметров, данных, времени.

**Решает.** "Результат хороший" может быть случайной удачей на конкретных параметрах/периоде
(overfitting, "lucky spike"), а не устойчивым эффектом.

**Что появляется.**
- Parameter sensitivity: сетка вокруг выбранных параметров (переиспользует sweep engine, 18c) +
  heatmap значений expectancy/Sharpe.
- Walk-forward: N последовательных OOS-окон подряд (переиспользует Фазу 20 как building block).
- Устойчивость к возмущениям входных данных: block bootstrap над сохранёнными trades (18a).

**Используются существующие компоненты.** Sweep engine (18c), OOS primitive (20), statistical
toolkit (19).

**Backend.** `robustness/sensitivity.py`, `robustness/walk_forward.py` — обе функции компонуют уже
существующие строительные блоки, новой логики симуляции не создают.

**Frontend.** Heatmap параметрической чувствительности; walk-forward — склейка нескольких OOS-окон
на одном графике.

**Данные для хранения.** Результаты sensitivity/walk-forward — коллекции обычных `experiments`
(через sweep/batch, 18c) + derived-отчёт поверх них; отдельная таблица не создаётся, если не
понадобится явно в начале фазы.

**Тесты.** На синтетических данных с заведомо устойчивым/неустойчивым поведением — sensitivity и
walk-forward корректно показывают разницу.

**Критерии завершения.** Можно явно показать: "в диапазоне fast_period 8-12 expectancy остаётся
положительным" vs "только при fast_period=10 — нестабильно".

**Не входит.** Автоматический выбор "лучших" робастных параметров — решение исследователя, не
платформы.

**Сделано 2026-10-02, TDD (red→green).** Новый пакет `vectorx/robustness/`:
`sensitivity.py::run_sensitivity_analysis(sweep)` (переиспользует `generate_sweep_specs`
18c + `run_experiment`, один `SensitivityPoint` на комбинацию: params + expectancy_sample +
sharpe); `walk_forward.py::generate_walk_forward_windows`/`run_walk_forward` (N окон,
каждое — вызов `run_out_of_sample` 20, окна разделены `_MIN_GAP=1мкс` чтобы не нарушать
OOS-инвариант "test_start > train_end" без знания интервала свечей); `block_bootstrap.py::
block_bootstrap_confidence_interval` (moving-block bootstrap, тот же `ConfidenceInterval`
из 19, другой алгоритм ресэмплинга). API/UI не добавлялись — сознательно отложено в
Фазу 23 (unification pass), см. ниже. 17 тестов.

---

## Фаза 22 — Multiple Strategies

**Цель.** Расширить множество кандидатных стратегий за пределы одной MA Crossover.

**Решает.** Весь research-pipeline (18-21) проверен только на одной стратегии — нужно подтвердить
генерализуемость.

**Что появляется.** Минимум одна дополнительная, по характеру отличная стратегия (например,
mean-reversion или breakout) — без ML и без автоматической оптимизации параметров.

**Используются существующие компоненты.** Весь pipeline 18-21 без изменений — если он спроектирован
верно, добавление стратегии — это просто ещё одна реализация `Strategy` protocol.

**Критерии завершения — лакмусовая бумажка для всего roadmap.** Если добавление новой стратегии
требует правок в sweep engine / statistics / OOS / robustness — значит архитектура 18-21 была
недостаточно обобщена, и это нужно явно зафиксировать как технический долг.

**Не входит.** ML, десятки стратегий "из коробки", сложная оптимизация.

**Сделано 2026-10-02, TDD (red→green).** `strategy/breakout.py::BreakoutStrategy` —
Donchian-channel breakout (вход на новый хай за `entry_lookback`, выход на новый
лоу за `exit_lookback`), по характеру отличная от MA Crossover (экстремумы, а не
сколзящее среднее). `BreakoutStrategySpec` добавлена в `HistoricalStrategySpec` union,
`runner.py::_build_strategy` — без правок вне добавления одной ветки. Лакмусовая
проверка (`tests/experiments/test_strategy_generalization.py`): breakout прогнан
через `run_experiment`, sweep engine (18c), sensitivity (21), out-of-sample (20)
**без единой правки** в этих модулях — архитектура 18-21 подтверждена обобщённой.
13 тестов.

---

## Фаза 23 — Research Dashboard (unification pass)

**Цель.** Не первое появление UI (он уже появился инкрементально в 18c-22), а согласование: единая
навигация между batch/OOS/robustness/strategy-comparison views, единый UX "начать новое исследование".

**Что появляется.** Навигация, общие паттерны отображения, возможно — общая "research session" view,
объединяющая batch → statistical analysis → OOS → robustness в одном месте.

**Не входит.** Новая backend-логика — только переиспользование и согласование уже существующих
эндпоинтов/данных.

**Сделано 2026-10-02.** Единая навигация в `App.vue` (таб-переключатель "Experiments /
Batches / Out-of-Sample", без правок backend). Новый `OutOfSampleView.vue` (форма
id базового эксперимента + train/test диапазоны → `POST /out-of-sample` → train/test/delta).
Кнопки "Export JSON"/"Export Markdown" в `ExperimentDetail.vue` (ссылки на Фазу 24
endpoint). Сознательно не сделано: heatmap для sensitivity (21) и walk-forward
chart — некритично для v1-определения ниже, можно добавить отдельным заходом.
2 новых frontend-теста (+ правки существующих для новых API-моков).

---

## Фаза 24 — Reproducible Research / Export

**Цель.** "Нажал кнопку — получил воспроизводимый отчёт с полным provenance."

**Что появляется.** Export в статический формат (JSON/markdown-отчёт), включающий: `code_version`,
`data_version` (18a), `experiment_version`, `analysis_version` (19), seed, полный `ExperimentSpec`,
`hypothesis`/`notes` (18c).

**Критерии завершения.** Два независимых запуска экспорта на одном и том же сохранённом эксперименте
дают побайтово идентичный отчёт.

**Сделано 2026-10-02, TDD (red→green).** `experiments/export.py::build_experiment_report`/
`render_json_report`/`render_markdown_report` — без зависимости от `vectorx.storage`
(дублирует маленький JSON-safe сериализатор `ExperimentSummary`, а не тянет
`storage.postgres.serializers`, чтобы пакет `experiments` остался storage-agnostic).
Байт-идентичность: `json.dumps(..., sort_keys=True)`, никаких `datetime.now()`/wall-clock
значений в отчёте — только уже сохранённые на эксперименте метаданные.
`storage.repository::get_batch_id_for_experiment()` новый метод (и в Protocol), чтобы
export мог подставить `hypothesis`/`notes`, если эксперимент входит в batch. API:
`GET /experiments/{id}/export?format=json|markdown` (возвращает сырую строку от
`render_*_report`, не пересериализует через FastAPI, чтобы байт-идентичность сохранялась
и на уровне HTTP-ответа). Frontend: кнопки экспорта в `ExperimentDetail.vue` (Фаза 23).
13 тестов.

**"VectorX Research Platform v1" достигнут этой датой** — все фазы из определения ниже
(18a+18b+18c+19+20+21+24) реализованы и протестированы; Фаза 22 (необязательная) и
Фаза 23 (unification pass) сделаны тоже. Итог: 309 backend тестов + 42 frontend теста
зелёные, `ruff check .` и `vue-tsc --noEmit` чисты.

---

## "VectorX Research Platform v1 Complete" — определение

Минимальный набор для честного исследовательского цикла (гипотеза → данные → стратегия → эксперимент
→ backtest → statistical analysis → robustness → out-of-sample → comparison → interpretation →
reproducible report):

```
18a + 18b + 18c + 19 + 20 + 21 + 24
```

Фаза 22 (Multiple Strategies) **не обязательна** для статуса v1 — это проверка генерализуемости
архитектуры, не core capability. Можно объявить платформу v1-готовой после 18a-21+24, если 22 ещё
не завершена.

## Архитектурные решения, принятые/зафиксированные до начала Фазы 18a

1. **Схема `trades`** — отдельная SQL-таблица (по трейду — строка), не JSONB-массив: объём может
   быть большим (100k+ trades на Monte Carlo run), нужна выборочная агрегация без вытягивания всего
   JSONB.
2. **`ExperimentBatch`** — новая родительская таблица, не тег/колонка на `experiments`: у batch есть
   собственные атрибуты (`hypothesis`, `notes`), не относящиеся ни к одному отдельному эксперименту.
3. **`data_version`** — content-hash (sha256) файла, не человекочитаемый номер версии в YAML: не
   требует дисциплины от человека, вычисляется автоматически.
4. **`store_trades` для batch-экспериментов** — форсируется `true` внутри `ExperimentBatch`; вне
   batch — остаётся `false` по умолчанию, как и сейчас.
5. **`analysis_version`** — заводится отдельно от `experiment_version`, по аналогии с тем, как
   `histogram`-алгоритм версионируется сейчас: статистические методы (bootstrap/CI) будут
   эволюционировать независимо от core experiment schema.
6. **Resource-guard на размер sweep/batch** — точное число фиксируется в начале Фазы 18c, по
   аналогии с `MAX_OPERATIONS`/`MAX_HISTORICAL_CANDLES`.

## Anti-scope (явно вне этого этапа)

Всё из `docs/VECTORX-POST-MVP-ROADMAP.md` (MEXC/CCXT/live trading/реальные ордера, WebSocket/Redis/
Kafka/Kubernetes, ML, short-позиции) плюс:

- Автоматический выбор "лучших" параметров по OOS/robustness — решение остаётся за исследователем.
- Персистентная таблица comparisons/analysis results, если не понадобится явно внутри конкретной фазы.
- Blockchain / on-chain analytics / wallets / DeFi / Web3 — отдельный, значительно более поздний этап.

---

## Статус

Roadmap согласован (2026-10-02). К реализации Фазы 18a переход только по явной команде пользователя.
