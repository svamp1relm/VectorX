"""Metrics registry: derives per-run statistics from sized Trade[] + equity curve.

Uses `simulate_portfolio` to produce realistic sized trades/equity, so this
test exercises the same data shape `compute_metrics` sees in production
(Phase 7's runner wires Monte Carlo -> Portfolio -> Metrics).
"""

import pytest

from vectorx.core.errors import EmptyTradesError
from vectorx.core.types import Trade
from vectorx.simulation.portfolio import simulate_portfolio
from vectorx.statistics.metrics import compute_metrics


def _trade(index: int, r_multiple: float) -> Trade:
    return Trade(trade_index=index, side="long", r_multiple=r_multiple)


def test_compute_metrics_known_values():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0), _trade(1, -1.0), _trade(2, 2.0), _trade(3, -1.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    metrics = compute_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=10_000.0,
        p_win=0.5,
        win_r=2.0,
        loss_r=-1.0,
        ruined=result.ruined,
    )

    assert metrics.trades == 4
    assert metrics.wins == 2
    assert metrics.losses == 2
    assert metrics.win_rate == pytest.approx(0.5)
    assert metrics.avg_win == pytest.approx(2.0)
    assert metrics.avg_loss == pytest.approx(-1.0)
    assert metrics.expectancy_theoretical == pytest.approx(0.5)
    assert metrics.expectancy_sample == pytest.approx(0.5)
    assert metrics.total_return == pytest.approx(0.01969604, rel=1e-6)
    assert metrics.avg_trade == pytest.approx(49.2401, rel=1e-6)
    assert metrics.variance == pytest.approx(2.25)
    assert metrics.stdev == pytest.approx(1.5)
    assert metrics.max_drawdown == pytest.approx(0.01)
    assert metrics.profit_factor == pytest.approx(2.0)
    assert metrics.ruined is False


def test_no_losing_trades_gives_infinite_profit_factor_and_zero_avg_loss():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0), _trade(1, 2.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    metrics = compute_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=10_000.0,
        p_win=0.5,
        win_r=2.0,
        loss_r=-1.0,
        ruined=result.ruined,
    )

    assert metrics.avg_loss == 0.0
    assert metrics.profit_factor == float("inf")


def test_no_winning_trades_gives_zero_profit_factor_and_zero_avg_win():
    result = simulate_portfolio(
        trades=(_trade(0, -1.0), _trade(1, -1.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    metrics = compute_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=10_000.0,
        p_win=0.5,
        win_r=2.0,
        loss_r=-1.0,
        ruined=result.ruined,
    )

    assert metrics.avg_win == 0.0
    assert metrics.profit_factor == 0.0


def test_rejects_empty_trades():
    with pytest.raises(EmptyTradesError):
        compute_metrics(
            trades=(),
            equity_curve=(),
            initial_capital=10_000.0,
            p_win=0.5,
            win_r=2.0,
            loss_r=-1.0,
            ruined=False,
        )


def test_expectancy_theoretical_is_none_without_model_parameters():
    # A historical backtest run has no p_win/win_r/loss_r model to derive a
    # theoretical expectancy from — compute_metrics must not require them.
    result = simulate_portfolio(
        trades=(_trade(0, 2.0), _trade(1, -1.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    metrics = compute_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=10_000.0,
        ruined=result.ruined,
    )

    assert metrics.expectancy_theoretical is None
    assert metrics.expectancy_sample == pytest.approx(0.5)


def test_expectancy_theoretical_is_still_computed_when_model_parameters_given():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0), _trade(1, -1.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    metrics = compute_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=10_000.0,
        p_win=0.5,
        win_r=2.0,
        loss_r=-1.0,
        ruined=result.ruined,
    )

    assert metrics.expectancy_theoretical == pytest.approx(0.5)
