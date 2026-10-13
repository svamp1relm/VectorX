"""MovingAverageCrossoverStrategy: SMA-based long/flat crossover strategy."""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.moving_average_crossover import MovingAverageCrossoverStrategy
from vectorx.strategy.protocol import Strategy
from vectorx.strategy.signal import Signal

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _candle(offset_minutes: int, close: float) -> MarketCandle:
    return MarketCandle(
        timestamp=_START + timedelta(minutes=offset_minutes),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000.0,
    )


def test_satisfies_strategy_protocol():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4, stop_loss_pct=0.01)

    assert isinstance(strategy, Strategy)


def test_exposes_stop_loss_pct():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4, stop_loss_pct=0.02)

    assert strategy.stop_loss_pct == 0.02


def test_rejects_fast_period_not_less_than_slow_period():
    with pytest.raises(InvalidModelParametersError):
        MovingAverageCrossoverStrategy(fast_period=4, slow_period=4, stop_loss_pct=0.01)


def test_rejects_non_positive_periods():
    with pytest.raises(InvalidModelParametersError):
        MovingAverageCrossoverStrategy(fast_period=0, slow_period=4, stop_loss_pct=0.01)


def test_rejects_non_positive_stop_loss_pct():
    with pytest.raises(InvalidModelParametersError):
        MovingAverageCrossoverStrategy(fast_period=2, slow_period=4, stop_loss_pct=0.0)


def test_holds_during_warm_up_period():
    strategy = MovingAverageCrossoverStrategy(fast_period=3, slow_period=5, stop_loss_pct=0.01)
    closes = [100.0, 101.0, 102.0, 103.0]

    signals = [strategy.on_candle(_candle(i, close)) for i, close in enumerate(closes)]

    assert signals == [Signal.HOLD] * 4


def test_flat_prices_never_cross():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4, stop_loss_pct=0.01)

    signals = [strategy.on_candle(_candle(i, 100.0)) for i in range(10)]

    assert signals == [Signal.HOLD] * 10


def test_known_crossover_sequence_produces_expected_signals():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4, stop_loss_pct=0.01)
    closes = [100.0, 100.0, 100.0, 100.0, 105.0, 110.0, 100.0, 90.0, 85.0, 95.0, 105.0, 110.0]
    expected = [
        Signal.HOLD,
        Signal.HOLD,
        Signal.HOLD,
        Signal.HOLD,  # first candle where both SMAs are defined, no prior diff yet
        Signal.BUY,  # fast crosses above slow
        Signal.HOLD,
        Signal.HOLD,
        Signal.SELL,  # fast crosses below slow
        Signal.HOLD,
        Signal.HOLD,
        Signal.BUY,  # fast crosses above slow again
        Signal.HOLD,
    ]

    signals = [strategy.on_candle(_candle(i, close)) for i, close in enumerate(closes)]

    assert signals == expected
