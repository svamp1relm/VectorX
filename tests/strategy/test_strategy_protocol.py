"""Strategy: the Protocol every trading strategy must satisfy structurally."""

from datetime import UTC, datetime

from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.protocol import Strategy
from vectorx.strategy.signal import Signal


def _candle(close: float = 100.0) -> MarketCandle:
    return MarketCandle(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000.0,
    )


class AlwaysHoldStrategy:
    stop_loss_pct = 0.01

    def on_candle(self, candle: MarketCandle) -> Signal:
        return Signal.HOLD


class BuyOnFirstCandleStrategy:
    stop_loss_pct = 0.01

    def __init__(self) -> None:
        self._seen_first_candle = False

    def on_candle(self, candle: MarketCandle) -> Signal:
        if not self._seen_first_candle:
            self._seen_first_candle = True
            return Signal.BUY
        return Signal.HOLD


def test_a_conforming_class_satisfies_the_protocol():
    assert isinstance(AlwaysHoldStrategy(), Strategy)


def test_a_non_conforming_class_does_not_satisfy_the_protocol():
    class NotAStrategy:
        pass

    assert not isinstance(NotAStrategy(), Strategy)


def test_always_hold_strategy_returns_hold_for_every_candle():
    strategy = AlwaysHoldStrategy()

    assert strategy.on_candle(_candle()) == Signal.HOLD
    assert strategy.on_candle(_candle()) == Signal.HOLD


def test_buy_on_first_candle_strategy_buys_once_then_holds():
    strategy = BuyOnFirstCandleStrategy()

    assert strategy.on_candle(_candle()) == Signal.BUY
    assert strategy.on_candle(_candle()) == Signal.HOLD
    assert strategy.on_candle(_candle()) == Signal.HOLD
