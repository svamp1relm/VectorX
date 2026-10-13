"""significance_vs_zero / significance_vs_benchmark: bootstrap significance
tests over sample R-multiples (Фаза 19). "Significant" means the resampled
CI excludes the null value — not a p-value, but the same percentile
bootstrap already used by `bootstrap_confidence_interval`.
"""

import pytest

from vectorx.core.errors import EmptyTradesError
from vectorx.statistics.significance import significance_vs_benchmark, significance_vs_zero


def test_significance_vs_zero_is_significant_for_a_clearly_positive_constant_sample():
    result = significance_vs_zero([2.0] * 20, seed=1)

    assert result.significant is True
    assert result.ci.lower > 0.0


def test_significance_vs_zero_is_not_significant_when_ci_includes_zero():
    result = significance_vs_zero([-1.0, 1.0, -1.0, 1.0], seed=1)

    assert result.significant is False


def test_significance_vs_zero_rejects_empty_sample():
    with pytest.raises(EmptyTradesError):
        significance_vs_zero([], seed=1)


def test_significance_vs_benchmark_is_significant_for_clearly_different_samples():
    result = significance_vs_benchmark([5.0] * 20, [0.0] * 20, seed=1)

    assert result.significant is True
    assert result.ci.lower > 0.0


def test_significance_vs_benchmark_is_not_significant_for_identical_samples():
    sample = [1.0, -1.0, 2.0, -2.0, 1.5, -1.5]

    result = significance_vs_benchmark(sample, sample, seed=1)

    assert result.significant is False


def test_significance_vs_benchmark_rejects_empty_samples():
    with pytest.raises(EmptyTradesError):
        significance_vs_benchmark([], [1.0], seed=1)
    with pytest.raises(EmptyTradesError):
        significance_vs_benchmark([1.0], [], seed=1)
