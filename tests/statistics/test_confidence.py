"""bootstrap_confidence_interval: percentile bootstrap CI on a sample mean
(Фаза 19). Deterministic given the same `values`/`seed`/`confidence`/
`n_resamples` — required for reproducible research (see
`vectorx.statistics.versioning.ANALYSIS_VERSION`).
"""

import pytest

from vectorx.core.errors import EmptyTradesError, InvalidModelParametersError
from vectorx.statistics.confidence import bootstrap_confidence_interval


def test_point_estimate_is_the_sample_mean():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]

    result = bootstrap_confidence_interval(values, seed=1)

    assert result.point_estimate == pytest.approx(3.0)


def test_confidence_interval_brackets_the_point_estimate():
    values = [-1.0, 2.0, -1.0, 2.0, 3.0, -2.0, 1.5]

    result = bootstrap_confidence_interval(values, seed=1)

    assert result.lower <= result.point_estimate <= result.upper


def test_single_value_gives_a_degenerate_interval_equal_to_that_value():
    result = bootstrap_confidence_interval([2.0], seed=1)

    assert result.point_estimate == pytest.approx(2.0)
    assert result.lower == pytest.approx(2.0)
    assert result.upper == pytest.approx(2.0)


def test_same_seed_is_reproducible():
    values = [1.0, -1.0, 2.0, -2.0, 3.0]

    result_a = bootstrap_confidence_interval(values, seed=42)
    result_b = bootstrap_confidence_interval(values, seed=42)

    assert result_a == result_b


def test_different_seed_diverges():
    values = [1.0, -1.3, 2.7, -2.1, 3.4, 0.6, -0.9, 1.8, -1.6, 2.2, 0.3, -2.8]

    result_a = bootstrap_confidence_interval(values, seed=1)
    result_b = bootstrap_confidence_interval(values, seed=2)

    assert (result_a.lower, result_a.upper) != (result_b.lower, result_b.upper)


def test_wider_confidence_level_gives_a_wider_interval():
    values = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0]

    narrow = bootstrap_confidence_interval(values, seed=1, confidence=0.80)
    wide = bootstrap_confidence_interval(values, seed=1, confidence=0.99)

    assert (wide.upper - wide.lower) >= (narrow.upper - narrow.lower)


def test_rejects_empty_values():
    with pytest.raises(EmptyTradesError):
        bootstrap_confidence_interval([], seed=1)


def test_rejects_confidence_out_of_bounds():
    with pytest.raises(InvalidModelParametersError):
        bootstrap_confidence_interval([1.0], seed=1, confidence=0.0)
    with pytest.raises(InvalidModelParametersError):
        bootstrap_confidence_interval([1.0], seed=1, confidence=1.0)


def test_rejects_non_positive_n_resamples():
    with pytest.raises(InvalidModelParametersError):
        bootstrap_confidence_interval([1.0], seed=1, n_resamples=0)
