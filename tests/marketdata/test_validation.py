"""validate_market_data: provider-independent OHLCV/timestamp validation."""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import InvalidMarketDataError
from vectorx.marketdata.types import MarketCandle, MarketData
from vectorx.marketdata.validation import validate_market_data

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _candle(
    offset_hours: int,
    *,
    open: float = 100.0,
    high: float = 110.0,
    low: float = 95.0,
    close: float = 105.0,
    volume: float = 1_000.0,
) -> MarketCandle:
    return MarketCandle(
        timestamp=_START + timedelta(hours=offset_hours),
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _data(candles: list[MarketCandle]) -> MarketData:
    return MarketData(symbol="BTCUSDT", timeframe="1h", candles=tuple(candles))


def test_valid_market_data_passes_without_gaps():
    data = _data([_candle(0), _candle(1), _candle(2)])

    gaps = validate_market_data(data)

    assert gaps == ()


def test_empty_market_data_raises():
    with pytest.raises(InvalidMarketDataError):
        validate_market_data(_data([]))


def test_duplicate_timestamp_raises():
    data = _data([_candle(0), _candle(0)])

    with pytest.raises(InvalidMarketDataError):
        validate_market_data(data)


def test_out_of_order_timestamp_raises():
    data = _data([_candle(1), _candle(0)])

    with pytest.raises(InvalidMarketDataError):
        validate_market_data(data)


def test_low_greater_than_high_raises():
    data = _data([_candle(0, low=120.0, high=110.0)])

    with pytest.raises(InvalidMarketDataError):
        validate_market_data(data)


def test_open_outside_low_high_range_raises():
    data = _data([_candle(0, open=200.0)])

    with pytest.raises(InvalidMarketDataError):
        validate_market_data(data)


def test_close_outside_low_high_range_raises():
    data = _data([_candle(0, close=1.0)])

    with pytest.raises(InvalidMarketDataError):
        validate_market_data(data)


def test_negative_volume_raises():
    data = _data([_candle(0, volume=-1.0)])

    with pytest.raises(InvalidMarketDataError):
        validate_market_data(data)


def test_gap_detected_but_not_fatal_when_expected_interval_given():
    data = _data([_candle(0), _candle(2)])  # missing hour 1

    gaps = validate_market_data(data, expected_interval=timedelta(hours=1))

    assert len(gaps) == 1
    assert gaps[0].after_index == 0
    assert gaps[0].expected_timestamp == _START + timedelta(hours=1)
    assert gaps[0].actual_timestamp == _START + timedelta(hours=2)


def test_no_gap_check_without_expected_interval():
    data = _data([_candle(0), _candle(5)])  # would be a gap, but no interval given

    gaps = validate_market_data(data)

    assert gaps == ()
