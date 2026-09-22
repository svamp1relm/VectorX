# VectorX

Исследовательская симуляционная платформа для торговых моделей: математическое
ожидание, Monte Carlo, статистика по распределению результатов. Не торговый
бот — нет live-ордеров, MEXC, CCXT.

Полный план и зафиксированные архитектурные решения:
[docs/VECTORX-MVP-PLAN.md](docs/VECTORX-MVP-PLAN.md).

## Что не входит в MVP

MEXC, CCXT, live trading, OHLCV backtesting, Redis, Kafka, Kubernetes,
multiprocessing, WebSocket, authentication, job queue, TimescaleDB,
хранение каждой сделки, Nuxt, pandas как ядро, сетка параметров,
comparison UI.

## Разработка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
