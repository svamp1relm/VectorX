"""compute_risk_adjusted_metrics: Sharpe/Sortino/Calmar over a run's
R-multiples + Metrics (Фаза 19). Unannualized by design — this domain has no
fixed trading frequency to annualize against (Monte Carlo trades have no
calendar time at all).
"""

import pytest

from vectorx.core.errors import EmptyTradesError
from vectorx.statistics.risk_adjusted import compute_risk_adjusted_metrics


def test_sharpe_is_mean_over_stdev_of_r_multiples():
    r_multiples = [1.0, -1.0, 2.0, -2.0, 3.0]

    result = compute_risk_adjusted_metrics(r_multiples, total_return=0.1, max_drawdown=0.05)

    mean_r = sum(r_multiples) / len(r_multiples)
    variance = sum((r - mean_r) ** 2 for r in r_multiples) / len(r_multiples)
    expected_sharpe = mean_r / variance**0.5
    assert result.sharpe == pytest.approx(expected_sharpe)


def test_sharpe_is_none_when_r_multiples_have_zero_variance():
    result = compute_risk_adjusted_metrics([1.0, 1.0, 1.0], total_return=0.1, max_drawdown=0.05)

    assert result.sharpe is None


def test_sortino_is_none_when_there_is_no_downside():
    result = compute_risk_adjusted_metrics([1.0, 2.0, 3.0], total_return=0.1, max_drawdown=0.05)

    assert result.sortino is None


def test_sortino_is_positive_when_mean_return_is_positive_with_some_downside():
    result = compute_risk_adjusted_metrics(
        [2.0, -1.0, 2.0, -1.0, 2.0], total_return=0.1, max_drawdown=0.05
    )

    assert result.sortino is not None
    assert result.sortino > 0.0


def test_calmar_is_total_return_over_max_drawdown():
    result = compute_risk_adjusted_metrics([1.0, -1.0], total_return=0.2, max_drawdown=0.1)

    assert result.calmar == pytest.approx(2.0)


def test_calmar_is_none_when_max_drawdown_is_zero():
    result = compute_risk_adjusted_metrics([1.0, -1.0], total_return=0.2, max_drawdown=0.0)

    assert result.calmar is None


def test_rejects_empty_r_multiples():
    with pytest.raises(EmptyTradesError):
        compute_risk_adjusted_metrics([], total_return=0.0, max_drawdown=0.0)
