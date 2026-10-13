"""BuyAndHoldStrategy/RandomEntryStrategy: benchmark `Strategy` implementations
(Фаза 19). Both implement `vectorx.strategy.protocol.Strategy` unchanged — a
benchmark is just another strategy the same `run_historical_backtest`/
`ExperimentSpec` pipeline already supports.

Statistical analysis (Фаза 19) is incomplete without something to compare
a candidate strategy's significance against: "better than buy-and-hold" and
"better than random entries" are the two baselines research platforms
typically need before trusting a strategy's edge.
"""

import numpy as np

from vectorx.core.errors import InvalidModelParametersError
from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.signal import Signal


class BuyAndHoldStrategy:
    """Buys on the very first candle seen, then holds forever (long/flat engine
    force-closes the position at the end of the data)."""

    def __init__(self, stop_loss_pct: float) -> None:
        if stop_loss_pct <= 0.0:
            raise InvalidModelParametersError(f"stop_loss_pct must be > 0, got {stop_loss_pct}")
        self.stop_loss_pct = stop_loss_pct
        self._has_bought = False

    def on_candle(self, candle: MarketCandle) -> Signal:
        if not self._has_bought:
            self._has_bought = True
            return Signal.BUY
        return Signal.HOLD


class RandomEntryStrategy:
    """Null-hypothesis benchmark: i.i.d. Bernoulli entry/exit decisions each
    candle, independent of price. Tracks its own flat/long state locally so it
    never emits a `BUY` while "in position" or a `SELL` while flat — matching
    the Backtest Engine's own ignore-redundant-signal rules (see
    `vectorx.backtest.engine`), so the two stay in sync without the strategy
    ever observing actual position state.
    """

    def __init__(
        self,
        stop_loss_pct: float,
        seed: int,
        entry_probability: float = 0.1,
        exit_probability: float = 0.1,
    ) -> None:
        if stop_loss_pct <= 0.0:
            raise InvalidModelParametersError(f"stop_loss_pct must be > 0, got {stop_loss_pct}")
        if not 0.0 < entry_probability <= 1.0:
            raise InvalidModelParametersError(
                f"entry_probability must be in (0, 1], got {entry_probability}"
            )
        if not 0.0 < exit_probability <= 1.0:
            raise InvalidModelParametersError(
                f"exit_probability must be in (0, 1], got {exit_probability}"
            )
        self.stop_loss_pct = stop_loss_pct
        self._entry_probability = entry_probability
        self._exit_probability = exit_probability
        self._rng = np.random.default_rng(seed)
        self._in_position = False

    def on_candle(self, candle: MarketCandle) -> Signal:
        if not self._in_position:
            if self._rng.random() < self._entry_probability:
                self._in_position = True
                return Signal.BUY
            return Signal.HOLD

        if self._rng.random() < self._exit_probability:
            self._in_position = False
            return Signal.SELL
        return Signal.HOLD
