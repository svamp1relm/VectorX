# AGENTS.md

## Назначение проекта

VectorX — локальная исследовательская платформа для Monte Carlo и historical backtesting.
Это не торговый бот: нет live-ордеров, MEXC, CCXT, WebSocket или подключения к биржам.

Не добавляйте без отдельного решения live trading, auth, job queue, Redis, Kafka, Kubernetes,
ML, multiprocessing, Nuxt или pandas как ядро.

## Архитектурные правила

Основной контракт:

```text
Monte Carlo / Historical → Trade[] → PortfolioSimulator → Metrics → Summary
```

Сохраняйте library-first:

- Ядро `src/vectorx/` не зависит от FastAPI, Vue, HTTP и SQLAlchemy.
- Historical и Monte Carlo используют один execution/statistics pipeline.
- `api/` — только HTTP-адаптеры, schemas, serialization, routers и data-path sandbox.
- `web/src/` — отображение и typed fetch; исследовательская статистика остаётся на backend.
- PostgreSQL — через `ExperimentRepository` и targeted read projections.
- Новые simulation/statistics pipelines не создаются для OOS или robustness.

Подробнее: `docs/VECTORX-ARCHITECTURE.md` и `docs/VECTORX-RESEARCH-MODEL.md`.

## Исследовательская семантика

- Historical signal на свече `t` исполняется по open `t+1`; same-close execution запрещён.
- `stop_loss_pct` нормирует R, но не исполняет stop-loss.
- `Trade.r_multiple` — gross R; `net_r_multiple` учитывает commission/slippage.
- Empty historical run — валидный результат: return 0, trade-derived metrics `null`.
- OOS использует timezone-aware ranges, indicator warm-up и in-memory срезы без временных CSV.
- Block bootstrap не пересекает границы runs.
- Package version, `experiment_version` и `analysis_version` независимы.
- Не меняйте численные результаты без regression fixtures и соответствующего version bump.
- Старые эксперименты не переписываются под новые алгоритмы.

## Код-стиль

- Python ≥ 3.12, Pydantic v2, frozen immutable domain containers.
- Следуйте существующим именам и структурным идиомам, не добавляйте зависимости без необходимости.
- Не добавляйте комментарии, описывающие очевидное поведение; обновляйте устаревшие docstrings.
- HTTP: 400 для доменных ошибок, 404 для отсутствующих сущностей, 403 для CSV sandbox, 422 для schema errors.
- Frontend не вычисляет bootstrap, sweep или walk-forward самостоятельно.
- API/JSON и TypeScript types обновляются вместе.
- Не добавляйте секреты, `.env`, demo volumes, logs и test artifacts в коммит.
- Не изменяйте `.claude/skills/run-vectorx/` — это отдельный untracked локальный каталог.

## Проверки

Установка:

```bash
uv sync --all-extras
cd web && npm ci
```

Перед завершением изменений обязательно:

```bash
uv run pytest
uv run ruff check .
cd web
npm test
npm run build
npm audit --omit=dev
```

Если изменены запуск/миграции/БД:

```bash
alembic upgrade head
docker compose config
```

Если изменён пользовательский workflow или frontend:

```bash
cd web
npx playwright install chromium
cd ..
./scripts/e2e.sh
```

Не объявляйте задачу завершённой при падающих тестах или непроверенном основном сценарии.

## Demo и окружение

- PostgreSQL: `127.0.0.1:55432`.
- API: `http://127.0.0.1:8001`.
- Web: `http://127.0.0.1:5173`.
- CSV API paths разрешены только внутри `VECTORX_DATA_ROOT` (по умолчанию `configs/experiments/data`).
- Не публикуйте API/PostgreSQL во внешнюю сеть без отдельной security-конфигурации.

```bash
./scripts/demo-up.sh
./scripts/seed_demo.sh
./scripts/demo-down.sh
```

## Изменения и Git

- Не коммитьте и не пушьте без явного запроса пользователя.
- Сохраняйте чистый, логичный состав коммита; не включайте посторонние untracked файлы.
- Не выполняйте force push, reset --hard, rebase или удаление веток без явного запроса.
- Перед завершением проверяйте `git status` и `git diff --check`.
- Не меняйте `master` напрямую: актуализация идёт через PR с зелёным CI.

## Документация

Актуальные документы:

- `docs/VECTORX-ARCHITECTURE.md`
- `docs/VECTORX-RESEARCH-MODEL.md`
- `docs/VECTORX-API.md`
- `docs/VECTORX-DATA-GUIDE.md`
- `docs/VECTORX-ACCESSIBILITY-CHECKLIST.md`
- `CHANGELOG.md`

Если изменение затрагивает задокументированное поведение, обновите соответствующие docs.
