"""BuyAndHoldStrategy/RandomEntryStrategy: benchmark `Strategy` implementations
(Фаза 19) — baselines to compare MA Crossover's statistical significance against.
"""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.benchmarks import BuyAndHoldStrategy, RandomEntryStrategy
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


def test_buy_and_hold_satisfies_strategy_protocol():
    strategy = BuyAndHoldStrategy(stop_loss_pct=0.1)

    assert isinstance(strategy, Strategy)


def test_buy_and_hold_buys_on_first_candle_then_always_holds():
    strategy = BuyAndHoldStrategy(stop_loss_pct=0.1)
    closes = [100.0, 101.0, 99.0, 105.0]

    signals = [strategy.on_candle(_candle(i, close)) for i, close in enumerate(closes)]

    assert signals == [Signal.BUY, Signal.HOLD, Signal.HOLD, Signal.HOLD]


def test_buy_and_hold_rejects_non_positive_stop_loss_pct():
    with pytest.raises(InvalidModelParametersError):
        BuyAndHoldStrategy(stop_loss_pct=0.0)


def test_random_entry_satisfies_strategy_protocol():
    strategy = RandomEntryStrategy(stop_loss_pct=0.1, seed=1)

    assert isinstance(strategy, Strategy)


def test_random_entry_is_deterministic_for_same_seed():
    closes = [100.0 + i for i in range(50)]

    strategy_a = RandomEntryStrategy(stop_loss_pct=0.1, seed=7)
    strategy_b = RandomEntryStrategy(stop_loss_pct=0.1, seed=7)

    signals_a = [strategy_a.on_candle(_candle(i, close)) for i, close in enumerate(closes)]
    signals_b = [strategy_b.on_candle(_candle(i, close)) for i, close in enumerate(closes)]

    assert signals_a == signals_b


def test_random_entry_diverges_for_different_seeds():
    closes = [100.0 + i for i in range(50)]

    strategy_a = RandomEntryStrategy(stop_loss_pct=0.1, seed=1)
    strategy_b = RandomEntryStrategy(stop_loss_pct=0.1, seed=2)

    signals_a = [strategy_a.on_candle(_candle(i, close)) for i, close in enumerate(closes)]
    signals_b = [strategy_b.on_candle(_candle(i, close)) for i, close in enumerate(closes)]

    assert signals_a != signals_b


def test_random_entry_never_buys_while_already_in_a_virtual_position():
    closes = [100.0 + i for i in range(200)]
    strategy = RandomEntryStrategy(
        stop_loss_pct=0.1, seed=3, entry_probability=0.5, exit_probability=0.5
    )

    in_position = False
    for i, close in enumerate(closes):
        signal = strategy.on_candle(_candle(i, close))
        if signal == Signal.BUY:
            assert not in_position
            in_position = True
        elif signal == Signal.SELL:
            assert in_position
            in_position = False


def test_random_entry_rejects_invalid_probabilities():
    with pytest.raises(InvalidModelParametersError):
        RandomEntryStrategy(stop_loss_pct=0.1, seed=1, entry_probability=0.0)
    with pytest.raises(InvalidModelParametersError):
        RandomEntryStrategy(stop_loss_pct=0.1, seed=1, exit_probability=1.5)


def test_random_entry_rejects_non_positive_stop_loss_pct():
    with pytest.raises(InvalidModelParametersError):
        RandomEntryStrategy(stop_loss_pct=0.0, seed=1)
