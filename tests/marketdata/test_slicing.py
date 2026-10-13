"""slice_market_data: time-range slicing primitive (Фаза 18b).

Both `start`/`end` are inclusive, so two adjacent, non-overlapping slices
are built from adjacent real candle timestamps (no half-open arithmetic),
and summing them reconstructs the original candle set exactly.
"""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import InvalidMarketDataError
from vectorx.marketdata.slicing import slice_market_data
from vectorx.marketdata.types import MarketCandle, MarketData

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _market_data(n: int) -> MarketData:
    candles = tuple(
        MarketCandle(
            timestamp=_START + timedelta(hours=i),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1_000.0,
        )
        for i in range(n)
    )
    return MarketData(symbol="BTCUSDT", timeframe="1h", candles=candles)


def test_slice_includes_candles_at_exact_start_and_end_boundaries():
    data = _market_data(5)

    sliced = slice_market_data(data, data.candles[1].timestamp, data.candles[3].timestamp)

    assert sliced.candles == data.candles[1:4]
    assert sliced.symbol == data.symbol
    assert sliced.timeframe == data.timeframe


def test_slice_empty_range_raises():
    data = _market_data(5)
    start = data.candles[-1].timestamp + timedelta(hours=1)
    end = data.candles[-1].timestamp + timedelta(hours=2)

    with pytest.raises(InvalidMarketDataError):
        slice_market_data(data, start, end)


def test_slice_rejects_start_after_end():
    data = _market_data(5)

    with pytest.raises(InvalidMarketDataError):
        slice_market_data(data, data.candles[3].timestamp, data.candles[1].timestamp)


def test_slice_does_not_mutate_original_market_data():
    data = _market_data(5)
    original_candles = data.candles

    slice_market_data(data, data.candles[1].timestamp, data.candles[3].timestamp)

    assert data.candles == original_candles


def test_two_adjacent_non_overlapping_slices_reconstruct_original_without_loss_or_duplication():
    data = _market_data(10)
    split_index = 6

    first = slice_market_data(data, data.candles[0].timestamp, data.candles[split_index - 1].timestamp)
    second = slice_market_data(data, data.candles[split_index].timestamp, data.candles[-1].timestamp)

    assert first.candles + second.candles == data.candles
    assert len(set(first.candles) & set(second.candles)) == 0
