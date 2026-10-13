"""CsvDataSource: first `DataSource` implementation, CSV via stdlib `csv` only."""

from pathlib import Path

import pytest

from vectorx.core.errors import InvalidMarketDataError
from vectorx.marketdata.csv_source import CsvDataSource, compute_data_version, write_market_data_csv
from vectorx.marketdata.source import DataSource

_FIXTURES = Path(__file__).parent / "fixtures"


def test_csv_data_source_satisfies_data_source_protocol():
    source = CsvDataSource(_FIXTURES / "sample_ohlcv.csv", symbol="BTCUSDT", timeframe="1h")

    assert isinstance(source, DataSource)


def test_loads_valid_csv_into_market_data():
    source = CsvDataSource(_FIXTURES / "sample_ohlcv.csv", symbol="BTCUSDT", timeframe="1h")

    data = source.load()

    assert data.symbol == "BTCUSDT"
    assert data.timeframe == "1h"
    assert len(data.candles) == 4
    first = data.candles[0]
    assert first.open == 100.0
    assert first.high == 110.0
    assert first.low == 95.0
    assert first.close == 105.0
    assert first.volume == 1_000.0
    assert first.timestamp.tzinfo is not None


def test_missing_column_raises(tmp_path):
    bad_csv = tmp_path / "missing_column.csv"
    bad_csv.write_text("timestamp,open,high,low,close\n2024-01-01T00:00:00+00:00,1,2,0,1\n")
    source = CsvDataSource(bad_csv, symbol="BTCUSDT", timeframe="1h")

    with pytest.raises(InvalidMarketDataError):
        source.load()


def test_non_numeric_value_raises(tmp_path):
    bad_csv = tmp_path / "bad_value.csv"
    bad_csv.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01T00:00:00+00:00,not-a-number,2,0,1,10\n"
    )
    source = CsvDataSource(bad_csv, symbol="BTCUSDT", timeframe="1h")

    with pytest.raises(InvalidMarketDataError):
        source.load()


def test_naive_timestamp_raises(tmp_path):
    bad_csv = tmp_path / "naive_ts.csv"
    bad_csv.write_text(
        "timestamp,open,high,low,close,volume\n2024-01-01T00:00:00,1,2,0,1,10\n"
    )
    source = CsvDataSource(bad_csv, symbol="BTCUSDT", timeframe="1h")

    with pytest.raises(InvalidMarketDataError):
        source.load()


def test_empty_csv_raises(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("timestamp,open,high,low,close,volume\n")
    source = CsvDataSource(empty_csv, symbol="BTCUSDT", timeframe="1h")

    with pytest.raises(InvalidMarketDataError):
        source.load()


def test_compute_data_version_is_stable_for_unchanged_content():
    path = _FIXTURES / "sample_ohlcv.csv"

    assert compute_data_version(path) == compute_data_version(path)


def test_compute_data_version_changes_with_content(tmp_path):
    path = tmp_path / "candles.csv"
    path.write_text("timestamp,open,high,low,close,volume\n2024-01-01T00:00:00+00:00,1,2,0,1,10\n")
    version_a = compute_data_version(path)

    path.write_text("timestamp,open,high,low,close,volume\n2024-01-01T00:00:00+00:00,1,2,0,2,10\n")
    version_b = compute_data_version(path)

    assert version_a != version_b


def test_compute_data_version_is_a_sha256_hex_digest():
    version = compute_data_version(_FIXTURES / "sample_ohlcv.csv")

    assert len(version) == 64
    assert all(c in "0123456789abcdef" for c in version)


def test_write_market_data_csv_round_trips_through_csv_data_source(tmp_path):
    source = CsvDataSource(_FIXTURES / "sample_ohlcv.csv", symbol="BTCUSDT", timeframe="1h")
    original = source.load()

    out_path = tmp_path / "written.csv"
    write_market_data_csv(original, out_path)
    reloaded = CsvDataSource(out_path, symbol="BTCUSDT", timeframe="1h").load()

    assert reloaded.candles == original.candles
