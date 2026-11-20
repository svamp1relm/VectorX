"""Strategy: the provider-independent contract every trading strategy implements.

Push model: a future Historical Backtest Engine (Фаза 15) feeds one
`MarketCandle` at a time; the strategy owns its own internal state (e.g. a
rolling window of closes) between calls. `Strategy` never sees positions,
capital, PostgreSQL, FastAPI, or Vue — it only signals directional intent.
Whether that intent can actually be acted on (e.g. ignoring a `SELL` signal
when there is no open long position) is the Backtest Engine's responsibility,
not the strategy's — the same split already used between `Trade` generation
and `PortfolioSimulator`.

`stop_loss_pct` is the strategy's own risk unit: the Backtest Engine converts
a trade's raw price PnL into `r_multiple` as
`(exit_price - entry_price) / (entry_price * stop_loss_pct)`. It is a unit of
measurement only in Фаза 15 — no stop-loss is actually triggered intrabar;
real stop execution is deliberately deferred (see the roadmap).
"""

from typing import Protocol, runtime_checkable

from vectorx.marketdata.types import MarketCandle
from vectorx.strategy.signal import Signal


@runtime_checkable
class Strategy(Protocol):
    """Consumes one candle at a time, returns a directional `Signal`."""

    stop_loss_pct: float

    def on_candle(self, candle: MarketCandle) -> Signal:
        """Update internal state with `candle` and return this candle's signal."""
        ...
