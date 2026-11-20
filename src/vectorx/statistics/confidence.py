"""bootstrap_confidence_interval: percentile bootstrap CI on a sample mean
(Фаза 19, locked to `vectorx.statistics.versioning.ANALYSIS_VERSION`).

Resamples `values` with replacement `n_resamples` times via a seeded RNG,
takes the mean of each resample, and reports the `confidence`-level
percentile interval of those means. Deterministic given the same
`values`/`seed`/`confidence`/`n_resamples` — required for reproducible
research.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """A bootstrap confidence interval around a point estimate."""

    point_estimate: float
    lower: float
    upper: float
    confidence: float
    n_resamples: int


def bootstrap_confidence_interval(
    values: Sequence[float],
    *,
    seed: int,
    confidence: float = 0.95,
    n_resamples: int = 2000,
) -> ConfidenceInterval:
    """Percentile bootstrap CI on `mean(values)`."""
    if not values:
        raise EmptyTradesError("bootstrap_confidence_interval requires at least one value")
    if not 0.0 < confidence < 1.0:
        raise InvalidModelParametersError(f"confidence must be in (0, 1), got {confidence}")
    if n_resamples <= 0:
        raise InvalidModelParametersError(f"n_resamples must be > 0, got {n_resamples}")

    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)

    resampled_means = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        resampled_means[i] = rng.choice(array, size=array.size, replace=True).mean()

    alpha = 1.0 - confidence
    lower = float(np.quantile(resampled_means, alpha / 2.0))
    upper = float(np.quantile(resampled_means, 1.0 - alpha / 2.0))

    return ConfidenceInterval(
        point_estimate=float(array.mean()),
        lower=lower,
        upper=upper,
        confidence=confidence,
        n_resamples=n_resamples,
    )
