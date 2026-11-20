# VectorX — план исправления результатов код-ревью

**Дата:** 2026-11-18  
**Базовая ветка:** `research-platform-v1`  
**Базовый коммит:** `d39698164208e86933283c6572ad50169bdb18cd`  
**Исходное состояние проверок:** 318 backend-тестов и 56 frontend-тестов зелёные.

Документ фиксирует порядок устранения проблем, найденных при код-ревью. Это план реализации, а не отчёт о уже внесённых исправлениях.

## Результат реализации — выполнено

**Дата завершения:** 2026-11-19.

Все фазы реализованы:

- preflight/aggregate guards для sweep, Monte Carlo, walk-forward и bootstrap;
- finite/OHLCV/CSV/seed/AwareDatetime валидация;
- next-open execution, empty historical runs и nullable trade-derived metrics;
- отдельные gross/net R-метрики, `EXPERIMENT_VERSION=2`, `ANALYSIS_VERSION=2`;
- Alembic-миграция `f4b8d2c61a90` с nullable empty-метриками и net-полями;
- summary-only PostgreSQL projections, pagination, bounded trade inserts и атомарные batches;
- in-memory OOS с indicator warm-up, content hash срезов и отсутствием временных CSV;
- block bootstrap без cross-run блоков и с `gross_r`/`net_r` cost basis;
- source hash, dependency provenance и run-level export;
- frontend error/stale-state handling, discriminated unions, keyboard/accessibility и responsive layouts;
- PostgreSQL только на loopback и CSV sandbox через `VECTORX_DATA_ROOT`;
- полная фиксация прямых и транзитивных исследовательских зависимостей в `uv.lock`.

Проверено: 361 backend-тест и 59 frontend-тестов, Ruff, production build, миграция
`downgrade base → upgrade head`, реальные API/OOS/robustness сценарии. Визуальная проверка
320px в браузере не автоматизирована; responsive-правила и keyboard interactions покрыты
компонентными тестами и production build.

## 1. Цели

1. Исключить исчерпание CPU/RAM до срабатывания resource-guard'ов.
2. Устранить execution bias и сделать стоимостную модель статистики однозначной.
3. Не загружать сырые сделки там, где нужны только summary.
4. Сделать batch-запуски атомарными, а robustness-статистику корректной для нескольких runs.
5. Не выдавать ошибки загрузки за валидные нулевые результаты.
6. Усилить валидацию данных, воспроизводимость, типизацию и доступность UI.
7. Сохранить локальный research-scope: без live trading, очередей, ML и автоматической оптимизации параметров.

## 2. Общие правила реализации

- Каждая фаза начинается с regression-тестов, воспроизводящих проблему.
- Численные изменения не маскируются под refactor: для них обновляются соответствующие версии и документация.
- Существующий конвейер `Trade[] → PortfolioSimulator → Metrics → Summary` сохраняется.
- Второй execution/statistics pipeline для historical, OOS или robustness не создаётся.
- Изменения схемы БД выполняются только через Alembic с upgrade/downgrade-тестами.
- Легаси-эксперименты остаются читаемыми. Их результаты не переписываются под новые алгоритмы.
- После каждой фазы: `pytest`, `ruff check .`, `npm test`, `npm run build`.
- Коммиты разделяются по фазам; исправления расчётной семантики не смешиваются с косметическими правками.

---

## Фаза 0 — Характеризационные тесты и базовые измерения

**Цель:** зафиксировать текущее поведение там, где его изменение может скрытно нарушить совместимость.

### Работы

- [ ] Записать эталонные результаты небольших Monte Carlo и historical экспериментов: метрики, equity, R-значения, API JSON и export.
- [ ] Добавить query-count fixture для PostgreSQL и измерить запросы `GET /experiments`, detail, results, equity и analysis.
- [ ] Измерить память/время на малых входах для sweep, walk-forward, bootstrap и CSV, чтобы регрессии можно было проверять без тяжёлого CI.
- [ ] Отметить, какие существующие тесты закрепляют ошибочную same-close семантику и должны быть изменены, а какие являются настоящими regression-тестами.

### Новые тесты

- `tests/characterization/test_experiment_contract.py`
- `tests/storage/test_query_counts.py`
- `tests/api/test_response_contracts.py`

### Критерий завершения

Есть задокументированная база для различия «намеренно изменённый результат» и «случайная регрессия».

---

## Фаза 1 — Resource safety и входная валидация

### 1.1. Preflight для parameter sweep

**Проблема:** `src/vectorx/experiments/sweep.py:56` материализует декартово произведение до лимита.

- [ ] Вычислять размер через `math.prod(len(values) for values in grid.values())` до `itertools.product`.
- [ ] Немедленно отклонять пустой список значений с понятной доменной ошибкой.
- [ ] После preflight генерировать комбинации лениво.
- [ ] Добавить совокупный бюджет `sum(runs * n_trades)` для batch и sensitivity, а не только лимит 100 спецификаций.
- [ ] Добавить независимые лимиты `runs` и `n_trades`, поскольку произведение само по себе не ограничивает число ORM/DOM-объектов.

**Тесты:**

- сетка с астрономическим числом комбинаций отклоняется без вызова `itertools.product` и без выделения большого списка;
- 101 комбинация → 400;
- пустой value list → 400/422, а не пустой результат;
- превышение aggregate work budget → 400 до первого эксперимента;
- граничные значения ровно на лимите проходят;
- большое `runs` при `n_trades=1` отклоняется.

### 1.2. Preflight для walk-forward

**Проблема:** окна полностью генерируются до проверки в `api/main.py:320`.

- [ ] Вычислять количество полных окон арифметически или передавать `max_windows` в генератор.
- [ ] Прерывать работу при попытке создать 101-е окно.
- [ ] Сохранить текущие inclusive-границы и `_MIN_GAP` без изменения численной семантики.

**Тесты:**

- очень маленький `step` на большом диапазоне отклоняется за ограниченное время;
- ровно 100 окон допускается, 101 — нет;
- пустой набор окон → 400;
- существующие границы окон побитово совпадают с прежними для валидных входов.

### 1.3. Числовая валидация

**Проблема:** NaN/Infinity проходят односторонние сравнения; OHLCV допускает неположительные и нефинитные цены.

- [ ] Требовать `math.isfinite` для всех float-параметров модели, портфеля, стратегий и analysis.
- [ ] Установить `allow_inf_nan=False`/эквивалентные ограничения на Pydantic-полях.
- [ ] Требовать строго положительные OHLC и конечный неотрицательный volume.
- [ ] Проверять CSV-строки на отсутствующие значения; превращать `TypeError`, `ValueError` и ожидаемые `OSError` в `InvalidMarketDataError`.
- [ ] Ограничить seed неотрицательным целым на YAML/API/library-границах.
- [ ] Использовать `AwareDatetime` для OOS и всех новых time-range контрактов.

**Тесты:**

- NaN, `+Infinity`, `-Infinity` для каждого числового поля;
- zero/negative/NaN/inf OHLC и NaN volume;
- truncated CSV row, отсутствующий файл, unreadable path;
- negative seed для Monte Carlo, Random Entry и bootstrap;
- naive и mixed-awareness OOS datetimes → 422, а не 500;
- zero entry price не доходит до деления в `backtest/engine.py`.

### Критерий завершения Фазы 1

Маленький malformed request не может запустить неограниченную работу, а невалидные числовые/рыночные данные отклоняются предсказуемым 400/422.

---

## Фаза 2 — Historical execution и пустые результаты

### 2.1. Устранение same-close execution bias

**Проблема:** сигнал по close свечи исполняется по тому же close в `src/vectorx/backtest/engine.py:43-47`.

- [ ] Разделить `signal_ts` и `execution_ts`.
- [ ] Сигнал на свече `t` исполнять по open свечи `t+1`.
- [ ] Повторный сигнал до исполнения не должен создавать pyramiding или short.
- [ ] Зафиксировать обработку последнего сигнала: он не исполняется без следующей свечи; уже открытая позиция закрывается по явному end-of-data правилу.
- [ ] Обновить timestamps, `pnl`, R-формулу и документацию стратегий.
- [ ] Увеличить `EXPERIMENT_VERSION`, поскольку historical результаты изменятся.

**Тесты:**

- fixture, где close `t` и open `t+1` существенно различаются: вход строго по open `t+1`;
- BUY/SELL, gap up/down, повторный BUY, SELL без позиции;
- сигнал на последней свече;
- принудительное закрытие открытой позиции;
- повторный запуск даёт тот же `Trade[]`;
- старые same-close ожидания заменены ручными next-open расчётами, а не просто новыми snapshot'ами.

### 2.2. Валидный historical run без сделок

**Проблема:** пустой `Trade[]` приводит к `EmptyTradesError`.

- [ ] Для historical empty run создавать equity из начального капитала, `total_return=0`, `max_drawdown=0`, `trades=wins=losses=0`.
- [ ] Trade-derived значения (`expectancy`, win rate, profit factor, Sharpe и др.) представлять как `null`/недоступные, а не нули.
- [ ] Определить явный empty-histogram контракт и поддержать его в API/UI.
- [ ] Monte Carlo с `n_trades=0` по-прежнему отклонять на валидации.
- [ ] Analysis для empty run возвращает понятное «недостаточно сделок», без 500.

**Тесты:**

- flat market + MA, недостаточный warm-up, always-HOLD fake strategy;
- empty sensitivity point не отменяет остальные комбинации;
- empty OOS test возвращает результат с явным `sample_size=0`;
- API и Vue отображают `—` для недоступных метрик и 0% для equity return.

### Критерий завершения Фазы 2

Backtest не использует будущую информацию для исполнения, а отсутствие сделок является валидным исследовательским результатом.

---

## Фаза 3 — Gross/net-метрики и интерпретация статистики

**Проблема:** комиссии и slippage влияют на money equity, но не на основную исследовательскую статистику.

### Работы

- [ ] Сохранить `Trade.r_multiple` как gross R.
- [ ] Добавить `Trade.net_r_multiple = r_multiple - commission_r - slippage_r` в sized trade.
- [ ] Добавить nullable `net_r_multiple` в `trades` через Alembic для совместимости со старыми записями.
- [ ] Не менять молча существующие gross-поля. Добавить явные net-метрики: expectancy, win rate, profit factor и risk-adjusted/significance.
- [ ] Expectancy comparison сравнивает только оценки с одинаковым `cost_basis`; theoretical gross не сравнивается с sample net без явного предупреждения.
- [ ] Для historical significance использовать dependence-aware вариант либо явно показывать i.i.d.-ограничение.
- [ ] Sharpe/Sortino подписать как gross/net, per-trade и unannualized.
- [ ] Calmar для нескольких runs считать per run и показывать распределение; не делить mean return одного набора на max drawdown другого.
- [ ] Показывать commission/slippage для всех типов экспериментов в UI/export.
- [ ] Обновить `EXPERIMENT_VERSION`/`ANALYSIS_VERSION` по фактически изменённым алгоритмам.

### Тесты

- `+0.1R` с издержками `0.2R`: gross win, net loss;
- zero-cost case: gross и net совпадают;
- comparison не смешивает разные `cost_basis` молча;
- сериализация `null`/Infinity единообразна;
- per-run Calmar не комбинирует разные runs;
- round-trip старого trade без `net_r_multiple` и нового trade через PostgreSQL/API/export;
- UI показывает стоимостную базу каждой метрики.

### Критерий завершения

Исследователь может отличить прибыльность до и после издержек, а подписи метрик не допускают ложной time-based/annualized интерпретации.

---

## Фаза 4 — PostgreSQL, атомарность и масштабирование чтения

### 4.1. Проекции вместо полного `get_experiment()`

**Проблема:** summary-запросы восстанавливают все runs и trades.

- [ ] Добавить отдельные repository-методы для summary list, detail metadata, runs, одной equity curve и analysis R-values.
- [ ] `GET /experiments` и batch detail использовать summary-only SQL без `TradeRow`.
- [ ] Analysis читать только `r_multiple`/`net_r_multiple`, без ORM-гидратации всех остальных полей.
- [ ] Не перечитывать полный эксперимент сразу после сохранения, если in-memory результат достаточен.
- [ ] Добавить pagination для experiments и runs; ограничить размер страницы.
- [ ] При чтении нескольких runs устранить N+1 через осознанный eager loading только в нужных проекциях.

**Тесты:**

- query-count для list не растёт линейно от числа experiments/runs;
- list/detail без analysis не обращаются к `trades`;
- equity загружает только выбранный run;
- результаты проекций совпадают с текущим JSON;
- pagination стабильна и проверена на границах.

### 4.2. Атомарный batch

**Проблема:** `api/main.py:242-245` оставляет частичный batch при ошибке.

- [ ] Выполнить все preflight-проверки до `save_batch`.
- [ ] Сохранять batch и его experiments в одной transaction/unit of work.
- [ ] Либо ввести явный `failed` статус с сохранённой ошибкой — только если будет выбрана такая модель; по умолчанию rollback всей группы.
- [ ] Не оставлять успешный префикс при повторном запуске после rollback.

**Тесты:**

- вторая комбинация невалидна: ни batch, ни первый experiment не сохраняются;
- ошибка БД на середине откатывает всю группу;
- повтор после ошибки не создаёт дубликаты;
- успешный batch сохраняет прежнюю структуру ответа.

### 4.3. Ограничение памяти записи и анализа

- [ ] Записывать raw trades bounded chunks/bulk insert вместо одного гигантского ORM graph.
- [ ] Ввести work budget `n_resamples * sample_size` для bootstrap.
- [ ] Block bootstrap вычислять через суммы блоков без полного resampled array на каждой итерации.
- [ ] Автоматический analysis в UI не запускать для заведомо тяжёлых выборок без подтверждения пользователя.

### Критерий завершения Фазы 4

Открытие каталога не загружает все сделки, batch не остаётся частичным, а память записи/анализа ограничена явным бюджетом.

---

## Фаза 5 — OOS, robustness и воспроизводимость

### 5.1. Indicator warm-up для OOS/walk-forward

- [ ] Загружать достаточный pre-test history для MA/Breakout.
- [ ] Во время warm-up обновлять только состояние стратегии; сигналы и позиции warm-up не попадают в scored result.
- [ ] На `test_start` начинать с явного flat state, если иное не выбрано отдельной моделью.
- [ ] Сохранять границы warm-up и scored range в результате.

**Тесты:** сигнал на первой test-свече использует предшествующую историю, но warm-up trades/PnL отсутствуют в метриках.

### 5.2. Block bootstrap с границами runs

**Проблема:** `api/main.py:347` склеивает независимые runs.

- [ ] Historical single sequence сохранить без изменений.
- [ ] Для Monte Carlo ресэмплировать блоки независимо внутри каждого run.
- [ ] Объединять run means с весами фактических длин runs; не создавать блоки через границу.
- [ ] Задокументировать pooled estimator и увеличить версию алгоритма.

**Тесты:**

- runs с контрастными распределениями доказывают отсутствие cross-run блоков;
- один run воспроизводит прежний результат при том же seed;
- разные длины runs учитываются корректно;
- одинаковый seed воспроизводит итоговый CI.

### 5.3. Провенанс OOS и исходного кода

- [ ] Не возвращать удалённые temporary CSV paths как executable spec.
- [ ] Возвращать original base spec, requested/actual ranges, original/slice data hashes и warm-up metadata.
- [ ] Читать CSV один раз: парсить и хэшировать один и тот же byte snapshot.
- [ ] `code_version` дополнить dirty flag и content hash исходников.
- [ ] Экспортировать Python/NumPy/Pydantic и другие значимые dependency versions.
- [ ] Добавить run-level metrics/derived seeds и параметры analysis в export; raw trades выгружать отдельным опциональным artifact.
- [ ] Расширить export для OOS/robustness либо явно переименовать текущий отчёт, не обещая полный research report.

**Тесты:**

- изменение файла между parse/hash невозможно на используемом snapshot;
- dirty tree даёт другой provenance marker;
- OOS result не содержит несуществующих путей;
- два export одного сохранённого результата байт-идентичны;
- экспорт содержит всё необходимое для повторения analysis с тем же seed.

### Критерий завершения Фазы 5

OOS и robustness имеют корректную статистическую семантику, а сохранённого provenance достаточно для независимого повторения результата.

---

## Фаза 6 — Frontend correctness, типы и доступность

### 6.1. Ошибки и устаревшие результаты

- [ ] `ExperimentDetail` показывает ошибки results/equity вместо `[]`.
- [ ] Скрывать analysis только при ожидаемом `AnalysisUnavailableError`; сетевые/500 ошибки показывать явно.
- [ ] Не подменять failed equity fallback-капиталом; run 0 и aggregate final capital подписывать раздельно.
- [ ] `ExpectancyComparison` очищать/помечать stale результат при изменении controls и при новом запросе.
- [ ] Добавить loading/error для списка counterparts.
- [ ] OOS: missing-base error, disabled button во время запроса и защита от повторного запуска.
- [ ] Robustness: snapshot base ID/name у результата и игнорирование stale responses.
- [ ] Очищать старые ошибки при повторной успешной загрузке Batches.

**Тесты:** rejected promises для каждого обязательного запроса, deferred response A после выбора B, double-click, failure→success, failed request не меняет отображаемые метрики.

### 6.2. Типы API

- [ ] Зеркалить backend discriminated union для MA, Buy&Hold, Random Entry и Breakout в `web/src/types.ts`.
- [ ] Типизировать `data.source`, historical `runs=1`, nullable metrics и error payloads.
- [ ] Убрать неполные fixtures, приводимые к `never`, и добавить contract fixtures для всех стратегий.

### 6.3. Accessibility и адаптивность

- [ ] Выбор experiment/batch делать button/link либо добавить keyboard Enter/Space и focus.
- [ ] Добавить accessible names и табличную альтернативу для equity/histogram.
- [ ] Настроить theme-aware цвета Chart.js с достаточным contrast и обновление при смене темы.
- [ ] Добавить `role=alert`/`role=status` для асинхронных сообщений и selected state для главной навигации.
- [ ] Добавить responsive overflow для таблиц, перенос segmented control и одноколоночные definition lists на узких экранах.
- [ ] Согласовать HTML min/max с backend: durations > 0, `0 < confidence < 1`.
- [ ] Показывать `null` как `—`; empty sensitivity grid/result получает явное состояние.

**Тесты:** keyboard selection, accessible roles/names, theme update, EN/RU на 320px, null/empty rendering, contract tests для всех strategy variants.

### Критерий завершения Фазы 6

UI не показывает ложные данные после ошибок, не путает результаты разных запросов и пригоден для keyboard/screen-reader/mobile пользователей.

---

## Фаза 7 — Security hardening для локального запуска

### Работы

- [ ] Публиковать PostgreSQL только на loopback: `127.0.0.1:${VECTORX_POSTGRES_PORT}:5432`.
- [ ] API по умолчанию запускать на `127.0.0.1`; внешний bind считать отдельной осознанной конфигурацией.
- [ ] Ограничить API CSV paths разрешённым `VECTORX_DATA_ROOT` (по умолчанию `configs/experiments/data`).
- [ ] Проверять `Path.resolve()` и принадлежность к root, включая symlink/`..` обходы.
- [ ] Не возвращать содержимое произвольных файлов или внутренние traceback в HTTP errors.
- [ ] Сохранить generic `DataSource` для библиотеки; path sandbox применять на API-границе.
- [ ] Задокументировать: auth отсутствует, потому что платформа рассчитана только на локальный запуск; внешний exposure требует отдельного security-проекта.

### Тесты

- абсолютный путь вне root, `../`, symlink escape → 403/400;
- разрешённый CSV продолжает работать;
- PostgreSQL не слушает `0.0.0.0` после `demo-up`;
- ошибки не раскрывают содержимое файла/внутренние stack traces.

### Критерий завершения

README-запуск работает только локально, а пользовательский API-request не может читать произвольные server-side CSV вне разрешённого каталога.

---

## 3. Итоговая матрица обязательных проверок

После всех фаз должны быть зелёными:

```bash
pytest
ruff check .
cd web
npm test
npm run build
```

Дополнительно:

- [ ] `alembic upgrade head` и `downgrade base` на чистой БД.
- [ ] Миграция старого snapshot с experiments/runs/trades без потери читаемости.
- [ ] Query-count и память не регрессируют относительно Фазы 0.
- [ ] Астрономический sweep/walk-forward отклоняется до тяжёлой работы.
- [ ] Next-open fixture подтверждает отсутствие same-close execution.
- [ ] Gross/net fixture подтверждает корректность статистики после издержек.
- [ ] Batch failure оставляет БД неизменной.
- [ ] Summary API не читает raw trades.
- [ ] Empty historical run проходит полный pipeline.
- [ ] Multi-run block bootstrap не создаёт cross-run blocks.
- [ ] OOS naive datetime и non-finite inputs получают клиентскую ошибку, не 500.
- [ ] Dirty tree и dependency versions отражены в provenance.
- [ ] Реальные BTC/ETH/SOL demo-эксперименты повторно запущены под новой `experiment_version`.
- [ ] Старые эксперименты открываются с явной пометкой старой версии алгоритма.
- [ ] Robustness/OOS проверены через реальные HTTP-запросы и вручную в Dashboard.
- [ ] Keyboard-only сценарий и 320px EN/RU layouts проверены вручную.
- [ ] `git diff --check` чист, сгенерированные тестовые файлы не попадают в коммит.

## 4. Порядок поставки и версии

Рекомендуемая последовательность коммитов:

1. `test: characterize research and storage contracts`
2. `fix: enforce preflight limits and input validation`
3. `fix: remove historical execution bias and support empty runs`
4. `feat: separate gross and net research metrics`
5. `perf: add storage projections and atomic batches`
6. `fix: correct OOS robustness and provenance`
7. `fix: surface UI failures and improve accessibility`
8. `fix: restrict demo services and CSV access to local scope`

После изменения execution/metrics опубликовать новую minor-версию платформы. Не выдавать изменённые historical результаты за regression-compatible: они должны быть явно маркированы новой версией алгоритма.

## 5. Definition of Done

Исправление считается завершённым только когда:

- каждая проблема из ревью имеет regression-тест;
- исправления подтверждены на реальных API/UI-сценариях, а не только unit-тестах;
- численные изменения версионированы и описаны;
- старые данные читаются;
- нет новых критических/высоких замечаний при повторном код-ревью;
- полный набор проверок зелёный, а ограничения verification явно задокументированы.
