"""Moving-block bootstrap that preserves sequential and run boundaries."""

from collections.abc import Sequence

import numpy as np

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.statistics.confidence import ConfidenceInterval


def _validate_inputs(
    run_values: Sequence[Sequence[float]],
    *,
    block_size: int,
    confidence: float,
    n_resamples: int,
) -> None:
    if not run_values or any(not values for values in run_values):
        raise EmptyTradesError("block bootstrap requires at least one value per run")
    if any(block_size <= 0 or block_size > len(values) for values in run_values):
        lengths = [len(values) for values in run_values]
        raise InvalidModelParametersError(
            f"block_size must be positive and fit every run, lengths={lengths}, got {block_size}"
        )
    if not 0.0 < confidence < 1.0:
        raise InvalidModelParametersError(f"confidence must be in (0, 1), got {confidence}")
    if n_resamples <= 0:
        raise InvalidModelParametersError(f"n_resamples must be > 0, got {n_resamples}")


def _moving_block_mean(
    values: np.ndarray,
    *,
    block_size: int,
    rng: np.random.Generator,
) -> float:
    n = values.size
    n_blocks_needed = -(-n // block_size)
    starts = rng.integers(0, n - block_size + 1, size=n_blocks_needed)
    sampled = np.concatenate([values[start : start + block_size] for start in starts])
    return float(sampled[:n].mean())


def _interval(
    arrays: tuple[np.ndarray, ...],
    *,
    block_size: int,
    seed: int,
    confidence: float,
    n_resamples: int,
) -> ConfidenceInterval:
    rng = np.random.default_rng(seed)
    total_size = sum(array.size for array in arrays)
    point_estimate = sum(float(array.sum()) for array in arrays) / total_size
    resampled_means = np.empty(n_resamples, dtype=float)
    for index in range(n_resamples):
        resampled_mean = sum(
            _moving_block_mean(array, block_size=block_size, rng=rng) * array.size
            for array in arrays
        ) / total_size
        resampled_means[index] = resampled_mean

    alpha = 1.0 - confidence
    return ConfidenceInterval(
        point_estimate=point_estimate,
        lower=float(np.quantile(resampled_means, alpha / 2.0)),
        upper=float(np.quantile(resampled_means, 1.0 - alpha / 2.0)),
        confidence=confidence,
        n_resamples=n_resamples,
    )


def block_bootstrap_confidence_interval(
    values: Sequence[float],
    *,
    block_size: int,
    seed: int,
    confidence: float = 0.95,
    n_resamples: int = 2000,
) -> ConfidenceInterval:
    """Moving-block bootstrap percentile CI on `mean(values)`."""
    _validate_inputs(
        [values],
        block_size=block_size,
        confidence=confidence,
        n_resamples=n_resamples,
    )
    return _interval(
        (np.asarray(values, dtype=float),),
        block_size=block_size,
        seed=seed,
        confidence=confidence,
        n_resamples=n_resamples,
    )


def block_bootstrap_confidence_interval_by_run(
    run_values: Sequence[Sequence[float]],
    *,
    block_size: int,
    seed: int,
    confidence: float = 0.95,
    n_resamples: int = 2000,
) -> ConfidenceInterval:
    """Pool independently resampled runs without creating cross-run blocks."""
    _validate_inputs(
        run_values,
        block_size=block_size,
        confidence=confidence,
        n_resamples=n_resamples,
    )
    arrays = tuple(np.asarray(values, dtype=float) for values in run_values)
    return _interval(
        arrays,
        block_size=block_size,
        seed=seed,
        confidence=confidence,
        n_resamples=n_resamples,
    )
