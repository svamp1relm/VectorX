"""significance_vs_zero / significance_vs_benchmark: bootstrap significance
tests over sample R-multiples (Фаза 19, locked to
`vectorx.statistics.versioning.ANALYSIS_VERSION`).

"Significant" means the resampled confidence interval excludes the null
value (0 for `significance_vs_zero`; the two-sample mean difference for
`significance_vs_benchmark`) — a bootstrap analogue of a two-sided
significance test, built on the same percentile bootstrap as
`bootstrap_confidence_interval`.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.statistics.confidence import ConfidenceInterval, bootstrap_confidence_interval


@dataclass(frozen=True, slots=True)
class SignificanceResult:
    """A confidence interval plus whether it excludes the null value."""

    ci: ConfidenceInterval
    significant: bool


def significance_vs_zero(
    r_multiples: Sequence[float],
    *,
    seed: int,
    confidence: float = 0.95,
    n_resamples: int = 2000,
) -> SignificanceResult:
    """Is `mean(r_multiples)` significantly different from 0?"""
    ci = bootstrap_confidence_interval(
        r_multiples, seed=seed, confidence=confidence, n_resamples=n_resamples
    )
    return SignificanceResult(ci=ci, significant=not (ci.lower <= 0.0 <= ci.upper))


def significance_vs_benchmark(
    sample_r_multiples: Sequence[float],
    benchmark_r_multiples: Sequence[float],
    *,
    seed: int,
    confidence: float = 0.95,
    n_resamples: int = 2000,
) -> SignificanceResult:
    """Is `mean(sample_r_multiples) - mean(benchmark_r_multiples)` significantly nonzero?

    Each resample draws independently (with replacement) from `sample` and
    `benchmark`; the CI is built on the resampled mean *differences*.
    """
    if not sample_r_multiples or not benchmark_r_multiples:
        raise EmptyTradesError("significance_vs_benchmark requires two non-empty samples")
    if not 0.0 < confidence < 1.0:
        raise InvalidModelParametersError(f"confidence must be in (0, 1), got {confidence}")
    if n_resamples <= 0:
        raise InvalidModelParametersError(f"n_resamples must be > 0, got {n_resamples}")

    sample = np.asarray(sample_r_multiples, dtype=float)
    benchmark = np.asarray(benchmark_r_multiples, dtype=float)
    rng = np.random.default_rng(seed)

    diffs = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        sample_mean = rng.choice(sample, size=sample.size, replace=True).mean()
        benchmark_mean = rng.choice(benchmark, size=benchmark.size, replace=True).mean()
        diffs[i] = sample_mean - benchmark_mean

    alpha = 1.0 - confidence
    lower = float(np.quantile(diffs, alpha / 2.0))
    upper = float(np.quantile(diffs, 1.0 - alpha / 2.0))

    ci = ConfidenceInterval(
        point_estimate=float(sample.mean() - benchmark.mean()),
        lower=lower,
        upper=upper,
        confidence=confidence,
        n_resamples=n_resamples,
    )
    return SignificanceResult(ci=ci, significant=not (ci.lower <= 0.0 <= ci.upper))
