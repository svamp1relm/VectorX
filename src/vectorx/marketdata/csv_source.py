"""CSV market data loaded from one byte-identical, content-hashed snapshot."""

import csv
import hashlib
from datetime import datetime
from io import StringIO
from pathlib import Path

from vectorx.core.errors import ExperimentTooLargeError, InvalidMarketDataError
from vectorx.marketdata.types import MarketCandle, MarketData

_REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def compute_data_version(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a market data file."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise InvalidMarketDataError(f"cannot read market data file {path}: {exc}") from exc


class CsvDataSource:
    """Loads OHLCV candles from a CSV file with fixed column names."""

    def __init__(self, path: str | Path, symbol: str, timeframe: str) -> None:
        self._path = Path(path)
        self._symbol = symbol
        self._timeframe = timeframe

    def load(self) -> MarketData:
        data, _ = self.load_with_version()
        return data

    def load_with_version(self, *, max_candles: int | None = None) -> tuple[MarketData, str]:
        """Parse and hash exactly the same bytes, optionally bounding row count."""
        try:
            raw = self._path.read_bytes()
        except OSError as exc:
            raise InvalidMarketDataError(
                f"cannot read market data file {self._path}: {exc}"
            ) from exc
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidMarketDataError(f"{self._path}: CSV must be UTF-8") from exc

        reader = csv.DictReader(StringIO(text))
        _validate_header(reader.fieldnames)
        candles = []
        for line_number, row in enumerate(reader, start=2):
            if max_candles is not None and len(candles) >= max_candles:
                raise ExperimentTooLargeError(
                    f"CSV contains more than {max_candles} candles: {self._path}"
                )
            candles.append(_row_to_candle(row, line_number))
        if not candles:
            raise InvalidMarketDataError(f"{self._path}: CSV has no data rows")

        data = MarketData(
            symbol=self._symbol,
            timeframe=self._timeframe,
            candles=tuple(candles),
        )
        return data, hashlib.sha256(raw).hexdigest()


def _validate_header(fieldnames: list[str] | None) -> None:
    missing = [
        column for column in _REQUIRED_COLUMNS if fieldnames is None or column not in fieldnames
    ]
    if missing:
        raise InvalidMarketDataError(f"CSV is missing required columns: {missing}")


def serialize_market_data_csv(data: MarketData) -> str:
    """Serialize candles deterministically for files and content hashes."""
    handle = StringIO()
    writer = csv.writer(handle, lineterminator="\n")
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
    return handle.getvalue()


def compute_market_data_content_version(data: MarketData) -> str:
    """Hash an in-memory market-data slice without creating a temporary file."""
    return hashlib.sha256(serialize_market_data_csv(data).encode()).hexdigest()


def write_market_data_csv(data: MarketData, path: str | Path) -> None:
    """Serialize `data.candles` back to the fixed CSV column format."""
    Path(path).write_text(serialize_market_data_csv(data))


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
    except (ValueError, TypeError, KeyError) as exc:
        raise InvalidMarketDataError(f"line {line_number}: invalid row {row!r}: {exc}") from exc


def _parse_timestamp(raw: str) -> datetime:
    timestamp = datetime.fromisoformat(raw)
    if timestamp.tzinfo is None:
        raise ValueError(f"timestamp {raw!r} must be timezone-aware")
    return timestamp
