"""BreakoutStrategy: Donchian-channel breakout, long/flat only (Фаза 22).

Reacts to *extremes* of a rolling window rather than a moving average:
enters when `close` makes a new high over the prior `entry_lookback`
candles, exits when `close` makes a new low over the prior `exit_lookback`
candles. The comparison windows only ever contain *prior* candles — each
candle's own high/low is appended after that candle's signal is decided, so
a candle can never trigger a breakout against itself.
"""

from collections import deque
from math import isfinite

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
        if not isfinite(stop_loss_pct):
            raise InvalidModelParametersError("stop_loss_pct must be finite")
        if stop_loss_pct <= 0.0:
            raise InvalidModelParametersError(f"stop_loss_pct must be > 0, got {stop_loss_pct}")
        self._entry_lookback = entry_lookback
        self._exit_lookback = exit_lookback
        self.stop_loss_pct = stop_loss_pct
        self._highs: deque[float] = deque(maxlen=entry_lookback)
        self._lows: deque[float] = deque(maxlen=exit_lookback)
        self._high_channel: deque[float] = deque()
        self._low_channel: deque[float] = deque()
        self._in_position = False

    def reset_position(self) -> None:
        self._in_position = False

    def _append_high(self, value: float) -> None:
        if len(self._highs) == self._entry_lookback:
            removed = self._highs[0]
            if self._high_channel and self._high_channel[0] == removed:
                self._high_channel.popleft()
        self._highs.append(value)
        while self._high_channel and self._high_channel[-1] <= value:
            self._high_channel.pop()
        self._high_channel.append(value)

    def _append_low(self, value: float) -> None:
        if len(self._lows) == self._exit_lookback:
            removed = self._lows[0]
            if self._low_channel and self._low_channel[0] == removed:
                self._low_channel.popleft()
        self._lows.append(value)
        while self._low_channel and self._low_channel[-1] >= value:
            self._low_channel.pop()
        self._low_channel.append(value)

    def on_candle(self, candle: MarketCandle) -> Signal:
        signal = Signal.HOLD

        if not self._in_position:
            if len(self._highs) == self._entry_lookback and candle.close > self._high_channel[0]:
                self._in_position = True
                signal = Signal.BUY
        elif len(self._lows) == self._exit_lookback and candle.close < self._low_channel[0]:
            self._in_position = False
            signal = Signal.SELL

        self._append_high(candle.high)
        self._append_low(candle.low)
        return signal
