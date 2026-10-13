"""MovingAverageCrossoverStrategy: the first concrete `Strategy` implementation.

Long/flat only (Фаза 14 of the Post-MVP roadmap): `BUY` when the fast SMA
crosses above the slow SMA, `SELL` on the reverse crossover, `HOLD` otherwise
— including during the warm-up period before `slow_period` candles have been
seen. Uses SMA, not EMA, for determinism and simplicity. A `SELL` signal with
no open long position is the Backtest Engine's concern (a future phase), not
this strategy's — it never opens short positions itself.
"""

from collections import deque
from collections.abc import Iterable

from vectorx.core.errors import InvalidModelParametersError
from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.signal import Signal


class MovingAverageCrossoverStrategy:
    """SMA crossover over `fast_period`/`slow_period` bars, long/flat only."""

    def __init__(self, fast_period: int, slow_period: int, stop_loss_pct: float) -> None:
        # `ExperimentSpec` already enforces these for YAML/API-sourced specs;
        # re-checked here so direct construction (CLI/tests) can't skip them
        # and silently misbehave (empty SMA window, division by zero in the
        # backtest engine's r_multiple calculation).
        if fast_period <= 0 or slow_period <= 0:
            raise InvalidModelParametersError(
                f"fast_period ({fast_period}) and slow_period ({slow_period}) must be > 0"
            )
        if fast_period >= slow_period:
            raise InvalidModelParametersError(
                f"fast_period ({fast_period}) must be < slow_period ({slow_period})"
            )
        if stop_loss_pct <= 0.0:
            raise InvalidModelParametersError(f"stop_loss_pct must be > 0, got {stop_loss_pct}")
        self._fast_period = fast_period
        self._slow_period = slow_period
        self.stop_loss_pct = stop_loss_pct
        self._closes: deque[float] = deque(maxlen=slow_period)
        self._previous_diff: float | None = None

    def on_candle(self, candle: MarketCandle) -> Signal:
        self._closes.append(candle.close)

        if len(self._closes) < self._slow_period:
            return Signal.HOLD

        fast_sma = _sma(list(self._closes)[-self._fast_period :])
        slow_sma = _sma(self._closes)
        diff = fast_sma - slow_sma

        signal = Signal.HOLD
        if self._previous_diff is not None:
            if self._previous_diff <= 0.0 < diff:
                signal = Signal.BUY
            elif self._previous_diff >= 0.0 > diff:
                signal = Signal.SELL

        self._previous_diff = diff
        return signal


def _sma(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values)
