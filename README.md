# VectorX

Исследовательская платформа для анализа торговых стратегий. Monte Carlo модели и
исторический бэктест (CSV + стратегии) сходятся в один контракт `Trade[]` →
`PortfolioSimulator` → статистика. Не торговый бот — нет live-ордеров, MEXC, CCXT.

Проект прошёл MVP и два этапа Post-MVP; текущий уровень — **"VectorX Research
Platform v1"**. Что уже реализовано:

- Monte Carlo эксперименты (вероятностная модель, N runs) и исторический бэктест
  (MA Crossover / Breakout / Buy&Hold / Random-entry на CSV OHLCV).
- Статистика: bootstrap confidence intervals, significance tests, Sharpe/Sortino/Calmar.
- Out-of-sample валидация (train/test split) и parameter sweep батчи под общей гипотезой.
- Robustness testing (parameter sensitivity, walk-forward, block bootstrap) —
  реализовано и протестировано в `src/vectorx/robustness/`; пока доступно только из
  Python (сознательно без API/UI в этом релизе).
- Воспроизводимый экспорт эксперимента (JSON/Markdown) с полным provenance
  (code_version, data_version, experiment_version, analysis_version, seed).
- Dashboard (Vue 3): список/детали экспериментов, equity/histogram графики, batches,
  out-of-sample, сравнение Monte Carlo vs historical, тёмная/светлая тема, EN/RU.

Документация по этапам (зафиксированные архитектурные решения, не переоткрывать):

- [docs/VECTORX-MVP-PLAN.md](docs/VECTORX-MVP-PLAN.md) — MVP (Monte Carlo, Postgres,
  API, dashboard).
- [docs/VECTORX-POST-MVP-ROADMAP.md](docs/VECTORX-POST-MVP-ROADMAP.md) — исторические
  данные, стратегии, backtest engine.
- [docs/VECTORX-RESEARCH-PLATFORM-ROADMAP.md](docs/VECTORX-RESEARCH-PLATFORM-ROADMAP.md) —
  raw trades, батчи, statistical toolkit, out-of-sample, robustness, экспорт.

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

Требуются Python 3.12+, Node.js с npm и Docker с Docker Compose.

### Быстрый запуск (демо)

```bash
./scripts/demo-up.sh
./scripts/seed_demo.sh
```

Первая команда поднимает Postgres (docker compose), накатывает миграции, запускает API
и web в фоне; вторая наполняет интерфейс демонстрационными данными для всех вкладок:

- API — `http://127.0.0.1:8000`
- Web — `http://127.0.0.1:5173`

Логи фоновых процессов — `.demo/api.log`, `.demo/web.log`. Остановить:

```bash
./scripts/demo-down.sh
```

Данные Postgres (docker volume) между показами сохраняются — `demo-down.sh` не удаляет volume.

Если порт 5432 (или 8000) уже занят другим процессом на вашей машине, скрипт честно
упадёт с ошибкой вместо того, чтобы тихо подключиться не туда. Переопределите порт и
перезапустите:

```bash
export VECTORX_POSTGRES_PORT=55432
export VECTORX_DATABASE_URL="postgresql+psycopg://vectorx:vectorx@localhost:55432/vectorx"
# при конфликте на 8000 — аналогично export VECTORX_API_PORT=8001
# при конфликте на 5173 — export VECTORX_WEB_PORT=5183 (порт также попадёт в CORS)
./scripts/demo-up.sh
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
   export VECTORX_DATABASE_URL="postgresql+psycopg://vectorx:vectorx@localhost:5432/vectorx"
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

5. В отдельном терминале запустите API с тем же `VECTORX_DATABASE_URL`:

   ```bash
   source .venv/bin/activate
   uvicorn api.main:app --reload
   ```

   API будет доступен по адресу `http://127.0.0.1:8000`.

6. В третьем терминале запустите интерфейс:

   ```bash
   cd web
   npm ci
   npm run dev
   ```

   Интерфейс будет доступен по адресу `http://127.0.0.1:5173`.

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
