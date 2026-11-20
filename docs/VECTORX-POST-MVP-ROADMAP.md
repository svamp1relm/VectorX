# VectorX — Post-MVP Development Roadmap

Документ фиксирует архитектуру и порядок реализации Post-MVP этапа.
Как и в MVP — реализация по фазам с паузой. После каждой фазы: стоп, отчёт, проверки, список файлов.
Следующая фаза — только после подтверждения.

**Статус:** MVP завершён (см. `docs/VECTORX-MVP-PLAN.md`). Фаза 12 выполнена (2026-09-22). Фаза 13 выполнена (2026-09-22). Фаза 14 выполнена (2026-09-22). Фаза 15 выполнена (2026-09-23). Фаза 16a выполнена (2026-09-23). Фаза 16b выполнена (2026-09-23). Фаза 17 выполнена (2026-09-30).

---

## Цель этапа

Первый крупный этап Post-MVP называется **Historical Research & Backtesting Platform**.

MVP проверил математическое ядро на полностью синтетической модели:

```
Experiment YAML → Monte Carlo → Trade[] → PortfolioSimulator → Metrics → Summary → Storage → API → Dashboard
```

У системы нет реальных рыночных данных. Цель этапа — превратить VectorX из платформы, работающей
только с абстрактной вероятностной моделью, в исследовательскую платформу, которая может проверять
те же гипотезы на реальных исторических данных — **не переписывая существующее ядро**.

## Архитектурная идея

Разные источники сделок сходятся в один и тот же контракт:

```
                    ┌── Monte Carlo Model ──┐
                    │                        │
Experiment ─────────┤                        ├──→ Trade[]
                    │                        │
                    └── Historical Backtest ─┘
                                             ↓
                                    PortfolioSimulator
                                             ↓
                                          Metrics
                                             ↓
                                    ExperimentSummary
                                             ↓
                                  PostgreSQL / API / Vue
```

`Trade` уже сегодня, в MVP, содержит поля `entry_ts`/`exit_ts`/`pnl`, зарезервированные под
исторический бэктест (см. `docs/VECTORX-MVP-PLAN.md`, раздел "Зафиксированные решения → 1. Время
сделки"). Это не новая архитектура — это реализация того, что уже было заложено.

---

## Архитектурные принципы Post-MVP этапа

Обязательны при реализации, как и раздел "Зафиксированные решения" в MVP-плане.

1. **`Trade[]` — единственный контракт** между источником сделок (Monte Carlo или Historical
   Backtest) и `PortfolioSimulator`/`Metrics`/`Storage`/`API`/`Dashboard`. Второй параллельной
   системы статистики для исторического бэктеста не создаётся.
2. **`PortfolioSimulator.simulate_portfolio()` не меняется.** Переиспользуется как есть для обоих
   источников сделок.
3. **`expectancy_theoretical` становится `float | None`** — на уровне `Metrics`, БД (`runs` таблица),
   API, UI. Для historical backtest всегда `None`, пока у стратегии нет собственной декларируемой
   теоретической модели (см. Фаза 17).
4. **`runs` для `historical_backtest` всегда равен `1`.** Один детерминированный проход по одному
   зафиксированному набору исторических данных. Parameter grid / несколько runs — не в этом этапе.
5. **`ExperimentSpec` становится полиморфной схемой** по полю `type`, со значением по умолчанию
   `type: monte_carlo` для полной обратной совместимости с существующими YAML v1 (без поля `type`).
   `EXPERIMENT_VERSION` не увеличивается, если изменение остаётся аддитивным.
6. **`DataSource` — Protocol**, независимый от конкретного провайдера. Первая реализация — CSV через
   stdlib `csv`, без pandas/pyarrow/parquet.
7. **Strategy API не знает о PostgreSQL/FastAPI/Vue.** Чистый контракт `MarketData → Strategy →
   Signal`.
8. **Первая стратегия — MA Crossover, только long/flat.** Коротких позиций нет. `PortfolioSimulator`
   (`max_positions=1`) не меняется.
9. **`MAX_OPERATIONS = runs * n_trades`** — Monte-Carlo-специфичный guard. Для historical backtest
   вводится отдельный лимит ресурса (по количеству свечей), определяется в Фазе 16a.
10. Anti-scope (ниже) обязателен к соблюдению; пересмотр — только отдельным решением, не по ходу
    реализации фазы.

## Anti-scope (явно вне этого этапа)

- MEXC, CCXT, любые live-источники/live trading, реальные ордера
- WebSocket, Redis, Kafka, Kubernetes
- ML, множественные стратегии "из коробки", сложная оптимизация
- Parameter grid, multiprocessing
- Short-позиции (пока)
- Comparison UI / исследовательский слой сравнения (Фаза 17 — предварительная идея, см. ниже)

## Зависимости между фазами

```
Фаза 12 (Historical Data Layer)
      ↓
Фаза 13 (Strategy API & Signal Contract)
      ↓
Фаза 14 (First Strategy: MA Crossover)          — проектируется вместе с Фазой 13,
      ↓                                            реализуется отдельной фазой
Фаза 15 (Historical Backtest Engine)
      ↓
Фаза 16a (Experiment System Integration — backend)
      ↓
Фаза 16b (Experiment System Integration — frontend)
      ↓
Фаза 17+ (предварительная идея, не спроектирована)
```

Каждая фаза строго зависит от предыдущей и не начинается без подтверждения завершения предыдущей
(как и в MVP-плане).

---

## Фаза 12 — Historical Data Layer ✅

**Цель.** Добавить независимый от бэктест-движка слой загрузки и валидации исторических рыночных
данных. Первый источник — CSV.

**Что меняется.** Полностью новый, изолированный пакет. Ничего в существующем `experiments/`,
`simulation/`, `statistics/`, `storage/`, `api/` не меняется — Фаза 12 ничего не ломает.

**Затронутые существующие компоненты.**
- `src/vectorx/core/errors.py` — добавляется новый тип ошибки (`InvalidMarketDataError`).
- `src/vectorx/core/types.py` — не меняется (`MarketCandle` живёт в `marketdata/`, а не в `core`,
  т.к. это не тип, производимый симуляцией).

**Новые компоненты.**
```
src/vectorx/marketdata/
    types.py       — MarketCandle, MarketData
    source.py      — DataSource (Protocol)
    csv_source.py  — CsvDataSource (первая реализация)
    validation.py  — validate_market_data (провайдер-независимая)
```
- `MarketCandle` — неизменяемый контейнер: `timestamp` (UTC-aware `datetime`), `open`, `high`, `low`,
  `close`, `volume`.
- `MarketData` — метаданные набора + свечи: `symbol: str`, `timeframe: str`,
  `candles: tuple[MarketCandle, ...]`.
- `DataSource` — `Protocol` (`runtime_checkable`, по образцу `storage/repository.py`) с методом
  загрузки, возвращающим `MarketData`.
- `CsvDataSource(path, symbol, timeframe)` — реализация `DataSource`; читает CSV через stdlib
  `csv.DictReader`, ожидает фиксированные имена колонок
  (`timestamp,open,high,low,close,volume`), нормализует их в `MarketCandle`.
- `validate_market_data(data: MarketData) -> None` — не знает о CSV/будущих источниках; работает
  только с уже нормализованным `MarketData`.

**Что НЕ входит.**
- Parquet, pandas, pyarrow, polars.
- MEXC/CCXT/любые live/API источники.
- Кэширование, потоковая загрузка, партиционирование больших файлов.
- Интеграция с `ExperimentSpec`/`ExperimentRunner` (это Фаза 16a).
- Исправление пропусков/дубликатов (только обнаружение, не gap-filling/интерполяция).
- Configurable column mapping для CSV (фиксированные имена колонок в v1; расширяемость — когда
  появится второй источник с другими именами).

**Критерии acceptance.**
- `CsvDataSource(...).load()` возвращает корректный `MarketData` с типизированными `MarketCandle`.
- `validate_market_data()` бросает `InvalidMarketDataError` на: невозрастающий или задублированный
  `timestamp`, `low > high`, `open`/`close` вне `[low, high]`, отрицательный `volume`.
- Провайдер-независимость подтверждена тестами: `test_validation.py` не импортирует `csv_source`.
- Фикстурный CSV-файл с реалистичными OHLCV-данными грузится и проходит валидацию end-to-end.
- Существующие тесты (117/117 на момент MVP) не сломаны, `ruff check .` чист.

**Тесты.**
- `tests/marketdata/test_types.py` — `MarketCandle`/`MarketData` как плоские неизменяемые
  контейнеры (аналог `tests/core/test_types.py`).
- `tests/marketdata/test_csv_source.py` — валидный CSV грузится корректно; отсутствующая/
  некорректная колонка → понятная ошибка.
- `tests/marketdata/test_validation.py` — по тесту на каждое правило (дубликат timestamp,
  невозрастающий timestamp, `low>high`, `close` вне диапазона, отрицательный volume, валидные данные
  проходят без ошибок).
- `tests/marketdata/fixtures/sample_ohlcv.csv` — общая fixture.

**Архитектурные решения, которые нужно принять до реализации.**
1. Формат `timestamp` в CSV фиксируется как единственный поддерживаемый вход для v1 (рекомендация:
   ISO 8601 строка, обязательно UTC) — расширение форматов позже, при появлении такой потребности.
2. Имена колонок CSV фиксированы (`timestamp,open,high,low,close,volume`), без настраиваемого
   маппинга в этой фазе.
3. Gap-detection (пропуски по ожидаемому интервалу timeframe) — рекомендация: реализовать как
   диагностику внутри `validate_market_data`, но **не** бросать исключение на обнаруженный пропуск
   (пропуски в реальных данных — нормальная ситуация, а не всегда ошибка); решение нужно
   зафиксировать явно перед началом кодирования.

**Сделано 2026-09-22, TDD (red→green).** Реализовано в `src/vectorx/marketdata/`:
- `types.py` — `MarketCandle` (`timestamp` обязательно timezone-aware, `open/high/low/close/volume`),
  `MarketData` (`symbol`, `timeframe`, `candles`) — неизменяемые `@dataclass(frozen=True, slots=True)`,
  без логики, по образцу `core/types.py`.
- `source.py` — `DataSource` (`Protocol`, `runtime_checkable`), по образцу
  `storage/repository.py::ExperimentRepository`.
- `csv_source.py` — `CsvDataSource(path, symbol, timeframe)`: stdlib `csv.DictReader`, фиксированные
  колонки `timestamp,open,high,low,close,volume`, ISO 8601 timestamp (обязателен offset/`Z`, наивные
  timestamp отклоняются), некорректные числа/отсутствующие колонки/пустой CSV → `InvalidMarketDataError`.
- `validation.py` — `validate_market_data(data, expected_interval=None) -> tuple[MarketDataGap, ...]`:
  бросает `InvalidMarketDataError` на пустой набор, дублирующийся/невозрастающий timestamp,
  `low>high`, `open`/`close` вне `[low, high]`, отрицательный `volume`; пропуски (gaps) относительно
  `expected_interval` — не фатальны, возвращаются как `MarketDataGap` для диагностики, не бросают.
- `core/errors.py`: `+InvalidMarketDataError(VectorXError)`.

25 новых тестов зелёные (`tests/marketdata/{test_types,test_source_protocol,test_validation,
test_csv_source}.py` + fixture `sample_ohlcv.csv`), полный набор 139/139, `ruff check .` чист.
Формат timestamp (ISO 8601, обязательно UTC-aware), фиксированные имена CSV-колонок и non-fatal
gap-detection — решения приняты и реализованы как описано выше.

---

## Фаза 13 — Strategy API & Signal Contract ✅

**Цель.** Определить чистый, независимый от инфраструктуры контракт `MarketData → Strategy →
Signal`, на основе которого будет работать Backtest Engine (Фаза 15). Проектируется вместе с
Фазой 14, но реализуется отдельной фазой.

**Что меняется.** Новый пакет; ничего существующего не меняется.

**Затронутые существующие компоненты.** Нет прямых изменений. Контракт проектируется с учётом того,
как Фаза 15 будет "кормить" стратегию данными.

**Новые компоненты.**
```
src/vectorx/strategy/
    signal.py     — Signal (BUY / SELL / HOLD)
    protocol.py   — Strategy (Protocol)
```
- `Signal` — простой enum v1: `BUY`, `SELL`, `HOLD`. Без confidence/weight/size — расширение не
  сейчас.
- `Strategy` — `Protocol` с push-моделью: метод получает одну `MarketCandle` за раз и возвращает
  `Signal`; стратегия сама владеет своим внутренним состоянием (rolling window и т.п.).

**Что НЕ входит.**
- Сама MA Crossover реализация (Фаза 14).
- Интеграция с Backtest Engine (структурно Фаза 15, хотя контракт проектируется совместно).

**Критерии acceptance.**
- Контракт `Strategy`/`Signal` определён и задокументирован.
- Покрыт unit-тестом на простейшей fake-стратегии ("always HOLD", "BUY на первой свече затем
  HOLD"), подтверждающим, что интерфейс вызываем и достаточен.

**Тесты.**
- `tests/strategy/test_signal.py`.
- `tests/strategy/test_strategy_protocol.py` — fake-реализация, `runtime_checkable`-проверка.

**Архитектурные решения до реализации.**
1. Push (`on_candle(candle) -> Signal`) vs pull (`get_signal(window) -> Signal`) — рекомендация:
   push, стратегия хранит состояние сама (проще тестировать по одной свече, соответствует
   "Candle 1, Candle 2, ..., Candle N" из идеи пользователя).
2. `Signal` — enum без параметров в v1 (без confidence/weight) — фиксируется явно.
3. Кто владеет position-state (уже "в рынке" или нет)? Рекомендация: `Strategy` сигнализирует
   только намерение направления; фактическое управление позицией (не открывать повторно, если уже
   в позиции; игнорировать `SELL` без открытой long-позиции) — ответственность Backtest Engine, не
   стратегии. Это то же разделение ответственности, что уже есть между `Trade`-генерацией и
   `PortfolioSimulator`.

**Сделано 2026-09-22, TDD (red→green).** Реализовано в `src/vectorx/strategy/`:
- `signal.py` — `Signal(StrEnum)`: `BUY`/`SELL`/`HOLD`, без confidence/weight/size.
- `protocol.py` — `Strategy` (`Protocol`, `runtime_checkable`), push-модель:
  `on_candle(candle: MarketCandle) -> Signal`; стратегия сама хранит своё состояние, ничего не
  знает о позициях/капитале/PostgreSQL/FastAPI/Vue.

6 новых тестов зелёные (`tests/strategy/{test_signal,test_strategy_protocol}.py`, включая
fake-стратегии "always HOLD" и "BUY на первой свече затем HOLD" из критериев acceptance), полный
набор 145/145, `ruff check .` чист. Все три архитектурных решения (push-модель, enum без
параметров, Strategy не владеет position-state) приняты и реализованы как описано выше.

---

## Фаза 14 — First Strategy: Moving Average Crossover ✅

**Цель.** Реализовать первую конкретную детерминированную стратегию, подтверждающую, что контракт
Фазы 13 достаточен и удобен на практике.

**Что меняется.** Добавляется конкретная реализация `Strategy`. Сам контракт Фазы 13 не меняется
(если тестирование не покажет обратного — тогда правки идут в модуль Фазы 13, отдельной фазы не
заводится).

**Затронутые существующие компоненты.** Нет.

**Новые компоненты.**
- `src/vectorx/strategy/moving_average_crossover.py` — `MovingAverageCrossoverStrategy(fast_period,
  slow_period)`: держит rolling buffer close-цен, `BUY` при пересечении fast>slow снизу вверх,
  `SELL` при обратном пересечении, иначе `HOLD`.

**Что НЕ входит.**
- Short-позиции.
- Множественные инструменты одновременно.
- Оптимизация периодов, любые другие стратегии (Momentum/Mean Reversion — не сейчас).

**Критерии acceptance.**
- На синтетическом наборе свечей с заранее известными пересечениями стратегия генерирует ожидаемую
  последовательность сигналов.
- До накопления `slow_period` свечей — `HOLD`, не ошибка.

**Тесты.**
- `tests/strategy/test_moving_average_crossover.py` — детерминированные fixture-данные с известными
  пересечениями; edge cases (warm-up period, плоские цены → нет пересечения).

**Архитектурные решения до реализации.**
1. SMA, не EMA — для простоты и детерминированности v1.
2. `SELL`-сигнал без открытой long-позиции — Backtest Engine его игнорирует (не открывает short);
   зафиксировано уже в Фазе 13.

**Сделано 2026-09-22, TDD (red→green).** Реализовано в
`src/vectorx/strategy/moving_average_crossover.py`:
- `MovingAverageCrossoverStrategy(fast_period, slow_period)` — `deque(maxlen=slow_period)` как
  rolling buffer close-цен; `BUY`/`SELL` определяются по смене знака `fast_sma - slow_sma` между
  предыдущим и текущим candle (первый расчёт после warm-up только фиксирует состояние, не даёт
  сигнала); плоские цены (`diff` всегда `0.0`) никогда не пересекают строгое `>`/`<` условие.

4 новых теста зелёные (`tests/strategy/test_moving_average_crossover.py`: warm-up period, плоские
цены, детерминированная последовательность из 12 свечей с двумя BUY и одним SELL, Protocol-
соответствие), полный набор 149/149, `ruff check .` чист.

---

## Фаза 15 — Historical Backtest Engine ✅

**Цель.** Последовательно пройти по `MarketData.candles`, на каждой свече запросить сигнал у
`Strategy`, преобразовать сигналы в `Trade[]`, совместимый с существующим `PortfolioSimulator`.

**Что меняется.**
- `src/vectorx/statistics/metrics.py` — `compute_metrics()`: параметры `p_win`/`win_r`/`loss_r`
  становятся `float | None = None`; если не переданы — `expectancy_theoretical=None`.
- `src/vectorx/core/types.py` — `Metrics.expectancy_theoretical: float | None`.
- **Не меняется**: `simulate_portfolio()` и `compute_experiment_summary()` — переиспользуются как
  есть.

**Затронутые существующие компоненты.** `statistics/metrics.py`, `core/types.py` (изменение типа
поля обратно совместимо: вызывающий код с явными `p_win/win_r/loss_r` продолжает работать как
раньше).

**Новые компоненты.**
- `src/vectorx/backtest/engine.py` — `run_historical_backtest(market_data: MarketData, strategy:
  Strategy) -> tuple[Trade, ...]`: итерирует по свечам, вызывает `strategy.on_candle(candle)`,
  конвертирует переходы `BUY`/`SELL` во вход/выход из позиции, вычисляет `r_multiple` по ценам
  входа/выхода, заполняет `entry_ts`/`exit_ts`/`pnl`; `size`/`pnl_money` остаются пустыми (их
  заполняет `simulate_portfolio()`, как и для Monte Carlo).

**Что НЕ входит.**
- Интеграция с `ExperimentSpec`/YAML (Фаза 16a).
- Сравнение с theoretical (Фаза 17).
- Множественные позиции/short.
- Денежные комиссии/slippage — переиспользуется существующая R-based модель.

**Критерии acceptance.**
- На фиксированном фикстурном наборе свечей + MA Crossover движок производит детерминированный,
  воспроизводимый повторным запуском `Trade[]`.
- Результирующий `Trade[]` проходит через `simulate_portfolio()` без единого изменения в этой
  функции.
- `compute_metrics()` на этом `Trade[]` возвращает `expectancy_theoretical=None`, остальные метрики
  вычисляются корректно.

**Тесты.**
- `tests/backtest/test_engine.py` — end-to-end на фикстурных свечах + MA Crossover → ожидаемый
  `Trade[]`.
- `tests/statistics/test_metrics.py` — новые кейсы: без `p_win/win_r/loss_r` →
  `expectancy_theoretical is None`; существующие кейсы с параметрами — regression, не ломаются.
- Интеграционный тест полного цикла: `Trade[]` из backtest engine → `simulate_portfolio()` →
  `compute_metrics()`, без Monte Carlo.

**Архитектурные решения до реализации (требуют отдельного обсуждения перед стартом фазы).**
1. **Как считать `r_multiple` сделки из реальных цен?** Это ключевой открытый вопрос: нужна явная
   "risk model", конвертирующая price PnL → R (например через `stop_loss_pct`, определяющий unit
   риска на уровне стратегии/эксперимента). Не решается в рамках этого roadmap-документа —
   отдельное обсуждение перед началом Фазы 15.
2. Что происходит с открытой позицией на последней свече датасета? Рекомендация: принудительно
   закрывать по последней `close`-цене, чтобы не терять данные о сделке.
3. Один инструмент / один timeframe за эксперимент — фиксируется для этой фазы; мульти-
   инструментальные портфели не рассматриваются.

**Сделано 2026-09-23, TDD (red→green).**
- **Решение по вопросу 1 (обсуждено и подтверждено отдельно):** `stop_loss_pct` — параметр
  стратегии (не движка), хранится как публичный атрибут (`Strategy.stop_loss_pct`), добавлен в
  `Strategy` Protocol (Фаза 13) и в `MovingAverageCrossoverStrategy` (Фаза 14). Используется
  **только** как единица измерения при переводе price PnL → R:
  `r_multiple = (exit_price - entry_price) / (entry_price * stop_loss_pct)`. Реальный intrabar-
  триггер стопа (закрытие сделки по `low`/`high`, а не только по сигналу стратегии) сознательно
  отложен — рассматривались оба варианта, выбран вариант без реального исполнения стопа
  (проще, детерминированнее, не создаёт неразрешимую по OHLC-данным двусмысленность
  "что сработало раньше в свече"). Возможное будущее расширение, не часть Фазы 15.
- `src/vectorx/backtest/engine.py` — `run_historical_backtest(market_data, strategy) ->
  tuple[Trade, ...]`: long/flat, без pyramiding (повторный `BUY` в позиции игнорируется), без
  short (`SELL` без открытой позиции игнорируется), принудительное закрытие открытой позиции по
  `close` последней свечи.
- `src/vectorx/statistics/metrics.py` / `core/types.py` — `compute_metrics()` и
  `Metrics.expectancy_theoretical` — параметры модели опциональны (`float | None`), обратно
  совместимо с существующими вызовами через keyword-аргументы.

10 новых/обновлённых тестов зелёные (`tests/backtest/test_engine.py`,
`tests/statistics/test_metrics.py`, `tests/strategy/{test_strategy_protocol,
test_moving_average_crossover}.py`), полный набор 159/159, `ruff check .` чист. Отдельный
интеграционный тест подтверждает: `Trade[]` из backtest engine проходит через
`simulate_portfolio()` без единого изменения в этой функции.

---

## Фаза 16a — Experiment System Integration (backend) ✅

**Цель.** Сделать historical backtest полноценным типом эксперимента в существующей
Experiment/Storage/API системе, без потери обратной совместимости с текущими Monte Carlo YAML.

**Что меняется.**
- `experiments/spec.py` — `ExperimentSpec` становится дискриминированным union по полю
  `type: Literal["monte_carlo", "historical_backtest"]`, default `"monte_carlo"` для существующих
  YAML без поля `type`.
- `experiments/runner.py` — `run_experiment()`: dispatch по `spec.type`. Monte Carlo ветка — код без
  изменений. Historical ветка — DataSource (Фаза 12) → Backtest Engine (Фаза 15) →
  `simulate_portfolio` → `compute_metrics(..., p_win=None, win_r=None, loss_r=None)` →
  `compute_experiment_summary` (с `runs=1`).
- `storage/postgres/repository.py` — `_params_from_spec()` обобщается (не хардкодит
  `.model`/`.portfolio`).
- `storage/postgres/models.py` — `RunRow.expectancy_theoretical` → nullable.
- Новая Alembic-миграция на nullable-колонку.
- Resource limit для historical (замена `MAX_OPERATIONS = runs*n_trades`): лимит по количеству
  свечей в `MarketData`.

**Затронутые существующие компоненты.** `experiments/spec.py`, `experiments/runner.py`,
`storage/postgres/{models,repository,serializers}.py`, `alembic/versions/`.

**Новые компоненты.**
- `ExperimentHistoricalBacktestSpec` (секции `data`/`strategy`/`portfolio` — точный YAML-формат
  фиксируется в начале этой фазы, сознательно не определяется сейчас).
- Новая Alembic-миграция.

**Что НЕ входит.** Изменения во frontend (Фаза 16b), Фаза 17 comparison logic, parameter grid.

**Критерии acceptance.**
- Все существующие Monte Carlo YAML (без `type`) продолжают парситься и запускаться без изменений
  в результатах — regression на фиксированном seed, побитово идентичные метрики.
- Новый YAML с `type: historical_backtest` парсится, запускается, сохраняется в Postgres и читается
  обратно через `get_experiment()`.
- Решение по `EXPERIMENT_VERSION` (остаётся `1` или увеличивается) явно зафиксировано и обосновано
  в этой фазе.

**Тесты.**
- `tests/experiments/test_spec.py` — YAML без `type` → `type == "monte_carlo"`; YAML с
  `type: historical_backtest` → правильный подтип; невалидный `type` → ошибка валидации.
- `tests/experiments/test_runner.py` — dispatch на оба типа; regression на существующих Monte Carlo
  кейсах.
- `tests/storage/test_postgres_repository.py` — round-trip historical эксперимента с
  `expectancy_theoretical=None`.
- Migration test (upgrade/downgrade), как в Фазе 8.

**Архитектурные решения до реализации.**
1. Точная YAML-структура секций `data`/`strategy` для historical — решается в начале этой фазы,
   после того как API Фаз 12-15 устоятся на практике.
2. Один и тот же набор эндпоинтов `/experiments` обрабатывает оба типа через единый `ExperimentSpec`
   (рекомендация) — отдельных historical-эндпоинтов не заводится.
3. Точное числовое значение resource limit по количеству свечей — определяется в этой фазе.

**Сделано 2026-09-23, TDD (red→green).**
- **Полиморфизм `ExperimentSpec`:** реализован как discriminated union
  (`Annotated[MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec, Field(discriminator="type"),
  BeforeValidator(...)]`), а не как класс — существующие вызовы `ExperimentSpec.model_validate(dict)`
  в тестах/storage заменены на новую `parse_experiment_spec(raw)` (Union-типы не имеют
  `.model_validate`). `BeforeValidator` подставляет `type: monte_carlo` при отсутствии ключа —
  проверено отдельным изолированным prototype на pydantic 2.13.5 и FastAPI 0.11x до внедрения в основной
  код — работает идентично и через `TypeAdapter`, и как тип параметра FastAPI-эндпоинта.
  `EXPERIMENT_VERSION` остался `1` (аддитивное изменение).
- **YAML-схема зафиксирована:** `type: historical_backtest`, `data: {source: csv, path, symbol,
  timeframe}`, `strategy: {type: moving_average_crossover, fast_period, slow_period, stop_loss_pct}`,
  `portfolio` — та же секция, что и у Monte Carlo. `runs` зафиксирован `Literal[1]` на уровне схемы
  (попытка передать другое значение — ошибка валидации, не тихое игнорирование).
- `experiments/runner.py` — `run_experiment()` диспатчит по `isinstance(spec, MonteCarloExperimentSpec)`;
  старая логика вынесена в `_run_monte_carlo_experiment()` без изменений; новая
  `_run_historical_backtest_experiment()`: `CsvDataSource` → `validate_market_data` → candle-limit
  guard → `MovingAverageCrossoverStrategy` → `run_historical_backtest` → те же `simulate_portfolio`/
  `compute_metrics`/`compute_experiment_summary`, что и у Monte Carlo.
- `MAX_HISTORICAL_CANDLES = 500_000` — отдельный resource-гард (по числу свечей после
  загрузки, т.к. размер данных не известен до загрузки CSV целиком), без изменения `MAX_OPERATIONS`.
- `storage/postgres/repository.py` — `_params_from_spec()` диспатчит по типу spec;
  `get_experiment()` использует `parse_experiment_spec()`.
- `storage/postgres/models.py` — `RunRow.expectancy_theoretical` — `nullable=True`; новая
  Alembic-миграция `91ad64596bcc` (`alter_column(..., nullable=True)`, цепочка от `588e5c05d5ab`).

27 новых/обновлённых теста зелёные (`tests/experiments/{test_spec,test_runner}.py`,
`tests/storage/test_postgres_repository.py`, `tests/api/test_main.py` — включая historical-эксперимент
через тот же `POST /experiments`), полный набор 170/170 (включая интеграционные против
реального эфемерного Postgres, с применённой новой миграцией), `ruff check .` чист.
Все существовавшие Monte Carlo тесты (spec/runner/storage/api) прошли без изменений в ожидаемых
результатах — подтверждая обратную совместимость.

---

## Фаза 16b — Experiment System Integration (frontend) ✅

**Цель.** Dashboard корректно отображает historical-эксперименты, не падая на отсутствующих
Monte-Carlo-специфичных полях.

**Что меняется.** `web/src/types.ts`, `ExperimentDetail.vue`, `RunsTable.vue` — null-safe рендеринг
`expectancy_theoretical`, отображение `spec.type`, обобщённый (generic key-value) рендер параметров
для historical вместо предположения о форме Monte Carlo (`model`/`portfolio.risk_per_trade`).

**Затронутые существующие компоненты.** `web/src/types.ts`,
`web/src/components/{ExperimentDetail,RunsTable,ExperimentsList}.vue`.

**Новые компоненты.** Возможно небольшой бейдж/индикатор типа эксперимента.

**Что НЕ входит.** Полноценный UI для historical-специфичных параметров (редактор конфигурации
стратегии и т.п.), comparison UI (Фаза 17).

**Критерии acceptance.**
- Существующие Monte Carlo эксперименты рендерятся как раньше (regression).
- Historical эксперимент (`expectancy_theoretical: null`, `spec.type: "historical_backtest"`)
  рендерится без ошибок.

**Тесты.** Обновление существующих `.test.ts` компонентов + новый кейс с `expectancy_theoretical:
null` и `spec.type === "historical_backtest"`.

**Архитектурные решения до реализации.** Насколько подробно показывать historical-специфичные
поля spec на этом этапе — рекомендация: минимально, обобщённый JSON/key-value рендер, без
специального UI (чтобы не начинать "UI для десятков стратегий" раньше времени).

**Сделано 2026-09-23, TDD (red→green).**
- `web/src/types.ts` — `Metrics.expectancy_theoretical: number | null`; `ExperimentSpec` стал
  дискриминированным union'ом `MonteCarloExperimentSpec | HistoricalBacktestExperimentSpec`
  (поле `type` как discriminant), зеркально отражая бэкенд-схему из Фазы 16a.
- `ExperimentDetail.vue` — секция Parameters ветвится по `spec.type`: Monte Carlo — прежняя
  вёрстка полей без изменений; historical — новый computed `historicalParamEntries`
  уплощает `data`/`strategy`/`portfolio` в плоский список ключ-значение (`data.symbol`,
  `strategy.fast_period` и т.д.) без жёсткой привязки к конкретным полям.
- `RunsTable.vue` — в Фазе 16b без изменений: `expectancy_theoretical` там и раньше не
  рендерился (только `expectancy_sample`), поэтому `null` тут никогда не вызывал риска падения —
  добавлентест подтверждает это явно. В дополнении 2026-09-27 в эту таблицу добавлена колонка
  `Trades` для наблюдаемости количества сделок.
- `ExperimentsList.vue` — проверен, изменений не потребовалось: `ExperimentSummaryItem`
  (API-ответ `GET /experiments`) уже полностью типо-агностичен и не содержит `spec`/`type` вообще
  (бэйдж-индикатор типа в списке потребовал бы изменения `api/serialization.py`, вне скопа
  фронтенд-толькой фазы — отложено).

2 новых теста зелёные (historical-кейс в `ExperimentDetail.test.ts`, null-кейс в
`RunsTable.test.ts`), полный frontend-набор 27/27 (`vitest`), `vue-tsc --noEmit` и `vite build`
чисты. Бэкенд: 170/170 (без изменений — Phase 16b чисто frontend).

---

## Исторические данные и observability — дополнение ✅

**Сделано 2026-09-27.** Добавлен первый реальный снимок исторических OHLCV-данных и
наблюдаемые показатели количества сделок/итогового капитала.

**Данные.**
- Загружены часовые (`1h`) свечи `BTCUSDT`, `ETHUSDT`, `SOLUSDT` из публичного
  Binance API за период `2024-09-27 … 2026-09-27` — по `17 540` свечей на инструмент.
- Файлы сохранены как `configs/experiments/data/btc_1h.csv`,
  `configs/experiments/data/eth_1h.csv`, `configs/experiments/data/sol_1h.csv`.
- Формат совпадает с контрактом `CsvDataSource`: колонки
  `timestamp,open,high,low,close,volume`; timestamp — UTC ISO 8601.
- Это локальный снимок данных, а не live-источник: рантайм-загрузка из Binance/MEXC/CCXT
  в текущем scope не добавлялась. Обновление снимка выполняется отдельной загрузкой CSV.

**Конфигурации экспериментов.**
- `configs/experiments/btc_1h.yaml`, `configs/experiments/eth_1h.yaml`,
  `configs/experiments/sol_1h.yaml`.
- Все три используют `type: historical_backtest`, Moving Average Crossover
  (`fast_period=10`, `slow_period=30`, `stop_loss_pct=0.01`), капитал `10 000` и
  `risk_per_trade=0.01`.

**Observability в UI.**
- `ExperimentDetail.vue` теперь показывает `Final capital` в Summary; значение
  вычисляется из последней точки equity curve (fallback — `initial_capital × (1 + mean_return)`).
- `RunsTable.vue` теперь показывает колонку `Trades` — число сделок каждого run.
- В Summary добавлена `Total trades` — сумма сделок всех runs.
- Для historical-экспериментов добавлено пояснение: `runs=1`, потому что один фиксированный
  набор исторических данных проигрывается один раз детерминированно. Несколько runs имеют
  смысл для Monte Carlo, где случайные выборки оценивают распределение исходов.

**Текущий снимок результатов.**
- `BTCUSDT`: `337` сделок; `ETHUSDT`: `344` сделки; `SOLUSDT`: `340` сделок.
- Все три эксперимента сохранены одной исторической run каждый и доступны через API/UI.

**Проверка.**
- Frontend: `npm test -- --run` — 27/27 на момент добавления данных; позднее набор расширен
  до 29/29 после локализации и темы; `npm run build` — успешно.
- Данные и конфигурации запускаются существующим pipeline
  `CsvDataSource → validate_market_data → MovingAverageCrossoverStrategy → Backtest Engine`.

---

## Локализация и тема — дополнение ✅

**Сделано 2026-09-28.** Добавлены переключатели языка и темы для всего dashboard.

**Поведение.**
- Язык интерфейса: `EN / RU`; словарь и переводы находятся в `web/src/preferences.ts`.
- Тема интерфейса: `Light / Dark`; CSS-переменные определяют фон, поверхности, текст,
  границы, акцентные цвета и hover-состояния для обеих тем.
- Выбор языка и темы сохраняется в `localStorage` (`vectorx.locale`, `vectorx.theme`)
  и восстанавливается при следующем открытии сайта.
- `document.documentElement.lang` и `document.documentElement.dataset.theme` обновляются
  вместе с переключателями.

**Затронутые компоненты.**
- `web/src/App.vue` — шапка с сегментированными переключателями `EN/RU` и `Light/Dark`,
  включая `aria-pressed` и keyboard focus.
- `web/src/components/{ExperimentsList,ExperimentDetail,RunsTable,EquityChart}.vue` —
  переведены заголовки, состояния, таблицы, summary, подписи графиков и пояснение
  про `runs=1`; значения данных и технические ключи параметров сохранены без искажений.
- `web/src/style.css` — светлая/тёмная темы через CSS-переменные, адаптивная шапка
  и видимый focus-state.
- `web/src/App.test.ts` — проверки переключения языка и темы, включая сохранение
  настроек в `localStorage`.

**Проверка.**
- `npm test -- --run` — 29/29.
- `npm run build` — успешно.

---

## Будущие этапы после Фазы 16b

### Фаза 17 — сравнение theoretical / sample / historical expectancy ✅

**Сделано 2026-09-30.** Фаза 17 численно сравнивает Monte Carlo и Historical через явное
преобразование исходных R-значений к общей опорной единице `1R = 1%` доли entry price.

#### Цель и границы

Фаза 17 добавляет исследовательский слой поверх уже существующих результатов экспериментов:

1. `theoretical` — аналитическое математическое ожидание Monte Carlo-модели.
2. `sample` — pooled mean `r_multiple` по всем фактически созданным Monte Carlo `Trade[]`.
3. `historical` — pooled mean `r_multiple` по фактически созданным historical `Trade[]`.

Оба источника продолжают использовать единый контракт `Trade[]`, затем
`simulate_portfolio()` → `compute_metrics()` → `ExperimentSummary`. Фаза 17 не создаёт вторую
статистическую pipeline и не меняет `Trade`, `run_historical_backtest()` или
`PortfolioSimulator.simulate_portfolio()`.

#### Типы и уровни модели

Типы размещаются в существующем `src/vectorx/core/types.py`; отдельный параллельный модельный
слой не создаётся.

`ExpectancyEstimate`:

- `value: float` — отсутствие оценки представляется отсутствием объекта, а не `value=None` или `0`.
- `canonical_value: float | None` — значение на общей опорной шкале после реального преобразования.
- `source: theoretical_model | monte_carlo_sample | historical_backtest`.
- `unit: "R"`.
- `sample_size: int | None` — фактически использованные `Trade[]`; `None` для theoretical.
- `planned_sample_size: int | None` — для Monte Carlo sample равно `runs * n_trades`;
  учитывает расхождение с `sample_size` при early-stop/ruin. Для Historical и theoretical — `None`.
- `risk_definition: RiskDefinition`.

`RiskDefinition`:

- `unit: "R"`.
- `normalization_version: "r-v1"`.
- `method: model_r | entry_price_stop_loss_fraction`.
- `risk_unit_fraction: float`.
- `cost_basis: gross_r`.

Для текущих спецификаций:

- Monte Carlo: `method="model_r"`, `risk_unit_fraction=model.risk_unit_fraction`;
  старые YAML без поля получают обратно совместимое значение `0.01`.
- Historical: `method="entry_price_stop_loss_fraction"`,
  `risk_unit_fraction=strategy.stop_loss_pct`; текущий движок вычисляет
  `r_multiple = (exit-entry) / (entry * stop_loss_pct)`.

Существующий `ExperimentSummary.expectancy` становится snapshot одного эксперимента и содержит
только три опциональные оценки:

- Monte Carlo: `theoretical`, `sample`, `historical=None`.
- Historical: `theoretical=None`, `sample=None`, `historical`.

`RiskCompatibility`, deltas и warnings относятся к сопоставлению нескольких экспериментов и
находятся в отдельном derived-объекте `ExpectancyComparisonResult`. Он собирается из сохранённых
`ExperimentSummary`/`Metrics`, не является второй статистической pipeline и по умолчанию не
сохраняется как отдельная сущность.

#### Расчёт оценок

- `theoretical = p_win * win_r + (1 - p_win) * loss_r`.
- `sample = sum(r_multiple всех выбранных Monte Carlo runs) / sample_size`.
- `historical = sum(r_multiple всех выбранных Historical runs) / sample_size`.
- `sample_size` — именно количество фактически использованных `Trade[]`, не количество runs.
  Пример: `100 runs * 1000 trades` даёт `planned_sample_size=100000`; если после ruin фактически
  обработано `87421` сделки, то `sample_size=87421`.
- Historical по умолчанию выбирает единственный run с `run_index=0`.
- Все оценки v1 используют текущий gross-`r_multiple`: `commission`/`slippage` влияют на
  `pnl_money`/equity, но не изменяют `Trade.r_multiple`. Поэтому `cost_basis="gross_r"`.

#### Общая шкала и совместимость risk definition

Режим `normalized_r` не используется. Вместо него применяется открытое математическое
преобразование к канонической шкале `r-v1`, где `reference_risk_fraction=0.01`:

`canonical_value = value * risk_unit_fraction / reference_risk_fraction`.

Таким образом, raw `0.5R` при `1R=2%` становится `1.0` canonical R при `1R=1%`.

Проверка совместимости сравнивает:

- `unit`;
- `normalization_version`;
- `method`;
- `risk_unit_fraction`;
- `cost_basis`.

`model_r` и `entry_price_stop_loss_fraction` считаются преобразуемыми, если указаны
`unit="R"`, `normalization_version="r-v1"`, `cost_basis="gross_r"` и положительный
`risk_unit_fraction`. `RiskCompatibility.same_risk_definition` отдельно показывает, были ли
исходные определения буквально одинаковыми. При различии canonical-дельты всё равно вычисляются,
а warning `risk_definitions_converted` фиксирует преобразование. Неизвестный method или
несовместимые базовые поля запрещают преобразование: deltas остаются `None`, warning —
`risk_definitions_incompatible`.

#### Deltas

Имена и направление фиксируются до API-контракта:

- `delta_theoretical_sample = theoretical - sample`.
- `delta_theoretical_historical = theoretical - historical`.
- `delta_sample_historical = sample - historical`.

Deltas вычисляются из `canonical_value`, строго по формулам `first - second`. Если оценка
отсутствует или преобразование не поддерживается, значение delta — `None`.

#### Persistence, API и UI

- Snapshot оценок хранится внутри существующего JSONB-поля `experiments.summary`; отдельная
  таблица comparisons в v1 не требуется.
- Сериализаторы summary обязаны сохранять и восстанавливать snapshot. Легаси-summary без нового
  поля загружается с `expectancy=None`.
- Сравнение выполняется `POST /comparisons/expectancy` поверх сохранённых экспериментов; frontend только
  отображает готовые оценки, compatibility, deltas и warnings и ничего не пересчитывает.
- UI показывает raw и canonical значения, `sample_size`/`planned_sample_size`, источник и risk
  definition. При несовместимости он отображает `None` как прочерк и показывает warning.

#### Acceptance criteria

- `100 runs * 1000 trades` без early-stop даёт `sample_size=100000` и
  `planned_sample_size=100000`; при обработанных после ruin `87421` сделках — `87421` и `100000`.
- Отсутствующая оценка сериализуется как отсутствие объекта (`None`), не как `value=0`.
- Одинаковые risk definitions не выполняют масштабирование; разные преобразуются по формуле выше.
- Совместимые оценки получают canonical deltas строго по формулам `first - second`.
- Непреобразуемые `RiskDefinition` не создают никаких числовых deltas и возвращают явный warning.
- Snapshot одного `ExperimentSummary` не содержит cross-experiment compatibility/deltas.
- `Trade[]`, `simulate_portfolio()`, `run_historical_backtest()` и существующая formula
  `expectancy_sample()` не меняются.

#### Проверка

- Backend: `178/178` тестов, включая API и ephemeral Postgres.
- Frontend: `31/31` тестов, `npm run build` успешно.
- `ruff check .` чисто.

### Далее (не спроектировано, вне текущего scope)

Дополнительные источники данных (MEXC/CCXT/live), множественные стратегии, параметрическая
оптимизация, live paper trading — остаются вне scope до отдельного решения после Фазы 17.
