# VectorX — руководство по историческим данным

## CSV-контракт

Обязательные колонки в фиксированных именах:

```text
timestamp,open,high,low,close,volume
```

Требования:

- UTF-8 и непустой набор data rows;
- ISO 8601 timestamp обязательно с timezone, предпочтительно UTC;
- timestamps строго возрастают, дубликаты запрещены;
- OHLC конечные и строго положительные;
- `low <= open,close <= high` и `low <= high`;
- volume конечный и неотрицательный;
- отсутствующие/некорректные поля вызывают `InvalidMarketDataError`.

Gap detection поддерживается библиотекой через expected interval. Пропуски не исправляются и не
интерполируются автоматически.

## Источники данных

Единственный production source — `CsvDataSource`. Встроенные BTC/ETH/SOL 1h CSV являются локальными
снимками, не live-feed. Обновление данных означает новый файл/снимок и новый content hash.

`CsvDataSource.load_with_version()` читает один byte snapshot, из которого получает одновременно candles
и SHA-256. Runner использует этот метод, поэтому `data_version` соответствует именно обработанным bytes.
При historical API лимит candles проверяется во время чтения.

## CSV sandbox в HTTP API

По умолчанию API разрешает только `configs/experiments/data`. Каталог можно задать:

```bash
export VECTORX_DATA_ROOT=/absolute/path/to/market-data
```

Пути с `..`, абсолютные пути и symlinks, ведущие вне resolved root, получают 403. Это ограничение
применяется к create/rerun/batch/OOS/robustness API. CLI и библиотечный `CsvDataSource` остаются
универсальными и не зависят от HTTP sandbox.

## Time ranges

OOS и walk-forward используют timezone-aware ISO timestamps. Границы `slice_market_data` inclusive.
Train/test OOS не пересекаются: `test_start > train_end`. Перед test start разрешены только candles для
indicator warm-up; их сделки/PnL не входят в scored result.

## Версионирование и замена данных

Не перезаписывайте файл молча, если нужно сравнивать эксперименты между собой: content hash изменится,
и это будет видно в provenance. Для повторяемых исследований храните исходные снимки и фиксируйте путь,
hash и spec в export.
