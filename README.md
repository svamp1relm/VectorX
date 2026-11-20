# VectorX

Исследовательская платформа для анализа торговых стратегий. Monte Carlo модели и
исторический бэктест (CSV + стратегии) сходятся в один контракт `Trade[]` →
`PortfolioSimulator` → статистика. Не торговый бот — нет live-ордеров, MEXC, CCXT.

Проект прошёл MVP и два этапа Post-MVP; текущий уровень — **"VectorX Research
Platform v1"**. Что уже реализовано:

- Monte Carlo эксперименты (вероятностная модель, N runs) и исторический бэктест
  (MA Crossover / Breakout / Buy&Hold / Random-entry на CSV OHLCV). Сигналы свечи `t`
  исполняются по open `t+1`, без same-close look-ahead. Возможен валидный результат без сделок.
- Статистика: bootstrap confidence intervals, significance tests, Sharpe/Sortino/Calmar.
  Gross R и net R после комиссий/slippage разделены; текущие версии — `experiment_version=2`,
  `analysis_version=2`.
- Out-of-sample валидация (train/test split) с indicator warm-up, in-memory срезами и
  parameter sweep батчами под общей гипотезой.
- Robustness testing (parameter sensitivity, walk-forward, block bootstrap) — из Python,
  через API и вкладку **Robustness** в Dashboard. Для block bootstrap эксперимент должен
  быть сохранён с `storage.store_trades=true`.
- Воспроизводимый экспорт эксперимента (JSON/Markdown) с полным provenance
  (code_version, data_version, experiment_version, analysis_version, seed).
- Dashboard (Vue 3): список/детали экспериментов, equity/histogram графики, batches,
  out-of-sample, robustness, сравнение Monte Carlo vs historical, тёмная/светлая тема, EN/RU.

Документация по этапам (зафиксированные архитектурные решения, не переоткрывать):

- [docs/VECTORX-MVP-PLAN.md](docs/VECTORX-MVP-PLAN.md) — MVP (Monte Carlo, Postgres,
  API, dashboard).
- [docs/VECTORX-POST-MVP-ROADMAP.md](docs/VECTORX-POST-MVP-ROADMAP.md) — исторические
  данные, стратегии, backtest engine.
- [docs/VECTORX-RESEARCH-PLATFORM-ROADMAP.md](docs/VECTORX-RESEARCH-PLATFORM-ROADMAP.md) —
  raw trades, батчи, statistical toolkit, out-of-sample, robustness, экспорт.
- [docs/VECTORX-CODE-REVIEW-REMEDIATION-PLAN.md](docs/VECTORX-CODE-REVIEW-REMEDIATION-PLAN.md) —
  исправления resource safety, execution, метрик, хранения, OOS, UI и security.

Актуальное устройство и использование:

- [docs/VECTORX-ARCHITECTURE.md](docs/VECTORX-ARCHITECTURE.md) — модули, routers, БД и тестовые уровни.
- [docs/VECTORX-RESEARCH-MODEL.md](docs/VECTORX-RESEARCH-MODEL.md) — execution, R, gross/net, OOS и bootstrap.
- [docs/VECTORX-API.md](docs/VECTORX-API.md) — HTTP-контракты и ошибки.
- [docs/VECTORX-DATA-GUIDE.md](docs/VECTORX-DATA-GUIDE.md) — CSV, time ranges и data sandbox.
- [docs/VECTORX-ACCESSIBILITY-CHECKLIST.md](docs/VECTORX-ACCESSIBILITY-CHECKLIST.md) — keyboard/charts/responsive checks.

## Что не входит

MEXC, CCXT, live trading, реальные ордера, WebSocket, Redis, Kafka, Kubernetes, ML,
аутентификация, job queue, TimescaleDB, Nuxt, pandas как ядро, short-позиции,
multiprocessing, автоматический выбор "лучших" параметров по robustness/OOS. Полный
список — в разделах Anti-scope документов выше.

## Разработка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[postgres,api,dev]"
```

Для полностью зафиксированного исследовательского окружения используйте `uv.lock`:

```bash
uv sync --all-extras
```

Требуются Python 3.12+, Node.js с npm и Docker с Docker Compose.

### Быстрый запуск (демо)

```bash
source .venv/bin/activate
# Нужно только если вы ранее вручную задавали переменные VectorX в этом терминале:
unset VECTORX_POSTGRES_PORT VECTORX_DATABASE_URL VECTORX_API_PORT VECTORX_WEB_PORT
unset VECTORX_CORS_ORIGINS VITE_API_BASE VECTORX_API_BASE

./scripts/demo-up.sh
./scripts/seed_demo.sh
```

Первая команда поднимает Postgres (docker compose), накатывает миграции, запускает API
и web в фоне; вторая наполняет интерфейс демонстрационными данными для всех вкладок.
По умолчанию используются порты, которые не конфликтуют с типичными локальными сервисами:

- PostgreSQL — `localhost:55432` (внутри контейнера — `5432`);
- API — `http://127.0.0.1:8001`;
- Web — `http://127.0.0.1:5173`.

Если в активированном окружении заданы `http_proxy`/`https_proxy`, скрипты автоматически
добавляют `localhost`, `127.0.0.1` и `::1` в `NO_PROXY`/`no_proxy`, чтобы локальные
health-check и API-запросы не проходили через внешний proxy. Остальные proxy-настройки
сохраняются.

PostgreSQL публикуется только на `127.0.0.1`. API читает CSV только внутри
`VECTORX_DATA_ROOT` (по умолчанию `configs/experiments/data`); пути с `..`, абсолютные пути
и symlinks за его пределами отклоняются. Платформа рассчитана на локальный запуск без auth;
для внешнего доступа требуется отдельная security-конфигурация.

Логи фоновых процессов — `.demo/api.log`, `.demo/web.log`. Остановить:

```bash
./scripts/demo-down.sh
```

Данные Postgres (docker volume) между показами сохраняются — `demo-down.sh` не удаляет volume.

Если порт 55432 (или 8001) уже занят другим процессом на вашей машине, скрипт честно
упадёт с ошибкой вместо того, чтобы тихо подключиться не туда. Переопределите порт и
перезапустите:

```bash
export VECTORX_POSTGRES_PORT=56432
export VECTORX_DATABASE_URL="postgresql+psycopg://vectorx:vectorx@localhost:${VECTORX_POSTGRES_PORT}/vectorx"
# при конфликте на 8001 — например, export VECTORX_API_PORT=8002
# при конфликте на 5173 — export VECTORX_WEB_PORT=5183 (порт также попадёт в CORS)
./scripts/demo-up.sh
./scripts/seed_demo.sh
```

См. также `.env.example` (`cp .env.example .env` + `export $(cat .env | xargs)`, либо
вручную).

### Запуск вручную, по шагам

Для демо быстрее использовать скрипты выше. Шаги ниже — то же самое руками, по отдельности
(полезно для отладки конкретной части стека).

1. Запустите PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

2. Укажите адрес базы данных. Для выбранной выше конфигурации Docker:

   ```bash
   export VECTORX_POSTGRES_PORT=55432
   export VECTORX_DATABASE_URL="postgresql+psycopg://vectorx:vectorx@localhost:55432/vectorx"
   ```

3. Примените миграции:

   ```bash
   alembic upgrade head
   ```

4. При необходимости создайте эксперимент через CLI. Например:

   ```bash
   vectorx run configs/experiments/btc_1h.yaml
   vectorx run configs/experiments/expectancy_test.yaml
   ```

   Исторический эксперимент создаётся одним детерминированным прогоном,
   а Monte Carlo-эксперимент — из указанных в YAML `runs`.

5. Запустите API с тем же `VECTORX_DATABASE_URL`:

   ```bash
   source .venv/bin/activate
   export VECTORX_DATABASE_URL="postgresql+psycopg://vectorx:vectorx@localhost:55432/vectorx"
   uvicorn api.main:app --reload --port 8001
   ```

   API будет доступен по адресу `http://127.0.0.1:8001`. Сервер работает в foreground
   и занимает текущий терминал; для его остановки нажмите `Ctrl+C`.

6. Не останавливая API, в другом терминале запустите интерфейс:

   ```bash
   cd web
   npm ci
   npm run dev
   ```

   Интерфейс будет доступен по адресу `http://127.0.0.1:5173` и по умолчанию обратится
   к API на порту `8001`.

7. В интерфейсе откройте эксперимент. В разделе **Сравнение математического
   ожидания** выберите эксперимент противоположного типа, при необходимости
   измените опорную долю риска и нажмите **Сравнить**. Для сравнения нужны
   хотя бы один Monte Carlo- и один исторический эксперимент.

### Проверка

```bash
pytest
ruff check .
cd web
npm test
npm run build
```

Browser E2E на отдельном Docker project и отдельных портах:

```bash
cd web
npx playwright install chromium
cd ..
./scripts/e2e.sh
```

Скрипт сам поднимает изолированный PostgreSQL/API/Web, выполняет 6 сценариев и останавливает стек.
