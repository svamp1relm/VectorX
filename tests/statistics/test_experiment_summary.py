"""Cross-run ExperimentSummary: aggregates + histograms, no raw Trade[] kept."""

import statistics as pystats

import pytest

from vectorx.core.errors import EmptyTradesError
from vectorx.core.types import Metrics
from vectorx.statistics.experiment_summary import compute_experiment_summary


def _metrics(total_return: float, ruined: bool) -> Metrics:
    return Metrics(
        trades=1,
        wins=1 if total_return > 0 else 0,
        losses=0 if total_return > 0 else 1,
        win_rate=1.0 if total_return > 0 else 0.0,
        avg_win=0.0,
        avg_loss=0.0,
        expectancy_theoretical=0.0,
        expectancy_sample=0.0,
        total_return=total_return,
        avg_trade=0.0,
        variance=0.0,
        stdev=0.0,
        max_drawdown=0.0,
        profit_factor=0.0,
        ruined=ruined,
    )


def test_aggregates_across_runs():
    total_returns = [0.10, -0.05, 0.20, -0.02]
    run_metrics = (
        _metrics(0.10, ruined=False),
        _metrics(-0.05, ruined=True),
        _metrics(0.20, ruined=False),
        _metrics(-0.02, ruined=False),
    )
    all_r_multiples = [2.0, -1.0, 2.0, -1.0, 2.0]

    summary = compute_experiment_summary(run_metrics, all_r_multiples)

    assert summary.runs == 4
    assert summary.mean_total_return == pytest.approx(pystats.mean(total_returns))
    assert summary.median_total_return == pytest.approx(pystats.median(total_returns))
    assert summary.stdev_total_return == pytest.approx(pystats.pstdev(total_returns))
    assert summary.p_negative == pytest.approx(0.5)
    assert summary.p_ruined == pytest.approx(0.25)


def test_total_return_histogram_covers_all_runs():
    run_metrics = (_metrics(0.1, False), _metrics(-0.1, True), _metrics(0.3, False))

    summary = compute_experiment_summary(run_metrics, all_r_multiples=[1.0])

    assert sum(summary.total_return_histogram.counts) == 3
    assert len(summary.total_return_histogram.edges) == 51


def test_r_multiple_histogram_covers_all_trades():
    run_metrics = (_metrics(0.1, False),)
    all_r_multiples = [2.0, -1.0, 2.0, -1.0, 2.0]

    summary = compute_experiment_summary(run_metrics, all_r_multiples)

    assert sum(summary.r_multiple_histogram.counts) == len(all_r_multiples)


def test_rejects_empty_run_metrics():
    with pytest.raises(EmptyTradesError):
        compute_experiment_summary((), all_r_multiples=[1.0])
