"""MarketCandle and MarketData: immutable historical OHLCV containers."""

from datetime import UTC, datetime

from vectorx.marketdata.types import MarketCandle, MarketData


def _candle() -> MarketCandle:
    return MarketCandle(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=1_000.0,
    )


def test_market_candle_construction():
    candle = _candle()

    assert candle.timestamp == datetime(2024, 1, 1, tzinfo=UTC)
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 95.0
    assert candle.close == 105.0
    assert candle.volume == 1_000.0


def test_market_candle_is_immutable():
    candle = _candle()
    try:
        candle.close = 106.0
    except AttributeError:
        pass
    else:
        raise AssertionError("MarketCandle must be immutable")


def test_market_data_construction():
    candle = _candle()
    data = MarketData(symbol="BTCUSDT", timeframe="1h", candles=(candle,))

    assert data.symbol == "BTCUSDT"
    assert data.timeframe == "1h"
    assert data.candles == (candle,)


def test_market_data_is_immutable():
    data = MarketData(symbol="BTCUSDT", timeframe="1h", candles=())
    try:
        data.symbol = "ETHUSDT"
    except AttributeError:
        pass
    else:
        raise AssertionError("MarketData must be immutable")
