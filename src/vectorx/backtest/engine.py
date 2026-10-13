"""run_historical_backtest: sequential candle-by-candle Strategy -> Trade[].

Reuses the exact `Trade` contract Monte Carlo already produces (see
`vectorx.core.types.Trade`'s docstring): `entry_ts`/`exit_ts`/`pnl` are filled
with real market data here, `size`/`pnl_money` stay `None` until
`vectorx.simulation.portfolio.simulate_portfolio` sizes them — that function
is reused unchanged.

Position management (long/flat only, no pyramiding, no short) is this
engine's responsibility, not the strategy's: a `BUY` while already in a
position is ignored, and a `SELL` with no open position is ignored (see
`vectorx.strategy.protocol.Strategy`'s docstring). A position still open when
the data ends is force-closed at the last candle's close so no open trade is
silently dropped.

`r_multiple` is derived from real prices via the strategy's own
`stop_loss_pct`: `(exit_price - entry_price) / (entry_price * stop_loss_pct)`.
This is a risk-unit measurement only — no stop-loss is actually triggered
intrabar; real stop execution is deliberately out of scope for this phase.
"""

from dataclasses import dataclass
from datetime import datetime

from vectorx.core.types import Trade
from vectorx.marketdata.types import MarketData
from vectorx.strategy.protocol import Strategy
from vectorx.strategy.signal import Signal


@dataclass(frozen=True, slots=True)
class _OpenPosition:
    entry_ts: datetime
    entry_price: float


def run_historical_backtest(market_data: MarketData, strategy: Strategy) -> tuple[Trade, ...]:
    """Replay `market_data.candles` through `strategy`, one candle at a time."""
    trades: list[Trade] = []
    position: _OpenPosition | None = None

    for candle in market_data.candles:
        signal = strategy.on_candle(candle)

        if position is None:
            if signal == Signal.BUY:
                position = _OpenPosition(entry_ts=candle.timestamp, entry_price=candle.close)
        elif signal == Signal.SELL:
            trades.append(
                _close_trade(position, len(trades), candle.timestamp, candle.close, strategy)
            )
            position = None

    if position is not None:
        last_candle = market_data.candles[-1]
        trades.append(
            _close_trade(
                position, len(trades), last_candle.timestamp, last_candle.close, strategy
            )
        )

    return tuple(trades)


def _close_trade(
    position: _OpenPosition,
    trade_index: int,
    exit_ts: datetime,
    exit_price: float,
    strategy: Strategy,
) -> Trade:
    pnl = exit_price - position.entry_price
    r_multiple = pnl / (position.entry_price * strategy.stop_loss_pct)
    return Trade(
        trade_index=trade_index,
        side="long",
        r_multiple=r_multiple,
        entry_ts=position.entry_ts,
        exit_ts=exit_ts,
        pnl=pnl,
    )
