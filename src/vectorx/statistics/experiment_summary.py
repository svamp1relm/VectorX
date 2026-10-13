"""ExperimentSummary: cross-run aggregates and histograms.

`all_r_multiples` is accepted as an already-flattened sequence so the caller
(the experiment runner, Phase 7) can stream trades in and discard them
immediately after — raw `Trade[]` are never retained here or in storage.
"""

import statistics
from collections.abc import Sequence

from vectorx.core.errors import EmptyTradesError
from vectorx.core.types import ExpectancyComparison, ExperimentSummary, Metrics
from vectorx.statistics.histogram import compute_histogram_bins


def compute_experiment_summary(
    run_metrics: tuple[Metrics, ...],
    all_r_multiples: Sequence[float],
    expectancy: ExpectancyComparison | None = None,
) -> ExperimentSummary:
    """Aggregate per-run metrics into experiment-level statistics."""
    if not run_metrics:
        raise EmptyTradesError("compute_experiment_summary requires at least one run")

    total_returns = [metrics.total_return for metrics in run_metrics]
    runs = len(run_metrics)
    mean_total_return = sum(total_returns) / runs
    median_total_return = statistics.median(total_returns)
    variance = sum((tr - mean_total_return) ** 2 for tr in total_returns) / runs

    return ExperimentSummary(
        runs=runs,
        mean_total_return=mean_total_return,
        median_total_return=median_total_return,
        stdev_total_return=variance**0.5,
        p_negative=sum(1 for tr in total_returns if tr < 0.0) / runs,
        p_ruined=sum(1 for metrics in run_metrics if metrics.ruined) / runs,
        total_return_histogram=compute_histogram_bins(total_returns),
        r_multiple_histogram=compute_histogram_bins(all_r_multiples),
        expectancy=expectancy,
    )
