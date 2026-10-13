"""BreakoutStrategy: Donchian-channel breakout, long/flat only (Фаза 22).

Distinct in character from MA Crossover (mean-following via moving
averages): reacts to *extremes* of a rolling window — enters on a new high
over `entry_lookback` candles, exits on a new low over `exit_lookback`
candles. Added as the Фаза 22 litmus test for the 18-21 pipeline's
generalization.
"""

from datetime import UTC, datetime, timedelta

import pytest

from vectorx.core.errors import InvalidModelParametersError
from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.breakout import BreakoutStrategy
from vectorx.strategy.protocol import Strategy
from vectorx.strategy.signal import Signal

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _candle(offset_hours: int, high: float, low: float, close: float) -> MarketCandle:
    return MarketCandle(
        timestamp=_START + timedelta(hours=offset_hours),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=1_000.0,
    )


def test_satisfies_strategy_protocol():
    strategy = BreakoutStrategy(entry_lookback=3, exit_lookback=3, stop_loss_pct=0.02)

    assert isinstance(strategy, Strategy)


def test_exposes_stop_loss_pct():
    strategy = BreakoutStrategy(entry_lookback=3, exit_lookback=3, stop_loss_pct=0.05)

    assert strategy.stop_loss_pct == 0.05


def test_holds_during_entry_warm_up():
    strategy = BreakoutStrategy(entry_lookback=3, exit_lookback=3, stop_loss_pct=0.02)
    candles = [_candle(i, 101.0, 99.0, 100.0) for i in range(3)]

    signals = [strategy.on_candle(c) for c in candles]

    assert signals == [Signal.HOLD, Signal.HOLD, Signal.HOLD]


def test_buys_on_new_high_breakout_after_warm_up():
    strategy = BreakoutStrategy(entry_lookback=3, exit_lookback=3, stop_loss_pct=0.02)
    warm_up = [_candle(i, 101.0, 99.0, 100.0) for i in range(3)]
    breakout = _candle(3, 110.0, 100.0, 110.0)

    for c in warm_up:
        strategy.on_candle(c)
    signal = strategy.on_candle(breakout)

    assert signal == Signal.BUY


def test_sells_on_new_low_breakdown_while_in_position():
    strategy = BreakoutStrategy(entry_lookback=2, exit_lookback=2, stop_loss_pct=0.02)
    warm_up = [_candle(0, 101.0, 99.0, 100.0), _candle(1, 101.0, 99.0, 100.0)]
    breakout = _candle(2, 110.0, 100.0, 110.0)
    hold_1 = _candle(3, 111.0, 100.0, 105.0)
    hold_2 = _candle(4, 106.0, 101.0, 103.0)
    breakdown = _candle(5, 103.0, 90.0, 90.0)

    for c in warm_up:
        strategy.on_candle(c)
    assert strategy.on_candle(breakout) == Signal.BUY
    assert strategy.on_candle(hold_1) == Signal.HOLD
    assert strategy.on_candle(hold_2) == Signal.HOLD
    assert strategy.on_candle(breakdown) == Signal.SELL


def test_rejects_non_positive_lookbacks():
    with pytest.raises(InvalidModelParametersError):
        BreakoutStrategy(entry_lookback=0, exit_lookback=3, stop_loss_pct=0.02)
    with pytest.raises(InvalidModelParametersError):
        BreakoutStrategy(entry_lookback=3, exit_lookback=0, stop_loss_pct=0.02)


def test_rejects_non_positive_stop_loss_pct():
    with pytest.raises(InvalidModelParametersError):
        BreakoutStrategy(entry_lookback=3, exit_lookback=3, stop_loss_pct=0.0)
