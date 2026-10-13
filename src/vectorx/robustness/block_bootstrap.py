"""block_bootstrap_confidence_interval: moving-block bootstrap CI (Фаза 21).

Resamples contiguous blocks of `block_size` consecutive values (with
replacement) rather than individual values
(`vectorx.statistics.confidence.bootstrap_confidence_interval`'s i.i.d.
assumption), preserving any autocorrelation between consecutive trades.
Tests robustness to the sequential structure of a realized trade sequence,
not just its marginal distribution. Reuses the same `ConfidenceInterval`
shape (Фаза 19) — this is a different resampling algorithm, not a new
result type.
"""

from collections.abc import Sequence

import numpy as np

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.statistics.confidence import ConfidenceInterval


def block_bootstrap_confidence_interval(
    values: Sequence[float],
    *,
    block_size: int,
    seed: int,
    confidence: float = 0.95,
    n_resamples: int = 2000,
) -> ConfidenceInterval:
    """Moving-block bootstrap percentile CI on `mean(values)`."""
    if not values:
        raise EmptyTradesError("block_bootstrap_confidence_interval requires at least one value")
    if not 0 < block_size <= len(values):
        raise InvalidModelParametersError(
            f"block_size must be in (0, len(values)={len(values)}], got {block_size}"
        )
    if not 0.0 < confidence < 1.0:
        raise InvalidModelParametersError(f"confidence must be in (0, 1), got {confidence}")
    if n_resamples <= 0:
        raise InvalidModelParametersError(f"n_resamples must be > 0, got {n_resamples}")

    array = np.asarray(values, dtype=float)
    n = array.size
    max_start = n - block_size
    n_blocks_needed = -(-n // block_size)  # ceil division: enough blocks to cover length n
    rng = np.random.default_rng(seed)

    resampled_means = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        block_starts = rng.integers(0, max_start + 1, size=n_blocks_needed)
        resample = np.concatenate([array[start : start + block_size] for start in block_starts])
        resampled_means[i] = resample[:n].mean()

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
