"""CsvDataSource: first `DataSource` implementation — plain CSV via stdlib `csv`.

Deliberately avoids pandas/pyarrow (Phase 12 of the Post-MVP roadmap keeps the
historical data layer's first source minimal). Column names are fixed
(`timestamp,open,high,low,close,volume`); a configurable column mapping is out
of scope until a second source actually needs different names.
"""

import csv
import hashlib
from datetime import datetime
from pathlib import Path

from vectorx.core.errors import InvalidMarketDataError
from vectorx.marketdata.types import MarketCandle, MarketData

_REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def compute_data_version(path: str | Path) -> str:
    """Sha256 hex digest of a market data file's raw bytes (`data_version`).

    Content-hash, not a human-maintained version number: if the file is
    overwritten with different data, this changes automatically, without
    relying on anyone to remember to bump a YAML field.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CsvDataSource:
    """Loads OHLCV candles from a CSV file with fixed column names."""

    def __init__(self, path: str | Path, symbol: str, timeframe: str) -> None:
        self._path = Path(path)
        self._symbol = symbol
        self._timeframe = timeframe

    def load(self) -> MarketData:
        with self._path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            _validate_header(reader.fieldnames)
            candles = tuple(
                _row_to_candle(row, line_number)
                for line_number, row in enumerate(reader, start=2)
            )

        if not candles:
            raise InvalidMarketDataError(f"{self._path}: CSV has no data rows")

        return MarketData(symbol=self._symbol, timeframe=self._timeframe, candles=candles)


def _validate_header(fieldnames: list[str] | None) -> None:
    missing = [
        column for column in _REQUIRED_COLUMNS if fieldnames is None or column not in fieldnames
    ]
    if missing:
        raise InvalidMarketDataError(f"CSV is missing required columns: {missing}")


def write_market_data_csv(data: MarketData, path: str | Path) -> None:
    """Serialize `data.candles` back to the fixed CSV column format.

    The inverse of `CsvDataSource.load` — round-tripping a `MarketData`
    through this and `CsvDataSource` reproduces the same candles. Used by
    Out-of-Sample (Фаза 20) to materialize a time-sliced `MarketData` as a
    file so the unchanged `run_experiment()` historical-backtest path can
    run on it without a second data-loading mechanism.
    """
    with Path(path).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(_REQUIRED_COLUMNS)
        for candle in data.candles:
            writer.writerow(
                [
                    candle.timestamp.isoformat(),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                ]
            )


def _row_to_candle(row: dict[str, str], line_number: int) -> MarketCandle:
    try:
        timestamp = _parse_timestamp(row["timestamp"])
        return MarketCandle(
            timestamp=timestamp,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
    except ValueError as exc:
        raise InvalidMarketDataError(f"line {line_number}: invalid row {row!r}: {exc}") from exc


def _parse_timestamp(raw: str) -> datetime:
    timestamp = datetime.fromisoformat(raw)
    if timestamp.tzinfo is None:
        raise ValueError(f"timestamp {raw!r} must be timezone-aware")
    return timestamp
