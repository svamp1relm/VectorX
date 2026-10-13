"""Metrics registry: reduces one run's sized Trade[] + equity curve to Metrics.

Consumes data only — no YAML, no Postgres, no HTTP. `trades` must already be
sized by `vectorx.simulation.portfolio.simulate_portfolio` (i.e. `pnl_money`
is populated). `p_win`/`win_r`/`loss_r` are the Monte Carlo model's
parameters and are optional: a historical backtest run has no such model, so
`expectancy_theoretical` is `None` unless all three are given.
"""

from vectorx.core.errors import EmptyTradesError
from vectorx.core.types import EquityPoint, Metrics, Trade
from vectorx.math.expectancy import expectancy_sample, expectancy_theoretical


def compute_metrics(
    trades: tuple[Trade, ...],
    equity_curve: tuple[EquityPoint, ...],
    initial_capital: float,
    ruined: bool,
    p_win: float | None = None,
    win_r: float | None = None,
    loss_r: float | None = None,
) -> Metrics:
    """Compute per-run statistics. `ruined` is passed through from the portfolio."""
    if not trades:
        raise EmptyTradesError("compute_metrics requires at least one trade")

    if p_win is not None and win_r is not None and loss_r is not None:
        expectancy_theo = expectancy_theoretical(p_win=p_win, win_r=win_r, loss_r=loss_r)
    else:
        expectancy_theo = None

    r_multiples = [trade.r_multiple for trade in trades]
    money_pnls = [trade.pnl_money for trade in trades]
    wins_r = [r for r in r_multiples if r > 0.0]
    losses_r = [r for r in r_multiples if r < 0.0]

    gross_profit = sum(wins_r)
    gross_loss = abs(sum(losses_r))
    if gross_loss > 0.0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0.0 else 0.0

    mean_r = sum(r_multiples) / len(r_multiples)
    variance = sum((r - mean_r) ** 2 for r in r_multiples) / len(r_multiples)
    equity_end = equity_curve[-1].equity

    return Metrics(
        trades=len(trades),
        wins=len(wins_r),
        losses=len(losses_r),
        win_rate=len(wins_r) / len(trades),
        avg_win=(sum(wins_r) / len(wins_r)) if wins_r else 0.0,
        avg_loss=(sum(losses_r) / len(losses_r)) if losses_r else 0.0,
        expectancy_theoretical=expectancy_theo,
        expectancy_sample=expectancy_sample(r_multiples),
        total_return=(equity_end - initial_capital) / initial_capital,
        avg_trade=sum(money_pnls) / len(money_pnls),
        variance=variance,
        stdev=variance**0.5,
        max_drawdown=max(point.drawdown for point in equity_curve),
        profit_factor=profit_factor,
        ruined=ruined,
    )
