"""Portfolio sizing: risk-per-trade compounds off the current equity.

`simulate_portfolio` sizes each incoming R-multiple trade against the
account's *current* equity (not the initial capital), applies commission
and slippage as R costs, tracks a full equity curve with running
peak-to-trough drawdown, and stops early on ruin (equity <= 0).
"""

import pytest

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.core.types import Trade
from vectorx.simulation.portfolio import simulate_portfolio


def _trade(index: int, r_multiple: float) -> Trade:
    return Trade(trade_index=index, side="long", r_multiple=r_multiple)


def test_single_trade_is_sized_against_initial_capital():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0),), initial_capital=10_000.0, risk_per_trade=0.01
    )

    sized = result.trades[0]
    assert sized.size == pytest.approx(100.0)
    assert sized.pnl_money == pytest.approx(200.0)
    assert result.equity_curve[-1].equity == pytest.approx(10_200.0)


def test_risk_compounds_from_updated_equity():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0), _trade(1, 2.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    first, second = result.trades
    assert first.size == pytest.approx(100.0)
    assert second.size == pytest.approx(102.0)
    assert second.pnl_money == pytest.approx(204.0)
    assert result.equity_curve[-1].equity == pytest.approx(10_404.0)


def test_commission_and_slippage_are_subtracted_in_r_before_sizing():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0),),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
        commission_r=0.01,
        slippage_r=0.01,
    )

    sized = result.trades[0]
    assert sized.size == pytest.approx(100.0)
    assert sized.pnl_money == pytest.approx(198.0)
    assert result.equity_curve[-1].equity == pytest.approx(10_198.0)


def test_equity_curve_starts_with_initial_capital_at_index_zero():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0),), initial_capital=10_000.0, risk_per_trade=0.01
    )

    start, after_trade = result.equity_curve
    assert start.index == 0
    assert start.equity == pytest.approx(10_000.0)
    assert start.drawdown == 0.0
    assert after_trade.index == 1
    assert after_trade.equity == pytest.approx(10_200.0)
    assert after_trade.drawdown == 0.0


def test_drawdown_tracks_peak_to_trough():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0), _trade(1, 2.0), _trade(2, -1.0), _trade(3, -1.0)),
        initial_capital=10_000.0,
        risk_per_trade=0.01,
    )

    points = result.equity_curve
    assert points[2].drawdown == pytest.approx(0.0)
    assert points[3].drawdown == pytest.approx(0.01)
    assert points[4].drawdown == pytest.approx(1 - 0.99 * 0.99)


def test_ruin_stops_processing_and_marks_ruined():
    result = simulate_portfolio(
        trades=(_trade(0, -1.0), _trade(1, 2.0)),
        initial_capital=10_000.0,
        risk_per_trade=1.0,
    )

    assert result.ruined is True
    assert len(result.trades) == 1
    assert result.equity_curve[-1].equity == pytest.approx(0.0)


def test_ruin_allows_negative_equity_without_clamping():
    result = simulate_portfolio(
        trades=(_trade(0, -1.0),),
        initial_capital=10_000.0,
        risk_per_trade=1.0,
        commission_r=0.05,
    )

    assert result.ruined is True
    assert result.equity_curve[-1].equity == pytest.approx(-500.0)


def test_no_ruin_when_equity_stays_positive():
    result = simulate_portfolio(
        trades=(_trade(0, 2.0),), initial_capital=10_000.0, risk_per_trade=0.01
    )

    assert result.ruined is False


def test_rejects_non_positive_initial_capital():
    with pytest.raises(InvalidModelParametersError):
        simulate_portfolio(trades=(_trade(0, 2.0),), initial_capital=0.0, risk_per_trade=0.01)


def test_rejects_risk_per_trade_out_of_bounds():
    with pytest.raises(InvalidModelParametersError):
        simulate_portfolio(trades=(_trade(0, 2.0),), initial_capital=10_000.0, risk_per_trade=0.0)
    with pytest.raises(InvalidModelParametersError):
        simulate_portfolio(trades=(_trade(0, 2.0),), initial_capital=10_000.0, risk_per_trade=1.01)


def test_rejects_negative_commission_or_slippage():
    with pytest.raises(InvalidModelParametersError):
        simulate_portfolio(
            trades=(_trade(0, 2.0),),
            initial_capital=10_000.0,
            risk_per_trade=0.01,
            commission_r=-0.01,
        )
    with pytest.raises(InvalidModelParametersError):
        simulate_portfolio(
            trades=(_trade(0, 2.0),),
            initial_capital=10_000.0,
            risk_per_trade=0.01,
            slippage_r=-0.01,
        )


def test_rejects_empty_trades():
    with pytest.raises(EmptyTradesError):
        simulate_portfolio(trades=(), initial_capital=10_000.0, risk_per_trade=0.01)
