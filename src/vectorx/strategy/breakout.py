"""BreakoutStrategy: Donchian-channel breakout, long/flat only (Фаза 22).

Reacts to *extremes* of a rolling window rather than a moving average:
enters when `close` makes a new high over the prior `entry_lookback`
candles, exits when `close` makes a new low over the prior `exit_lookback`
candles. The comparison windows only ever contain *prior* candles — each
candle's own high/low is appended after that candle's signal is decided, so
a candle can never trigger a breakout against itself.
"""

from collections import deque

from vectorx.core.errors import InvalidModelParametersError
from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.signal import Signal


class BreakoutStrategy:
    """Long/flat Donchian-channel breakout."""

    def __init__(self, entry_lookback: int, exit_lookback: int, stop_loss_pct: float) -> None:
        if entry_lookback <= 0 or exit_lookback <= 0:
            raise InvalidModelParametersError(
                f"entry_lookback ({entry_lookback}) and exit_lookback ({exit_lookback}) "
                "must be > 0"
            )
        if stop_loss_pct <= 0.0:
            raise InvalidModelParametersError(f"stop_loss_pct must be > 0, got {stop_loss_pct}")
        self._entry_lookback = entry_lookback
        self._exit_lookback = exit_lookback
        self.stop_loss_pct = stop_loss_pct
        self._highs: deque[float] = deque(maxlen=entry_lookback)
        self._lows: deque[float] = deque(maxlen=exit_lookback)
        self._in_position = False

    def on_candle(self, candle: MarketCandle) -> Signal:
        signal = Signal.HOLD

        if not self._in_position:
            if len(self._highs) == self._entry_lookback and candle.close > max(self._highs):
                self._in_position = True
                signal = Signal.BUY
        elif len(self._lows) == self._exit_lookback and candle.close < min(self._lows):
            self._in_position = False
            signal = Signal.SELL

        self._highs.append(candle.high)
        self._lows.append(candle.low)
        return signal
