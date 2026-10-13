"""Portfolio simulation: size trades against current equity, track drawdown.

This is the MVP portfolio model: exactly one open position at a time
(`max_positions=1`). That is a limitation of *this* simulator, not of the
architecture — `Trade` and the core types place no such restriction, so a
future multi-position portfolio can reuse them unchanged.

Costs (`commission_r`, `slippage_r`) are R-denominated per-trade drags,
subtracted from a trade's `r_multiple` before it is sized into money.
`Trade.risk` (always 1.0 from Monte Carlo) is the R-normalization unit the
trade's `r_multiple` is expressed against; it is unrelated to
`risk_per_trade` (this portfolio's equity fraction) or the resulting
money `size` (risk_amount) — the three must not be conflated.
"""

from dataclasses import dataclass, replace

import numpy as np

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.core.types import EquityPoint, Trade


@dataclass(frozen=True, slots=True)
class PortfolioResult:
    """Sized trades and the full (non-downsampled) equity curve for one run."""

    trades: tuple[Trade, ...]
    equity_curve: tuple[EquityPoint, ...]
    ruined: bool


def _validate_portfolio_parameters(
    initial_capital: float, risk_per_trade: float, commission_r: float, slippage_r: float
) -> None:
    if initial_capital <= 0.0:
        raise InvalidModelParametersError(f"initial_capital must be > 0, got {initial_capital}")
    if not 0.0 < risk_per_trade <= 1.0:
        raise InvalidModelParametersError(
            f"risk_per_trade must be in (0, 1], got {risk_per_trade}"
        )
    if commission_r < 0.0:
        raise InvalidModelParametersError(f"commission_r must be >= 0, got {commission_r}")
    if slippage_r < 0.0:
        raise InvalidModelParametersError(f"slippage_r must be >= 0, got {slippage_r}")


def simulate_portfolio(
    trades: tuple[Trade, ...],
    initial_capital: float,
    risk_per_trade: float,
    commission_r: float = 0.0,
    slippage_r: float = 0.0,
) -> PortfolioResult:
    """Apply position sizing and equity tracking to a run's Monte Carlo trades.

    Risk is a fraction of *current* equity, so each trade's risk_amount is
    computed just before it is applied, not fixed at `initial_capital`.
    Processing stops at the first trade that leaves equity <= 0 (ruin); that
    trade's result is kept as-is (equity is not clamped to zero), and no
    later trades are executed or sized.
    """
    if not trades:
        raise EmptyTradesError("simulate_portfolio requires at least one trade")
    _validate_portfolio_parameters(initial_capital, risk_per_trade, commission_r, slippage_r)

    equity = initial_capital
    peak = initial_capital
    sized_trades: list[Trade] = []
    equity_curve: list[EquityPoint] = [EquityPoint(index=0, equity=equity, drawdown=0.0)]
    ruined = False

    for trade in trades:
        risk_amount = equity * risk_per_trade
        net_r = trade.r_multiple - commission_r - slippage_r
        pnl_money = risk_amount * net_r
        equity += pnl_money

        sized_trades.append(replace(trade, size=risk_amount, pnl_money=pnl_money))
        peak = max(peak, equity)
        # Not clamped to 1.0: equity is allowed to go negative on ruin (see
        # the docstring above), so drawdown can legitimately exceed 100%.
        drawdown = (peak - equity) / peak
        equity_curve.append(
            EquityPoint(index=len(equity_curve), equity=equity, drawdown=drawdown)
        )

        if equity <= 0.0:
            ruined = True
            break

    return PortfolioResult(
        trades=tuple(sized_trades), equity_curve=tuple(equity_curve), ruined=ruined
    )


def downsample_equity_curve(
    curve: tuple[EquityPoint, ...], max_points: int = 500
) -> tuple[EquityPoint, ...]:
    """Reduce a curve to at most `max_points`, evenly spaced, keeping the ends.

    Used only for storage/UI; statistics always operate on the full curve.
    """
    if len(curve) <= max_points:
        return curve

    positions = np.linspace(0, len(curve) - 1, num=max_points)
    indices = sorted({round(float(p)) for p in positions})
    return tuple(curve[i] for i in indices)
