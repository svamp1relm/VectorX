# VectorX — план улучшения структуры и возможностей проекта

**Дата:** 2026-11-19  
**Базовый коммит:** `adbe0d8d8fc18daea8125b68a9a8266c0347c0dc`  
**Текущие проверки:** 368 backend-тестов, 59 frontend component-тестов и 6 Playwright E2E зелёные.

Документ содержит оставшиеся архитектурные, технические и продуктовые задачи после завершения
`VECTORX-CODE-REVIEW-REMEDIATION-PLAN.md`. Это план последующих улучшений, а не список уже
выполненных изменений.

## Результат реализации — 2026-11-20

Задачи плана выполнены:

- package version `0.2.0`, `CHANGELOG.md` и полный `uv.lock`;
- `api/main.py` разделён на schemas/data_paths/routers без изменения HTTP JSON;
- `RobustnessView.vue` разделён на три панели и `useAsyncAnalysis`;
- analysis/bootstrap читают targeted gross/net R values без ORM-гидратации trades;
- добавлены 6 Playwright E2E на изолированном Docker project и отдельных портах;
- добавлен migration test с реальными v1 experiment/run/trade rows;
- добавлены performance regression guards для rolling strategies, SQL, bounded inserts и CSV limit;
- созданы актуальные Architecture, Research Model, API, Data Guide и Accessibility docs;
- README обновлён для `uv sync --all-extras` и `./scripts/e2e.sh`.

Ручная screen-reader и визуальная 320/720px проверка остаётся релизным чек-листом и явно не отмечена
как автоматизированная в `VECTORX-ACCESSIBILITY-CHECKLIST.md`.

## 1. Текущая архитектурная оценка

Основу проекта менять не требуется:

```text
Monte Carlo / Historical → Trade[] → PortfolioSimulator → Metrics → Summary
                                      → PostgreSQL → FastAPI → Vue
```

Сильные стороны:

- library-first ядро в `src/vectorx/`;
- единый execution/statistics pipeline для Monte Carlo и historical;
- независимые `DataSource`, `Strategy`, `ExperimentRepository`;
- Alembic-миграции и versioning алгоритмов;
- типизированный Vue-клиент и большой набор component/integration-тестов;
- осознанный local research scope без лишней инфраструктуры.

Redis, Kubernetes, микросервисы, Nuxt, live trading и job queue для текущих задач не нужны.

---

## 2. Приоритет P0 — Актуализация пакета и проверки совместимости

### 2.1. Версия пакета не соответствует состоянию проекта

**Проблема:** `pyproject.toml` содержит `0.1.0`, при этом проект уже включает Research Platform,
robustness и вторую версию experiment/analysis algorithms.

**Задачи:**

- [ ] Выбрать и зафиксировать независимую схему версионирования пакета, experiment и analysis.
- [ ] Обновить package version до `0.2.0`.
- [ ] Добавить `CHANGELOG.md` с изменениями по релизам.
- [ ] Не приравнивать package version к `experiment_version`: это разные контракты.
- [ ] Проверять package version в export/provenance.

**Критерий готовности:** версия пакета, release notes и export однозначно идентифицируют поставляемый
результат, а версии алгоритмов остаются независимыми.

### 2.2. Неполная фиксация исследовательского окружения

**Проблема:** `requirements-research.lock` фиксирует только прямые зависимости, не транзитивные.

**Задачи:**

- [ ] Перейти на полный lockfile, например `uv.lock`.
- [ ] Зафиксировать Python-версию для CI/research environment.
- [ ] Использовать lockfile при локальной установке и в CI.
- [ ] Сохранить зависимости runtime/test отдельно от исследовательского lockfile, если это упростит
  поддержку пакета.
- [ ] Проверить чистую установку в новом окружении.

**Критерий готовности:** два независимых окружения с одним lockfile дают одинаковые результаты seeded
экспериментов и bootstrap.

---

## 3. Приоритет P1 — Структурная поддерживаемость

### 3.1. Централизация ответственности в `api/main.py`

**Проблема:** маршруты, request-схемы, CSV security, batches, analysis, OOS и robustness находятся
в одном модуле.

**Задачи:**

- [ ] Вынести маршруты в `api/routers/experiments.py`, `batches.py`, `robustness.py`.
- [ ] Вынести request-модели в `api/schemas.py`.
- [ ] Вынести sandbox логику CSV в `api/data_paths.py`.
- [ ] Сохранить dependency injection и существующие HTTP-контракты.
- [ ] Добавить API contract tests перед перемещением маршрутов.

**Критерий готовности:** `api/main.py` отвечает только за сборку приложения/middleware/exception handlers;
URL и JSON остаются совместимыми.

### 3.2. Громоздкий `RobustnessView.vue`

**Проблема:** три независимых workflow находятся в одном компоненте с большим количеством состояния.

**Задачи:**

- [ ] Вынести `SensitivityPanel.vue`, `WalkForwardPanel.vue`, `BlockBootstrapPanel.vue`.
- [ ] Оставить общий base experiment в `RobustnessView.vue`.
- [ ] Вынести повторяющиеся loading/error/stale-response паттерны в composable.
- [ ] Перенести существующие component-тесты на панели без потери сценариев.

**Критерий готовности:** каждая панель имеет один workflow и собственные тесты; общий base ID не
приводит к отображению результатов другого эксперимента.

### 3.3. Универсальный тяжёлый `ExperimentResult` при чтении

**Проблема:** summary projections уже есть, но `get_experiment(include_trades=...)` всё ещё объединяет
несколько read-сценариев и форм результата.

**Задачи:**

- [ ] Добавить отдельные read-модели для detail metadata, runs/equity и analysis R-values.
- [ ] Не загружать ORM `TradeRow` для detail, export и comparison.
- [ ] Для analysis читать только необходимые gross/net поля.
- [ ] Убрать N+1 во всех read-сценариях, не только summary list.
- [ ] Добавить query-count и memory regression tests.

**Критерий готовности:** число SQL-запросов и объём читаемых строк определяется конкретным endpoint,
а не всем содержимым эксперимента.

---

## 4. Приоритет P1 — End-to-end качество

### 4.1. Нет браузерных E2E-тестов

**Проблема:** component-тесты не проверяют полную связку Vue → API → PostgreSQL → миграции.

**Задачи:**

- [ ] Добавить Playwright или эквивалентный browser-runner без изменения production-зависимостей ядра.
- [ ] Поднимать тестовый стек на отдельных портах с эфемерной БД.
- [ ] Реализовать сценарии:
  - запуск приложения и открытие эксперимента;
  - historical run без сделок;
  - sensitivity/walk-forward/block bootstrap;
  - OOS с warm-up;
  - ошибка API не выглядит как нулевой эксперимент;
  - EN/RU и dark/light;
  - keyboard-only navigation.
- [ ] Запускать E2E в CI отдельно от component-тестов.

**Критерий готовности:** критические исследовательские workflows проходят в реальном браузере против
реальных API и PostgreSQL.

### 4.2. Миграции проверяются на схеме, но недостаточно на старых данных

**Проблема:** `downgrade base → upgrade head` проверен, но нужен снапшот с реальными v1-записями.

**Задачи:**

- [ ] Создать минимальный PostgreSQL snapshot с experiments/runs/trades старой схемы.
- [ ] Проверить миграцию на новую схему без потери данных.
- [ ] Открыть старые эксперименты через API/UI.
- [ ] Создать рядом новый v2-эксперимент и проверить различие provenance.
- [ ] Проверить rollback на тестовой копии, не на demo-БД.

**Критерий готовности:** старые данные читаются после миграции, а новые алгоритмы не переписывают их
исторические результаты.

### 4.3. Performance regression проверки ограничены

**Задачи:**

- [ ] Зафиксировать маленькие бюджеты времени/памяти для sweep, MA, Breakout, CSV и bootstrap.
- [ ] Проверять query count для list/detail/analysis.
- [ ] Проверять bounded memory для raw-trade insert.
- [ ] Добавить stress case «астрономическая сетка отклоняется до тяжёлой работы» в CI.
- [ ] Не полагаться только на wall-clock: использовать query/row/allocation counters там, где возможно.

**Критерий готовности:** ухудшение сложности или неограниченный расход памяти обнаруживается тестами,
а не только код-ревью.

---

## 5. Приоритет P2 — Документация и исследовательская семантика

### 5.1. Документация распределена по историческим roadmap

**Задачи:**

- [ ] Создать актуальный `docs/VECTORX-ARCHITECTURE.md` с картой модулей и data flow.
- [ ] Добавить `docs/VECTORX-RESEARCH-MODEL.md`: next-open, R/gross/net, costs, empty runs,
  warm-up, bootstrap boundaries, ограничения random-entry и отсутствие исполняемого stop-loss.
- [ ] Добавить `docs/VECTORX-API.md` с endpoint contracts и ошибками.
- [ ] Добавить `docs/VECTORX-DATA-GUIDE.md`: CSV schema, UTC, validation, `VECTORX_DATA_ROOT`.
- [ ] Сохранить roadmap как историю, а не основной источник текущего поведения.

**Критерий готовности:** исследователь может объяснить численные результаты по документации без чтения
исходного кода.

### 5.2. Accessibility требует визуальной проверки

**Задачи:**

- [ ] Проверить 320px, 720px и desktop layouts в EN/RU.
- [ ] Проверить keyboard-only сценарий всех основных действий.
- [ ] Проверить chart data alternatives и contrast в обеих темах.
- [ ] Проверить screen-reader announcements для loading/error/selected states.

**Критерий готовности:** задокументирован ручной accessibility checklist в дополнение к component-тестам.

---

## 6. Что не требуется реализовывать сейчас

- Live trading, MEXC/CCXT, реальные ордера.
- Redis, Kafka, Kubernetes, микросервисы.
- ML и автоматический выбор «лучших» параметров.
- Переход на Nuxt или другой frontend-фреймворк.
- Переписывание доменного `Trade[]` pipeline.

## 7. Итоговый порядок поставки

1. Актуализировать package version и полный dependency lock.
2. Разделить API и RobustnessView без изменения контрактов.
3. Завершить targeted read-модели PostgreSQL.
4. Добавить Playwright E2E и legacy-data migration tests.
5. Добавить performance regression budgets.
6. Обновить актуальную architecture/research/API/data документацию.
7. Провести ручную accessibility-проверку.

## 8. Definition of Done

- Структурные изменения не меняют численные результаты без новой версии алгоритма.
- API/JSON обратно совместимы либо изменения явно версионированы.
- Все новые workflows покрыты unit/component/integration/E2E-тестами.
- Полный набор проверок проходит локально и в CI.
- Актуальная документация соответствует коду.
- Нет новых критических или высоких замечаний при повторном код-ревью.
