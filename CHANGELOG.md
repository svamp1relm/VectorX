# Changelog

Все заметные изменения VectorX документируются здесь. Формат основан на Keep a Changelog.
Версия пакета не зависит от `experiment_version` и `analysis_version`.

## [0.2.0] — 2026-11-20

### Added

- Robustness Workbench: parameter sensitivity, walk-forward и block bootstrap через FastAPI и Vue.
- Gross/net R-метрики после комиссий и slippage; `experiment_version=2`, `analysis_version=2`.
- Alembic-миграция `f4b8d2c61a90` с net-полями и поддержкой empty historical runs.
- In-memory OOS с indicator warm-up, source/slice content hashes и run-level provenance.
- Source hash, dependency metadata и полный `uv.lock`.
- Summary-only PostgreSQL projections, pagination, bounded trade inserts и атомарные batches.
- Frontend error/stale-state handling, discriminated unions, keyboard/accessibility и responsive layouts.
- Подробные remediation и improvement планы в `docs/`.

### Changed

- Historical signals исполняются по open следующей свечи вместо close текущей.
- Версия пакета обновлена до `0.2.0`; численные изменения явно отделены от версии пакета.

### Fixed

- Preflight resource guards для sweep, walk-forward, Monte Carlo и bootstrap.
- Строгая валидация NaN/Infinity, OHLCV, CSV, seed и timezone-aware datetime.
- Empty historical runs возвращают валидный результат вместо ошибки.
- Block bootstrap больше не создаёт блоки между независимыми runs.
- Batch creation атомарен и не оставляет частичных записей при ошибке.

### Security

- PostgreSQL публикуется только на `127.0.0.1`.
- API читает CSV только внутри `VECTORX_DATA_ROOT`, включая защиту от `..` и symlink escape.
- Локальные demo health-check и API-запросы обходят внешний proxy.
