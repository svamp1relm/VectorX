"""block_bootstrap_confidence_interval: moving-block bootstrap CI (Фаза 21).

Resamples contiguous blocks of `block_size` consecutive trades (with
replacement), preserving any autocorrelation between consecutive trades —
unlike `vectorx.statistics.confidence.bootstrap_confidence_interval`'s i.i.d.
per-trade resampling. Used to test whether a result is robust to the
sequential structure of the realized trade sequence, not just its marginal
distribution.
"""

import pytest

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.robustness.block_bootstrap import block_bootstrap_confidence_interval


def test_point_estimate_is_the_sample_mean():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    result = block_bootstrap_confidence_interval(values, block_size=2, seed=1)

    assert result.point_estimate == pytest.approx(3.5)


def test_confidence_interval_brackets_the_point_estimate():
    values = [-1.0, 2.0, -1.0, 2.0, 3.0, -2.0, 1.5, -0.5]

    result = block_bootstrap_confidence_interval(values, block_size=2, seed=1)

    assert result.lower <= result.point_estimate <= result.upper


def test_same_seed_is_reproducible():
    values = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0]

    result_a = block_bootstrap_confidence_interval(values, block_size=2, seed=42)
    result_b = block_bootstrap_confidence_interval(values, block_size=2, seed=42)

    assert result_a == result_b


def test_different_seed_diverges():
    values = [1.0, -1.3, 2.7, -2.1, 3.4, 0.6, -0.9, 1.8, -1.6, 2.2, 0.3, -2.8]

    result_a = block_bootstrap_confidence_interval(values, block_size=3, seed=1)
    result_b = block_bootstrap_confidence_interval(values, block_size=3, seed=2)

    assert (result_a.lower, result_a.upper) != (result_b.lower, result_b.upper)


def test_block_size_of_one_behaves_like_iid_bootstrap_bounds_shape():
    values = [1.0, -1.0, 2.0, -2.0, 3.0]

    result = block_bootstrap_confidence_interval(values, block_size=1, seed=1)

    assert result.lower <= result.point_estimate <= result.upper


def test_rejects_empty_values():
    with pytest.raises(EmptyTradesError):
        block_bootstrap_confidence_interval([], block_size=1, seed=1)


def test_rejects_block_size_out_of_bounds():
    with pytest.raises(InvalidModelParametersError):
        block_bootstrap_confidence_interval([1.0, 2.0], block_size=0, seed=1)
    with pytest.raises(InvalidModelParametersError):
        block_bootstrap_confidence_interval([1.0, 2.0], block_size=3, seed=1)


def test_rejects_confidence_out_of_bounds():
    with pytest.raises(InvalidModelParametersError):
        block_bootstrap_confidence_interval([1.0, 2.0], block_size=1, seed=1, confidence=0.0)


def test_rejects_non_positive_n_resamples():
    with pytest.raises(InvalidModelParametersError):
        block_bootstrap_confidence_interval([1.0, 2.0], block_size=1, seed=1, n_resamples=0)
